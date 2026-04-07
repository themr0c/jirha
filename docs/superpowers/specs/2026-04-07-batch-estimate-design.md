# Batch SP Estimation — Design Spec

**Date**: 2026-04-07
**Status**: Draft

## Problem

SP estimation is currently a per-issue manual process. There is no way to see which of your open issues are missing SP or missing a reasoning comment. The existing `/jirha:estimate KEY` slash command works for one issue at a time, and `jirha hygiene` only covers sprint-scoped issues with linked PRs.

## Goal

A batch estimation workflow: CLI command finds all open issues needing SP attention, slash command layers LLM reasoning on top for a guided estimation session.

## Target Audience

RHDH documentation team — same users as jirha.

## Approach

Two components that work together:

1. **`jirha estimate`** (CLI) — reporter that finds open issues missing SP or missing an SP reasoning comment. Presents hierarchy context summary per issue. Interactive mode allows setting SP inline. JSON output mode feeds the slash command.

2. **`/jirha:estimate-batch`** (slash command) — calls the CLI for the overview, then runs LLM reasoning per issue using the existing 4-dimension framework, presents results with accept/adjust/skip flow.

## CLI Command: `jirha estimate`

### Query

```
assignee = currentUser()
AND status not in (Closed, Resolved, "In Progress", "In Review")
AND type not in (Epic, Feature)
```

Excludes review subtasks whose summary matches `[DOC] Peer Review` or `[DOC] Technical Review`.

### Two checks per issue

1. **Missing SP** — `story_points` field is None (not set). 0 SP is treated as a valid value.
2. **Missing reasoning comment** — SP is set but no comment on the issue contains all four keywords: `Complexity`, `Risk`, `Uncertainty`, `Effort`

### Output format (text)

```
RHIDP-12345  [3SP, no reasoning]  Authentication troubleshooting
  Epic: RHIDP-100 — Auth docs overhaul
  Feature: RHIDP-50 [L] — Authentication improvements
  Eng PRs: 3 (suggested 3-5 SP, weak)
  https://redhat.atlassian.net/browse/RHIDP-12345

RHIDP-12346  [no SP]  New plugin installation guide
  Epic: RHIDP-200 — Plugin docs
  No eng PRs — estimate manually
  https://redhat.atlassian.net/browse/RHIDP-12346
```

Summary line: `Found 5 issues: 3 missing SP, 2 missing reasoning.`

### Output format (JSON)

`--json` outputs a JSON array for slash command consumption:

```json
[
  {
    "key": "RHIDP-12345",
    "summary": "Authentication troubleshooting",
    "status": "New",
    "current_sp": 3,
    "missing": "reasoning",
    "epic": {"key": "RHIDP-100", "summary": "Auth docs overhaul"},
    "feature": {"key": "RHIDP-50", "summary": "Authentication improvements", "size": "L"},
    "suggested_sp_range": [3, 5],
    "data_quality": "weak",
    "eng_pr_count": 3
  }
]
```

### Flags

| Flag | Default | Description |
|---|---|---|
| `--dry-run` | false | Report only, no interactive prompts |
| `--max N` | 50 | Maximum results |
| `--json` | false | Output as JSON (for slash command) |

### Interactive mode (default)

After listing all issues, prompts per issue:

```
RHIDP-12345 [no SP] — Set SP? [value/skip/quit]: 5
  → Set RHIDP-12345 to 5 SP
```

When a value is entered, writes SP to Jira via the API. Does not write a reasoning comment — that is the LLM's job (via the slash command) or done manually.

`quit` exits the interactive loop, leaving remaining issues untouched.

### Implementation

New file: `jirha/ops/estimate.py`

- `cmd_estimate(args)` — main entry point
- `_find_issues_needing_sp(jira, max_results)` — runs the JQL, checks SP and comments
- `_has_reasoning_comment(jira, issue_key)` — fetches comments, checks for all four dimension keywords
- `_format_context_summary(jira, issue)` — reuses `assemble_context_json` from `context.py` to build the one-line context (epic, feature, eng PR count, suggested range)

Comment detection: a comment counts as "reasoning" if its body contains all four strings: `Complexity`, `Risk`, `Uncertainty`, `Effort` (case-sensitive, matching the format produced by `/jirha:estimate`).

## Slash Command: `/jirha:estimate-batch`

New file: `commands/estimate-batch.md`

### Flow

1. Run `jirha estimate --json --dry-run` to get the batch overview
2. Parse the JSON — list of issues needing SP or reasoning
3. For each issue:
   a. Run `jirha context KEY --json` (do not display raw JSON — process internally)
   b. Skip if summary matches `[DOC] Peer Review` or `[DOC] Technical Review`
   c. Apply LLM reasoning across the 4 SP dimensions (Complexity, Risk, Uncertainty, Effort) using the SP reference table from the existing `/jirha:estimate` command
   d. Present assessment with the Jira URL:
   ```
   RHIDP-12345 — Authentication troubleshooting
   https://redhat.atlassian.net/browse/RHIDP-12345

   Complexity: Low — single procedure module, clear scope
   Risk: Low — no cross-references affected
   Uncertainty: Small — may need SME input on error codes
   Effort: Some time — new section with 3-4 steps

   Suggested: 3 SP
   ```
   e. Ask: `Accept 3 SP? [Y/n/adjust/skip-all]`
   f. If accepted: `jirha update KEY --sp 3 -c "Complexity: Low — ... Risk: Low — ... Uncertainty: Small — ... Effort: Some time — ..."`
   g. For issues that already have SP but need reasoning only: present reasoning, ask to confirm, then add comment without changing SP

4. After all issues, print summary: `Done. 5 estimated, 2 skipped, 1 already had reasoning.`

### Differences from `/jirha:estimate KEY`

- Batch — iterates through all qualifying issues automatically
- Handles both missing-SP and missing-reasoning cases
- `skip-all` option to abort early
- For missing-reasoning issues: adds the comment without changing SP

## What Stays the Same

- `/jirha:estimate KEY` — unchanged, still available for single-issue estimation
- `jirha hygiene` — unchanged, sprint-scoped SP reassessment from PRs
- `jirha context KEY` — unchanged, reused by the new command
- SP heuristics in `api.py` — no changes

## Files Changed

| File | Change |
|---|---|
| `jirha/ops/estimate.py` | New — `cmd_estimate`, comment reasoning detection, JSON output |
| `jirha/cli.py` | Add `estimate` subcommand |
| `commands/estimate-batch.md` | New slash command template |
| `.claude/CLAUDE.md` | Add `estimate` to command table and slash command list |
| `docs/jira-reference.md` | Document the `estimate` command |
