"""Sprint status command: swimlane assignment, velocity, risk assessment."""

from datetime import date, timedelta

from jirha.api import (
    _REVIEW_SUMMARIES,
    _assignee_filter,
    _assignee_name,
    _checklist_items,
    _fetch_pr_checklists,
    _fetch_reviewer_prs,
    _format_pr_checklist,
    _issue_sp,
    _parse_jira_date,
    _status_sort_key,
    _warn_in_progress_no_sprint,
    get_jira,
    get_sprint_info,
)
from jirha.config import (
    CF_GIT_PR,
    CF_SPRINT,
    CF_STORY_POINTS,
    DEFAULT_COMPONENT,
    SERVER,
    SWIMLANES,
)


def _assign_swimlanes(issues):
    """Assign each issue to its first matching swimlane. Returns dict of name -> issue list."""
    result = {name: [] for name, _ in SWIMLANES}
    for issue in issues:
        for name, match_fn in SWIMLANES:
            if match_fn(issue):
                result[name].append(issue)
                break
    return result


def _business_days(start, end):
    """Count weekdays (Mon-Fri) between two dates, inclusive of end."""
    return sum(
        1 for i in range((end - start).days + 1) if (start + timedelta(days=i)).weekday() < 5
    )


def _blended_velocity(hist_velocities, current_velocity, elapsed_days, total_days):
    """Blend historical and current velocity, weighted by sprint progress."""
    if not hist_velocities:
        return current_velocity
    hist_avg = sum(v for _, _, _, v in hist_velocities) / len(hist_velocities)
    elapsed_pct = elapsed_days / total_days if total_days else 0
    if elapsed_pct < 0.25:
        return 0.9 * hist_avg + 0.1 * current_velocity
    elif elapsed_pct < 0.5:
        return 0.7 * hist_avg + 0.3 * current_velocity
    else:
        return 0.4 * hist_avg + 0.6 * current_velocity


def _enrich_sprint(sprint_dict):
    """Add remaining_days and total_days to a sprint dict with ISO date strings."""
    if not sprint_dict:
        return None
    start = date.fromisoformat(sprint_dict["start"])
    end = date.fromisoformat(sprint_dict["end"])
    today = date.today()
    return {
        **sprint_dict,
        "remaining_days": _business_days(today, end),
        "total_days": _business_days(start, end),
    }


def _historical_velocities(jira, board_id):
    """Return list of (name, closed_sp, days, velocity) for last 3 Documentation sprints."""
    if not board_id:
        return []
    try:
        closed_sprints = jira.sprints(board_id, state="closed")
        doc_sprints = [s for s in closed_sprints if DEFAULT_COMPONENT in s.name][-3:]
        result = []
        for s in doc_sprints:
            s_start = _parse_jira_date(s.startDate)
            s_end = _parse_jira_date(s.endDate)
            s_days = _business_days(s_start, s_end)
            s_issues = jira.search_issues(
                f"assignee = currentUser() AND sprint = {s.id} AND status = Closed",
                maxResults=200,
                fields=CF_STORY_POINTS,
            )
            s_closed_sp = sum(_issue_sp(i) for i in s_issues)
            s_vel = s_closed_sp / s_days if s_days else 0
            result.append((s.name, int(s_closed_sp), s_days, s_vel))
        return result
    except Exception:
        return []


def _format_issue_line(issue, team=False, pr_status=None, pr_checklist=None):
    """Format an issue as a pipe-separated line with optional PR checklist."""
    sp = _issue_sp(issue)
    sp_str = f"{int(sp):>2} SP"
    labels = ", ".join(issue.fields.labels or [])
    priority = str(issue.fields.priority)
    assignee_str = f" @{_assignee_name(issue)}" if team else ""
    checkbox = "[x]" if str(issue.fields.status) == "Closed" else "[ ]"
    parts = [
        f"- {checkbox} {SERVER}/browse/{issue.key}",
        priority,
        sp_str,
        labels,
        f"{issue.fields.summary}{assignee_str}",
    ]
    if pr_status:
        parts.append(pr_status)
    line = " | ".join(parts)

    if pr_checklist and str(issue.fields.status) != "Closed":
        items = _checklist_items(pr_checklist)
        for item in items:
            line += f"\n        [ ] {item}"

    return line


