from jirha.api import _pr_metrics


def _adoc(path, additions, deletions):
    return {'path': path, 'additions': additions, 'deletions': deletions}


def test_tier_0_under_30_lines():
    files = [_adoc('docs/file.adoc', 10, 5)]
    tier, reason = _pr_metrics(files, commits=1)
    assert tier == 0
    assert '1 .adoc files' in reason


def test_tier_1_30_to_149_lines():
    files = [_adoc('docs/file.adoc', 50, 20)]
    tier, reason = _pr_metrics(files, commits=1)
    assert tier == 1  # 70 lines


def test_tier_2_150_to_399_lines():
    files = [_adoc('docs/file.adoc', 200, 0)]
    tier, reason = _pr_metrics(files, commits=1)
    assert tier == 2


def test_tier_3_400_to_799_lines():
    files = [_adoc('docs/file.adoc', 500, 0)]
    tier, reason = _pr_metrics(files, commits=1)
    assert tier == 3


def test_tier_4_800_plus_lines():
    files = [_adoc('docs/file.adoc', 900, 0)]
    tier, reason = _pr_metrics(files, commits=1)
    assert tier == 4


def test_non_adoc_files_ignored():
    files = [
        {'path': 'images/img.png', 'additions': 0, 'deletions': 0},
        _adoc('docs/file.adoc', 10, 5),
    ]
    tier, reason = _pr_metrics(files, commits=1)
    assert tier == 0


def test_complexity_bump_two_signals():
    # 2 new adoc files + 2 assembly files = 2 signals → tier+1
    files = [
        _adoc('assemblies/a1.adoc', 50, 0),  # new + assembly
        _adoc('assemblies/a2.adoc', 50, 0),  # new + assembly
    ]
    # base: 100 lines = tier 1; 2 new adocs + 2 assemblies → bump to tier 2
    tier, reason = _pr_metrics(files, commits=1)
    assert tier == 2


def test_complexity_bump_six_commits():
    files = [_adoc('docs/f.adoc', 50, 0), _adoc('docs/g.adoc', 50, 0)]
    # base: 100 lines = tier 1; 6 commits alone is 1 signal, need 1 more
    tier_without, _ = _pr_metrics(files, commits=5)
    tier_with, _ = _pr_metrics(files, commits=6)
    # With 2 new adoc files + 6 commits = 2 signals → bump
    assert tier_with == tier_without + 1 or tier_with == 4  # capped at 4


def test_mechanical_discount():
    # 10 files × 4 lines each = 40 lines (tier 1), all mechanical → tier 0
    files = [_adoc(f'docs/file{i}.adoc', 2, 2) for i in range(10)]
    tier, reason = _pr_metrics(files, commits=1)
    assert tier == 0
    assert 'mechanical' in reason


def test_mechanical_requires_more_than_3_files():
    # Only 3 files → not mechanical even if all <= 4 lines
    files = [_adoc(f'docs/file{i}.adoc', 2, 2) for i in range(3)]
    tier, reason = _pr_metrics(files, commits=1)
    assert 'mechanical' not in reason


def test_images_counted():
    files = [
        _adoc('docs/file.adoc', 50, 0),
        {'path': 'images/a.png', 'additions': 0, 'deletions': 0},
        {'path': 'images/b.svg', 'additions': 0, 'deletions': 0},
        {'path': 'images/c.jpg', 'additions': 0, 'deletions': 0},
    ]
    # base: 50 lines = tier 1; 1 new adoc + 3 images = 2 signals → bump to tier 2
    tier, reason = _pr_metrics(files, commits=1)
    assert tier == 2
    assert '3 images' in reason
