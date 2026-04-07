from jirha.api import _pr_metrics


def _adoc(path, additions, deletions):
    return {"path": path, "additions": additions, "deletions": deletions}


# --- Base tier thresholds (adoc lines) ---
# <5=tier0(0SP), 5-29=tier1(1SP), 30-59=tier2(2SP), 60-119=tier3(3SP),
# 120-299=tier4(5SP), 300-549=tier5(8SP), 550-1199=tier6(13SP), 1200+=tier6


def test_tier_0_trivial():
    files = [_adoc("docs/file.adoc", 2, 1)]  # 3 lines
    tier, reason, _ = _pr_metrics(files, commits=1)
    assert tier == 0  # 0 SP
    assert "1 .adoc files" in reason


def test_tier_1_small_fix():
    files = [_adoc("docs/file.adoc", 10, 5)]  # 15 lines
    tier, reason, _ = _pr_metrics(files, commits=1)
    assert tier == 1  # 1 SP


def test_tier_2_simple_task():
    files = [_adoc("docs/file.adoc", 25, 10)]  # 35 lines
    tier, reason, _ = _pr_metrics(files, commits=1)
    assert tier == 2  # 2 SP


def test_tier_3_moderate():
    files = [_adoc("docs/file.adoc", 50, 20)]  # 70 lines
    tier, reason, _ = _pr_metrics(files, commits=1)
    assert tier == 3  # 3 SP


def test_tier_4_significant():
    files = [_adoc("docs/file.adoc", 150, 0)]  # 150 lines
    tier, reason, _ = _pr_metrics(files, commits=1)
    assert tier == 4  # 5 SP


def test_tier_5_large():
    files = [_adoc("docs/file.adoc", 400, 0)]  # 400 lines
    tier, reason, _ = _pr_metrics(files, commits=1)
    assert tier == 5  # 8 SP


def test_tier_6_very_large():
    files = [_adoc("docs/file.adoc", 700, 0)]  # 700 lines
    tier, reason, _ = _pr_metrics(files, commits=1)
    assert tier == 6  # 13 SP


def test_tier_6_massive():
    files = [_adoc("docs/file.adoc", 1500, 0)]  # 1500 lines, still tier 6
    tier, reason, _ = _pr_metrics(files, commits=1)
    assert tier == 6  # 13 SP (capped, never suggests 21)


# --- Non-adoc files don't affect adoc tier ---


def test_non_adoc_files_ignored_for_adoc_tier():
    files = [
        {"path": "images/img.png", "additions": 0, "deletions": 0},
        _adoc("docs/file.adoc", 10, 5),  # 15 lines → tier 1
    ]
    tier, reason, _ = _pr_metrics(files, commits=1)
    assert tier == 1


# --- Complexity bump (2+ of: new_adoc>=2, adoc_files>=12, commits>=12) ---


def test_complexity_bump_new_adoc_and_many_files():
    # 14 new adoc files, each 10 lines = 140 lines → tier 4 (5SP)
    # 2+ new files + 12+ adoc files → bump to tier 5 (8SP)
    files = [_adoc(f"docs/new{i}.adoc", 10, 0) for i in range(14)]
    tier, reason, _ = _pr_metrics(files, commits=1)
    assert tier == 5  # bumped from 4 to 5


def test_complexity_bump_new_adoc_and_commits():
    # 3 new adoc files, 70 lines each = 210 lines → tier 4 (5SP)
    # 2+ new files + 12+ commits → bump to tier 5 (8SP)
    files = [_adoc(f"docs/new{i}.adoc", 70, 0) for i in range(3)]
    tier, reason, _ = _pr_metrics(files, commits=15)
    assert tier == 5  # bumped from 4 to 5


def test_no_bump_with_single_signal():
    # 3 new adoc files but only 2 commits and 3 total files → only 1 signal
    files = [_adoc(f"docs/new{i}.adoc", 30, 0) for i in range(3)]  # 90 lines → tier 3
    tier, reason, _ = _pr_metrics(files, commits=2)
    assert tier == 3  # no bump


def test_bump_capped_at_tier_5():
    # Even with many signals, bump can't exceed tier 5 (8SP → won't go to 13SP)
    files = [_adoc(f"docs/new{i}.adoc", 30, 0) for i in range(15)]  # 450 lines → tier 5
    tier, reason, _ = _pr_metrics(files, commits=20)
    assert tier == 5  # capped, not 6


