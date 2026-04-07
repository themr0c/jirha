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
