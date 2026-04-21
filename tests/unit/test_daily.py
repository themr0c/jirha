from unittest.mock import MagicMock

from jirha.config import SWIMLANES
from jirha.ops.daily import (
    _actionability_key,
    _build_action_menu,
    _determine_action,
    _has_actionable_work,
)


def _cl(
    state="open",
    review_decision="",
    failing_checks=None,
    pending_reviewers=None,
    unresolved_comments=0,
    has_conflicts=False,
):
    """Build a PR checklist dict matching api.py's structure."""
    return {
        "url": "https://github.com/org/repo/pull/1",
        "state": state,
        "review_decision": review_decision,
        "failing_checks": failing_checks or [],
        "pending_reviewers": pending_reviewers or [],
        "unresolved_comments": unresolved_comments,
        "has_conflicts": has_conflicts,
        "is_author": True,
    }


class TestDetermineAction:
    def test_merged_pr(self):
        assert _determine_action("Review", _cl(state="merged")) == "Transition Jira to Closed"

    def test_approved_pr(self):
        assert _determine_action("Review", _cl(review_decision="APPROVED")) == "Merge the PR"

    def test_merge_conflict(self):
        result = _determine_action("In Progress", _cl(has_conflicts=True))
        assert result == "Resolve merge conflict"

    def test_failing_checks(self):
        result = _determine_action("In Progress", _cl(failing_checks=["tide", "lint"]))
        assert "Fix failing checks" in result
        assert "tide" in result

    def test_changes_requested(self):
        result = _determine_action("In Progress", _cl(review_decision="CHANGES_REQUESTED"))
        assert result == "Address requested changes"

    def test_unresolved_comments(self):
        result = _determine_action("Review", _cl(unresolved_comments=3))
        assert "3 unresolved review comments" in result

    def test_unresolved_comments_singular(self):
        result = _determine_action("Review", _cl(unresolved_comments=1))
        assert "1 unresolved review comment" in result
        assert "comments" not in result

    def test_awaiting_review(self):
        result = _determine_action("Review", _cl(pending_reviewers=["alice", "bob"]))
        assert "Waiting for review" in result
        assert "alice" in result

    def test_review_required_no_reviewers(self):
        result = _determine_action("Review", _cl(review_decision="REVIEW_REQUIRED"))
        assert result == "Waiting for review"

    def test_no_pr_in_progress(self):
        assert _determine_action("In Progress", None) == "Create PR or continue working"

    def test_no_pr_new(self):
        assert _determine_action("New", None) == "Start working on this issue"

    def test_no_pr_review_status(self):
        assert _determine_action("Review", None) == "Check review status"


class TestBuildActionMenu:
    def test_no_pr_new_issue(self):
        menu = _build_action_menu("New", None, sp=3)
        labels = [text for text, _ in menu]
        recommended = [text for text, rec in menu if rec]
        assert recommended == ["Start working on this issue"]
        assert "Update Jira" in labels

    def test_no_pr_new_issue_missing_sp(self):
        menu = _build_action_menu("New", None, sp=0)
        labels = [text for text, _ in menu]
        assert "Estimate SP" in labels

    def test_pr_with_failing_checks(self):
        cl = _cl(failing_checks=["tide"], unresolved_comments=2)
        menu = _build_action_menu("In Progress", cl, sp=5)
        labels = [text for text, _ in menu]
        recommended = [text for text, rec in menu if rec]
        assert "Fix failing checks: tide" in recommended
        assert any("2 unresolved" in t for t in labels)
        assert "Update Jira" in labels

    def test_pr_approved_shows_merge(self):
        cl = _cl(review_decision="APPROVED")
        menu = _build_action_menu("Review", cl, sp=5)
        recommended = [text for text, rec in menu if rec]
        assert "Merge the PR" in recommended

    def test_merged_pr_shows_transition(self):
        cl = _cl(state="merged")
        menu = _build_action_menu("Review", cl, sp=5)
        recommended = [text for text, rec in menu if rec]
        assert "Transition Jira to Closed" in recommended

    def test_awaiting_review_no_duplicate(self):
        cl = _cl(review_decision="REVIEW_REQUIRED", pending_reviewers=["alice"])
        menu = _build_action_menu("Review", cl, sp=5)
        labels = [text for text, _ in menu]
        assert labels.count("Waiting for review from alice") == 1

    def test_recommended_is_always_first(self):
        cl = _cl(failing_checks=["tide"])
        menu = _build_action_menu("In Progress", cl, sp=5)
        assert menu[0][1] is True

    def test_exactly_one_recommended(self):
        cl = _cl(has_conflicts=True, failing_checks=["tide"], unresolved_comments=3)
        menu = _build_action_menu("In Progress", cl, sp=5)
        recommended_count = sum(1 for _, rec in menu if rec)
        assert recommended_count == 1