def _print_swimlanes(
    swimlane_issues, team=False, pr_statuses=None, pr_checklists=None,
    open_only=False,
):
    """Print swimlane sections and return (total_by_status, sp_by_status) dicts."""
    if pr_statuses is None:
        pr_statuses = {}
    if pr_checklists is None:
        pr_checklists = {}
    total_by_status = {}
    sp_by_status = {}
    for name, _ in SWIMLANES:
        lane_issues = swimlane_issues[name]
        if not lane_issues:
            continue
        lane_total_sp = sum(_issue_sp(i) for i in lane_issues)
        lane_closed_sp = sum(
            _issue_sp(i) for i in lane_issues
            if str(i.fields.status) == "Closed"
        )
        lane_pct = (lane_closed_sp / lane_total_sp * 100) if lane_total_sp else 0
        print(f"\n## {name} — {int(lane_closed_sp)}/{int(lane_total_sp)} SP ({lane_pct:.0f}%)\n")

        by_status = {}
        for issue in lane_issues:
            status = str(issue.fields.status)
            by_status.setdefault(status, []).append(issue)

        for status in sorted(by_status.keys(), key=_status_sort_key):
            count = len(by_status[status])
            sp = sum(_issue_sp(i) for i in by_status[status])
            total_by_status[status] = total_by_status.get(status, 0) + count
            sp_by_status[status] = sp_by_status.get(status, 0) + sp
            if open_only and status == "Closed":
                print(f"### Closed | {count} issues | {int(sp)} SP\n")
                continue
            print(f"### {status}")
            for issue in by_status[status]:
                pr = pr_statuses.get(issue.key)
                cl = pr_checklists.get(issue.key)
                print(_format_issue_line(issue, team, pr_status=pr, pr_checklist=cl))
            print()
    return total_by_status, sp_by_status


def _drop_candidates(swimlane_issues):
    """Return candidate issues to drop, sorted by priority (lowest first) then status."""
    candidates = []
    for name, _ in reversed(SWIMLANES):
        for issue in swimlane_issues[name]:
            if str(issue.fields.status) == "Closed":
                continue
            summary = issue.fields.summary or ""
            if any(r in summary for r in _REVIEW_SUMMARIES):
                continue
            sp = _issue_sp(issue)
            candidates.append((_status_sort_key(str(issue.fields.status)), name, issue, sp))
    candidates.sort(key=lambda x: x[0])
    return candidates


def _print_risk_assessment(jira, sprint, closed_sp, remaining_sp, swimlane_issues):
    """Print risk assessment section."""
    if not sprint or not sprint["remaining_days"] or remaining_sp <= 0:
        return
    remaining_days = sprint["remaining_days"]
    total_days = sprint["total_days"]
    elapsed_days = total_days - remaining_days
    current_velocity = closed_sp / elapsed_days if elapsed_days > 0 else 0

    hist_velocities = _historical_velocities(jira, sprint.get("board_id"))
    velocity = _blended_velocity(hist_velocities, current_velocity, elapsed_days, total_days)
    projected_sp = velocity * remaining_days
    shortfall = remaining_sp - projected_sp

    print("\n## Risk Assessment")
    print(
        f"**Current sprint velocity:** {current_velocity:.1f} SP/day "
        f"({int(closed_sp)} SP in {elapsed_days} days)"
    )
    if hist_velocities:
        hist_avg = sum(v for _, _, _, v in hist_velocities) / len(hist_velocities)
        print("**Historical velocity (last 3 sprints):**")
        for name, sp, days, vel in hist_velocities:
            print(f"  - {name}: {sp} SP in {days} days = {vel:.1f} SP/day")
        print(f"  - Average: {hist_avg:.1f} SP/day")
    print(f"**Blended velocity:** {velocity:.1f} SP/day")
    print(f"**Projected:** {projected_sp:.0f} SP completable in {remaining_days} remaining days")

    if shortfall <= 0:
        print(
            f"**Status:** ON TRACK — projected to complete {int(projected_sp)} SP, "
            f"{int(remaining_sp)} SP remaining"
        )
        return

    print(
        f"**Status:** AT RISK — {int(shortfall)} SP shortfall "
        f"({int(remaining_sp)} SP remaining, ~{int(projected_sp)} SP projected)"
    )
    print(f"\n### Suggested issues to remove ({int(shortfall)}+ SP to cut):")
    cut_sp = 0
    for _, lane, issue, sp in _drop_candidates(swimlane_issues):
        if cut_sp >= shortfall:
            break
        sp_str = f" {int(sp)}SP" if sp else ""
        print(f"- {issue.key}{sp_str} [{lane}] [{issue.fields.status}] — {issue.fields.summary}")
        cut_sp += sp


