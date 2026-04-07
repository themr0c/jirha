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


# --- Tooling PR tier behavior ---


def test_tooling_uses_total_lines_as_primary():
    """Tooling PRs (0 adoc) use total-lines thresholds as primary tier."""
    files = [{"path": "scripts/build.py", "additions": 400, "deletions": 200}]
    # total = 600 → tier 4 (600-1499)
    tier, reason, pr_type = _pr_metrics(files, commits=1)
    assert pr_type == "tooling"
    assert tier == 4  # 5 SP


def test_tooling_skips_complexity_bump():
    """Tooling PRs skip the complexity bump (adoc-specific signals don't apply)."""
    files = [{"path": f"scripts/s{i}.py", "additions": 15, "deletions": 0} for i in range(15)]
    # total = 225 → tier 2 (100-249), many files + commits but no adoc
    tier, reason, pr_type = _pr_metrics(files, commits=15)
    assert pr_type == "tooling"
    assert tier == 2  # no bump despite 15 commits and 15 files


def test_tooling_small_pr():
    """Small tooling PR → tier 0."""
    files = [{"path": ".github/workflows/ci.yml", "additions": 5, "deletions": 3}]
    # total = 8 → tier 0 (<20)
    tier, reason, pr_type = _pr_metrics(files, commits=1)
    assert pr_type == "tooling"
    assert tier == 0  # 0 SP


def test_tooling_large_pr():
    """Large tooling PR → high tier."""
    files = [{"path": "build/index.js", "additions": 3000, "deletions": 2500}]
    # total = 5500 → tier 6 (5000-14999)
    tier, reason, pr_type = _pr_metrics(files, commits=5)
    assert pr_type == "tooling"
    assert tier == 6  # 13 SP


def test_mixed_uses_higher_of_adoc_and_total():
    """Mixed PRs use the higher of adoc tier and total-lines tier."""
    files = [
        _adoc("docs/file.adoc", 20, 5),  # 25 adoc → tier 1
        {"path": "scripts/build.py", "additions": 400, "deletions": 200},  # 600 non-adoc
    ]
    # total = 625 → total tier 4 (600-1499), adoc tier 1 → max(1, 4) = 4
    tier, reason, pr_type = _pr_metrics(files, commits=1)
    assert pr_type == "mixed"
    assert tier == 4  # 5 SP — total-lines wins


# --- Multi-PR aggregation ---


from unittest.mock import patch
from jirha.api import _assess_multi_pr_sp


def _mock_gh_pr_view(files, title="Add docs", commits=1):
    """Build a mock gh pr view JSON response."""
    import json
    return json.dumps({
        "files": files,
        "commits": [{"oid": f"abc{i}"} for i in range(commits)],
        "title": title,
    })


def test_assess_multi_pr_aggregation():
    """Multiple PRs aggregate their file metrics."""
    pr_field = (
        "https://github.com/org/repo/pull/100\n"
        "https://github.com/org/repo/pull/101\n"
    )
    pr100_files = [{"path": "docs/a.adoc", "additions": 30, "deletions": 5}]
    pr101_files = [{"path": "docs/b.adoc", "additions": 40, "deletions": 10}]

    def mock_run(cmd, **kwargs):
        class Result:
            returncode = 0
        r = Result()
        if "100" in cmd:
            r.stdout = _mock_gh_pr_view(pr100_files)
        else:
            r.stdout = _mock_gh_pr_view(pr101_files)
        return r

    with patch("jirha.api.subprocess.run", side_effect=mock_run):
        result = _assess_multi_pr_sp(pr_field)

    assert result is not None
    sp, reason, pr_numbers = result
    assert set(pr_numbers) == {"100", "101"}
    # Combined: 30+5 + 40+10 = 85 adoc lines → tier 3 (60-119)
    assert sp == 3
    assert "2 PRs" in reason


