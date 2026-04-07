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

4. **Auto-link PRs** — fetches all PRs authored by the user and modified during the sprint (via `gh search prs`). Matches PRs to Jiras by Jira key found in the PR title (authoritative). Falls back to branch name and body only if the title contains no Jira key. Auto-updates the Jira PR field without confirmation. Skipped in `--dry-run` mode (reports matches but does not write to Jira).

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

### estimate

Find open issues assigned to the current user that are missing SP or missing an SP reasoning comment. Queries issues not in Closed, Resolved, In Progress, or In Review. Excludes Epics, Features, and review subtasks.

```
jirha estimate [--max N] [--dry-run] [--json]
```

| Flag | Default | Description |
|---|---|---|
| `--max` | 50 | Maximum results |
| `--dry-run` | false | Report only, no interactive prompts |
| `--json` | false | Output as JSON (for `/jirha:estimate-batch` slash command) |

**Two checks per issue:**

1. **Missing SP** — story_points field is None (0 SP is valid).
2. **Missing reasoning** — SP is set but no comment contains all four keywords: Complexity, Risk, Uncertainty, Effort (matching the format from `/jirha:estimate`).

**Interactive mode** (default): after listing issues, prompts per issue to set SP. Does not write reasoning comments — use `/jirha:estimate-batch` for LLM-generated reasoning.

**JSON mode** (`--json`): outputs a JSON array with issue details, context summary, and suggested SP range. Used by the `/jirha:estimate-batch` slash command.

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

## Story Points

See [docs/sp-heuristics.md](sp-heuristics.md) for the SP reference table, auto-suggest heuristics, and threshold methodology.

## Inline python-jira

For use cases the `jirha` script doesn't cover:

```python
from jira import JIRA
import os
jira = JIRA(server='https://redhat.atlassian.net',
            basic_auth=(os.environ['JIRA_EMAIL'],
                        os.environ['JIRA_API_TOKEN']))
```