def _print_reviewer_prs():
    """Print section for PRs where the current user is requested as reviewer."""
    prs = _fetch_reviewer_prs()
    if not prs:
        return
    print("\n## Pending Reviews\n")
    for pr in prs:
        repo = pr.get("repository", {}).get("nameWithOwner", "")
        number = pr.get("number", "")
        title = pr.get("title", "")
        url = pr.get("url", "")
        created = pr.get("createdAt", "")
        if created:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                days = (datetime.now(dt.tzinfo) - dt).days
                age = f" (opened {days}d ago)" if days > 0 else ""
            except (ValueError, TypeError):
                age = ""
        else:
            age = ""
        short = f"{repo}#{number}" if repo else url
        print(f"- [ ] {short} — \"{title}\"{age}")
        print(f"        {url}")


def _run_sprint_status(args, open_only=False):
    """Show sprint status grouped by priority swimlanes."""
    jira = get_jira()
    refresh = getattr(args, "refresh", False)
    issues = jira.search_issues(
        f"{_assignee_filter(args.team)} AND sprint in openSprints() ORDER BY status ASC",
        maxResults=200,
        fields=f"summary,status,priority,labels,issuetype,components,assignee,"
        f"{CF_STORY_POINTS},{CF_SPRINT},{CF_GIT_PR}",
    )

    sprint_info = get_sprint_info(jira, refresh=refresh)
    sprint = _enrich_sprint(sprint_info.get("current_sprint"))
    if sprint:
        print(f"# {sprint['name']}")
        print(
            f"**Dates:** {sprint['start']} → {sprint['end']}  "
            f"**Working days:** {sprint['remaining_days']} remaining / {sprint['total_days']} total"
        )

    swimlane_issues = _assign_swimlanes(issues)
    pr_checklists = _fetch_pr_checklists(issues)
    pr_statuses = {
        k: _format_pr_checklist(cl) for k, cl in pr_checklists.items()
    }
    total_by_status, sp_by_status = _print_swimlanes(
        swimlane_issues, args.team, pr_statuses,
        pr_checklists=pr_checklists, open_only=open_only,
    )

    total_sp = sum(sp_by_status.values())
    closed_sp = sp_by_status.get("Closed", 0)
    pct = (closed_sp / total_sp * 100) if total_sp else 0
    parts = ", ".join(
        f"{c} {s}"
        for s, c in sorted(
            total_by_status.items(), key=lambda x: _status_sort_key(x[0])
        )
    )
    sp_parts = ", ".join(
        f"{int(sp)} {s}"
        for s, sp in sorted(
            sp_by_status.items(), key=lambda x: _status_sort_key(x[0])
        )
        if sp
    )
    print(f"**Total:** {sum(total_by_status.values())} issues — {parts}")
    print(f"**SP:** {int(total_sp)} total — {sp_parts}")
    print(f"**Progress:** {int(closed_sp)}/{int(total_sp)} SP ({pct:.0f}%)")

    _print_risk_assessment(
        jira, sprint, closed_sp, total_sp - closed_sp, swimlane_issues
    )
    _warn_in_progress_no_sprint(jira, args.team)
    _print_reviewer_prs()


def cmd_sprint_status(args):
    """Show sprint status grouped by priority swimlanes."""
    _run_sprint_status(args, open_only=False)


def cmd_short_sprint_status(args):
    """Show sprint status with only open issues."""
    _run_sprint_status(args, open_only=True)
