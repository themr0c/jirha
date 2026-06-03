"""Release notes checklist: publication-section view with validation."""

import sys

from jirha.api import get_jira
from jirha.config import CF_RN_STATUS, CF_RN_TEXT, CF_RN_TYPE, SERVER

_SECTION_MAP = {
    "Feature": (1, "New features and enhancements"),
    "Enhancement": (1, "New features and enhancements"),
    "Technology Preview": (2, "Technology Preview features"),
    "Developer Preview": (3, "Developer Preview features"),
    "Deprecated Functionality": (4, "Deprecated features"),
    "Removed Functionality": (5, "Removed features"),
    "Known Issue": (6, "Known issues"),
    "Bug Fix": (7, "Fixed issues"),
}

_SECTION_TITLES = {
    1: "New features and enhancements",
    2: "Technology Preview features",
    3: "Developer Preview features",
    4: "Deprecated features",
    5: "Removed features",
    6: "Known issues",
    7: "Fixed issues",
}


def _classify_rn_bucket(rn_status, rn_type):
    """Classify an issue into one of: done, not_required, in_progress, proposed, empty."""
    if rn_type == "Release Notes Not Required":
        return "not_required"
    if rn_status == "Rejected":
        return "not_required"
    if rn_status == "Done" and rn_type:
        return "done"
    if rn_status == "In Progress":
        return "in_progress"
    if rn_status == "Proposed":
        return "proposed"
    return "empty"


def _map_to_section(rn_type):
    """Map an RN Type string to (section_number, section_title), or None if unclassified."""
    if not rn_type:
        return None
    return _SECTION_MAP.get(rn_type)


def _todo_text(bucket, classified):
    """Return the TODO string for a given bucket."""
    if bucket == "done" or bucket == "not_required":
        return ""
    if bucket == "proposed":
        return "TODO: Review draft proposed by SME"
    if bucket == "in_progress":
        return "TODO: Review RN text submitted by Docs team"
    if not classified:
        return "TODO: Set RN Type and RN Text"
    return "TODO: Author release notes"


def _check_violations(items, minor_version):
    """Find issues that are fixed in this release but typed as Known Issue."""
    violations = []
    for item in items:
        if item.get("rn_type") == "Known Issue" and item.get("from_query") == 1:
            violations.append(
                {
                    "key": item["key"],
                    "message": (
                        f"VIOLATION: Known Issue but fixed in {minor_version}"
                        " — will publish as KI instead of Bug Fix."
                        f" Duplicate: keep one as KI for prior release,"
                        f" use other as Bug Fix for {minor_version}"
                    ),
                }
            )
    return violations


def _check_deduplication(rhidp_issues):
    """Find RHIDP issues with RN text that should live on parent RHDHPLAN."""
    dupes = []
    for item in rhidp_issues:
        if item.get("rn_text"):
            parent = item["parent_key"]
            dupes.append(
                {
                    "key": item["key"],
                    "parent_key": parent,
                    "message": f"TODO: Move Release Note Text to parent feature {parent}",
                }
            )
    return dupes


def _check_warnings(items):
    """Find issues with security level set."""
    warnings = []
    for item in items:
        if item.get("security"):
            warnings.append(
                {
                    "key": item["key"],
                    "message": (
                        "WARNING: Security level set — remove restriction or"
                        " duplicate Jira and add RN to duplicate"
                    ),
                }
            )
    return warnings


def _format_item_line(key, bucket, todo, source_keys):
    """Format a single checklist line."""
    url = f"{SERVER}/browse/{key}"
    if bucket == "done":
        marker = "[x]"
    elif bucket == "not_required":
        marker = "[-]"
    else:
        marker = "[ ]"

    parts = [f"{marker} {url}"]
    if todo:
        parts.append(f"   {todo}")
    if source_keys:
        parts.append(f"  ← {', '.join(source_keys)}")
    return "".join(parts)


def _format_section_header(number, title, status_counts, total, not_closed):
    """Format a publication section header with counts."""
    if total == 0:
        return f"\n{number}. {title} (0)"

    count_parts = []
    for status in ("done", "proposed", "in_progress"):
        count = status_counts.get(status, 0)
        if count:
            label = status.replace("_", " ")
            count_parts.append(f"{count} {label}")

    if count_parts:
        header = f"\n{number}. {title} ({total}, {', '.join(count_parts)})"
    else:
        header = f"\n{number}. {title} ({total})"
    if not_closed > 0:
        header += f" [{not_closed} not closed]"
    return header


