from jirha.ops.release_notes import (
    _build_fix_version_jql,
    _build_known_issues_jql,
    _check_deduplication,
    _check_violations,
    _check_warnings,
    _classify_rn_bucket,
    _filter_versions,
    _format_item_line,
    _format_section_header,
    _map_to_section,
    _todo_text,
)


class TestClassifyRnBucket:
    def test_done(self):
        assert _classify_rn_bucket("Done", "Feature") == "done"

    def test_not_required_by_type(self):
        assert _classify_rn_bucket(None, "Release Notes Not Required") == "not_required"

    def test_not_required_by_status_rejected(self):
        assert _classify_rn_bucket("Rejected", "Bug Fix") == "not_required"

    def test_in_progress(self):
        assert _classify_rn_bucket("In Progress", "Enhancement") == "in_progress"

    def test_proposed(self):
        assert _classify_rn_bucket("Proposed", "Bug Fix") == "proposed"

    def test_empty_all_none(self):
        assert _classify_rn_bucket(None, None) == "empty"

    def test_empty_status_set_but_type_none(self):
        assert _classify_rn_bucket("Draft", None) == "empty"

    def test_done_requires_all_fields(self):
        assert _classify_rn_bucket("Done", None) == "empty"


class TestMapToSection:
    def test_feature(self):
        assert _map_to_section("Feature") == (1, "New features and enhancements")

    def test_enhancement(self):
        assert _map_to_section("Enhancement") == (1, "New features and enhancements")

    def test_tech_preview(self):
        assert _map_to_section("Technology Preview") == (2, "Technology Preview features")

    def test_dev_preview(self):
        assert _map_to_section("Developer Preview") == (3, "Developer Preview features")

    def test_deprecated(self):
        assert _map_to_section("Deprecated Functionality") == (4, "Deprecated features")

    def test_removed(self):
        assert _map_to_section("Removed Functionality") == (5, "Removed features")

    def test_known_issue(self):
        assert _map_to_section("Known Issue") == (6, "Known issues")

    def test_bug_fix(self):
        assert _map_to_section("Bug Fix") == (7, "Fixed issues")

    def test_none_returns_none(self):
        assert _map_to_section(None) is None

    def test_unknown_type_returns_none(self):
        assert _map_to_section("SomethingElse") is None


class TestTodoText:
    def test_done(self):
        assert _todo_text("done", classified=True) == ""

    def test_proposed(self):
        assert _todo_text("proposed", classified=True) == "TODO: Review draft proposed by SME"

    def test_in_progress(self):
        assert (
            _todo_text("in_progress", classified=True)
            == "TODO: Review RN text submitted by Docs team"
        )

    def test_empty_classified(self):
        assert _todo_text("empty", classified=True) == "TODO: Author release notes"

    def test_empty_unclassified(self):
        assert _todo_text("empty", classified=False) == "TODO: Set RN Type and RN Text"

    def test_not_required(self):
        assert _todo_text("not_required", classified=True) == ""


class TestCheckViolations:
    def test_known_issue_with_fix_version_in_range(self):
        items = [{"key": "RHDHBUGS-100", "rn_type": "Known Issue", "from_query": 1}]
        violations = _check_violations(items, "1.10")
        assert len(violations) == 1
        assert "RHDHBUGS-100" in violations[0]["key"]

    def test_known_issue_from_query2_is_ok(self):
        items = [{"key": "RHDHBUGS-200", "rn_type": "Known Issue", "from_query": 2}]
        violations = _check_violations(items, "1.10")
        assert len(violations) == 0

    def test_bug_fix_from_query1_is_ok(self):
        items = [{"key": "RHDHBUGS-300", "rn_type": "Bug Fix", "from_query": 1}]
        violations = _check_violations(items, "1.10")
        assert len(violations) == 0


class TestCheckDeduplication:
    def test_rhidp_with_rn_text(self):
        rhidp_issues = [
            {"key": "RHIDP-890", "rn_text": "Some text", "parent_key": "RHDHPLAN-400"},
        ]
        dupes = _check_deduplication(rhidp_issues)
        assert len(dupes) == 1
        assert dupes[0]["parent_key"] == "RHDHPLAN-400"

    def test_rhidp_without_rn_text_is_ok(self):
        rhidp_issues = [
            {"key": "RHIDP-891", "rn_text": None, "parent_key": "RHDHPLAN-400"},
        ]
        dupes = _check_deduplication(rhidp_issues)
        assert len(dupes) == 0


