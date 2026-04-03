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

**Signal selection:** 20 parameters were evaluated (line counts, file counts, commits, review rounds, days open, PR comments, images, assemblies, etc.). Each was scored for monotonicity (does the median consistently increase with SP?) and discrimination (how well does a threshold separate high-SP from low-SP tasks). Only signals with monotonicity ≥ 0.80 and discrimination ≥ +30 were retained. Assembly files and images scored 0.0 (zero signal across all SP levels) and were dropped.

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
