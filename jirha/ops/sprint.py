"""Sprint status command: swimlane assignment, velocity, risk assessment."""

from datetime import date, timedelta

from jirha.api import (
    _REVIEW_SUMMARIES,
    _assignee_filter,
    _assignee_name,
    _issue_sp,
    _parse_jira_date,
    _status_sort_key,
    _warn_in_progress_no_sprint,
    get_jira,
)
from jirha.config import CF_SPRINT, CF_STORY_POINTS, DEFAULT_COMPONENT, SWIMLANES


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


def _get_active_sprint(jira):
    """Return active sprint info dict or None."""
    issues = jira.search_issues(
        "assignee = currentUser() AND sprint in openSprints()", maxResults=1, fields=CF_SPRINT
    )
    if not issues:
        return None
    sprint_data = getattr(issues[0].fields, CF_SPRINT, None) or []
    for s in sprint_data:
        if getattr(s, "state", "") == "active":
            start = _parse_jira_date(s.startDate)
            end = _parse_jira_date(s.endDate)
            today = date.today()
            return {
                "id": s.id,
                "name": s.name,
                "start": start,
                "end": end,
                "board_id": getattr(s, "boardId", None),
                "remaining_days": _business_days(today, end),
                "total_days": _business_days(start, end),
            }
    return None


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


def _format_issue_line(issue, team=False):
    """Format a single issue as a markdown list item."""
    sp = _issue_sp(issue)
    sp_str = f" {int(sp)}SP" if sp else ""
    labels = issue.fields.labels or []
    label_str = f" [{', '.join(labels)}]" if labels else ""
    assignee_str = f" @{_assignee_name(issue)}" if team else ""
    return f"- {issue.key}{sp_str}{assignee_str}{label_str} — {issue.fields.summary}"


def _print_swimlanes(swimlane_issues, team=False):
    """Print swimlane sections and return (total_by_status, sp_by_status) dicts."""
    total_by_status = {}
    sp_by_status = {}
    for name, _ in SWIMLANES:
        lane_issues = swimlane_issues[name]
        if not lane_issues:
            continue
        lane_total_sp = sum(_issue_sp(i) for i in lane_issues)
        lane_closed_sp = sum(_issue_sp(i) for i in lane_issues if str(i.fields.status) == "Closed")
        lane_pct = (lane_closed_sp / lane_total_sp * 100) if lane_total_sp else 0
        print(f"\n## {name} — {int(lane_closed_sp)}/{int(lane_total_sp)} SP ({lane_pct:.0f}%)\n")

        by_status = {}
        for issue in lane_issues:
            status = str(issue.fields.status)
            by_status.setdefault(status, []).append(issue)

        for status in sorted(by_status.keys(), key=_status_sort_key):
            print(f"### {status}")
            for issue in by_status[status]:
                print(_format_issue_line(issue, team))
                total_by_status[status] = total_by_status.get(status, 0) + 1
                sp_by_status[status] = sp_by_status.get(status, 0) + _issue_sp(issue)
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


def cmd_sprint_status(args):
    """Show sprint status grouped by priority swimlanes."""
    jira = get_jira()
    issues = jira.search_issues(
        f"{_assignee_filter(args.team)} AND sprint in openSprints() ORDER BY status ASC",
        maxResults=200,
        fields=f"summary,status,priority,labels,issuetype,components,assignee,"
        f"{CF_STORY_POINTS},{CF_SPRINT}",
    )

    sprint = _get_active_sprint(jira)
    if sprint:
        print(f"# {sprint['name']}")
        print(
            f"**Dates:** {sprint['start']} → {sprint['end']}  "
            f"**Working days:** {sprint['remaining_days']} remaining / {sprint['total_days']} total"
        )

    swimlane_issues = _assign_swimlanes(issues)
    total_by_status, sp_by_status = _print_swimlanes(swimlane_issues, args.team)

    total_sp = sum(sp_by_status.values())
    closed_sp = sp_by_status.get("Closed", 0)
    pct = (closed_sp / total_sp * 100) if total_sp else 0
    parts = ", ".join(
        f"{c} {s}" for s, c in sorted(total_by_status.items(), key=lambda x: _status_sort_key(x[0]))
    )
    sp_parts = ", ".join(
        f"{int(sp)} {s}"
        for s, sp in sorted(sp_by_status.items(), key=lambda x: _status_sort_key(x[0]))
        if sp
    )
    print(f"**Total:** {sum(total_by_status.values())} issues — {parts}")
    print(f"**SP:** {int(total_sp)} total — {sp_parts}")
    print(f"**Progress:** {int(closed_sp)}/{int(total_sp)} SP ({pct:.0f}%)")

    _print_risk_assessment(jira, sprint, closed_sp, total_sp - closed_sp, swimlane_issues)
    _warn_in_progress_no_sprint(jira, args.team)
