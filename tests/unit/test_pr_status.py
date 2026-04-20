import json
from unittest.mock import MagicMock, patch

import pytest

from jirha.api import (
    _checklist_items,
    _fetch_pr_statuses,
    _format_pr_checklist,
    _pr_checklist_cache,
    _pr_status,
)
from jirha.config import CF_GIT_PR


@pytest.fixture(autouse=True)
def _clear_pr_cache():
    _pr_checklist_cache.clear()
    yield
    _pr_checklist_cache.clear()


class TestPrStatus:
    def _mock_gh(self, data, returncode=0):
        result = MagicMock()
        result.returncode = returncode
        result.stdout = json.dumps(data)
        return result

    @patch("jirha.api.subprocess.run")
    def test_open_approved_ci_pass(self, mock_run):
        mock_run.return_value = self._mock_gh(
            {
                "state": "OPEN",
                "reviewDecision": "APPROVED",
                "statusCheckRollup": [{"conclusion": "SUCCESS"}],
                "url": "https://github.com/org/repo/pull/42",
            }
        )
        result = _pr_status("https://github.com/org/repo/pull/42")
        assert result == "PR: open, approved, CI pass — https://github.com/org/repo/pull/42"

    @patch("jirha.api.subprocess.run")
    def test_open_changes_requested_ci_fail(self, mock_run):
        mock_run.return_value = self._mock_gh(
            {
                "state": "OPEN",
                "reviewDecision": "CHANGES_REQUESTED",
                "statusCheckRollup": [{"conclusion": "SUCCESS"}, {"conclusion": "FAILURE"}],
                "url": "https://github.com/org/repo/pull/10",
            }
        )
        result = _pr_status("https://github.com/org/repo/pull/10")
        assert (
            result == "PR: open, changes requested, CI fail — https://github.com/org/repo/pull/10"
        )

    @patch("jirha.api.subprocess.run")
    def test_merged_no_review_no_checks(self, mock_run):
        mock_run.return_value = self._mock_gh(
            {
                "state": "MERGED",
                "reviewDecision": "",
                "statusCheckRollup": [],
                "url": "https://github.com/org/repo/pull/5",
            }
        )
        result = _pr_status("https://github.com/org/repo/pull/5")
        assert result == "PR: merged — https://github.com/org/repo/pull/5"

    @patch("jirha.api.subprocess.run")
    def test_ci_running(self, mock_run):
        mock_run.return_value = self._mock_gh(
            {
                "state": "OPEN",
                "reviewDecision": "REVIEW_REQUIRED",
                "statusCheckRollup": [{"conclusion": "SUCCESS"}, {"conclusion": ""}],
                "url": "https://github.com/org/repo/pull/7",
            }
        )
        result = _pr_status("https://github.com/org/repo/pull/7")
        assert (
            result == "PR: open, review required, CI running — https://github.com/org/repo/pull/7"
        )

    @patch("jirha.api.subprocess.run")
    def test_gh_failure_returns_none(self, mock_run):
        mock_run.return_value = self._mock_gh({}, returncode=1)
        result = _pr_status("https://github.com/org/repo/pull/42")
        assert result is None

    def test_invalid_url_returns_none(self):
        result = _pr_status("https://not-github.com/foo")
        assert result is None

    @patch("jirha.api.subprocess.run")
    def test_timeout_returns_none(self, mock_run):
        import subprocess as sp

        mock_run.side_effect = sp.TimeoutExpired(cmd="gh", timeout=15)
        result = _pr_status("https://github.com/org/repo/pull/1")
        assert result is None


def _make_issue(key, status, pr_url=None):
    issue = MagicMock()
    issue.key = key
    issue.fields.status = status
    setattr(issue.fields, CF_GIT_PR, pr_url)
    return issue


