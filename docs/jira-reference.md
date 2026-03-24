# Jira Reference

## Conventions

- Component: Documentation (unless otherwise specified).
- Team: RHDH Documentation.
- Story points: 1, 3, 5, 8, 13.
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

## Sprint Status Format

Present sprint status as a list grouped by priority swimlanes, then by status:
```
# <Sprint Name>
**Dates:** YYYY-MM-DD → YYYY-MM-DD  **Working days:** N remaining / M total
## <Priority> — X/Y SP (Z%)
### <Status>
- [KEY](https://redhat.atlassian.net/browse/KEY) <SP>SP <labels> — <summary>
## Risk Assessment
**Velocity / Projected / Status (ON TRACK or AT RISK)**
```
- Swimlane order: Blocker, AEM migration, Test-day, Customer, Must-have, Nice-to-have, Critical, Doc sprint lower, Reviews, Other
- Risk assessment uses blended velocity (historical avg from last 3 closed sprints + current sprint, weighted by elapsed time). If projected SP < remaining SP → AT RISK with suggested issues to drop.
- End with totals per status and SP progress (closed/total SP, percentage)

## SP Heuristics (`--check-sp`)

`jirha hygiene --check-sp` reassesses story points by analyzing the linked GitHub PR. It only flags mismatches of 2+ tiers (e.g. 1 SP vs 5 SP) to avoid noise.

**Base tier** — determined by .adoc line volume (additions + deletions):

| Lines changed | Tier | SP |
|---|---|---|
| < 30 | 0 | 1 |
| 30–149 | 1 | 3 |
| 150–399 | 2 | 5 |
| 400–799 | 3 | 8 |
| 800+ | 4 | 13 |

**Complexity bumps** (tier +1 if 2+ signals present):
- 2+ new .adoc files (no deletions, >5 lines added)
- 2+ assembly files changed
- 3+ images added/changed
- 6+ commits

**Mechanical discount** (tier -1): if >80% of .adoc files have ≤4 lines changed and there are 4+ .adoc files, the change is likely mechanical (bulk rename, xref update).

## Inline python-jira

For use cases the `jirha` script doesn't cover:

```python
from jira import JIRA
import os
jira = JIRA(server='https://redhat.atlassian.net',
            basic_auth=(os.environ['JIRA_EMAIL'],
                        os.environ['JIRA_API_TOKEN']))
```