class TestCheckWarnings:
    def test_security_level_set(self):
        items = [{"key": "RHDHPLAN-500", "security": "Red Hat Employee"}]
        warnings = _check_warnings(items)
        assert len(warnings) == 1

    def test_no_security_level(self):
        items = [{"key": "RHDHPLAN-600", "security": None}]
        warnings = _check_warnings(items)
        assert len(warnings) == 0


class TestFormatItemLine:
    def test_done_item(self):
        line = _format_item_line("RHDHPLAN-200", "done", "", [])
        assert line == "[x] https://redhat.atlassian.net/browse/RHDHPLAN-200"

    def test_actionable_with_todo(self):
        line = _format_item_line(
            "RHDHPLAN-300",
            "proposed",
            "TODO: Review draft proposed by SME",
            ["RHIDP-5679"],
        )
        assert "[x]" not in line
        assert "[ ]" in line
        assert "TODO: Review draft proposed by SME" in line
        assert "← RHIDP-5679" in line

    def test_no_sources(self):
        line = _format_item_line("RHDHBUGS-1234", "empty", "TODO: Author release notes", [])
        assert "←" not in line
        assert "TODO: Author release notes" in line

    def test_multiple_sources(self):
        line = _format_item_line(
            "RHDHPLAN-400",
            "in_progress",
            "TODO: Review RN text submitted by Docs team",
            ["RHIDP-1", "RHIDP-2"],
        )
        assert "← RHIDP-1, RHIDP-2" in line


class TestFormatSectionHeader:
    def test_with_counts(self):
        header = _format_section_header(
            1,
            "New features and enhancements",
            {"done": 5, "proposed": 19, "in_progress": 3},
            27,
            5,
        )
        assert "1. New features and enhancements" in header
        assert "27" in header
        assert "5 done" in header
        assert "19 proposed" in header
        assert "3 in progress" in header
        assert "[5 not closed]" in header

    def test_empty_section(self):
        header = _format_section_header(4, "Deprecated features", {}, 0, 0)
        assert "4. Deprecated features (0)" in header

    def test_no_not_closed(self):
        header = _format_section_header(3, "Developer Preview features", {"done": 3}, 3, 0)
        assert "[" not in header


class TestBuildJql:
    def test_fix_version_jql_mine(self):
        versions = ["1.10.0", "1.10.1"]
        jql = _build_fix_version_jql(versions, mine_only=True)
        assert "project in (RHDHBUGS, RHDHPLAN, RHIDP)" in jql
        assert 'fixVersion in ("1.10.0", "1.10.1")' in jql
        assert "assignee = currentUser()" in jql

    def test_fix_version_jql_all(self):
        versions = ["1.10.0"]
        jql = _build_fix_version_jql(versions, mine_only=False)
        assert "assignee" not in jql

    def test_known_issues_jql_mine(self):
        versions = ["1.10.0", "1.10.1"]
        jql = _build_known_issues_jql(versions, mine_only=True)
        assert '"Release Note Type" in ("Known Issue")' in jql
        assert 'affectedVersion in ("1.10.0", "1.10.1")' in jql
        assert 'fixVersion NOT IN ("1.10.0", "1.10.1")' in jql
        assert "assignee = currentUser()" in jql

    def test_known_issues_jql_all(self):
        versions = ["1.10.0"]
        jql = _build_known_issues_jql(versions, mine_only=False)
        assert "assignee" not in jql


class TestFilterVersions:
    def test_filters_by_prefix(self):
        class V:
            def __init__(self, name):
                self.name = name

        versions = [
            V("1.9.0"),
            V("1.10.0"),
            V("1.10.1"),
            V("1.10.2"),
            V("2.0.0"),
        ]
        result = _filter_versions(versions, "1.10")
        assert result == ["1.10.0", "1.10.1", "1.10.2"]

    def test_no_match_returns_empty(self):
        class V:
            def __init__(self, name):
                self.name = name

        versions = [V("1.9.0")]
        result = _filter_versions(versions, "1.10")
        assert result == []