class TestFetchPrStatuses:
    @patch("jirha.api._fetch_pr_checklist")
    def test_skips_closed_issues(self, mock_cl):
        closed = _make_issue("RHIDP-1", "Closed", "https://github.com/org/repo/pull/1")
        result = _fetch_pr_statuses([closed])
        mock_cl.assert_not_called()
        assert result == {}

    @patch("jirha.api._fetch_pr_checklist")
    def test_skips_issues_without_pr(self, mock_cl):
        issue = _make_issue("RHIDP-2", "In Progress", None)
        result = _fetch_pr_statuses([issue])
        mock_cl.assert_not_called()
        assert result == {}

    @patch("jirha.api._fetch_pr_checklist")
    def test_fetches_for_open_issue_with_pr(self, mock_cl):
        mock_cl.return_value = {
            "url": "https://github.com/org/repo/pull/3",
            "state": "open",
            "review_decision": "APPROVED",
            "failing_checks": [],
            "pending_reviewers": [],
            "unresolved_comments": 0,
            "has_conflicts": False,
            "is_author": True,
        }
        issue = _make_issue("RHIDP-3", "In Progress", "https://github.com/org/repo/pull/3")
        result = _fetch_pr_statuses([issue])
        assert "RHIDP-3" in result
        assert "open" in result["RHIDP-3"]
        assert "approved" in result["RHIDP-3"]

    @patch("jirha.api._fetch_pr_checklist")
    def test_mixed_issues(self, mock_cl):
        mock_cl.return_value = {
            "url": "https://github.com/org/repo/pull/4",
            "state": "open",
            "review_decision": "",
            "failing_checks": [],
            "pending_reviewers": [],
            "unresolved_comments": 0,
            "has_conflicts": False,
            "is_author": True,
        }
        open_with_pr = _make_issue("RHIDP-4", "Review", "https://github.com/org/repo/pull/4")
        open_no_pr = _make_issue("RHIDP-5", "In Progress", None)
        closed_with_pr = _make_issue("RHIDP-6", "Closed", "https://github.com/org/repo/pull/6")
        result = _fetch_pr_statuses([open_with_pr, open_no_pr, closed_with_pr])
        assert "RHIDP-4" in result
        assert "RHIDP-5" not in result
        assert "RHIDP-6" not in result
        mock_cl.assert_called_once()

    @patch("jirha.api._fetch_pr_checklist")
    def test_pr_checklist_returns_none(self, mock_cl):
        mock_cl.return_value = None
        issue = _make_issue("RHIDP-7", "In Progress", "https://github.com/org/repo/pull/7")
        result = _fetch_pr_statuses([issue])
        assert result == {}


class TestFormatPrChecklist:
    def _cl(self, **overrides):
        base = {
            "url": "https://github.com/org/repo/pull/1",
            "state": "open",
            "review_decision": "",
            "failing_checks": [],
            "pending_reviewers": [],
            "unresolved_comments": 0,
            "has_conflicts": False,
            "is_author": True,
        }
        base.update(overrides)
        return base

    def test_open_approved_ci_pass(self):
        result = _format_pr_checklist(self._cl(review_decision="APPROVED"))
        assert "open" in result
        assert "approved" in result
        assert "CI pass" in result

    def test_changes_requested_ci_fail(self):
        result = _format_pr_checklist(
            self._cl(
                review_decision="CHANGES_REQUESTED",
                failing_checks=["ci/prow"],
            )
        )
        assert "changes requested" in result
        assert "CI fail" in result

    def test_merged_state(self):
        result = _format_pr_checklist(self._cl(state="merged"))
        assert "merged" in result


class TestChecklistItems:
    def _cl(self, **overrides):
        base = {
            "url": "https://github.com/org/repo/pull/1",
            "state": "open",
            "review_decision": "",
            "failing_checks": [],
            "pending_reviewers": [],
            "unresolved_comments": 0,
            "has_conflicts": False,
            "is_author": True,
        }
        base.update(overrides)
        return base

    def test_no_items_when_clean(self):
        assert _checklist_items(self._cl()) == []

    def test_unresolved_comments(self):
        items = _checklist_items(self._cl(unresolved_comments=3))
        assert any("3 unresolved" in i for i in items)

    def test_single_comment_no_plural(self):
        items = _checklist_items(self._cl(unresolved_comments=1))
        assert any("1 unresolved review comment" in i for i in items)
        assert not any("comments" in i for i in items)

    def test_failing_checks(self):
        items = _checklist_items(self._cl(failing_checks=["ci/prow/e2e", "tide"]))
        assert any("ci/prow/e2e" in i and "tide" in i for i in items)

    def test_pending_reviewers(self):
        items = _checklist_items(self._cl(pending_reviewers=["alice", "bob"]))
        assert any("alice" in i and "bob" in i for i in items)

    def test_merge_conflict(self):
        items = _checklist_items(self._cl(has_conflicts=True))
        assert any("Merge conflict" in i for i in items)

    def test_multiple_items(self):
        items = _checklist_items(
            self._cl(
                unresolved_comments=2,
                failing_checks=["ci"],
                has_conflicts=True,
            )
        )
        assert len(items) == 3
