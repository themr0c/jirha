from unittest.mock import MagicMock, mock_open, patch

from jirha.ops.issues import (
    _build_comment,
    _fmt_components,
    _fmt_labels,
    _fmt_links,
    _fmt_sprint,
    _fmt_versions,
    _modify_label,
)


class TestFmtVersions:
    def test_empty(self):
        assert _fmt_versions([]) == "unset"

    def test_single(self):
        v = MagicMock()
        v.name = "1.10.0"
        assert _fmt_versions([v]) == "1.10.0"

    def test_multiple(self):
        v1, v2 = MagicMock(), MagicMock()
        v1.name, v2.name = "1.9.0", "1.10.0"
        assert _fmt_versions([v1, v2]) == "1.9.0, 1.10.0"


class TestFmtComponents:
    def test_empty(self):
        assert _fmt_components([]) == "unset"

    def test_single(self):
        c = MagicMock()
        c.name = "Documentation"
        assert _fmt_components([c]) == "Documentation"


class TestFmtLabels:
    def test_empty(self):
        assert _fmt_labels([]) == "unset"

    def test_multiple(self):
        assert _fmt_labels(["must-have", "customer"]) == "must-have, customer"


class TestFmtSprint:
    def test_empty(self):
        assert _fmt_sprint([]) == "unset"
        assert _fmt_sprint(None) == "unset"

    def test_active_sprint(self):
        s = MagicMock()
        s.state = "active"
        s.name = "Doc Sprint 2024-1"
        assert _fmt_sprint([s]) == "Doc Sprint 2024-1"

    def test_no_active_returns_last(self):
        s = MagicMock()
        s.state = "closed"
        s.name = "Doc Sprint 2024-0"
        assert _fmt_sprint([s]) == "Doc Sprint 2024-0"


class TestFmtLinks:
    def test_empty(self):
        assert _fmt_links([]) == "none"

    def test_outward_link(self):
        link = MagicMock()
        link.outwardIssue.key = "RHIDP-456"
        link.type.outward = "relates to"
        link.inwardIssue = None
        assert _fmt_links([link]) == "relates to RHIDP-456"

    def test_inward_link(self):
        link = MagicMock()
        link.outwardIssue = None
        link.inwardIssue.key = "RHIDP-789"
        link.type.inward = "is blocked by"
        assert _fmt_links([link]) == "is blocked by RHIDP-789"


class TestModifyLabel:
    def test_add_new_label(self):
        labels = ["existing"]
        result = _modify_label(labels, "new", add=True)
        assert result == "Label added: new"
        assert "new" in labels

    def test_add_existing_label_noop(self):
        labels = ["existing"]
        result = _modify_label(labels, "existing", add=True)
        assert result is None
        assert labels == ["existing"]

    def test_remove_label(self):
        labels = ["existing", "other"]
        result = _modify_label(labels, "existing", add=False)
        assert result == "Label removed: existing"
        assert "existing" not in labels

    def test_remove_missing_label_noop(self):
        labels = ["existing"]
        result = _modify_label(labels, "gone", add=False)
        assert result is None


class TestBuildComment:
    def _args(self, comment=None, comment_file=None):
        args = MagicMock()
        args.comment = comment
        args.comment_file = comment_file
        return args

    def test_changes_only(self):
        result = _build_comment(self._args(), ["SP: 5", "PR: https://example.com"])
        assert "SP: 5" in result
        assert "PR: https://example.com" in result

    def test_comment_appended(self):
        result = _build_comment(self._args(comment="my note"), ["SP: 5"])
        assert "SP: 5" in result
        assert "my note" in result

    def test_empty_changes_no_comment_returns_none(self):
        result = _build_comment(self._args(), [])
        assert result is None

    def test_comment_file(self):
        args = self._args(comment_file="/tmp/note.txt")
        with patch("builtins.open", mock_open(read_data="file content")):
            result = _build_comment(args, [])
        assert result == "file content"
