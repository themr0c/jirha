---
name: jira-workflow
description: Jira conventions, field IDs, SP heuristics, and sprint format for RHDH docs workflow
type: reference
---

## Jira Instance

Server: https://redhat.atlassian.net
Project: RHIDP (tasks, epics), RHDHBUG (bugs)

## Custom Field IDs

| Field | ID | Notes |
|---|---|---|
| Story Points | `customfield_10028` | Float value |
| Release Note Text | `customfield_10783` | |
| Release Note Status | `customfield_10807` | |
| Release Note Type | `customfield_10785` | |
| Git Pull Request | `customfield_10875` | |
| Docs Pull Request | `customfield_10964` | |
| Team | `customfield_10001` | Requires `{id: ...}` format |
| Sprint | `customfield_10020` | List of PropertyHolder objects |

## Conventions

- Component: Documentation (default)
- Team: RHDH Documentation
- Story points: 1, 3, 5, 8, 13

## SP Heuristics (--sp auto)

Base tier from .adoc line volume (additions + deletions):

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

**Mechanical discount** (tier -1): if >80% of .adoc files have ≤4 lines changed and there are 4+ .adoc files.

SP mismatches of <2 tiers are ignored as noise (hygiene --check-sp).

## Sprint Status Swimlane Order

Blocker → AEM migration → Test-day → Customer → Must-have → Nice-to-have → Critical → Doc sprint (lower priority) → Reviews → Other

Each issue assigned to first matching swimlane. Risk assessment uses blended velocity (historical avg last 3 sprints + current, weighted by elapsed sprint %).

## Post-PR Workflow

After `gh pr create` or `gh pr edit`:
1. `jirha update KEY --pr <PR_URL> --sp auto -c "summary of changes"`
2. If Jira description is empty/boilerplate, populate with the template below.

## Jira Description Templates (wiki markup)

### Task (RHIDP project)
```
h3. Task
As a documentation engineer working on RHDH, I want to <ACTION> so that <OUTCOME>.

h3. Background
<DESCRIPTION OF CHANGES: what should be done and why>

h3. Dependencies and Blockers
<FROM PR OR "None.">

h3. QE impacted work
<FROM PR OR "None.">

h3. Documentation impacted work
<FILES CHANGED SUMMARY>

h3. Acceptance Criteria
<CHECKLIST ITEMS FROM PR, using (/) for completed>
```

### Epic (RHIDP project)
```
h1. EPIC Goal
<What are we trying to solve?>

h2. Background/Feature Origin
<Why is this important?>

h2. User Scenarios
<User scenarios>

h2. Dependencies (internal and external)
<Dependencies>

h2. Acceptance Criteria
(?) Release Enablement/Demo
(?) DEV - Upstream code and tests merged
(?) DEV - Upstream documentation merged
(?) DEV - Downstream build attached to advisory
(?) QE - Test plans in Playwright
(?) QE - Automated tests merged
(?) DOC - Downstream documentation merged
```
