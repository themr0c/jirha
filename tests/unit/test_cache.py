from jirha.cache import cache_age_str, read_cache, write_cache


def test_write_and_read(tmp_path):
    data = {"key": "RHIDP-1234", "summary": "test"}
    write_cache(tmp_path, "features", "RHDHPLAN-50", data)
    result = read_cache(tmp_path, "features", "RHDHPLAN-50")
    assert result is not None
    assert result["data"]["key"] == "RHIDP-1234"
    assert "cached_at" in result


def test_read_missing(tmp_path):
    result = read_cache(tmp_path, "features", "NONEXISTENT")
    assert result is None


def test_cache_age_str_seconds():
    assert cache_age_str(30) == "30s"


def test_cache_age_str_minutes():
    assert cache_age_str(120) == "2m"


def test_cache_age_str_hours():
    assert cache_age_str(7200) == "2h"


def test_cache_age_str_days():
    assert cache_age_str(172800) == "2d"
