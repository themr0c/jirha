from unittest.mock import MagicMock

from jirha.ops.release_notes import (
    _build_fix_version_jql,
    _build_known_issues_jql,
    _check_deduplication,
    _check_violations,
    _check_warnings,
    _classify_rn_bucket,
    _count_actions,
    _filter_versions,
    _format_item_line,
    _format_section_header,
    _format_summary_table,
    _map_to_section,
    _resolve_and_group,
    _todo_text,
)


class TestClassifyRnBucket:
    def test_done(self):
        assert _classify_rn_bucket("Done", "Feature") == "done"

    def test_not_required_by_type(self):
        assert _classify_rn_bucket(None, "Release Note Not Required") == "not_required"

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

    def test_all_empty_bucket(self):
        header = _format_section_header(2, "Technology Preview features", {"empty": 1}, 1, 1)
        assert "(1)" in header
        assert "(1, )" not in header
        assert "[1 not closed]" in header


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


def _item(bucket, todo):
    return {"bucket": bucket, "todo": todo, "key": "X-1", "source_keys": []}


class TestCountActions:
    def test_classify(self):
        items = [_item("empty", "TODO: Set RN Type and RN Text")]
        assert _count_actions(items) == {"classify": 1, "author": 0, "review": 0, "done": 0}

    def test_author(self):
        items = [_item("empty", "TODO: Author release notes")]
        assert _count_actions(items) == {"classify": 0, "author": 1, "review": 0, "done": 0}

    def test_review_proposed(self):
        items = [_item("proposed", "TODO: Review draft proposed by SME")]
        assert _count_actions(items) == {"classify": 0, "author": 0, "review": 1, "done": 0}

    def test_review_in_progress(self):
        items = [_item("in_progress", "TODO: Review RN text submitted by Docs team")]
        assert _count_actions(items) == {"classify": 0, "author": 0, "review": 1, "done": 0}

    def test_done(self):
        items = [_item("done", "")]
        assert _count_actions(items) == {"classify": 0, "author": 0, "review": 0, "done": 1}

    def test_mixed(self):
        items = [
            _item("done", ""),
            _item("done", ""),
            _item("empty", "TODO: Author release notes"),
            _item("proposed", "TODO: Review draft proposed by SME"),
            _item("empty", "TODO: Set RN Type and RN Text"),
        ]
        assert _count_actions(items) == {"classify": 1, "author": 1, "review": 1, "done": 2}


class TestFormatSummaryTable:
    def test_all_sections_present(self):
        table = _format_summary_table({}, [], [])
        for sec_num in range(1, 8):
            assert f"{sec_num}." in table

    def test_unclassified_row(self):
        unclassified = [
            _item("empty", "TODO: Set RN Type and RN Text"),
            _item("empty", "TODO: Set RN Type and RN Text"),
            _item("proposed", "TODO: Review draft proposed by SME"),
        ]
        table = _format_summary_table({}, unclassified, [])
        lines = table.split("\n")
        uc_line = [ln for ln in lines if ln.startswith("Unclassified")][0]
        nums = [int(x) for x in uc_line.split() if x.isdigit()]
        assert nums == [2, 0, 1, 0, 3]

    def test_section_counts(self):
        sections = {
            1: {
                "title": "New features and enhancements",
                "items": [
                    _item("done", ""),
                    _item("done", ""),
                    _item("empty", "TODO: Author release notes"),
                ],
                "status_counts": {"done": 2},
                "total": 3,
                "not_closed": 0,
            }
        }
        table = _format_summary_table(sections, [], [])
        lines = table.split("\n")
        sec1_line = [ln for ln in lines if "1. New features" in ln][0]
        nums = [int(x) for x in sec1_line.split() if x.isdigit()]
        assert nums[0] == 0  # classify
        assert nums[1] == 1  # author
        assert nums[2] == 0  # review
        assert nums[3] == 2  # done
        assert nums[4] == 3  # total

    def test_total_row_sums(self):
        sections = {
            7: {
                "title": "Fixed issues",
                "items": [
                    _item("done", ""),
                    _item("empty", "TODO: Author release notes"),
                ],
                "status_counts": {"done": 1},
                "total": 2,
                "not_closed": 0,
            }
        }
        unclassified = [_item("empty", "TODO: Set RN Type and RN Text")]
        table = _format_summary_table(sections, unclassified, [])
        lines = table.split("\n")
        total_line = [ln for ln in lines if ln.startswith("TOTAL")][0]
        nums = [int(x) for x in total_line.split() if x.isdigit()]
        assert nums == [1, 1, 0, 1, 3]

    def test_warnings_note(self):
        warnings = [{"key": "X-1", "message": "test"}]
        table = _format_summary_table({}, [], warnings)
        assert "1 security-level warnings" in table

    def test_no_warnings_no_note(self):
        table = _format_summary_table({}, [], [])
        assert "security-level" not in table

    def test_all_done(self):
        sections = {
            1: {
                "title": "New features and enhancements",
                "items": [_item("done", ""), _item("done", "")],
                "status_counts": {"done": 2},
                "total": 2,
                "not_closed": 0,
            }
        }
        table = _format_summary_table(sections, [], [])
        lines = table.split("\n")
        total_line = [ln for ln in lines if ln.startswith("TOTAL")][0]
        nums = [int(x) for x in total_line.split() if x.isdigit()]
        assert nums == [0, 0, 0, 2, 2]


