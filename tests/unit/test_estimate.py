from jirha.ops.estimate import _has_reasoning_comment


def test_has_reasoning_all_four_dimensions():
    comments = [
        _mock_comment("Complexity: Low — simple task\nRisk: Low\nUncertainty: None\nEffort: Minimal")
    ]
    assert _has_reasoning_comment(comments) is True


def test_missing_one_dimension():
    comments = [
        _mock_comment("Complexity: Low — simple task\nRisk: Low\nUncertainty: None")
    ]
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
    comments = [
        _mock_comment("SP reassessed from PRs: 2 PRs, 28 .adoc files, +108/-117 lines")
    ]
    assert _has_reasoning_comment(comments) is False


def test_dimensions_spread_across_comments():
    """All four dimensions must be in a single comment, not spread across multiple."""
    comments = [
        _mock_comment("Complexity: Low\nRisk: Low"),
        _mock_comment("Uncertainty: None\nEffort: Minimal"),
    ]
    assert _has_reasoning_comment(comments) is False


class _mock_comment:
    def __init__(self, body):
        self.body = body


from unittest.mock import MagicMock
from jirha.ops.estimate import _classify_issues


def _make_issue(key, summary, sp=None, comments=None):
    """Create a mock Jira issue."""
    issue = MagicMock()
    issue.key = key
    issue.fields.summary = summary
    issue.fields.status = MagicMock(__str__=lambda self: "New")
    issue.fields.assignee = MagicMock()
    issue.fields.assignee.displayName = "Test User"
    # SP field
    from jirha.config import CF_STORY_POINTS
    setattr(issue.fields, CF_STORY_POINTS, sp)
    # Comments
    if comments is None:
        comments = []
    comment_obj = MagicMock()
    comment_obj.comments = [_mock_comment(c) for c in comments]
    issue.fields.comment = comment_obj
    return issue


def test_classify_missing_sp():
    issues = [_make_issue("RHIDP-1", "Some task", sp=None)]
    result = _classify_issues(issues)
    assert len(result) == 1
    assert result[0]["missing"] == "sp"


def test_classify_missing_reasoning():
    issues = [_make_issue("RHIDP-1", "Some task", sp=3.0, comments=["just a note"])]
    result = _classify_issues(issues)
    assert len(result) == 1
    assert result[0]["missing"] == "reasoning"


def test_classify_has_both():
    reasoning = "Complexity: Low\nRisk: Low\nUncertainty: None\nEffort: Minimal"
    issues = [_make_issue("RHIDP-1", "Some task", sp=3.0, comments=[reasoning])]
    result = _classify_issues(issues)
    assert len(result) == 0


def test_classify_sp_zero_is_valid():
    """0 SP is a valid value, not 'missing'."""
    issues = [_make_issue("RHIDP-1", "Some task", sp=0.0, comments=["no reasoning"])]
    result = _classify_issues(issues)
    assert len(result) == 1
    assert result[0]["missing"] == "reasoning"
