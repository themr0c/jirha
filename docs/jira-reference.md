# Jira Reference

## Commands

### list

List issues assigned to the current user.

```
jirha list [--open] [--jql "..."] [--max N]
```

| Flag | Default | Description |
|---|---|---|
| `--open` | false | Only open issues (excludes Closed) |
| `--jql` | — | Custom JQL query (overrides default) |
| `--max` | 50 | Maximum results |

### show

Show full details for a single issue: status, priority, components, SP, PR, links, release notes, description, and recent comments.

```
jirha show KEY [--comments]
```

| Flag | Default | Description |
|---|---|---|
| `--comments` | false | Show all comments (default: last 3, truncated to 200 chars) |

### jql

Run an arbitrary JQL query and print matching issues.

```
jirha jql "QUERY" [--max N]
```

### update

Batch-update fields on a single issue.

```
jirha update KEY [options]
```

| Flag | Default | Description |
|---|---|---|
| `-s`, `--summary` | — | New summary/title |
| `--type` | — | Issue type (Task, Bug, Story, ...) |
| `--desc` | — | Description text |
| `--desc-file` | — | Read description from file |
| `--sp` | — | Story points (0, 1, 2, 3, 5, 8, 13, 21, or `auto`) |
| `--pr` | — | Git PR URL (appends to existing) |
| `--priority` | — | Blocker, Critical, Major, Normal, Minor |
| `--fix-version` | — | Add fix version |
| `--affects-version` | — | Add affects version |
| `--component` | — | Add component |
| `--team` | — | Set team (e.g., "RHDH Documentation") |
| `--add-label` | — | Add a label |
| `--remove-label` | — | Remove a label |
| `--assignee` | — | Set assignee (Jira username) |
| `--link-to` | — | Link to another issue key |
| `--link-type` | "relates to" | Link type |
| `--sprint` | — | Add to sprint (no value = active sprint, or specify name) |
| `--attach` | — | Attach a file to the issue |
| `--rn-status` | — | Release note status |
| `--rn-type` | — | Release note type |
| `--rn-text` | — | Release note text |
| `-c`, `--comment` | — | Comment text |
| `-f`, `--comment-file` | — | Read comment from file |

`--sp auto` assesses SP from the linked PR using the heuristics below.

### transition

Transition an issue to a new status, or list available transitions.

```
jirha transition KEY [STATUS]
```

Without `STATUS`, lists available transitions. With `STATUS`, performs case-insensitive match and transitions.

### create

Create a new issue.

```
jirha create PROJECT SUMMARY [options]
```

| Flag | Default | Description |
|---|---|---|
| `--type` | Task | Issue type |
| `--component` | — | Component name |
| `--priority` | — | Priority name |
| `--parent` | — | Parent issue key (for sub-tasks) |
| `--desc` | — | Description text |
| `-f`, `--file` | — | Read description from file |
| `--affects-version` | — | Affects version |

### hygiene

Full sprint hygiene audit. Scans all issues (open and closed) in the current sprint.

```
jirha hygiene [--max N] [--team] [--dry-run]
```

| Flag | Default | Description |
|---|---|---|
| `--max` | 50 | Maximum results per query |
| `--team` | false | Audit entire RHDH Documentation team |
| `--dry-run` | false | Report only, no interactive prompts |

**Steps:**

1. **Sprint detection** — prints sprint name and date range.

2. **Metadata checks** — flags issues missing: component, team, priority, SP, description. Also flags Epics/Features that have SP set (should be empty). Warns about In Progress issues not in the current sprint.

3. **Missing descriptions** — for issues with empty descriptions that have a linked PR, fetches the PR body and proposes it as the description. Interactive: `[a]ll / [n]one / [1,2,...]`.

4. **Auto-link PRs** — fetches all PRs authored by the user and modified during the sprint (via `gh search prs`). Matches PRs to Jiras by key in PR title, branch name, or body. Auto-updates the Jira PR field without confirmation.

5. **SP reassessment** — compares current SP against PR-based assessment. Flags mismatches of 2+ tiers. Interactive: `[a]ll / [n]one / [1,2,...] / [1=5] override`.

6. **PR/Jira status cross-check:**
   - Open PR on Closed Jira → proposes reopen (transition to In Progress).
   - All PRs merged/closed on Open Jira → proposes close. Also closes open review subtasks.
   - Open review subtasks on Closed Jiras → proposes close.
   - Each group prompts: `[a]ll / [n]one / [1,2,...]`.

**Modes:**
- **Terminal** (`jirha hygiene`): interactive — prompts for decisions, applies accepted changes.
- **Dry-run** (`jirha hygiene --dry-run`): report only — prints findings with `To update: jirha update KEY ...` hints. Used by the Claude slash command.

### sprint-status

Sprint board grouped by priority swimlanes.

```
jirha sprint-status [--team]
```

Shows all issues (open and closed) in the current sprint, grouped by swimlane then by status.

**Swimlane order:** Blocker, AEM migration, Test-day, Customer, Must-have, Nice-to-have, Critical, Doc sprint (lower priority), Reviews, Other.

**Output format:**

