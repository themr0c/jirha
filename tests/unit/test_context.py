from jirha.api import _is_doc_repo
from jirha.ops.context import (
    _extract_links,
    _extract_pr_urls,
    _is_eng_task,
    _suggest_sp_range,
    format_context,
)

# --- _is_doc_repo ---


def test_is_doc_repo_rhdh():
    assert _is_doc_repo(
        "https://github.com/redhat-developer/red-hat-developers-documentation-rhdh/pull/123"
    )


def test_is_doc_repo_other():
    assert not _is_doc_repo("https://github.com/redhat-developer/rhdh-operator/pull/456")


def test_is_doc_repo_partial_match():
    assert _is_doc_repo("https://github.com/org/red-hat-developers-documentation-other/pull/1")


# --- _extract_pr_urls ---


def test_extract_pr_urls_plain():
    text = "https://github.com/org/repo/pull/123"
    assert _extract_pr_urls(text) == ["https://github.com/org/repo/pull/123"]


def test_extract_pr_urls_wiki_markup():
    text = (
        "[https://github.com/org/repo/pull/1|https://github.com/org/repo/pull/1|smart-link]\n"
        "[https://github.com/org/repo/pull/2|https://github.com/org/repo/pull/2|smart-link]"
    )
    urls = _extract_pr_urls(text)
    # Duplicates from wiki markup format
    assert "https://github.com/org/repo/pull/1" in urls
    assert "https://github.com/org/repo/pull/2" in urls


def test_extract_pr_urls_empty():
    assert _extract_pr_urls("") == []
    assert _extract_pr_urls(None) == []


# --- _suggest_sp_range ---


def test_suggest_sp_range_multiple():
    metrics = [
        {"sp": 3, "url": "", "reason": "", "number": "1"},
        {"sp": 5, "url": "", "reason": "", "number": "2"},
        {"sp": 5, "url": "", "reason": "", "number": "3"},
    ]
    result = _suggest_sp_range(metrics)
    assert result is not None
    low, high = result
    assert low <= 5 <= high


def test_suggest_sp_range_insufficient():
    metrics = [{"sp": 3, "url": "", "reason": "", "number": "1"}]
    assert _suggest_sp_range(metrics) is None


def test_suggest_sp_range_empty():
    assert _suggest_sp_range([]) is None


def test_suggest_sp_range_all_zeros():
    metrics = [
        {"sp": 0, "url": "", "reason": "", "number": "1"},
        {"sp": 0, "url": "", "reason": "", "number": "2"},
    ]
    assert _suggest_sp_range(metrics) is None


# --- format_context ---


def _eng_metric(url, sp):
    return {"url": url, "sp": sp, "reason": "reason", "number": "1"}


class _FakeFields:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _FakeIssue:
    def __init__(self, key, summary="", description="", status="New", sp=0, components=None):
        self.key = key
        self.fields = _FakeFields(
            summary=summary,
            description=description,
            status=status,
            components=components or [],
            **{"customfield_10028": sp},
        )


def test_format_context_standalone():
    ctx = {
        "task": _FakeIssue("RHDHBUGS-100", "Fix broken link", "Some desc", "New"),
        "epic": None,
        "feature": None,
        "sibling_epics": [],
        "eng_metrics": [],
        "suggested_sp_range": None,
        "data_quality": "none",
    }
    output = format_context(ctx)
    assert "RHDHBUGS-100" in output
    assert "Standalone task" in output


def test_format_context_with_range():
    ctx = {
        "task": _FakeIssue("RHIDP-1234", "Doc new feature", "", "New"),
        "epic": _FakeIssue("RHIDP-100", "Epic A", "Epic description"),
        "feature": _FakeIssue("RHDHPLAN-50", "Feature X", "Feature description"),
        "sibling_epics": [],
        "eng_metrics": [
            _eng_metric("https://github.com/org/repo/pull/1", 5),
            _eng_metric("https://github.com/org/repo/pull/2", 3),
        ],
        "suggested_sp_range": (2, 5),
        "data_quality": "weak",
    }
    output = format_context(ctx)
    assert "RHIDP-1234" in output
    assert "2–5 SP" in output
    assert "weak" in output
    assert "Feature X" in output


# --- _is_eng_task ---


def test_is_eng_task_different_team():
    """Task with a non-doc team is engineering."""
    task = _FakeIssue("RHIDP-100")
    task.fields.customfield_10001 = type("Team", (), {"name": "rhdh-core"})()
    assert _is_eng_task(task) is True


def test_is_eng_task_doc_team():
    """Task with RHDH Documentation team is not engineering."""
    task = _FakeIssue("RHIDP-100")
    task.fields.customfield_10001 = type("Team", (), {"name": "RHDH Documentation"})()
    assert _is_eng_task(task) is False


def test_is_eng_task_no_team():
    """Task with no team field defaults to not engineering."""
    task = _FakeIssue("RHIDP-100")
    assert _is_eng_task(task) is False


# --- _extract_links ---


class _FakeLink:
    def __init__(self, link_type, outward_key=None, inward_key=None):
        link_attrs = {"outward": link_type, "inward": link_type, "name": link_type}
        self.type = type("LinkType", (), link_attrs)()
        if outward_key:
            self.outwardIssue = type("Issue", (), {"key": outward_key})()
            self.inwardIssue = None
        else:
            self.outwardIssue = None
            self.inwardIssue = type("Issue", (), {"key": inward_key})()


def test_extract_links_outward():
    links = [_FakeLink("relates to", outward_key="RHIDP-200")]
    result = _extract_links(links)
    assert len(result) == 1
    assert result[0]["key"] == "RHIDP-200"
    assert result[0]["link_type"] == "relates to"
    assert result[0]["direction"] == "outward"


def test_extract_links_empty():
    assert _extract_links([]) == []
    assert _extract_links(None) == []
