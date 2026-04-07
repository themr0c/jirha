# SP Heuristics v2: Multi-PR Aggregation, Task-Type Awareness, Threshold Re-derivation

**Date:** 2026-04-10
**Status:** Draft
**Motivation:** The post-PR SP reassessment heuristic has two bugs: (1) it only evaluates the first PR on multi-PR tasks (60% of Jiras have multiple PRs), and (2) it treats tooling/CI tasks the same as doc tasks, causing false positives like RHDHBUGS-2903 (8 SP tooling task suggested as 0 SP). Additionally, thresholds were derived once from the initial dataset and should be reproducibly re-derivable as data grows.

## 1. Multi-PR Aggregation

### Problem

`_sp_reassessment` (hygiene.py:186) passes the raw multi-line PR field to `_assess_pr_sp`, which regex-matches only the first URL. 255 of 426 Jiras (60%) have multiple PRs. Only the first is evaluated.

### Solution

New function `_assess_multi_pr_sp(pr_field)` in `api.py`:

1. Split `pr_field` by newlines, filter valid GitHub PR URLs
2. Fetch file-level data for each via `gh pr view`
3. Deduplicate cherry-picks: PRs with `[release-*]` title prefix or identical `total_lines` to another PR on the same Jira. Count their files only once.
4. Aggregate: union of files (by path, summing additions/deletions for unique paths), max commits
5. Call `_pr_metrics(aggregated_files, max_commits)`
6. Return `(sp, reason, list_of_pr_numbers)`

### Cherry-pick detection

A PR is a cherry-pick if:
- Its title starts with `[release-` (branch backport convention), OR
- Its `total_lines` matches exactly another PR on the same Jira AND the file lists overlap by >80% (prevents false-matching unrelated PRs that happen to have the same line count)

Cherry-pick file metrics are excluded from aggregation. The PR count in the reason string distinguishes: `3 PRs (2 cherry-picks)`.

## 2. Task-Type Classification

### Problem

The heuristic treats everything as a doc task. 52 of 1090 PRs (5%) have 0 `.adoc` files — tooling, CI workflows, config. The total-lines floor catches them but uses doc-calibrated thresholds.

### Classification

Applied to the aggregated PR set (not individual PRs):

| Type | Rule | Dataset count |
|---|---|---|
| **doc** | `.adoc` lines > 50% of total lines | ~1020 PRs |
| **tooling** | 0 `.adoc` files | ~52 PRs |
| **mixed** | `.adoc` files present but < 50% of total lines | ~18 PRs |

### Impact on tier logic

- **doc** — existing `.adoc` thresholds as primary tier, total-lines as floor (unchanged)
- **tooling** — total-lines thresholds as *primary* tier (not just floor), skip complexity bump (`.adoc`-specific signals don't apply)
- **mixed** — higher of `.adoc` tier and total-lines tier (current behavior, unchanged)

### Code change

`_pr_metrics()` updated signature:

```python
def _pr_metrics(files, commits):
    """Return (tier, reason, pr_type) where pr_type is 'doc', 'tooling', or 'mixed'."""
```

The `pr_type` classification is determined inside `_pr_metrics` from the file list. No caller changes needed for classification — callers just receive the extra return value.

## 3. Threshold Re-derivation Script

### Purpose

Reproducible script that reads the CSVs, segments by task type, computes percentile boundaries, and outputs updated threshold constants.

### Location

`scripts/derive_thresholds.py`

### Algorithm

1. Read both CSVs (`docs/superpowers/pr_sp_data.csv`, `pr_sp_data_2025.csv`)
2. Aggregate PRs per Jira key (summing metrics, deduplicating cherry-picks)
3. Segment aggregated Jiras into doc/tooling/mixed
4. For each segment and signal (`adoc_total`, `total_lines`), compute p25/p75 per SP level
5. Derive tier boundaries at the midpoint between adjacent SP levels' distributions
6. Round to clean numbers

### Output

- Updated `_ADOC_TIER_THRESHOLDS` and `_TOTAL_TIER_THRESHOLDS` constants (copy-paste into `api.py`)
- Validation summary: for each SP level, % of Jiras landing in the correct tier
- Signal evaluation table (monotonicity + discrimination) to confirm no signal drift
- Warning when segment N < 30 (directional only)

### Output format example

```
=== doc segment (N=380 Jiras) ===
adoc_total thresholds: [5, 30, 60, 120, 300, 550, 1200]  (current)
                       [5, 28, 55, 115, 280, 520, 1100]  (re-derived)
Accuracy: 72% within 1 tier (was 71%)

=== tooling segment (N=18 Jiras) ===
total_lines thresholds: [20, 100, 250, 600, 1500, 5000, 15000]  (current)
Warning: N<30, treat as directional only
```

### Does NOT

- Auto-patch `api.py` — human reviews output and decides
- Touch complexity bump or mechanical discount — re-validated but only changed if data shows drift

## 4. Integration

### New function

```python
def _assess_multi_pr_sp(pr_field):
    """Assess SP from all PRs linked to a Jira.
    Returns (sp, reason, pr_numbers) or None.
    """
```

### Callers updated

| Caller | File | Change |
|---|---|---|
| `_sp_reassessment` | `jirha/ops/hygiene.py` | Replace `_assess_pr_sp(pr_url)` with `_assess_multi_pr_sp(pr_field)` |
| `jirha update --sp auto` | `jirha/ops/issues.py` | Same replacement |

### Backward compatibility

`_assess_pr_sp(single_url)` stays as a public function for single-PR use cases. `_assess_multi_pr_sp` calls it internally per URL, then aggregates.

### Reason string

Multi-PR aggregation noted in reason:
```
3 PRs (2 cherry-picks), 0 .adoc files, +674/-0 lines, tooling
```

## 5. Testing and Verification

### Unit tests

Extend `tests/unit/test_sp.py`:

| Test | What it verifies |
|---|---|
| `test_pr_metrics_tooling` | 0 `.adoc` files → `pr_type="tooling"`, tier from total-lines |
| `test_pr_metrics_mixed` | `.adoc` < 50% total → `pr_type="mixed"` |
| `test_pr_metrics_doc` | Existing tests + `pr_type="doc"` assertion |
| `test_assess_multi_pr_aggregation` | 3 PRs → summed metrics |
| `test_assess_multi_pr_cherry_pick_dedup` | 2 PRs identical `total_lines` → counted once |

### Integration verification

1. Run `scripts/derive_thresholds.py` — confirm output matches or improves current thresholds
2. Run `jirha hygiene --dry-run` — compare before/after:
   - RHDHBUGS-2903 (3 tooling PRs, 8→5 SP) should produce a reasonable suggestion
   - Multi-PR doc tasks should produce aggregated assessments
3. Spot-check `jirha update KEY --sp auto` on a known multi-PR task

### Validation target

Current baseline: ~71% accuracy (within 1 tier). Target: maintain or improve.

## Files Modified

| File | Change |
|---|---|
| `jirha/api.py` | Updated `_pr_metrics` return, new `_assess_multi_pr_sp`, threshold constants |
| `jirha/ops/hygiene.py` | Use `_assess_multi_pr_sp` in `_sp_reassessment` |
| `jirha/ops/issues.py` | Use `_assess_multi_pr_sp` in `--sp auto` |
| `scripts/derive_thresholds.py` | New script |
| `tests/unit/test_sp.py` | New tests for type classification, multi-PR, dedup |
| `docs/sp-heuristics.md` | Updated methodology, thresholds, signal table |