class TestActionabilityKey:
    def test_pr_author_action_is_highest(self):
        checklists = {"K-1": _cl(failing_checks=["tide"])}
        assert _actionability_key("K-1", "In Progress", checklists) == 0

    def test_pr_conflicts_is_author_action(self):
        checklists = {"K-1": _cl(has_conflicts=True)}
        assert _actionability_key("K-1", "In Progress", checklists) == 0

    def test_pr_changes_requested_is_author_action(self):
        checklists = {"K-1": _cl(review_decision="CHANGES_REQUESTED")}
        assert _actionability_key("K-1", "In Progress", checklists) == 0

    def test_pr_unresolved_comments_is_author_action(self):
        checklists = {"K-1": _cl(unresolved_comments=2)}
        assert _actionability_key("K-1", "Review", checklists) == 0

    def test_pr_awaiting_review(self):
        checklists = {"K-1": _cl(review_decision="REVIEW_REQUIRED")}
        assert _actionability_key("K-1", "Review", checklists) == 1

    def test_in_progress_no_pr(self):
        assert _actionability_key("K-1", "In Progress", {}) == 2

    def test_review_no_pr(self):
        assert _actionability_key("K-1", "Review", {}) == 3

    def test_new_status(self):
        assert _actionability_key("K-1", "New", {}) == 4

    def test_ordering_is_correct(self):
        checklists = {"K-1": _cl(failing_checks=["tide"]), "K-2": _cl()}
        author_action = _actionability_key("K-1", "In Progress", checklists)
        awaiting = _actionability_key("K-2", "Review", checklists)
        in_progress = _actionability_key("K-3", "In Progress", {})
        new = _actionability_key("K-4", "New", {})
        assert author_action < awaiting < in_progress < new


def _mock_issue(status="New"):
    issue = MagicMock()
    issue.fields.status = MagicMock(__str__=lambda self: status)
    return issue


class TestHasActionableWork:
    def test_empty_swimlanes(self):
        lanes = {name: [] for name, _ in SWIMLANES}
        assert _has_actionable_work(lanes) is False

    def test_only_closed(self):
        lanes = {name: [] for name, _ in SWIMLANES}
        lanes["Blocker"] = [_mock_issue("Closed")]
        assert _has_actionable_work(lanes) is False

    def test_only_review(self):
        lanes = {name: [] for name, _ in SWIMLANES}
        lanes["Customer"] = [_mock_issue("Review")]
        assert _has_actionable_work(lanes) is False

    def test_has_new(self):
        lanes = {name: [] for name, _ in SWIMLANES}
        lanes["Must-have"] = [_mock_issue("New")]
        assert _has_actionable_work(lanes) is True

    def test_has_in_progress(self):
        lanes = {name: [] for name, _ in SWIMLANES}
        lanes["Other"] = [_mock_issue("In Progress")]
        assert _has_actionable_work(lanes) is True

    def test_mixed_review_and_new(self):
        lanes = {name: [] for name, _ in SWIMLANES}
        lanes["Customer"] = [_mock_issue("Review")]
        lanes["Other"] = [_mock_issue("New")]
        assert _has_actionable_work(lanes) is True
