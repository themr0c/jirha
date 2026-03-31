from datetime import date
from unittest.mock import MagicMock

import pytest

from jirha.ops.sprint import _assign_swimlanes, _blended_velocity, _business_days


def _make_issue(priority="Normal", labels=None, components=None, issuetype="Task", summary="Test"):
    """Build a mock Jira issue."""
    issue = MagicMock()
    issue.fields.priority = priority
    issue.fields.labels = labels or []
    comps = []
    for c in components or []:
        comp = MagicMock()
        comp.name = c
        comps.append(comp)
    issue.fields.components = comps
    issue.fields.issuetype = issuetype
    issue.fields.summary = summary
    return issue


class TestAssignSwimLanes:
    def test_blocker(self):
        issue = _make_issue(priority="Blocker")
        result = _assign_swimlanes([issue])
        assert issue in result["Blocker"]

    def test_aem_migration_by_label(self):
        issue = _make_issue(labels=["CQreview_pre-migration"])
        result = _assign_swimlanes([issue])
        assert issue in result["AEM migration"]

    def test_aem_migration_by_component(self):
        issue = _make_issue(components=["AEM Migration"])
        result = _assign_swimlanes([issue])
        assert issue in result["AEM migration"]

    def test_test_day(self):
        issue = _make_issue(labels=["test-day"])
        result = _assign_swimlanes([issue])
        assert issue in result["Test-day"]

    def test_rhdh_testday_label(self):
        issue = _make_issue(labels=["rhdh-testday"])
        result = _assign_swimlanes([issue])
        assert issue in result["Test-day"]

    def test_customer(self):
        issue = _make_issue(labels=["customer"])
        result = _assign_swimlanes([issue])
        assert issue in result["Customer"]

    def test_must_have(self):
        issue = _make_issue(labels=["must-have"])
        result = _assign_swimlanes([issue])
        assert issue in result["Must-have"]

    def test_nice_to_have(self):
        issue = _make_issue(labels=["nice-to-have"])
        result = _assign_swimlanes([issue])
        assert issue in result["Nice-to-have"]

    def test_critical_priority(self):
        issue = _make_issue(priority="Critical")
        result = _assign_swimlanes([issue])
        assert issue in result["Critical"]

    def test_review_subtask(self):
        issue = _make_issue(issuetype="Sub-task", summary="[DOC] Peer Review: something")
        result = _assign_swimlanes([issue])
        assert issue in result["Reviews"]

    def test_other_fallthrough(self):
        issue = _make_issue()
        result = _assign_swimlanes([issue])
        assert issue in result["Other"]

    def test_first_match_wins(self):
        issue = _make_issue(priority="Blocker", labels=["must-have"])
        result = _assign_swimlanes([issue])
        assert issue in result["Blocker"]
        assert issue not in result["Must-have"]

    def test_all_swimlanes_present_in_result(self):
        result = _assign_swimlanes([])
        expected = [
            "Blocker",
            "AEM migration",
            "Test-day",
            "Customer",
            "Must-have",
            "Nice-to-have",
            "Critical",
            "Doc sprint (lower priority)",
            "Reviews",
            "Other",
        ]
        assert list(result.keys()) == expected


class TestBusinessDays:
    def test_same_day_weekday(self):
        monday = date(2024, 3, 11)
        assert _business_days(monday, monday) == 1

    def test_full_week(self):
        monday = date(2024, 3, 11)
        friday = date(2024, 3, 15)
        assert _business_days(monday, friday) == 5

    def test_skips_weekend(self):
        friday = date(2024, 3, 15)
        monday = date(2024, 3, 18)
        assert _business_days(friday, monday) == 2

    def test_two_weeks(self):
        monday = date(2024, 3, 11)
        friday2 = date(2024, 3, 22)
        assert _business_days(monday, friday2) == 10