```
# <Sprint Name>
**Dates:** YYYY-MM-DD → YYYY-MM-DD  **Working days:** N remaining / M total

## <Swimlane> — X/Y SP (Z%)
### <Status>
- [x] https://redhat.atlassian.net/browse/KEY | Priority | SP | labels | summary
```

Each issue line is pipe-separated: checkbox, Jira URL, priority, SP, labels, summary. `[x]` for Closed, `[ ]` otherwise. PR status appended when available.

**Risk assessment** (when sprint is active with remaining work):
- Current velocity: closed SP / elapsed business days.
- Historical velocity: average of last 3 closed Documentation sprints.
- Blended velocity: weighted by sprint progress (early = 90% historical, late = 60% current).
- **ON TRACK** if projected SP ≥ remaining SP.
- **AT RISK** if shortfall — lists candidate issues to drop, lowest priority first.

**Totals:** issue count by status, SP by status, progress percentage.

### short-sprint-status

Same as `sprint-status` but collapses Closed issues to a single summary line per swimlane:

```
### Closed | N issues | X SP
```

### close-subtasks

Close open subtasks of closed parent issues.

```
jirha close-subtasks [--dry-run]
```

Finds all user's closed parent issues and closes any open subtasks.

## Conventions

- Component: Documentation (unless otherwise specified).
- Team: RHDH Documentation.
- Story points: 0, 1, 2, 3, 5, 8, 13, 21.
- Keep PR URL field populated.

## Custom Field IDs

| Field | ID | Notes |
|---|---|---|
| Story Points | `customfield_10028` | Value must be float |
| Release Note Text | `customfield_10783` | |
| Release Note Status | `customfield_10807` | |
| Release Note Type | `customfield_10785` | |
| Git Pull Request | `customfield_10875` | |
| Docs Pull Request | `customfield_10964` | |
| Team | `customfield_10001` | Requires `{id: ...}` format |
| Sprint | `customfield_10020` | List of PropertyHolder with name/state/startDate/endDate |

## JQL Queries

| Category | Name | JQL |
|---|---|---|
| General | All my issues | `assignee = currentUser() ORDER BY updated DESC` |
| General | Open only | `assignee = currentUser() AND status != Closed ORDER BY updated DESC` |
| General | By project | `assignee = currentUser() AND project = RHIDP ORDER BY updated DESC` |
| General | By status | `assignee = currentUser() AND status = "In Progress"` |
| Triage | Missing component | `component not in (Documentation, "AEM Migration")` |
| Triage | Missing team | `Team is EMPTY` |
| Triage | Missing priority | `priority is EMPTY` |
| Triage | Missing SP | `"Story Points" is EMPTY AND priority != Undefined AND type not in (Epic, Feature)` |
| Priority | Blocker | `priority = Blocker` |
| Priority | AEM migration | `labels in (CQreview_pre-migration) OR component in ("AEM Migration")` |
| Priority | Test-day | `labels in (test-day, rhdh-testday)` |
| Priority | Customer | `labels in (customer, RHDH-Customer)` |
| Priority | Must-have | `labels in (must-have)` |
| Priority | Nice-to-have | `labels in (nice-to-have)` |
| Priority | Critical | `priority = Critical` |
| Priority | Doc sprint (lower) | `Sprint in (Documentation) AND type != Sub-task AND summary !~ Review` |
| Priority | Reviews | `type = Sub-task AND summary ~ Review` |

## Jira Description Templates (wiki markup)

**RHIDP project:** Task, Epic
**RHDHBUG project:** Bug (no template — free-form description)

### Task

```
h3. Task

As a documentation engineer working on RHDH, I want to <ACTION FROM PR SUMMARY> so that <OUTCOME>.

h3. Background

<DESCRIPTION OF CHANGES FROM PR BODY: what should be done and why>

h3. Dependencies and Blockers

<FROM PR OR "None.">

h3. QE impacted work

<FROM PR OR "None.">

h3. Documentation impacted work

<FILES CHANGED SUMMARY>

h3. Acceptance Criteria

<CHECKLIST ITEMS FROM PR, using (/) for completed items>
```

### Epic

```
h1. EPIC Goal

<What are we trying to solve here?>

h2. Background/Feature Origin

<Why is this important?>

h2. User Scenarios

<User scenarios>

h2. Dependencies (internal and external)

<Dependencies>

h2. Acceptance Criteria

(?) Release Enablement/Demo - Provide necessary release enablement details and documents
(?) DEV - Upstream code and tests merged: <link to meaningful PR or GitHub Issue>
(?) DEV - Upstream documentation merged: <link to meaningful PR or GitHub Issue>
(?) DEV - Downstream build attached to advisory: <link to errata>
(?) QE - Test plans in Playwright: <link or reference to playwright>
(?) QE - Automated tests merged: <link or reference to automated tests>
(?) DOC - Downstream documentation merged: <link to meaningful PR>
```

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

## Inline python-jira

For use cases the `jirha` script doesn't cover:

```python
from jira import JIRA
import os
jira = JIRA(server='https://redhat.atlassian.net',
            basic_auth=(os.environ['JIRA_EMAIL'],
                        os.environ['JIRA_API_TOKEN']))
```
