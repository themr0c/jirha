"""Release notes checklist: publication-section view with validation."""

from jirha.config import SERVER

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

    counts_str = ", ".join(count_parts)
    header = f"\n{number}. {title} ({total}, {counts_str})"
    if not_closed > 0:
        header += f" [{not_closed} not closed]"
    return header
