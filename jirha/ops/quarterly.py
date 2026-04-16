"""Quarterly connections: gather resolved issues and output a structured report."""

import sys
from collections import defaultdict
from datetime import date, timedelta

from jirha.api import (
    _assignee_filter,
    _issue_sp,
    get_jira,
)
from jirha.config import (
    CF_GIT_PR,
    CF_SPRINT,
    CF_STORY_POINTS,
    EMAIL,
    JOB_PROFILE,
    SERVER,
)

# Quarter boundaries (month, day) for start of each quarter
_QUARTER_START = {
    "Q1": (1, 1),
    "Q2": (4, 1),
    "Q3": (7, 1),
    "Q4": (10, 1),
}

_FIELDS = (
    f"summary,status,issuetype,priority,components,labels,parent,resolution,"
    f"resolutiondate,reporter,{CF_STORY_POINTS},{CF_GIT_PR},{CF_SPRINT}"
)


def _quarter_range(quarter_str=None):
    """Return (start_date, end_date, label) for a quarter.

    quarter_str: "Q1-2026" format. If None, auto-detect previous quarter.
    Returns: (date, date, str) where end_date is exclusive (first day of next quarter).
    """
    if quarter_str:
        parts = quarter_str.upper().split("-")
        if len(parts) != 2 or parts[0] not in _QUARTER_START or not parts[1].isdigit():
            sys.exit(
                f"Error: invalid quarter format '{quarter_str}'. "
                "Use Q1-2026, Q2-2026, Q3-2026, or Q4-2026."
            )
        q, year = parts[0], int(parts[1])
    else:
        today = date.today()
        current_q = (today.month - 1) // 3 + 1
        if current_q == 1:
            q, year = "Q4", today.year - 1
        else:
            q, year = f"Q{current_q - 1}", today.year

    m, d = _QUARTER_START[q]
    start = date(year, m, d)
    q_num = int(q[1])
    if q_num == 4:
        end = date(year + 1, 1, 1)
    else:
        end_m, end_d = _QUARTER_START[f"Q{q_num + 1}"]
        end = date(year, end_m, end_d)

    label = f"{q}-{year}"
    return start, end, label


def _resolve_level(args_level):
    """Resolve job profile level from CLI arg or config. Returns int 1-5."""
    if args_level is not None:
        level = args_level
    else:
        raw = JOB_PROFILE.strip() if isinstance(JOB_PROFILE, str) else JOB_PROFILE
        if isinstance(raw, str):
            cleaned = raw.lower().replace("tw", "")
            if not cleaned.isdigit():
                sys.exit(f"Error: invalid JOB_PROFILE '{JOB_PROFILE}'. Use tw1-tw5 or 1-5.")
            level = int(cleaned)
        else:
            level = raw
    if level not in range(1, 6):
        sys.exit("Error: --level must be 1-5")
    return level


def _fetch_resolved_issues(jira, start, end):
    """Fetch all issues resolved in the date range by the current user."""
    jql = (
        f"{_assignee_filter(team=False)}"
        f' AND resolved >= "{start.strftime("%Y-%m-%d")}"'
        f' AND resolved < "{end.strftime("%Y-%m-%d")}"'
        f" ORDER BY resolved ASC"
    )
    return jira.search_issues(jql, maxResults=False, fields=_FIELDS)


_UNGROUPED = ("Ungrouped", "Issues without an epic")


def _extract_epic(issue, jira=None, _cache=None):
    """Extract epic key and summary from the issue's parent chain.

    Walks up the parent hierarchy to find the epic. For sub-tasks whose
    parent is a task (not an epic), fetches the parent to find the grandparent
    epic. Uses _cache dict to avoid redundant API calls.

    Returns (epic_key, epic_summary) or ("Ungrouped", "Issues without an epic").
    """
    parent = getattr(issue.fields, "parent", None)
    if not parent:
        return _UNGROUPED

    parent_type = str(getattr(parent.fields, "issuetype", ""))
    if parent_type == "Epic":
        return parent.key, str(getattr(parent.fields, "summary", parent.key))

    # Parent is a task/story — walk up to find the epic
    if jira and _cache is not None:
        if parent.key in _cache:
            return _cache[parent.key]
        try:
            parent_issue = jira.issue(parent.key, fields="parent,summary,issuetype")
            grandparent = getattr(parent_issue.fields, "parent", None)
            if grandparent:
                gp_summary = str(getattr(grandparent.fields, "summary", grandparent.key))
                result = (grandparent.key, gp_summary)
            else:
                # Parent has no epic — group under the parent itself
                result = (parent.key, str(getattr(parent.fields, "summary", parent.key)))
            _cache[parent.key] = result
            return result
        except Exception:
            pass

    # Fallback: use the direct parent
    return parent.key, str(getattr(parent.fields, "summary", parent.key))


