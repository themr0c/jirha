from unittest.mock import MagicMock

from jirha.ops.estimate import _classify_issues, _has_reasoning_comment


class _mock_comment:
    def __init__(self, body):
        self.body = body


def _make_issue(key, summary, sp=None, comments=None):
    """Create a mock Jira issue."""
    issue = MagicMock()
    issue.key = key
    issue.fields.summary = summary
    issue.fields.status = MagicMock(__str__=lambda self: "New")
    issue.fields.assignee = MagicMock()
    issue.fields.assignee.displayName = "Test User"
    from jirha.config import CF_STORY_POINTS

    setattr(issue.fields, CF_STORY_POINTS, sp)
    if comments is None:
        comments = []
    comment_obj = MagicMock()
    comment_obj.comments = [_mock_comment(c) for c in comments]
    issue.fields.comment = comment_obj
    return issue


# _has_reasoning_comment tests


def test_has_reasoning_all_four_dimensions():
    comments = [
        _mock_comment(
            "Complexity: Low — simple task\nRisk: Low\nUncertainty: None\nEffort: Minimal"
        )
    ]
    assert _has_reasoning_comment(comments) is True


def test_missing_one_dimension():
    comments = [_mock_comment("Complexity: Low — simple task\nRisk: Low\nUncertainty: None")]
    assert _has_reasoning_comment(comments) is False


def test_no_comments():
    assert _has_reasoning_comment([]) is False


def test_reasoning_in_second_comment():
    comments = [
        _mock_comment("Updated SP: 3 → 5"),
        _mock_comment("Complexity: Medium\nRisk: Low\nUncertainty: Small\nEffort: Moderate"),
    ]
    assert _has_reasoning_comment(comments) is True


def test_sp_reassessed_without_dimensions():
    """hygiene-style 'SP reassessed from PRs' comments don't count as reasoning."""
    comments = [_mock_comment("SP reassessed from PRs: 2 PRs, 28 .adoc files, +108/-117 lines")]
    assert _has_reasoning_comment(comments) is False


def test_dimensions_spread_across_comments():
    """All four dimensions must be in a single comment, not spread across multiple."""
    comments = [
        _mock_comment("Complexity: Low\nRisk: Low"),
        _mock_comment("Uncertainty: None\nEffort: Minimal"),
    ]
    assert _has_reasoning_comment(comments) is False


# _classify_issues tests (returns (ok, needs_attention) tuple)


def test_classify_missing_sp():
    issues = [_make_issue("RHIDP-1", "Some task", sp=None)]
    ok, needs = _classify_issues(issues)
    assert len(ok) == 0
    assert len(needs) == 1
    assert needs[0]["missing"] == "sp"


def test_classify_missing_reasoning():
    issues = [_make_issue("RHIDP-1", "Some task", sp=3.0, comments=["just a note"])]
    ok, needs = _classify_issues(issues)
    assert len(ok) == 0
    assert len(needs) == 1
    assert needs[0]["missing"] == "reasoning"


def test_classify_has_both():
    reasoning = "Complexity: Low\nRisk: Low\nUncertainty: None\nEffort: Minimal"
    issues = [_make_issue("RHIDP-1", "Some task", sp=3.0, comments=[reasoning])]
    ok, needs = _classify_issues(issues)
    assert len(ok) == 1
    assert len(needs) == 0
    assert ok[0]["missing"] is None


def test_classify_sp_zero_is_valid():
    """0 SP is a valid value, not 'missing'."""
    issues = [_make_issue("RHIDP-1", "Some task", sp=0.0, comments=["no reasoning"])]
    ok, needs = _classify_issues(issues)
    assert len(ok) == 0
    assert len(needs) == 1
    assert needs[0]["missing"] == "reasoning"


def test_classify_mixed():
    """Verify ok and needs_attention are properly separated."""
    reasoning = "Complexity: Low\nRisk: Low\nUncertainty: None\nEffort: Minimal"
    issues = [
        _make_issue("RHIDP-1", "OK issue", sp=3.0, comments=[reasoning]),
        _make_issue("RHIDP-2", "No SP", sp=None),
        _make_issue("RHIDP-3", "No reasoning", sp=5.0, comments=["just a note"]),
    ]
    ok, needs = _classify_issues(issues)
    assert len(ok) == 1
    assert ok[0]["key"] == "RHIDP-1"
    assert len(needs) == 2
    assert needs[0]["key"] == "RHIDP-2"
    assert needs[1]["key"] == "RHIDP-3"