# --- Mechanical discount ---


def test_mechanical_discount():
    # 10 files × 4 lines each = 40 lines (tier 2), all mechanical → tier 1
    files = [_adoc(f"docs/file{i}.adoc", 2, 2) for i in range(10)]
    tier, reason, _ = _pr_metrics(files, commits=1)
    assert tier == 1  # discounted from tier 2
    assert "mechanical" in reason


def test_mechanical_requires_more_than_3_files():
    # Only 3 files → not mechanical even if all <= 4 lines
    files = [_adoc(f"docs/file{i}.adoc", 2, 2) for i in range(3)]
    tier, reason, _ = _pr_metrics(files, commits=1)
    assert "mechanical" not in reason


def test_mechanical_only_when_adoc_dominant():
    """Mechanical discount doesn't apply when adoc is a small fraction."""
    files = [_adoc(f"docs/file{i}.adoc", 2, 2) for i in range(10)] + [
        {"path": "scripts/big.py", "additions": 200, "deletions": 0},
    ]
    # 10 adoc files × 4 lines = 40 adoc lines → tier 2
    # total = 240, adoc = 40 → adoc is 17% of total → no mechanical discount
    # But total_lines floor: 240 → tier 2 (100-249)
    tier, reason, _ = _pr_metrics(files, commits=1)
    assert tier == 2  # no discount applied (adoc < 50% of total)
    assert "mechanical" in reason  # still labeled, just not discounted


# --- Total-lines floor (tooling/script PRs) ---
# <20=tier0, 20-99=tier1, 100-249=tier2, 250-599=tier3,
# 600-1499=tier4, 1500-4999=tier5, 5000-14999=tier6, 15000+=tier6


def test_total_lines_floor_small_tooling():
    """Small tooling PR gets floor tier from total lines."""
    files = [
        _adoc("docs/file.adoc", 2, 1),  # 3 adoc lines → tier 0
        {"path": "scripts/tool.js", "additions": 150, "deletions": 50},
    ]
    # total = 203 → floor tier 2 (100-249); max(0, 2) = 2
    tier, reason, _ = _pr_metrics(files, commits=1)
    assert tier == 2


def test_total_lines_floor_large_tooling():
    """Large tooling PR gets high floor tier."""
    files = [
        _adoc("docs/f1.adoc", 1, 1),
        _adoc("docs/f2.adoc", 1, 1),
        _adoc("docs/f3.adoc", 1, 1),
        _adoc("docs/f4.adoc", 1, 1),
        {"path": "build/index.js", "additions": 4000, "deletions": 3000},
    ]
    # adoc: 8 lines → tier 1, total = 7008 → floor tier 6 (5000-14999)
    # mechanical fires but adoc < 50% of total → no discount
    tier, reason, _ = _pr_metrics(files, commits=1)
    assert tier == 6  # 13 SP


def test_total_lines_floor_does_not_lower_adoc_tier():
    """Total-lines floor never lowers the adoc-based tier."""
    files = [_adoc("docs/file.adoc", 400, 0)]  # 400 adoc lines → tier 5
    # total = 400 → floor tier 3 (250-599); max(5, 3) = 5
    tier, reason, _ = _pr_metrics(files, commits=1)
    assert tier == 5


# --- Task-type classification ---


def test_pr_type_doc():
    """Pure doc PR: adoc lines > 50% of total → pr_type='doc'."""
    files = [_adoc("docs/file.adoc", 100, 20)]  # 120 adoc, 120 total
    tier, reason, pr_type = _pr_metrics(files, commits=1)
    assert pr_type == "doc"


def test_pr_type_tooling():
    """Zero adoc files → pr_type='tooling'."""
    files = [
        {"path": "scripts/build.py", "additions": 200, "deletions": 50},
        {"path": ".github/workflows/ci.yml", "additions": 30, "deletions": 10},
    ]
    tier, reason, pr_type = _pr_metrics(files, commits=1)
    assert pr_type == "tooling"


def test_pr_type_mixed():
    """Adoc files present but < 50% of total lines → pr_type='mixed'."""
    files = [
        _adoc("docs/file.adoc", 20, 5),  # 25 adoc lines
        {"path": "scripts/build.py", "additions": 200, "deletions": 0},  # 200 non-adoc
    ]
    # adoc = 25, total = 225, adoc/total = 11% → mixed
    tier, reason, pr_type = _pr_metrics(files, commits=1)
    assert pr_type == "mixed"
