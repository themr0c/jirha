from datetime import date, timedelta

from jirha.cache import (
    cache_age_str,
    read_cache,
    read_sprint_cache,
    write_cache,
    write_sprint_cache,
)


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


class TestSprintCache:
    def _sprint_data(self, end_offset_days=7):
        end = date.today() + timedelta(days=end_offset_days)
        return {
            "current_sprint": {
                "id": 100,
                "name": "Test Sprint",
                "start": (end - timedelta(days=14)).isoformat(),
                "end": end.isoformat(),
                "board_id": 42,
            },
            "next_sprint": None,
            "team_name": "Test Team",
        }

    def test_write_and_read(self, tmp_path):
        data = self._sprint_data()
        write_sprint_cache(tmp_path, data)
        result = read_sprint_cache(tmp_path)
        assert result is not None
        assert result["current_sprint"]["name"] == "Test Sprint"
        assert result["next_sprint"] is None

    def test_expired_cache_returns_none(self, tmp_path):
        data = self._sprint_data(end_offset_days=-1)
        write_sprint_cache(tmp_path, data)
        result = read_sprint_cache(tmp_path)
        assert result is None

    def test_missing_cache_returns_none(self, tmp_path):
        result = read_sprint_cache(tmp_path)
        assert result is None

    def test_next_sprint_preserved(self, tmp_path):
        data = self._sprint_data()
        data["next_sprint"] = {
            "id": 101,
            "name": "Next Sprint",
            "start": None,
            "end": None,
            "board_id": 42,
        }
        write_sprint_cache(tmp_path, data)
        result = read_sprint_cache(tmp_path)
        assert result["next_sprint"]["name"] == "Next Sprint"