def test_assess_multi_pr_single_url():
    """Single PR URL works like _assess_pr_sp."""
    pr_field = "https://github.com/org/repo/pull/42\n"
    files = [{"path": "docs/a.adoc", "additions": 10, "deletions": 5}]

    def mock_run(cmd, **kwargs):
        class Result:
            returncode = 0
            stdout = _mock_gh_pr_view(files)
        return Result()

    with patch("jirha.api.subprocess.run", side_effect=mock_run):
        result = _assess_multi_pr_sp(pr_field)

    assert result is not None
    sp, reason, pr_numbers = result
    assert pr_numbers == ["42"]
    # 15 adoc lines → tier 1
    assert sp == 1
    assert "1 PR" in reason


def test_assess_multi_pr_cherry_pick_by_title():
    """PRs with [release-*] title prefix are treated as cherry-picks."""
    pr_field = (
        "https://github.com/org/repo/pull/100\n"
        "https://github.com/org/repo/pull/101\n"
    )
    files = [{"path": "docs/a.adoc", "additions": 50, "deletions": 10}]

    def mock_run(cmd, **kwargs):
        class Result:
            returncode = 0
        r = Result()
        if "100" in cmd:
            r.stdout = _mock_gh_pr_view(files, title="Add new feature docs")
        else:
            r.stdout = _mock_gh_pr_view(files, title="[release-1.8] Add new feature docs")
        return r

    with patch("jirha.api.subprocess.run", side_effect=mock_run):
        result = _assess_multi_pr_sp(pr_field)

    sp, reason, pr_numbers = result
    # PR 101 is a cherry-pick, only PR 100 metrics counted
    # 60 adoc lines → tier 3 (60-119) → 3 SP
    assert sp == 3
    assert "1 cherry-pick" in reason
    assert len(pr_numbers) == 2  # both PRs listed, but metrics from 1


def test_assess_multi_pr_cherry_pick_by_total_lines():
    """PRs with identical total_lines and >80% file overlap are cherry-picks."""
    pr_field = (
        "https://github.com/org/repo/pull/100\n"
        "https://github.com/org/repo/pull/101\n"
    )
    files = [
        {"path": "docs/a.adoc", "additions": 30, "deletions": 5},
        {"path": "docs/b.adoc", "additions": 10, "deletions": 5},
    ]

    def mock_run(cmd, **kwargs):
        class Result:
            returncode = 0
            # Same files, same totals → cherry-pick
            stdout = _mock_gh_pr_view(files, title="Add docs")
        return Result()

    with patch("jirha.api.subprocess.run", side_effect=mock_run):
        result = _assess_multi_pr_sp(pr_field)

    sp, reason, pr_numbers = result
    # Only 1 PR's metrics counted: 50 adoc lines → tier 2
    assert "1 cherry-pick" in reason


def test_assess_multi_pr_no_false_cherry_pick():
    """PRs with same total_lines but different files are NOT cherry-picks."""
    pr_field = (
        "https://github.com/org/repo/pull/100\n"
        "https://github.com/org/repo/pull/101\n"
    )
    pr100_files = [{"path": "docs/a.adoc", "additions": 25, "deletions": 25}]
    pr101_files = [{"path": "docs/z.adoc", "additions": 25, "deletions": 25}]
    # Same total (50) but 0% file overlap → NOT a cherry-pick

    def mock_run(cmd, **kwargs):
        class Result:
            returncode = 0
        r = Result()
        if "100" in cmd:
            r.stdout = _mock_gh_pr_view(pr100_files)
        else:
            r.stdout = _mock_gh_pr_view(pr101_files)
        return r

    with patch("jirha.api.subprocess.run", side_effect=mock_run):
        result = _assess_multi_pr_sp(pr_field)

    sp, reason, pr_numbers = result
    # Both PRs counted — no cherry-pick dedup
    assert "cherry-pick" not in reason
    # Combined: 100 adoc lines → tier 3
    assert sp == 3