def _group_issues(issues, jira=None):
    """Group issues by epic. Returns ordered dict.

    When jira client is provided, walks up parent chains for sub-tasks
    to find the correct epic grouping.
    """
    groups = {}
    epic_cache = {}
    for issue in issues:
        epic_key, epic_summary = _extract_epic(issue, jira=jira, _cache=epic_cache)
        if epic_key not in groups:
            groups[epic_key] = {"summary": epic_summary, "issues": []}
        groups[epic_key]["issues"].append(issue)
    return groups


def _is_self_reported(issue):
    """Return True if the current user is the reporter of this issue."""
    reporter = getattr(issue.fields, "reporter", None)
    if not reporter or not EMAIL:
        return False
    reporter_email = getattr(reporter, "emailAddress", None)
    return reporter_email == EMAIL


def _compute_stats(issues):
    """Compute aggregate stats for a list of issues."""
    total_sp = 0
    by_type = defaultdict(int)
    by_priority = defaultdict(int)
    components = set()
    labels = set()
    has_pr = 0
    self_reported = 0

    for issue in issues:
        sp = _issue_sp(issue)
        total_sp += sp
        by_type[str(issue.fields.issuetype)] += 1
        by_priority[str(issue.fields.priority)] += 1
        for c in issue.fields.components or []:
            components.add(c.name)
        for label in issue.fields.labels or []:
            labels.add(label)
        if getattr(issue.fields, CF_GIT_PR, None):
            has_pr += 1
        if _is_self_reported(issue):
            self_reported += 1

    return {
        "total_issues": len(issues),
        "total_sp": int(total_sp),
        "by_type": dict(by_type),
        "by_priority": dict(by_priority),
        "components": components,
        "labels": labels,
        "has_pr_count": has_pr,
        "self_reported": self_reported,
    }


def _print_report(label, start, end, level, groups, global_stats):
    """Print the quarterly report as structured markdown."""
    print(f"# Quarterly Activity Report \u2014 {label}")
    print(f"**Period:** {start} to {end - timedelta(days=1)}")
    print("**Scope:** Current user resolved issues")
    print(f"**Job profile level:** tw{level}\n")

    print("## Summary\n")
    print(f"- **Total issues resolved:** {global_stats['total_issues']}")
    print(f"- **Total story points:** {global_stats['total_sp']}")
    type_parts = ", ".join(
        f"{v} {k}" for k, v in sorted(global_stats["by_type"].items(), key=lambda x: -x[1])
    )
    print(f"- **By type:** {type_parts}")
    if global_stats["components"]:
        print(f"- **Components:** {', '.join(sorted(global_stats['components']))}")
    if global_stats["labels"]:
        top_labels = sorted(global_stats["labels"])[:15]
        print(f"- **Labels:** {', '.join(top_labels)}")
    print(f"- **Issues with linked PRs:** {global_stats['has_pr_count']}")
    if global_stats["self_reported"]:
        print(f"- **Self-reported issues:** {global_stats['self_reported']}")
    print()

    print("## Issues by Epic\n")
    for epic_key, group in groups.items():
        epic_issues = group["issues"]
        stats = _compute_stats(epic_issues)
        epic_url = f"{SERVER}/browse/{epic_key}" if epic_key != "Ungrouped" else ""
        header = f"### {group['summary']}"
        if epic_url:
            header += f" ({epic_url})"
        header += f" \u2014 {stats['total_issues']} issues, {stats['total_sp']} SP"
        print(header)
        print()
        for issue in epic_issues:
            sp = _issue_sp(issue)
            sp_str = f" [{int(sp)}SP]" if sp else ""
            labels = ", ".join(issue.fields.labels or [])
            label_str = f" ({labels})" if labels else ""
            pr = getattr(issue.fields, CF_GIT_PR, None)
            pr_str = ""
            if pr:
                first_pr = pr.strip().splitlines()[0].strip()
                pr_str = f" PR: {first_pr}"
            self_str = " [self-reported]" if _is_self_reported(issue) else ""
            print(
                f"- {SERVER}/browse/{issue.key}{sp_str}"
                f" [{issue.fields.issuetype}]"
                f" {issue.fields.summary}{label_str}{pr_str}{self_str}"
            )
        print()


def cmd_quarterly(args):
    """Generate quarterly activity report for connections review."""
    start, end, label = _quarter_range(args.quarter)
    level = _resolve_level(args.level)
    jira = get_jira()

    issues = _fetch_resolved_issues(jira, start, end)
    if not issues:
        print(f"No resolved issues found for {label} ({start} to {end}).")
        return

    groups = _group_issues(issues, jira=jira)
    global_stats = _compute_stats(issues)
    _print_report(label, start, end, level, groups, global_stats)
