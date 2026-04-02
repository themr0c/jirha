from jirha.api import _extract_jira_keys
from jirha.ops.hygiene import _parse_sp_choice


def test_parse_all():
    mismatches = [{"key": "RHIDP-1"}, {"key": "RHIDP-2"}]
    apply, overrides = _parse_sp_choice("a", mismatches)
    assert apply == {0, 1}
    assert overrides == {}


def test_parse_all_word():
    mismatches = [{"key": "RHIDP-1"}, {"key": "RHIDP-2"}]
    apply, overrides = _parse_sp_choice("all", mismatches)
    assert apply == {0, 1}
    assert overrides == {}


def test_parse_individual():
    mismatches = [{"key": "RHIDP-1"}, {"key": "RHIDP-2"}]
    apply, overrides = _parse_sp_choice("1", mismatches)
    assert apply == {0}
    assert overrides == {}


def test_parse_multiple():
    mismatches = [{"key": "RHIDP-1"}, {"key": "RHIDP-2"}, {"key": "RHIDP-3"}]
    apply, overrides = _parse_sp_choice("1,3", mismatches)
    assert apply == {0, 2}
    assert overrides == {}


def test_parse_override():
    mismatches = [{"key": "RHIDP-1"}]
    apply, overrides = _parse_sp_choice("1=5", mismatches)
    assert apply == {0}
    assert overrides == {0: 5}


def test_parse_none_or_unknown():
    mismatches = [{"key": "RHIDP-1"}]
    apply, overrides = _parse_sp_choice("n", mismatches)
    assert apply == set()
    assert overrides == {}


def test_parse_out_of_range_ignored():
    mismatches = [{"key": "RHIDP-1"}]
    apply, overrides = _parse_sp_choice("99", mismatches)
    assert apply == set()
    assert overrides == {}


# --- _extract_jira_keys tests ---


def test_extract_keys_from_title():
    assert _extract_jira_keys("RHIDP-1234: fix docs") == {"RHIDP-1234"}


def test_extract_multiple_keys():
    assert _extract_jira_keys("RHIDP-1 and RHDHBUG-99") == {"RHIDP-1", "RHDHBUG-99"}


def test_extract_keys_from_branch():
    assert _extract_jira_keys("feature/RHIDP-5678-add-auth") == {"RHIDP-5678"}


def test_extract_keys_none():
    assert _extract_jira_keys(None) == set()


def test_extract_keys_no_match():
    assert _extract_jira_keys("no jira key here") == set()
