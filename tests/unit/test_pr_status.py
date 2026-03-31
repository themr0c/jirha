import json
from unittest.mock import MagicMock, patch

from jirha.api import _pr_status


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
