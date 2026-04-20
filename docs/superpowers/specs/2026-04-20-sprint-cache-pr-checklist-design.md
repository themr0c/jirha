# Sprint Cache & PR Action Checklist

## Context

Every `jirha sprint-status` invocation hits the Jira API for sprint metadata and shells out to `gh pr view` for each open issue's PR — even though sprint names, dates, and team name don't change mid-sprint. The PR output is a flat status line (`open, changes requested, CI fail`) that tells you something needs attention but not what specifically to do.

This design adds two capabilities:

1. **Sprint cache** — cache stable sprint metadata to disk, invalidated at sprint boundary
2. **PR action checklist** — enrich sprint-status with per-PR actionable items (failing checks by name, unresolved comments, pending reviewers, merge conflicts) and a slash command for interactive deep-dive

## 1. Sprint Cache Layer

### What gets cached

File: `~/.cache/jirha/sprint/current.json`

```json
{
  "current_sprint": {
    "id": 12345,
    "name": "RHDH Docs 2026-04-07",
    "start": "2026-04-07",
    "end": "2026-04-18",
    "board_id": 7654
  },
  "next_sprint": null,
  "team_name": "RHDH Documentation",
  "cached_at": 1713607200.0
}
```

- `next_sprint`: same shape as `current_sprint`, or `null` when Jira has no future sprint created yet. `null` is a cached fact — it means "cannot add issues to next sprint." Not re-checked on every run.
- `team_name`: the `DEFAULT_TEAM` value, cached alongside sprint data for downstream consumers.

### Invalidation

- **Automatic**: `datetime.now() > current_sprint.end` — cache is stale once the sprint ends.
- **Manual**: `--refresh` flag forces a fresh fetch (same pattern as `context` command).
- No TTL-based expiry within a sprint.

### Code changes

**`jirha/cache.py`** — Add `read_sprint_cache()` and `write_sprint_cache()` convenience functions wrapping existing `read_cache`/`write_cache` with the `sprint` category and `current` key.

**`jirha/api.py`** — New public function:

```python
def get_sprint_info(jira, refresh=False):
    """Return sprint metadata, from cache if valid.

    Returns dict with current_sprint, next_sprint (or None), team_name.
    """
```

- Checks cache first. If valid (not expired, not refresh), returns cached data.
- On cache miss: calls `_get_active_sprint(jira)` for current sprint, queries `state=future` sprints on the same board for next sprint (earliest one), writes cache.
- Replaces the inline `_get_active_sprint()` call in `_run_sprint_status()`.

### Consumers

- `sprint-status` / `short-sprint-status`: use cached sprint name/dates instead of a discovery query each time.
- `update --sprint`: could validate sprint existence before attempting to add an issue (future enhancement, not in scope).

## 2. PR Action Checklist

### Data model

New function `_fetch_pr_checklist(pr_url)` in `jirha/api.py` returns:

```python
{
    "url": "https://github.com/org/repo/pull/123",
    "state": "open",
    "review_decision": "CHANGES_REQUESTED",
    "failing_checks": ["ci/prow/e2e", "tide"],
    "pending_reviewers": ["alice", "bob"],
    "unresolved_comments": 3,
    "has_conflicts": True,
    "is_author": True,
}
```

### GitHub data source

Single `gh pr view` call per PR with expanded fields:

```
--json state,reviewDecision,statusCheckRollup,reviewRequests,
       latestReviews,comments,mergeable,url,author
```

This replaces the PR-fetching logic inside `_fetch_pr_statuses(issues)` (api.py:548), which currently calls `gh pr view` with a smaller field set per PR. The internal per-PR fetch is replaced by `_fetch_pr_checklist()` — a strict superset. `_fetch_pr_statuses()` itself is refactored to call `_fetch_pr_checklist()` and return structured data instead of formatted strings.

### Session caching

PR checklist data is cached in a module-level dict for the duration of one CLI invocation. No disk persistence — PR data is too volatile for disk caching. This avoids re-fetching if the same PR URL appears in multiple issues.

### CLI output

Under each open-PR issue in sprint-status, render actionable items:

```
- [ ] RHIDP-1234 | Major | 3 SP | Improve auth docs
      PR: open, changes requested — github.com/org/repo/pull/123
        [ ] 3 unresolved review comments
        [ ] Failing: ci/prow/e2e, tide
        [ ] Merge conflict
```

- Closed/merged PRs: no checklist (nothing to act on).
- Draft PRs: show `draft` state, still show CI failures if any.
- Issues without PRs: unchanged (no checklist line).

### Reviewer PRs

Separate section at the end of sprint-status output:

```
## Pending Reviews
- [ ] org/repo#456 — "Add SSO config docs" (requested 2d ago)
      [ ] CI pass, awaiting your review
```

Discovery: `gh search prs --review-requested=@me --state=open` — single call returning all PRs awaiting review. No per-PR fetching for the overview. Deep-dive fetches full checklist on demand.

## 3. Slash Command: PR Dashboard

### File

`commands/pr-dashboard.md`

### Flow

1. **Dashboard phase**: Run `jirha sprint-status` (with checklist output). Present the full board in the conversation.

2. **Deep-dive phase**: Parse checklist output, ask which issue to focus on. Available actions for the selected issue:
   - Open PR in browser (`gh pr view --web`)
   - Fetch and display unresolved review comments (`gh pr view --comments`)
   - Show failing check logs (`gh run view`)
   - Add a Jira comment summarizing PR status
   - Transition the Jira issue if the PR is merged

3. **Iterate**: After addressing one issue, return to dashboard and pick the next.

### Scope

- The slash command orchestrates existing CLI tools — no new Python subcommand.
- Data gathering stays in Python (`sprint-status`), interactive workflow is handled by Claude.
- The command surfaces information and offers actions. It does not auto-fix anything.

## Files to modify

| File | Change |
|------|--------|
| `jirha/cache.py` | Add `read_sprint_cache()`, `write_sprint_cache()` |
| `jirha/api.py` | Add `get_sprint_info()`, `_fetch_pr_checklist()`. Refactor `_fetch_pr_statuses()` to use it. |
| `jirha/ops/sprint.py` | Use `get_sprint_info()` for sprint metadata. Render PR checklist in output. Add reviewer PRs section. |
| `jirha/cli.py` | Add `--refresh` flag to `sprint-status` and `short-sprint-status` |
| `commands/pr-dashboard.md` | New slash command for dashboard + deep-dive workflow |
| `commands/sprint-status.md` | Pass through `--refresh` if present in `$ARGUMENTS` |
| `commands/sprint-status-short.md` | Same |

## Verification

1. **Cache**: Run `jirha sprint-status` twice. Second run should be noticeably faster (no sprint discovery query). Check `~/.cache/jirha/sprint/current.json` exists with correct data. Run with `--refresh` to force cache update.
2. **Next sprint null**: Verify that when no future sprint exists in Jira, cache stores `null` and no error is raised.
3. **PR checklist**: Run `jirha sprint-status` on a sprint with open PRs that have failing checks or pending reviews. Verify checklist items appear under each issue.
4. **Reviewer PRs**: Verify "Pending Reviews" section appears with PRs awaiting your review.
5. **Slash command**: Run `/jirha:pr-dashboard` in Claude Code. Verify dashboard displays, deep-dive offers correct actions.
6. **Tests**: Run `pytest` — existing tests pass, add tests for cache invalidation logic and PR checklist parsing.
