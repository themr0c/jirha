# SP Estimation Skill Design

## Summary

A Claude Code skill that estimates story points for RHDH doc tasks by reasoning over Jira hierarchy context. Instead of statistical heuristics (which fail on Jira-only signals — see `docs/sp-heuristics.md`), the skill feeds structured hierarchy data to Claude, which reasons across the team's 4-dimension SP reference table (complexity, risk, uncertainty, effort).

## Architecture

**Approach:** Claude skill with jirha as data layer. `jirha` fetches and caches hierarchy data as JSON; the skill file contains the SP reference table, prompting strategy, and output format. Clean separation — jirha is a pure data tool, Claude reasons.

### Data Layer

#### `jirha context KEY --json`

New output mode for the existing `jirha context` command. Returns a structured JSON dict.

**Hierarchy walk:** task → epic → feature, same as today.

**Sibling classification:** Uses Team field (`customfield_10001`) instead of component or PR URL. Tasks with team != "RHDH Documentation" are engineering tasks. This is more reliable than component-based or repo-URL-based classification.

**Feature size:** T-shirt size field included on the feature object (e.g., "S", "M", "L", "XL").

**Issue links:** Fetched at all three levels (task, epic, feature). For every linked issue, the full tree is walked:
- Linked to a feature → walk feature → epics → tasks → PRs
- Linked to an epic → walk epic → tasks → PRs, and walk up to parent feature
- Linked to a task → get PRs/PR bodies, walk up to parent epic and feature

Links are followed one hop from the source issue, but the complete tree is always walked from whatever issue is reached:
- Linked to a feature → walk down: feature → epics → tasks → PRs (full sibling tree)
- Linked to an epic → walk down: epic → tasks → PRs. Walk up to parent feature for context (summary/size only, not its full sibling tree — that would re-expand the primary feature or duplicate work)
- Linked to a task → fetch task details + PRs/PR bodies. Walk up to parent epic and feature for context (summary/size only)

This ensures the LLM gets full context regardless of where the link points, while keeping API calls bounded through the feature-level cache.

**PR body harvesting:** PR descriptions fetched via `gh pr view --json body` for scope signals — upstream doc links, acceptance criteria, design specs. Applies to the task's own PRs and linked tasks' PRs.

#### JSON Output Structure

```json
{
  "task": {
    "key": "RHIDP-1234",
    "summary": "Document RBAC for plugins",
    "description": "...",
    "status": "New",
    "sp": null,
    "components": ["Documentation"],
    "pr_urls": [],
    "pr_bodies": []
  },
  "epic": {
    "key": "RHIDP-100",
    "summary": "RBAC for plugins",
    "description": "...",
    "status": "In Progress",
    "links": [{"link_type": "depends on", "issue": {"key": "...", "summary": "..."}}]
  },
  "feature": {
    "key": "RHDHPLAN-50",
    "summary": "Plugin RBAC",
    "description": "...",
    "status": "In Progress",
    "size": "L",
    "links": [...]
  },
  "sibling_epics": [
    {
      "epic": {"key": "RHIDP-101", "summary": "...", "team": "rhdh-core", "sp": 13},
      "tasks": [
        {"key": "RHIDP-200", "summary": "...", "team": "rhdh-core", "sp": 5, "pr_urls": ["..."]}
      ]
    }
  ],
  "linked_features": [
    {
      "link_type": "relates to",
      "source": "RHDHPLAN-50",
      "feature": {"key": "RHDHPLAN-188", "summary": "...", "size": "M"},
      "epics": [
        {
          "epic": {"key": "RHIDP-300", "team": "rhdh-core", "sp": 8},
          "tasks": [{"key": "RHIDP-301", "team": "rhdh-core", "sp": 5, "pr_urls": ["..."]}]
        }
      ]
    }
  ],
  "linked_issues": [
    {
      "source": "RHIDP-1234",
      "level": "task",
      "link_type": "relates to",
      "issue": {"key": "...", "summary": "...", "pr_urls": ["..."], "pr_bodies": ["..."]}
    }
  ],
  "eng_metrics": [{"url": "...", "sp": 5, "reason": "...", "number": "42"}],
  "suggested_sp_range": [3, 5],
  "data_quality": "weak",
  "cache_age": "2h"
}
```

### Disk Cache

**Location:** `.jirha-cache/` at repo root (gitignored).

```
.jirha-cache/
  features/
    RHDHPLAN-50.json     # full tree: feature + child epics + tasks + PRs
  contexts/
    RHIDP-1234.json      # assembled context for a specific task
```

**Lifetime:** Permanent. No TTL-based deletion — Jira descriptions and hierarchy are essentially write-once. `jirha context KEY --refresh` forces re-fetch. Cache age is reported in output (`cache_age` field) so the LLM can factor freshness into confidence.

**Deduplication:** Feature-level caching means linked features and sibling walks that hit the same feature tree are free after the first fetch. Over time the cache warms and covers most of the project.

### Skill

**File:** `.claude/commands/jirha-estimate.md`

**Flow:**

1. Run `jirha context KEY --json`
2. Feed JSON context to Claude with the SP reference table embedded in the skill
3. Claude reasons across 4 dimensions independently:
   ```
   Complexity: moderate — 3 new API endpoints to document, existing patterns available
   Risk: low — eng PR merged, no open questions
   Uncertainty: small — upstream docs exist, scope is clear
   Effort: significant — ~12 files, new module + updates to existing guides

   Suggested: 5 SP
   ```
4. Ask: `Accept 5 SP? [Y/n/adjust]`
5. On confirm → `jirha update KEY --sp 5 -c "SP estimated from hierarchy context"`

**Prompt contents:**
- Full SP reference table (1, 2, 3, 5, 8, 13, 21 — complexity/risk/uncertainty/effort per level)
- Instructions to reason over each dimension independently
- Guidelines: never suggest 21 (should be split), prefer statistical range when data quality is strong, weight PR body/upstream doc links for scope assessment
- Auto-suggest caps at 13 SP

### Entry Points

1. **`/jirha:estimate KEY`** — standalone slash command. Runs the full flow: fetch context, reason, suggest, confirm, write.

2. **`/jirha:update KEY --sp auto`** — when no PR is linked, `_resolve_sp()` outputs JSON context instead of printing markdown and stopping. The skill picks up and runs the reasoning flow.

3. **`jirha hygiene`** — `_report_context_suggestions()` batch-collects context for all SP-less tasks with no linked PR and presents them one by one for estimation, same interactive confirm flow.

## Files to Create/Modify

### New files
- `.claude/commands/jirha-estimate.md` — skill file with SP reference table and prompt
- `.jirha-cache/` directory + `.gitignore` entry

### Modified files
- `jirha/ops/context.py` — add `--json` output, Team-based classification, feature size, issue links at all levels, full tree walk on linked issues, PR body harvesting, disk cache read/write
- `jirha/cli.py` — add `--json` and `--refresh` flags to context subparser
- `jirha/ops/issues.py` — modify `_resolve_sp()` no-PR path to output JSON for skill pickup
- `jirha/ops/hygiene.py` — update `_report_context_suggestions()` to use skill flow
- `jirha/config.py` — add Team field to `_HIERARCHY_FIELDS` equivalent, cache directory constant

## Constraints

- Never suggest 21 SP (team guide says should be split)
- Auto-suggest caps at 13 SP
- Prefer statistical range when data quality is strong
- Cache is permanent — no automatic deletion
- Follow links one hop only, but always walk the complete tree from the linked issue
- Feature-level cache handles deduplication across linked trees
