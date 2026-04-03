# Story Points

## SP Reference

Story points are a relative measure of effort, complexity, risk, and uncertainty (not hours). The team uses the Fibonacci sequence: 1, 2, 3, 5, 8, 13, 21. Based on [Vidya Iyengar's SP Estimation guide](https://redhat.atlassian.net).

| SP | Complexity | Risk | Uncertainty | Effort |
|---|---|---|---|---|
| 1 | Simple task, minimal work | Low | None | Very little effort needed |
| 2 | Simple task, minimal work, acceptance criteria are short and can be satisfied with ease | Low | None | Little effort needed |
| 3 | Simple task. Longer acceptance criteria, though they are clear and manageable | Low | Small — may need to consult with peers | Will take some time to complete |
| 5 | Some difficulty but still feasible. Acceptance criteria are mostly clear and manageable | Medium — may need mitigation plan | Small — may need to consult with peers or other sources | Significant amount of sprint needed to complete |
| 8 | Difficult and complicated. Lots of work and lots of acceptance criteria | High — must have a mitigation plan | Medium — may need a spike to investigate it | High effort and will take whole sprint to complete |
| 13 | Story is too big and should be broken into smaller tasks if there is a possibility for a spillover | High — should not be in a sprint as a whole if there are other tasks in addition to this | Large — no idea how to do it, create a spike | Significant effort and may require an entire sprint as a dedicated effort |
| 21 | Story is too big for a 3 week sprint and should be broken into smaller tasks | High — should not be in a sprint | Large — no idea how to do it, create a spike | Significant effort and will require more than one sprint to complete |

**Key rules:**
- Sub-tasks (peer review, SME review, QE review) do not get SP.
- Epics do not get SP.
- SP must be assigned before the sprint begins, never after work has started.
- Do not modify SP of spillover tasks.
- Tasks estimated at 13+ SP should be split into smaller Jiras.

## SP Heuristics

`jirha update KEY --sp auto` and `jirha hygiene` assess story points by analyzing the linked GitHub PR. Hygiene only flags mismatches of 2+ tiers.

### How thresholds were derived

Thresholds are empirical, derived from 380 Jira issues with SP across 1088 merged PRs in 2025–2026. Raw data is in `docs/superpowers/pr_sp_data*.csv`.

**Methodology:**

1. Harvested file-level metrics (additions, deletions, file types) and commit counts for every PR merged in 2025–2026 in `redhat-developer/red-hat-developers-documentation-rhdh`.
2. Cross-referenced each PR to its Jira issue via key in the PR title or branch name, and fetched the human-assigned SP value.
3. Aggregated metrics per Jira (some issues have multiple PRs — cherry-picks, follow-ups).
4. For each SP level, computed the 25th and 75th percentile of `.adoc` lines changed.
5. Set each tier boundary at the **midpoint** between the 75th percentile of the lower SP and the 25th percentile of the upper SP — the natural separation point where the two distributions overlap least.

**Boundary derivation (`.adoc` lines changed):**

| Transition | Lower SP p75 | Upper SP p25 | Midpoint | Threshold used |
|---|---|---|---|---|
| 1 → 2 SP | 72 | 18 | 45 | 30 |
| 2 → 3 SP | 116 | 43 | 79 | 60 |
| 3 → 5 SP | 210 | 126 | 168 | 120 |
| 5 → 8 SP | 420 | 197 | 308 | 300 |
| 8 → 13 SP | 668 | 462 | 565 | 550 |

Where the midpoint and the chosen threshold differ, the threshold was rounded to a clean number that better splits the distributions.

Note that the lower SP p75 often exceeds the upper SP p25 (e.g., 1 SP p75=72 > 2 SP p25=18). This overlap is expected — SP measures effort, complexity, risk, and uncertainty, not just line count. The heuristic is a starting signal, not a definitive answer.

**Signal selection:** 22 parameters were evaluated across two rounds. The first round (from the base CSV) evaluated line counts, file counts, commits, images, and assemblies. The second round used enriched data (review rounds, approvals, reviewer count, CI results, PR body length, directory diversity, days open, PR comments, Jira comments, link count, subtask count, sprint count, cycle time, status changes). Each was scored for monotonicity (does the median consistently increase with SP?) and discrimination (how well does a threshold separate high-SP from low-SP tasks). Only signals with monotonicity ≥ 0.80 and discrimination ≥ +30 were retained.

**Full signal evaluation (380 Jiras, 1088 PRs):**

| Signal | Monotonicity | Discrimination | Verdict |
|---|---|---|---|
| adoc_total | 1.00 | +50.8 | **Primary signal** (base tier) |
| total_lines | 1.00 | +51.2 | **Floor signal** (tooling PRs) |
| adoc_files | 1.00 | +41.4 | **Bump signal** (≥12) |
| commits | 0.80 | +37.4 | **Bump signal** (≥12) |
| new_adoc_files | 1.00 | +51.7* | **Bump signal** (≥2, requires 2-of-3) |
| dir_count | 1.00 | +33.5 | Redundant with adoc_files |
| module_dir_count | 1.00 | +24.6 | Redundant with adoc_files |
| reviewer_count | 0.80 | +17.2 | Too weak |
| subtask_count | 0.80 | +17.3 | Non-monotonic at SP 13 |
| jira_comment_count | 0.80 | +15.5 | Too weak |
| pr_body_length | 0.60 | +14.6 | Flat for SP 1–5, spikes at 13 |
| sprint_count | 0.80 | +13.0 | Non-monotonic at SP 13 |
| days_open | 0.60 | +12.6 | Non-monotonic |
| status_changes | 0.80 | +4.2 | Near-zero discrimination |
| comments | 0.80 | −0.1 | Flat across all SP levels |
| review_rounds | 1.00 | 0.0 | All zeros (rarely used in this repo) |
| approvals | 0.80 | −8.9 | Inverse signal (drops at SP 13) |
| in_progress_days | 1.00 | 0.0 | All zeros (not used for time tracking) |
| ci_failures | 1.00 | 0.0 | All zeros |
| ci_total | 0.80 | −4.9 | No signal |
| assembly_files | — | 0.0 | Zero signal across all SP levels |
| image_files | — | 0.0 | Zero signal across all SP levels |

*new_adoc_files discrimination is measured at the ≥2 threshold within the bump system, not standalone.

### Thresholds

**Base tier** — determined by .adoc line volume (additions + deletions):

| Lines changed | Tier | SP |
|---|---|---|
| < 5 | 0 | 0 |
| 5–29 | 1 | 1 |
| 30–59 | 2 | 2 |
| 60–119 | 3 | 3 |
| 120–299 | 4 | 5 |
| 300–549 | 5 | 8 |
| 550–1199 | 6 | 13 |
| 1200+ | 6 | 13 |

Auto-suggest caps at 13 SP. 21 SP is accepted as valid but never auto-suggested (the team guide says 21 SP should be split).

**Complexity bumps** (tier +1, capped at tier 5 = 8 SP, if 2+ signals present):
- 2+ new .adoc files (no deletions, >5 lines added) — discrimination: +51.7
- 12+ total .adoc files touched — discrimination: +46.9
- 12+ commits — discrimination: +32.7

The bump requires 2 of 3 signals to fire. With the current thresholds, the bump fires for 5% of 1 SP tasks (false positive) vs 75–92% of 8–13 SP tasks (true positive).

**Total-lines floor** (for tooling/script PRs): when non-.adoc changes dominate, total lines across all files set a minimum tier:

| Total lines | Floor tier | SP |
|---|---|---|
| < 20 | 0 | 0 |
| 20–99 | 1 | 1 |
| 100–249 | 2 | 2 |
| 250–599 | 3 | 3 |
| 600–1499 | 4 | 5 |
| 1500–4999 | 5 | 8 |
| 5000–14999 | 6 | 13 |
| 15000+ | 6 | 13 |

**Mechanical discount** (tier -1): if >80% of .adoc files have ≤4 lines changed, there are 4+ .adoc files, and .adoc accounts for >50% of total lines changed.

## Jira-Only Estimation (No PR)

When a doc task has no linked PR, `--sp auto` falls back to Jira-only context. This section documents the investigation into Jira-based signals and why a statistical heuristic is not feasible.

### Investigation (100 doc tasks, 2023–2026)

**Hierarchy structure:** Doc tasks sit under epics, which sit under features (often in RHDHPLAN). Features also contain engineering epics with code PRs. The hypothesis was that engineering PR size could proxy doc effort.

**Coverage problem:**
- 86% of doc tasks have a parent epic
- 40% have a feature (grandparent)
- 12% have engineering PR data from sibling tasks
- Engineering PRs are only available when eng work runs ahead of doc work (RHOAIENG pattern). For RHIDP, eng and doc work run in parallel — PRs don't exist yet at estimation time.

**Signal evaluation (40 tasks with feature parents):**

| Signal | Monotonicity | Finding |
|---|---|---|
| desc_len | 0.60 | SP 5 median is 0 — half have no description |
| epic_desc_len | 0.60 | Clusters at ~1900 chars (template length) |
| feature_desc_len | 0.60 | Higher for SP 2 than SP 8 (inverse) |
| combined_desc | 0.60 | Best signal, but p25/p75 ranges overlap completely |
| sibling_epic_count | 0.80 | Flat at 4 across all SP levels |
| sibling_eng_task_count | 0.80 | Dominated by a few large features (clusters at 31) |

**Acceptance criteria:** Investigated as a potential signal — Jira checkbox-style AC items. Of 100 doc tasks sampled, only 2 out of 15 parent features use Jira checkboxes. The extracted AC item count is zero across all SP levels. Dead signal.

**Why Jira metadata doesn't predict task-level SP:** PR metrics measure actual output (lines changed) — directly correlated with effort. Jira metadata measures planning intent — multiple tasks under the same feature receive different SP values based on *which part* of the feature they document. That granularity isn't captured in any Jira field.

### Context assembler

Instead of predicting SP, the Jira-only path assembles hierarchy context for human estimation:

1. Walks task → epic → feature hierarchy
2. Fetches sibling epics and their child tasks under the same feature
3. Collects engineering PR metrics from non-doc-repo siblings
4. Suggests an SP range based on the median of engineering PR assessments (when ≥2 data points)

**Usage:**

- `jirha context KEY` — standalone command, prints full hierarchy context
- `jirha update KEY --sp auto` — when no PR is linked, falls back to context assembler output with a suggested range (if available), then prompts for manual `--sp <value>`
- `jirha hygiene` — reports context suggestions for tasks missing SP with no linked PR

**Data quality tiers:**

| Engineering PRs found | Quality | Meaning |
|---|---|---|
| ≥ 5 | strong | Enough data for a reliable range |
| 2–4 | weak | Directional signal only |
| 0–1 | none | Estimate manually from descriptions |