def _filter_versions(all_versions, minor_version):
    """Filter version objects matching '{minor}.x'. Returns sorted names."""
    prefix = f"{minor_version}."
    matching = [v.name for v in all_versions if v.name.startswith(prefix)]
    matching.sort()
    return matching


def _quoted_list(versions):
    """Build a quoted, comma-separated list for JQL IN clauses."""
    return ", ".join(f'"{v}"' for v in versions)


def _build_fix_version_jql(versions, mine_only):
    """Build JQL for Query 1: items fixed in this release."""
    jql = f"project in (RHDHBUGS, RHDHPLAN, RHIDP) AND fixVersion in ({_quoted_list(versions)})"
    if mine_only:
        jql += " AND assignee = currentUser()"
    return jql


def _build_known_issues_jql(versions, mine_only):
    """Build JQL for Query 2: known issues affecting this version, not fixed in it."""
    jql = (
        f"project in (RHDHBUGS, RHDHPLAN, RHIDP)"
        f' AND "Release Note Type" in ("Known Issue")'
        f" AND affectedVersion in ({_quoted_list(versions)})"
        f" AND (fixVersion NOT IN ({_quoted_list(versions)}) OR fixVersion is EMPTY)"
    )
    if mine_only:
        jql += " AND assignee = currentUser()"
    return jql


_RN_FIELDS = (
    f"summary,status,issuetype,parent,fixVersions,project,"
    f"{CF_RN_TEXT},{CF_RN_STATUS},{CF_RN_TYPE},security"
)


def _extract_rn_fields(issue):
    """Extract RN fields from a Jira issue into a plain dict."""
    f = issue.fields
    rn_status_field = getattr(f, CF_RN_STATUS, None)
    rn_type_field = getattr(f, CF_RN_TYPE, None)
    return {
        "key": issue.key,
        "summary": f.summary,
        "status": str(f.status),
        "project": f.project.key,
        "issuetype": str(f.issuetype),
        "rn_text": getattr(f, CF_RN_TEXT, None),
        "rn_status": str(rn_status_field) if rn_status_field else None,
        "rn_type": str(rn_type_field) if rn_type_field else None,
        "security": str(getattr(f, "security", None)) if getattr(f, "security", None) else None,
        "fix_versions": [v.name for v in (f.fixVersions or [])],
        "parent_key": getattr(f.parent, "key", None) if getattr(f, "parent", None) else None,
    }


def _resolve_and_group(jira, raw_items, minor_version):
    """Resolve RHIDP parents, deduplicate, classify, validate, and group by section.

    Returns (sections, unclassified, violations, deduplication, warnings) where
    sections is {section_num: {title, items, status_counts, total, not_closed}}.
    """
    rhidp_issues = []
    rn_targets = {}  # key -> {item, source_keys}

    for item in raw_items:
        if item["project"] == "RHIDP":
            parent_key = item["parent_key"]
            resolved_key = None
            if parent_key:
                parent = jira.issue(parent_key, fields=_RN_FIELDS)
                parent_item = _extract_rn_fields(parent)
                parent_item["from_query"] = item["from_query"]
                if parent_item["project"] == "RHIDP" and parent_item["parent_key"]:
                    grandparent = jira.issue(parent_item["parent_key"], fields=_RN_FIELDS)
                    grandparent_item = _extract_rn_fields(grandparent)
                    grandparent_item["from_query"] = item["from_query"]
                    resolved_key = grandparent_item["key"]
                    rn_targets.setdefault(
                        resolved_key, {"item": grandparent_item, "source_keys": []}
                    )
                else:
                    resolved_key = parent_item["key"]
                    rn_targets.setdefault(resolved_key, {"item": parent_item, "source_keys": []})
                rn_targets[resolved_key]["source_keys"].append(item["key"])

            rhidp_issues.append(
                {
                    "key": item["key"],
                    "rn_text": item["rn_text"],
                    "parent_key": resolved_key or parent_key,
                }
            )
        else:
            if item["key"] not in rn_targets:
                rn_targets[item["key"]] = {"item": item, "source_keys": []}

    all_items_for_validation = [entry["item"] for entry in rn_targets.values()]
    violations = _check_violations(all_items_for_validation, minor_version)
    deduplication = _check_deduplication(rhidp_issues)
    warnings = _check_warnings(all_items_for_validation)

    sections = {}
    unclassified = []

    for key, entry in rn_targets.items():
        item = entry["item"]
        rn_status = item.get("rn_status")
        rn_type = item.get("rn_type")

        bucket = _classify_rn_bucket(rn_status, rn_type)
        if bucket == "not_required":
            continue

        section_info = _map_to_section(rn_type)
        classified = section_info is not None

        todo = _todo_text(bucket, classified)
        is_closed = item.get("status") == "Closed"

        formatted = {
            "key": key,
            "bucket": bucket,
            "todo": todo,
            "source_keys": entry["source_keys"],
            "is_closed": is_closed,
            "fix_versions": item.get("fix_versions", []),
        }

        if not classified:
            unclassified.append(formatted)
        else:
            sec_num, sec_title = section_info
            if sec_num not in sections:
                sections[sec_num] = {
                    "title": sec_title,
                    "items": [],
                    "status_counts": {},
                    "total": 0,
                    "not_closed": 0,
                }
            sec = sections[sec_num]
            sec["items"].append(formatted)
            sec["total"] += 1
            sec["status_counts"][bucket] = sec["status_counts"].get(bucket, 0) + 1
            if not is_closed:
                sec["not_closed"] += 1

    return sections, unclassified, violations, deduplication, warnings