class TestBlendedVelocity:
    def test_no_history_returns_current(self):
        result = _blended_velocity([], current_velocity=5.0, elapsed_days=5, total_days=10)
        assert result == 5.0

    def test_early_sprint_weights_history_heavily(self):
        hist = [("Sprint 1", 50, 10, 5.0)]
        result = _blended_velocity(hist, current_velocity=10.0, elapsed_days=2, total_days=10)
        assert result == pytest.approx(0.9 * 5.0 + 0.1 * 10.0)

    def test_mid_sprint_balanced(self):
        hist = [("Sprint 1", 50, 10, 5.0)]
        result = _blended_velocity(hist, current_velocity=10.0, elapsed_days=3, total_days=10)
        assert result == pytest.approx(0.7 * 5.0 + 0.3 * 10.0)

    def test_late_sprint_weights_current(self):
        hist = [("Sprint 1", 50, 10, 5.0)]
        result = _blended_velocity(hist, current_velocity=10.0, elapsed_days=6, total_days=10)
        assert result == pytest.approx(0.4 * 5.0 + 0.6 * 10.0)

    def test_multiple_history_entries_averaged(self):
        hist = [("S1", 40, 10, 4.0), ("S2", 60, 10, 6.0)]
        result = _blended_velocity(hist, current_velocity=0.0, elapsed_days=1, total_days=10)
        assert result == pytest.approx(0.9 * 5.0 + 0.1 * 0.0)


def _make_format_issue(key, status, sp=0, labels=None, summary="Test summary", assignee=None):
    """Build a mock issue for _format_issue_line tests."""
    issue = MagicMock()
    issue.key = key
    issue.fields.status = status
    issue.fields.summary = summary
    issue.fields.labels = labels or []
    setattr(issue.fields, "customfield_10028", sp)  # CF_STORY_POINTS
    if assignee:
        issue.fields.assignee = MagicMock()
        issue.fields.assignee.displayName = assignee
    else:
        issue.fields.assignee = None
    return issue


class TestFormatIssueLine:
    def test_closed_issue_has_checked_checkbox(self):
        issue = _make_format_issue("RHIDP-100", "Closed", sp=3)
        from jirha.ops.sprint import _format_issue_line

        line = _format_issue_line(issue)
        assert line.startswith("- [x] ")

    def test_open_issue_has_unchecked_checkbox(self):
        issue = _make_format_issue("RHIDP-101", "In Progress", sp=5)
        from jirha.ops.sprint import _format_issue_line

        line = _format_issue_line(issue)
        assert line.startswith("- [ ] ")

    def test_issue_key_is_markdown_link(self):
        issue = _make_format_issue("RHIDP-102", "New", sp=1)
        from jirha.ops.sprint import _format_issue_line

        line = _format_issue_line(issue)
        assert "[RHIDP-102](https://redhat.atlassian.net/browse/RHIDP-102)" in line

    def test_sp_and_labels_present(self):
        issue = _make_format_issue("RHIDP-103", "Review", sp=8, labels=["must-have"])
        from jirha.ops.sprint import _format_issue_line

        line = _format_issue_line(issue)
        assert " 8SP" in line
        assert "[must-have]" in line

    def test_pr_status_appended_when_provided(self):
        issue = _make_format_issue("RHIDP-104", "In Progress", sp=3)
        from jirha.ops.sprint import _format_issue_line

        pr = "[PR: open, approved](https://github.com/org/repo/pull/42)"
        line = _format_issue_line(issue, pr_status=pr)
        assert line.endswith(f" — {pr}")

    def test_no_pr_suffix_when_none(self):
        issue = _make_format_issue("RHIDP-105", "In Progress", sp=3)
        from jirha.ops.sprint import _format_issue_line

        line = _format_issue_line(issue)
        assert "PR:" not in line

    def test_team_mode_shows_assignee(self):
        issue = _make_format_issue("RHIDP-106", "New", sp=1, assignee="Jane Doe")
        from jirha.ops.sprint import _format_issue_line

        line = _format_issue_line(issue, team=True)
        assert "@Jane Doe" in line

    def test_full_format_open_with_pr(self):
        issue = _make_format_issue(
            "RHIDP-107", "In Progress", sp=8, labels=["must-have"], summary="Fix auth"
        )
        from jirha.ops.sprint import _format_issue_line

        pr = "[PR: open, approved, CI pass](https://github.com/org/repo/pull/10)"
        line = _format_issue_line(issue, pr_status=pr)
        expected = (
            "- [ ] [RHIDP-107](https://redhat.atlassian.net/browse/RHIDP-107)"
            " 8SP [must-have] — Fix auth — [PR: open, approved, CI pass](https://github.com/org/repo/pull/10)"
        )
        assert line == expected

    def test_full_format_closed(self):
        issue = _make_format_issue("RHIDP-108", "Closed", sp=3, summary="Update docs")
        from jirha.ops.sprint import _format_issue_line

        line = _format_issue_line(issue)
        expected = (
            "- [x] [RHIDP-108](https://redhat.atlassian.net/browse/RHIDP-108) 3SP — Update docs"
        )
        assert line == expected
