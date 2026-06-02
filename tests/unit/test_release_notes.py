from jirha.ops.release_notes import _classify_rn_bucket, _map_to_section


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
