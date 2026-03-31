import json
from unittest.mock import MagicMock, patch

from jirha.api import _fetch_pr_statuses, _pr_status
from jirha.config import CF_GIT_PR


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
        assert result == "[PR: open, approved, CI pass](https://github.com/org/repo/pull/42)"

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
            result == "[PR: open, changes requested, CI fail](https://github.com/org/repo/pull/10)"
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
        assert result == "[PR: merged](https://github.com/org/repo/pull/5)"

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
            result == "[PR: open, review required, CI running](https://github.com/org/repo/pull/7)"
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
    @patch("jirha.api._pr_status")
    def test_skips_closed_issues(self, mock_pr):
        closed = _make_issue("RHIDP-1", "Closed", "https://github.com/org/repo/pull/1")
        result = _fetch_pr_statuses([closed])
        mock_pr.assert_not_called()
        assert result == {}

    @patch("jirha.api._pr_status")
    def test_skips_issues_without_pr(self, mock_pr):
        issue = _make_issue("RHIDP-2", "In Progress", None)
        result = _fetch_pr_statuses([issue])
        mock_pr.assert_not_called()
        assert result == {}

    @patch("jirha.api._pr_status")
    def test_fetches_for_open_issue_with_pr(self, mock_pr):
        mock_pr.return_value = "[PR: open, approved](https://github.com/org/repo/pull/3)"
        issue = _make_issue("RHIDP-3", "In Progress", "https://github.com/org/repo/pull/3")
        result = _fetch_pr_statuses([issue])
        assert result == {"RHIDP-3": "[PR: open, approved](https://github.com/org/repo/pull/3)"}

    @patch("jirha.api._pr_status")
    def test_mixed_issues(self, mock_pr):
        mock_pr.return_value = "[PR: open](https://github.com/org/repo/pull/4)"
        open_with_pr = _make_issue("RHIDP-4", "Review", "https://github.com/org/repo/pull/4")
        open_no_pr = _make_issue("RHIDP-5", "In Progress", None)
        closed_with_pr = _make_issue("RHIDP-6", "Closed", "https://github.com/org/repo/pull/6")
        result = _fetch_pr_statuses([open_with_pr, open_no_pr, closed_with_pr])
        assert "RHIDP-4" in result
        assert "RHIDP-5" not in result
        assert "RHIDP-6" not in result
        mock_pr.assert_called_once()

    @patch("jirha.api._pr_status")
    def test_pr_status_returns_none(self, mock_pr):
        mock_pr.return_value = None
        issue = _make_issue("RHIDP-7", "In Progress", "https://github.com/org/repo/pull/7")
        result = _fetch_pr_statuses([issue])
        assert result == {}
