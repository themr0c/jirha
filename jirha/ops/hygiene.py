"""Hygiene check command: missing metadata and SP reassessment."""

import re
from collections import Counter

from jirha.api import (
    REVIEW_FILTER,
    SP_TIERS,
    _assess_pr_sp,
    _assignee_filter,
    _assignee_name,
    _issue_sp,
    _warn_in_progress_no_sprint,
    get_jira,
)
from jirha.config import (
    CF_GIT_PR,
    CF_STORY_POINTS,
    DEFAULT_COMPONENT,
    SERVER,
)


def _print_hygiene_report(issue_gaps, team=False):
    """Print hygiene report for issues with missing metadata."""
    if not issue_gaps:
        print("All issues have complete metadata.")
        return
    sorted_issues = sorted(issue_gaps.values(), key=lambda x: -len(x["missing"]))
    print(f"Found {len(sorted_issues)} issues with incomplete metadata:\n")
    for entry in sorted_issues:
        issue = entry["issue"]
        missing = entry["missing"]
        sp = _issue_sp(issue)
        sp_str = f" {int(sp)}SP" if sp else ""
        priority = getattr(issue.fields, "priority", None) or "unset"
        components = ", ".join(c.name for c in (issue.fields.components or [])) or "none"
        assignee_str = ""
        if team:
            assignee_str = f" @{_assignee_name(issue)}"
        summary = issue.fields.summary
        print(f"{issue.key}{sp_str}{assignee_str} [{issue.fields.status}] [{priority}] — {summary}")
        print(f"  {SERVER}/browse/{issue.key}")
        print(f"  Components: {components}")
        print(f"  Missing: {', '.join(missing)}")
        print()

    gap_counts = Counter(m for e in sorted_issues for m in e["missing"])
    print("Summary:")
    for gap, count in gap_counts.most_common():
        print(f"  {gap}: {count} issues")
    print(f"  Total: {len(sorted_issues)} issues need attention")


def _find_sp_mismatches(jira, scope, max_results):
    """Scan issues for SP mismatches against linked PRs.

    Returns (mismatches, confirmed, skipped).
    """
    sp_issues = jira.search_issues(
        f'{scope} AND sprint in openSprints() AND "Story Points" is not EMPTY'
        f"{REVIEW_FILTER}",
        maxResults=max_results,
        fields=f"summary,status,assignee,{CF_STORY_POINTS},{CF_GIT_PR}",
    )

    mismatches, confirmed, skipped = [], 0, 0
    for issue in sp_issues:
        pr_url = getattr(issue.fields, CF_GIT_PR, None)
        if not pr_url:
            skipped += 1
            continue
        current_sp = int(_issue_sp(issue))
        if current_sp not in SP_TIERS:
            skipped += 1
            continue
        result = _assess_pr_sp(pr_url)
        if not result:
            skipped += 1
            continue
        suggested_sp, reason, pr_number = result
        if abs(SP_TIERS[current_sp] - SP_TIERS[suggested_sp]) >= 2:
            mismatches.append(
                {
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "current_sp": current_sp,
                    "suggested_sp": suggested_sp,
                    "reason": reason,
                    "pr_url": pr_url,
                    "pr_number": pr_number,
                    "assignee": _assignee_name(issue),
                }
            )
        else:
            confirmed += 1
    return mismatches, confirmed, skipped


def _parse_sp_choice(choice, mismatches):
    """Parse user choice for SP reassessment. Returns (apply_indices, overrides)."""
    if choice in ("a", "all"):
        return set(range(len(mismatches))), {}
    apply_indices = set()
    overrides = {}
    for part in choice.split(","):
        part = part.strip()
        m = re.match(r"(\d+)=(\d+)", part)
        if m:
            idx, sp_val = int(m.group(1)) - 1, int(m.group(2))
            if sp_val in SP_TIERS and 0 <= idx < len(mismatches):
                apply_indices.add(idx)
                overrides[idx] = sp_val
        elif part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(mismatches):
                apply_indices.add(idx)
    return apply_indices, overrides


def _sp_reassessment(jira, scope, max_results, team=False, dry_run=False):
    """Reassess story points from linked PRs and optionally apply changes."""
    print("\n## SP Reassessment (from PRs)\n")
    mismatches, confirmed, skipped = _find_sp_mismatches(jira, scope, max_results)

    if not mismatches:
        print(f"No SP mismatches found. ({confirmed} confirmed, {skipped} skipped/no PR)")
        return

    print("### Mismatches found:\n")
    for i, m in enumerate(mismatches, 1):
        assignee_str = f" @{m['assignee']}" if team else ""
        print(
            f"{i}. {m['key']} {m['current_sp']}SP → suggested {m['suggested_sp']}SP{assignee_str}"
        )
        print(f"   {m['reason']}")
        print(f"   {SERVER}/browse/{m['key']}")
        print(f"   {m['pr_url']}")
        print()
    print(f"({confirmed} confirmed, {skipped} skipped/no PR)\n")

    if dry_run:
        return

    try:
        choice = (
            input("Apply changes? [a]ll / [n]one / [1,2,...] individual / [1=5] override: ")
            .strip()
            .lower()
        )
    except (EOFError, KeyboardInterrupt):
        print("\nSkipped.")
        return
    if not choice or choice in ("n", "none"):
        print("No changes applied.")
        return

    apply_indices, overrides = _parse_sp_choice(choice, mismatches)
    for idx in sorted(apply_indices):
        m = mismatches[idx]
        new_sp = overrides.get(idx, m["suggested_sp"])
        comment = f"SP reassessed from PR #{m['pr_number']}: {m['reason']}"
        jira.issue(m["key"]).update(fields={CF_STORY_POINTS: float(new_sp)})
        jira.add_comment(m["key"], f"Updated SP: {m['current_sp']} → {new_sp}\n\n{comment}")
        print(f"  → {m['key']}: {m['current_sp']}SP → {new_sp}SP")
    print(f"\nApplied {len(apply_indices)} change(s).")


def cmd_hygiene(args):
    """List all issues with missing metadata and summarize what needs fixing."""
    jira = get_jira()
    scope = _assignee_filter(args.team)
    base = f"{scope} AND status not in (Closed, Resolved){REVIEW_FILTER}"
    fields_base = f"summary,status,priority,assignee,components,{CF_STORY_POINTS}"
    checks = [
        (
            "component",
            f'{base} AND component not in ({DEFAULT_COMPONENT}, "AEM Migration")',
            fields_base,
        ),
        ("team", f"{base} AND Team is EMPTY", fields_base),
        ("priority", f"{base} AND priority is EMPTY", fields_base),
        (
            "SP",
            f'{base} AND "Story Points" is EMPTY AND priority != Undefined '
            f"AND type not in (Epic, Feature)",
            f"{fields_base},issuetype",
        ),
        ("description", f"{base} AND description is EMPTY", fields_base),
    ]

    issue_gaps = {}
    for gap_name, jql, fields in checks:
        issues = jira.search_issues(jql, maxResults=args.max, fields=fields)
        for issue in issues:
            if issue.key not in issue_gaps:
                issue_gaps[issue.key] = {"issue": issue, "missing": []}
            issue_gaps[issue.key]["missing"].append(gap_name)

    _warn_in_progress_no_sprint(jira, args.team)
    _print_hygiene_report(issue_gaps, args.team)

    if args.check_sp:
        _sp_reassessment(jira, scope, args.max, args.team, args.dry_run)
