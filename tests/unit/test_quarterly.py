from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from jirha.ops.quarterly import (
    _extract_epic,
    _group_issues,
    _is_self_reported,
    _quarter_range,
    _resolve_level,
)

# _quarter_range tests


def test_quarter_range_explicit():
    start, end, label = _quarter_range("Q1-2026")
    assert start == date(2026, 1, 1)
    assert end == date(2026, 4, 1)
    assert label == "Q1-2026"


def test_quarter_range_q4_wraps_year():
    start, end, label = _quarter_range("Q4-2025")
    assert start == date(2025, 10, 1)
    assert end == date(2026, 1, 1)
    assert label == "Q4-2025"


def test_quarter_range_case_insensitive():
    start, end, label = _quarter_range("q2-2026")
    assert start == date(2026, 4, 1)
    assert end == date(2026, 7, 1)
    assert label == "Q2-2026"


def test_quarter_range_invalid_quarter():
    with pytest.raises(SystemExit):
        _quarter_range("Q5-2026")


def test_quarter_range_invalid_format():
    with pytest.raises(SystemExit):
        _quarter_range("2026-Q1")


def test_quarter_range_non_numeric_year():
    with pytest.raises(SystemExit):
        _quarter_range("Q1-abcd")


@patch("jirha.ops.quarterly.date")
def test_quarter_range_auto_detect_midyear(mock_date):
    mock_date.today.return_value = date(2026, 7, 15)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
    start, end, label = _quarter_range()
    assert label == "Q2-2026"
    assert start == date(2026, 4, 1)


@patch("jirha.ops.quarterly.date")
def test_quarter_range_auto_detect_q1_wraps_to_previous_year(mock_date):
    mock_date.today.return_value = date(2026, 2, 10)
    mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
    start, end, label = _quarter_range()
    assert label == "Q4-2025"
    assert start == date(2025, 10, 1)
    assert end == date(2026, 1, 1)


# _resolve_level tests


@patch("jirha.ops.quarterly.JOB_PROFILE", "tw3")
def test_resolve_level_from_config():
    assert _resolve_level(None) == 3


@patch("jirha.ops.quarterly.JOB_PROFILE", "TW4")
def test_resolve_level_uppercase():
    assert _resolve_level(None) == 4


@patch("jirha.ops.quarterly.JOB_PROFILE", "tw3")
def test_resolve_level_cli_overrides_config():
    assert _resolve_level(2) == 2


@patch("jirha.ops.quarterly.JOB_PROFILE", "")
def test_resolve_level_empty_string():
    with pytest.raises(SystemExit):
        _resolve_level(None)


@patch("jirha.ops.quarterly.JOB_PROFILE", "garbage")
def test_resolve_level_invalid_string():
    with pytest.raises(SystemExit):
        _resolve_level(None)


def test_resolve_level_out_of_range():
    with pytest.raises(SystemExit):
        _resolve_level(6)


def test_resolve_level_zero():
    with pytest.raises(SystemExit):
        _resolve_level(0)


# _extract_epic tests


def test_extract_epic_with_epic_parent():
    issue = MagicMock()
    issue.fields.parent.key = "RHIDP-100"
    issue.fields.parent.fields.summary = "My Epic"
    issue.fields.parent.fields.issuetype = MagicMock(__str__=lambda s: "Epic")
    key, summary = _extract_epic(issue)
    assert key == "RHIDP-100"
    assert summary == "My Epic"


def test_extract_epic_no_parent():
    issue = MagicMock(spec=[])
    issue.fields = MagicMock(spec=[])
    issue.fields.parent = None
    key, summary = _extract_epic(issue)
    assert key == "Ungrouped"


def test_extract_epic_subtask_walks_up_to_epic():
    """Sub-task parent is a Task — should walk up to find the epic."""
    issue = MagicMock()
    issue.fields.parent.key = "RHIDP-50"
    issue.fields.parent.fields.summary = "Parent Task"
    issue.fields.parent.fields.issuetype = MagicMock(__str__=lambda s: "Task")

    # Mock the jira.issue() call that fetches the parent
    parent_issue = MagicMock()
    parent_issue.fields.parent.key = "RHIDP-100"
    parent_issue.fields.parent.fields.summary = "The Epic"
    jira = MagicMock()
    jira.issue.return_value = parent_issue

    key, summary = _extract_epic(issue, jira=jira, _cache={})
    assert key == "RHIDP-100"
    assert summary == "The Epic"
    jira.issue.assert_called_once_with("RHIDP-50", fields="parent,summary,issuetype")


def test_extract_epic_subtask_uses_cache():
    """Second sub-task under same parent should use cache, not call Jira."""
    issue = MagicMock()
    issue.fields.parent.key = "RHIDP-50"
    issue.fields.parent.fields.summary = "Parent Task"
    issue.fields.parent.fields.issuetype = MagicMock(__str__=lambda s: "Task")

    jira = MagicMock()
    cache = {"RHIDP-50": ("RHIDP-100", "The Epic")}

    key, summary = _extract_epic(issue, jira=jira, _cache=cache)
    assert key == "RHIDP-100"
    assert summary == "The Epic"
    jira.issue.assert_not_called()


# _group_issues tests


def _make_issue_with_parent(key, epic_key, epic_summary):
    issue = MagicMock()
    issue.key = key
    issue.fields.parent.key = epic_key
    issue.fields.parent.fields.summary = epic_summary
    issue.fields.parent.fields.issuetype = MagicMock(__str__=lambda s: "Epic")
    return issue


def test_group_issues_groups_by_epic():
    issues = [
        _make_issue_with_parent("RHIDP-1", "RHIDP-100", "Epic A"),
        _make_issue_with_parent("RHIDP-2", "RHIDP-100", "Epic A"),
        _make_issue_with_parent("RHIDP-3", "RHIDP-200", "Epic B"),
    ]
    groups = _group_issues(issues)
    assert len(groups) == 2
    assert len(groups["RHIDP-100"]["issues"]) == 2
    assert len(groups["RHIDP-200"]["issues"]) == 1


# _is_self_reported tests


@patch("jirha.ops.quarterly.EMAIL", "user@redhat.com")
def test_is_self_reported_true():
    issue = MagicMock()
    issue.fields.reporter.emailAddress = "user@redhat.com"
    assert _is_self_reported(issue) is True


@patch("jirha.ops.quarterly.EMAIL", "user@redhat.com")
def test_is_self_reported_false():
    issue = MagicMock()
    issue.fields.reporter.emailAddress = "other@redhat.com"
    assert _is_self_reported(issue) is False


@patch("jirha.ops.quarterly.EMAIL", "")
def test_is_self_reported_no_email_configured():
    issue = MagicMock()
    issue.fields.reporter.emailAddress = "user@redhat.com"
    assert _is_self_reported(issue) is False