def _raw_item(
    key,
    project,
    issuetype="Feature",
    rn_type=None,
    rn_status=None,
    rn_text=None,
    fix_versions=None,
    parent_key=None,
    from_query=1,
):
    """Build a raw item dict matching _extract_rn_fields output."""
    return {
        "key": key,
        "summary": f"Summary for {key}",
        "status": "Closed",
        "project": project,
        "issuetype": issuetype,
        "rn_text": rn_text,
        "rn_status": rn_status,
        "rn_type": rn_type,
        "security": None,
        "fix_versions": fix_versions or [],
        "parent_key": parent_key,
        "from_query": from_query,
    }


def _mock_jira_for_parents(parent_items):
    """Build a mock jira client that returns parent items by key."""
    from jirha.config import CF_RN_STATUS, CF_RN_TEXT, CF_RN_TYPE

    jira = MagicMock()

    def issue_side_effect(key, fields=None):
        item = parent_items[key]
        mock_issue = MagicMock()
        mock_issue.key = key
        mock_issue.fields.summary = item.get("summary", f"Summary for {key}")
        mock_issue.fields.status = MagicMock(__str__=lambda s: item.get("status", "Closed"))
        mock_issue.fields.project.key = item["project"]
        mock_issue.fields.issuetype = MagicMock(__str__=lambda s: item.get("issuetype", "Feature"))
        setattr(mock_issue.fields, CF_RN_TEXT, item.get("rn_text"))
        setattr(mock_issue.fields, CF_RN_STATUS, item.get("rn_status"))
        setattr(mock_issue.fields, CF_RN_TYPE, item.get("rn_type"))
        mock_issue.fields.security = None

        class FakeVersion:
            def __init__(self, name):
                self.name = name

        mock_issue.fields.fixVersions = [FakeVersion(v) for v in item.get("fix_versions", [])]
        if item.get("parent_key"):
            mock_issue.fields.parent = MagicMock()
            mock_issue.fields.parent.key = item["parent_key"]
        else:
            mock_issue.fields.parent = None
        return mock_issue

    jira.issue = MagicMock(side_effect=issue_side_effect)
    return jira