def cmd_release_notes(args):
    """Entry point for the release-notes CLI command."""
    jira = get_jira()
    minor = args.version
    mine_only = not args.all

    all_versions = jira.project_versions("RHDHBUGS")
    versions = _filter_versions(all_versions, minor)
    if not versions:
        sys.exit(f"No versions found matching {minor}.* in RHDHBUGS project.")

    print(f"Release Notes: RHDH {minor} (versions: {', '.join(versions)})", end="")

    jql1 = _build_fix_version_jql(versions, mine_only)
    jql2 = _build_known_issues_jql(versions, mine_only)

    issues1 = jira.search_issues(jql1, maxResults=args.max, fields=_RN_FIELDS)
    issues2 = jira.search_issues(jql2, maxResults=args.max, fields=_RN_FIELDS)

    seen_keys = set()
    raw_items = []
    for issue in issues1:
        item = _extract_rn_fields(issue)
        item["from_query"] = 1
        raw_items.append(item)
        seen_keys.add(issue.key)
    for issue in issues2:
        if issue.key not in seen_keys:
            item = _extract_rn_fields(issue)
            item["from_query"] = 2
            raw_items.append(item)

    sections, unclassified, violations, deduplication, warnings = _resolve_and_group(
        jira, raw_items, minor
    )

    action_count = len(unclassified) + len(violations) + len(deduplication)
    for sec in sections.values():
        action_count += sum(
            1 for it in sec["items"] if it["bucket"] not in ("done", "not_required")
        )
    print(f" — {action_count} need action\n")

    if unclassified:
        print(
            "── Unclassified ({}) — RN Type not set ───────────────────────────".format(
                len(unclassified)
            )
        )
        for item in unclassified:
            print(_format_item_line(item["key"], item["bucket"], item["todo"], item["source_keys"]))
        print()

    if violations:
        print("── VIOLATIONS ────────────────────────────────────────────────────")
        for v in violations:
            print(f"[!] {SERVER}/browse/{v['key']}  {v['message']}")
        print()

    if deduplication:
        print("── DEDUPLICATION ─────────────────────────────────────────────────")
        for d in deduplication:
            print(f"[!] {SERVER}/browse/{d['key']}  {d['message']}")
        print()

    if warnings:
        print("── WARNINGS ──────────────────────────────────────────────────────")
        for w in warnings:
            print(f"[!] {SERVER}/browse/{w['key']}  {w['message']}")
        print()

    for sec_num in range(1, 8):
        if sec_num in sections:
            sec = sections[sec_num]
            print(
                _format_section_header(
                    sec_num,
                    sec["title"],
                    sec["status_counts"],
                    sec["total"],
                    sec["not_closed"],
                )
            )
            if sec_num == 7:
                by_version = {}
                for item in sec["items"]:
                    for fv in item.get("fix_versions", []):
                        by_version.setdefault(fv, []).append(item)
                sub_idx = 1
                for fv in sorted(by_version.keys()):
                    sub_items = by_version[fv]
                    print(f"  7.{sub_idx}. Fixed issues in {fv} ({len(sub_items)})")
                    for item in sub_items:
                        line = _format_item_line(
                            item["key"], item["bucket"], item["todo"], item["source_keys"]
                        )
                        print(f"  {line}")
                    sub_idx += 1
            else:
                for item in sec["items"]:
                    print(
                        _format_item_line(
                            item["key"], item["bucket"], item["todo"], item["source_keys"]
                        )
                    )
        else:
            title = _SECTION_TITLES.get(sec_num, f"Section {sec_num}")
            print(f"\n{sec_num}. {title} (0)")