class TestResolveAndGroupFiltering:
    def test_subtask_excluded(self):
        """Sub-tasks in RHDHPLAN should be excluded from RN targets."""
        raw_items = [
            _raw_item("RHDHPLAN-990", "RHDHPLAN", issuetype="Sub-task", fix_versions=["1.9.0"]),
        ]
        jira = MagicMock()
        sections, unclassified, not_required, *_ = _resolve_and_group(
            jira, raw_items, "1.9", ["1.9.0"]
        )
        all_keys = {e["key"] for e in unclassified}
        for sec in sections.values():
            all_keys.update(it["key"] for it in sec["items"])
        assert "RHDHPLAN-990" not in all_keys

    def test_rhidp_not_rn_target(self):
        """RHIDP issues should resolve to their parent, not become RN targets themselves."""
        raw_items = [
            _raw_item(
                "RHIDP-9604",
                "RHIDP",
                issuetype="Epic",
                fix_versions=["1.9.0"],
                parent_key="RHDHPLAN-667",
            ),
        ]
        parent_items = {
            "RHDHPLAN-667": {
                "project": "RHDHPLAN",
                "issuetype": "Feature",
                "rn_type": "Developer Preview",
                "rn_status": "Done",
                "fix_versions": ["1.9.0"],
            },
        }
        jira = _mock_jira_for_parents(parent_items)
        sections, unclassified, not_required, *_ = _resolve_and_group(
            jira, raw_items, "1.9", ["1.9.0"]
        )
        all_keys = set()
        for sec in sections.values():
            all_keys.update(it["key"] for it in sec["items"])
        assert "RHIDP-9604" not in all_keys
        assert "RHDHPLAN-667" in all_keys

    def test_rhidp_parent_wrong_fix_version_excluded(self):
        """When an RHIDP child resolves to a parent with a different fix version, exclude it."""
        raw_items = [
            _raw_item(
                "RHIDP-7609",
                "RHIDP",
                issuetype="Task",
                fix_versions=["1.9.0"],
                parent_key="RHDHPLAN-495",
            ),
        ]
        parent_items = {
            "RHDHPLAN-495": {
                "project": "RHDHPLAN",
                "issuetype": "Feature",
                "rn_type": None,
                "rn_status": None,
                "fix_versions": ["1.8.0"],
            },
        }
        jira = _mock_jira_for_parents(parent_items)
        sections, unclassified, not_required, *_ = _resolve_and_group(
            jira, raw_items, "1.9", ["1.9.0", "1.9.1"]
        )
        all_keys = {e["key"] for e in unclassified}
        for sec in sections.values():
            all_keys.update(it["key"] for it in sec["items"])
        for nr in not_required:
            all_keys.add(nr["key"])
        assert "RHDHPLAN-495" not in all_keys

    def test_rhidp_grandparent_wrong_fix_version_excluded(self):
        """When RHIDP→RHIDP→RHDHPLAN grandparent has wrong fix version, exclude it."""
        raw_items = [
            _raw_item(
                "RHIDP-100",
                "RHIDP",
                issuetype="Task",
                fix_versions=["1.9.0"],
                parent_key="RHIDP-200",
            ),
        ]
        parent_items = {
            "RHIDP-200": {
                "project": "RHIDP",
                "issuetype": "Epic",
                "fix_versions": ["1.9.0"],
                "parent_key": "RHDHPLAN-300",
            },
            "RHDHPLAN-300": {
                "project": "RHDHPLAN",
                "issuetype": "Feature",
                "rn_type": "Feature",
                "rn_status": "Done",
                "fix_versions": ["1.7.0"],
            },
        }
        jira = _mock_jira_for_parents(parent_items)
        sections, unclassified, not_required, *_ = _resolve_and_group(
            jira, raw_items, "1.9", ["1.9.0"]
        )
        all_keys = set()
        for sec in sections.values():
            all_keys.update(it["key"] for it in sec["items"])
        for e in unclassified:
            all_keys.add(e["key"])
        assert "RHDHPLAN-300" not in all_keys

    def test_non_rhidp_feature_included(self):
        """Regular RHDHPLAN Features with matching fix version are included."""
        raw_items = [
            _raw_item(
                "RHDHPLAN-100",
                "RHDHPLAN",
                issuetype="Feature",
                rn_type="Feature",
                rn_status="Done",
                fix_versions=["1.9.0"],
            ),
        ]
        jira = MagicMock()
        sections, unclassified, *_ = _resolve_and_group(jira, raw_items, "1.9", ["1.9.0"])
        sec1_keys = {it["key"] for it in sections.get(1, {}).get("items", [])}
        assert "RHDHPLAN-100" in sec1_keys

    def test_rhdhbugs_bug_included(self):
        """RHDHBUGS Bugs with matching fix version are included."""
        raw_items = [
            _raw_item(
                "RHDHBUGS-100",
                "RHDHBUGS",
                issuetype="Bug",
                rn_type="Bug Fix",
                rn_status="Done",
                fix_versions=["1.9.0"],
            ),
        ]
        jira = MagicMock()
        sections, *_ = _resolve_and_group(jira, raw_items, "1.9", ["1.9.0"])
        sec7_keys = {it["key"] for it in sections.get(7, {}).get("items", [])}
        assert "RHDHBUGS-100" in sec7_keys
