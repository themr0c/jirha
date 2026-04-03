# SP Estimation Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code skill that estimates story points for doc tasks by reasoning over Jira hierarchy context, with disk caching and interactive confirmation.

**Architecture:** `jirha context KEY --json` fetches and caches hierarchy data (team-based classification, issue links, PR bodies, feature size). A Claude slash command (`/jirha:estimate KEY`) feeds the JSON to Claude, which reasons across 4 SP dimensions and prompts for confirmation before writing.

**Tech Stack:** Python 3, python-jira, GitHub CLI (`gh`), Claude Code skills (markdown)

---

### Task 1: Add cache infrastructure and config constants

**Files:**
- Modify: `jirha/config.py`
- Modify: `.gitignore`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing test for cache dir constant**

```python
# tests/unit/test_config.py — append to existing file

def test_cache_dir_constant():
    from jirha.config import CACHE_DIR
    assert CACHE_DIR.name == ".jirha-cache"

def test_cf_size_constant():
    from jirha.config import CF_SIZE
    assert CF_SIZE.startswith("customfield_")  # actual ID discovered in step 6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/unit/test_config.py::test_cache_dir_constant -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Add constants to config.py**

Add after `TEAM_RHDH_DOCS_ID` (line 16):

```python
# Feature T-shirt size (Jira custom field — discover via `jirha meta PROJECT --type Feature`)
CF_SIZE = "customfield_12310243"

# Disk cache for hierarchy context (permanent, no TTL)
CACHE_DIR = _repo_root / ".jirha-cache"
```

Note: `_repo_root` is defined on line 68. Move the `CF_SIZE` and `CACHE_DIR` lines after line 68 so `_repo_root` is available. Alternatively, keep `CF_SIZE` with the other `CF_*` constants (before `_repo_root`) and only put `CACHE_DIR` after `_repo_root`.

- [ ] **Step 4: Add .jirha-cache/ to .gitignore**

Append to `.gitignore`:
```
.jirha-cache/
```

- [ ] **Step 5: Run test to verify it passes**

Run: `venv/bin/pytest tests/unit/test_config.py -v`
Expected: all PASS

- [ ] **Step 6: Discover the actual custom field ID for feature size**

Run: `jirha meta RHDHPLAN --type Feature`

Look for a field named "Size", "T-Shirt Size", or similar. Update `CF_SIZE` in config.py with the correct field ID. If the field doesn't exist, remove `CF_SIZE` and skip size in subsequent tasks.

- [ ] **Step 7: Commit**

```bash
git add jirha/config.py .gitignore tests/unit/test_config.py
git commit -m "feat: add cache dir and size field constants"
```

---

### Task 2: Add disk cache module

**Files:**
- Create: `jirha/cache.py`
- Test: `tests/unit/test_cache.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_cache.py

import json
import time
from pathlib import Path

from jirha.cache import read_cache, write_cache, cache_age_str


def test_write_and_read(tmp_path):
    data = {"key": "RHIDP-1234", "summary": "test"}
    write_cache(tmp_path, "features", "RHDHPLAN-50", data)
    result = read_cache(tmp_path, "features", "RHDHPLAN-50")
    assert result is not None
    assert result["data"]["key"] == "RHIDP-1234"
    assert "cached_at" in result


def test_read_missing(tmp_path):
    result = read_cache(tmp_path, "features", "NONEXISTENT")
    assert result is None


def test_cache_age_str_seconds():
    assert cache_age_str(30) == "30s"


def test_cache_age_str_minutes():
    assert cache_age_str(120) == "2m"


def test_cache_age_str_hours():
    assert cache_age_str(7200) == "2h"


def test_cache_age_str_days():
    assert cache_age_str(172800) == "2d"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/unit/test_cache.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement cache module**

```python
# jirha/cache.py
"""Disk cache for Jira hierarchy context."""

import json
import time
from pathlib import Path


def write_cache(cache_dir, category, key, data):
    """Write data to cache. category is 'features' or 'contexts'."""
    path = Path(cache_dir) / category
    path.mkdir(parents=True, exist_ok=True)
    payload = {"data": data, "cached_at": time.time()}
    (path / f"{key}.json").write_text(json.dumps(payload, default=str))


def read_cache(cache_dir, category, key):
    """Read from cache. Returns dict with 'data' and 'cached_at', or None."""
    path = Path(cache_dir) / category / f"{key}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def cache_age_str(seconds):
    """Format cache age as human-readable string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds / 60)}m"
    if seconds < 86400:
        return f"{int(seconds / 3600)}h"
    return f"{int(seconds / 86400)}d"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/unit/test_cache.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add jirha/cache.py tests/unit/test_cache.py
git commit -m "feat: add disk cache module for hierarchy context"
```

---

### Task 3: Add issue link walking and team-based classification to context assembler

**Files:**
- Modify: `jirha/ops/context.py`
- Test: `tests/unit/test_context.py`

This is the largest task — it refactors the context assembler to:
1. Use Team field for eng/doc classification
2. Fetch issue links at all levels
3. Walk full trees for linked issues
4. Fetch PR bodies
5. Include feature size

- [ ] **Step 1: Write failing tests for team-based classification**

Append to `tests/unit/test_context.py`:

```python
from jirha.ops.context import _is_eng_task


def test_is_eng_task_different_team():
    """Task with a non-doc team is engineering."""
    task = _FakeIssue("RHIDP-100")
    task.fields.customfield_10001 = type("Team", (), {"name": "rhdh-core"})()
    assert _is_eng_task(task) is True


def test_is_eng_task_doc_team():
    """Task with RHDH Documentation team is not engineering."""
    task = _FakeIssue("RHIDP-100")
    task.fields.customfield_10001 = type("Team", (), {"name": "RHDH Documentation"})()
    assert _is_eng_task(task) is False


def test_is_eng_task_no_team():
    """Task with no team field defaults to not engineering."""
    task = _FakeIssue("RHIDP-100")
    assert _is_eng_task(task) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/unit/test_context.py::test_is_eng_task_different_team -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement `_is_eng_task` in context.py**

Add after the imports in `jirha/ops/context.py`:

```python
from jirha.config import CF_TEAM, DEFAULT_TEAM

def _is_eng_task(issue):
    """Return True if the issue belongs to an engineering (non-doc) team."""
    team = getattr(issue.fields, CF_TEAM, None)
    if not team:
        return False
    team_name = getattr(team, "name", str(team))
    return team_name != DEFAULT_TEAM
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/unit/test_context.py -v`
Expected: all PASS

- [ ] **Step 5: Write failing tests for issue link extraction**

Append to `tests/unit/test_context.py`:

```python
from jirha.ops.context import _extract_links


class _FakeLink:
    def __init__(self, link_type, outward_key=None, inward_key=None):
        self.type = type("LinkType", (), {"outward": link_type, "inward": link_type, "name": link_type})()
        if outward_key:
            self.outwardIssue = type("Issue", (), {"key": outward_key})()
            self.inwardIssue = None
        else:
            self.outwardIssue = None
            self.inwardIssue = type("Issue", (), {"key": inward_key})()


def test_extract_links_outward():
    links = [_FakeLink("relates to", outward_key="RHIDP-200")]
    result = _extract_links(links)
    assert len(result) == 1
    assert result[0]["key"] == "RHIDP-200"
    assert result[0]["link_type"] == "relates to"
    assert result[0]["direction"] == "outward"


def test_extract_links_empty():
    assert _extract_links([]) == []
    assert _extract_links(None) == []
```

- [ ] **Step 6: Implement `_extract_links`**

Add to `jirha/ops/context.py`:

```python
def _extract_links(issuelinks):
    """Extract issue links as list of dicts with key, link_type, direction."""
    if not issuelinks:
        return []
    result = []
    for link in issuelinks:
        if hasattr(link, "outwardIssue") and link.outwardIssue:
            result.append({
                "key": link.outwardIssue.key,
                "link_type": link.type.outward,
                "direction": "outward",
            })
        elif hasattr(link, "inwardIssue") and link.inwardIssue:
            result.append({
                "key": link.inwardIssue.key,
                "link_type": link.type.inward,
                "direction": "inward",
            })
    return result
```

- [ ] **Step 7: Run all context tests**

Run: `venv/bin/pytest tests/unit/test_context.py -v`
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add jirha/ops/context.py tests/unit/test_context.py
git commit -m "feat: add team-based classification and link extraction to context"
```

---

### Task 4: Refactor context assembler for JSON output with links and caching

**Files:**
- Modify: `jirha/ops/context.py`
- Modify: `jirha/cli.py`
- Test: `tests/unit/test_context.py`

- [ ] **Step 1: Write failing test for `_issue_to_dict`**

Append to `tests/unit/test_context.py`:

```python
from jirha.ops.context import _issue_to_dict


def test_issue_to_dict_basic():
    issue = _FakeIssue("RHIDP-100", "Fix link", "Some desc", "New", sp=3)
    result = _issue_to_dict(issue)
    assert result["key"] == "RHIDP-100"
    assert result["summary"] == "Fix link"
    assert result["description"] == "Some desc"
    assert result["status"] == "New"
    assert result["sp"] == 3
    assert result["components"] == []


def test_issue_to_dict_with_components():
    comp = type("Comp", (), {"name": "Documentation"})()
    issue = _FakeIssue("RHIDP-100", components=[comp])
    result = _issue_to_dict(issue)
    assert result["components"] == ["Documentation"]
```

- [ ] **Step 2: Implement `_issue_to_dict`**

Add to `jirha/ops/context.py`:

```python
def _issue_to_dict(issue, include_links=False, include_pr=False):
    """Convert a Jira issue to a serializable dict."""
    result = {
        "key": issue.key,
        "summary": issue.fields.summary or "",
        "description": issue.fields.description or "",
        "status": str(issue.fields.status),
        "sp": _issue_sp(issue) or None,
        "components": [c.name for c in (issue.fields.components or [])],
    }
    team = getattr(issue.fields, CF_TEAM, None)
    if team:
        result["team"] = getattr(team, "name", str(team))
    size = getattr(issue.fields, CF_SIZE, None)
    if size:
        result["size"] = str(size)
    if include_links:
        result["links"] = _extract_links(getattr(issue.fields, "issuelinks", None))
    if include_pr:
        pr_field = getattr(issue.fields, CF_GIT_PR, None) or ""
        result["pr_urls"] = _extract_pr_urls(pr_field)
    return result
```

Add the import at the top of context.py:
```python
from jirha.config import CF_GIT_PR, CF_SIZE, CF_STORY_POINTS, CF_TEAM, DEFAULT_TEAM, SERVER, SP_VALUES
```

- [ ] **Step 3: Run tests**

Run: `venv/bin/pytest tests/unit/test_context.py -v`
Expected: all PASS

- [ ] **Step 4: Write failing test for `assemble_context_json`**

Append to `tests/unit/test_context.py`:

```python
from jirha.ops.context import assemble_context_json


def test_assemble_context_json_returns_dict():
    """assemble_context_json returns a dict with expected top-level keys."""
    # This test requires mocking jira — skip for now, will be an integration test
    pass
```

- [ ] **Step 5: Implement `assemble_context_json`**

Add to `jirha/ops/context.py`. This function wraps `assemble_context` but returns a JSON-serializable dict instead of Jira objects, adds linked feature tree walking, PR body fetching, and cache integration:

```python
import time
from jirha.cache import read_cache, write_cache, cache_age_str
from jirha.config import CACHE_DIR

def _fetch_pr_bodies(pr_urls):
    """Fetch PR description bodies for a list of PR URLs."""
    bodies = []
    for url in pr_urls:
        body = _pr_body(url)
        if body:
            bodies.append(body)
    return bodies


def _walk_linked_issue(jira, link_info):
    """Walk a linked issue's full tree. Returns a dict describing what was found."""
    key = link_info["key"]
    issue = _cached_issue(jira, key, _HIERARCHY_FIELDS + ",issuelinks")

    issue_type = str(issue.fields.issuetype).lower()
    result = {
        "source_link_type": link_info["link_type"],
        "direction": link_info["direction"],
    }

    if "feature" in issue_type or "initiative" in issue_type:
        # It's a feature — walk full tree down
        sibling_epics = _fetch_sibling_tasks(jira, key)
        result["type"] = "feature"
        result["feature"] = _issue_to_dict(issue, include_links=True)
        result["epics"] = []
        for entry in sibling_epics:
            epic_dict = _issue_to_dict(entry["epic"])
            tasks = []
            for te in entry["tasks"]:
                t = te["issue"]
                task_dict = _issue_to_dict(t, include_pr=True)
                if _is_eng_task(t):
                    task_dict["is_eng"] = True
                tasks.append(task_dict)
            result["epics"].append({"epic": epic_dict, "tasks": tasks})
    elif "epic" in issue_type:
        # It's an epic — walk down to tasks, walk up for feature context
        tasks_raw = jira.search_issues(
            f"parent = {key} ORDER BY key",
            maxResults=100,
            fields=_HIERARCHY_FIELDS + f",{CF_TEAM},{CF_GIT_PR}",
        )
        result["type"] = "epic"
        result["epic"] = _issue_to_dict(issue, include_links=True)
        result["tasks"] = [_issue_to_dict(t, include_pr=True) for t in tasks_raw]
        # Walk up to parent feature (summary/size only)
        parent = getattr(issue.fields, "parent", None)
        if parent:
            feat = _cached_issue(jira, parent.key, _HIERARCHY_FIELDS)
            result["parent_feature"] = {
                "key": feat.key,
                "summary": feat.fields.summary or "",
                "size": str(getattr(feat.fields, CF_SIZE, "") or ""),
            }
    else:
        # It's a task — get its PRs, walk up for context
        result["type"] = "task"
        result["issue"] = _issue_to_dict(issue, include_links=True, include_pr=True)
        pr_urls = result["issue"].get("pr_urls", [])
        result["issue"]["pr_bodies"] = _fetch_pr_bodies(pr_urls)
        # Walk up
        parent = getattr(issue.fields, "parent", None)
        if parent:
            epic = _cached_issue(jira, parent.key, _HIERARCHY_FIELDS)
            result["parent_epic"] = {"key": epic.key, "summary": epic.fields.summary or ""}
            feat_parent = getattr(epic.fields, "parent", None)
            if feat_parent:
                feat = _cached_issue(jira, feat_parent.key, _HIERARCHY_FIELDS)
                result["parent_feature"] = {
                    "key": feat.key,
                    "summary": feat.fields.summary or "",
                    "size": str(getattr(feat.fields, CF_SIZE, "") or ""),
                }

    return result


def assemble_context_json(jira, issue_key, refresh=False):
    """Assemble full hierarchy context as a JSON-serializable dict.

    Checks disk cache first. Returns dict with cache_age field.
    """
    # Check context cache
    if not refresh:
        cached = read_cache(CACHE_DIR, "contexts", issue_key)
        if cached:
            age = time.time() - cached["cached_at"]
            result = cached["data"]
            result["cache_age"] = cache_age_str(age)
            return result

    # Build fresh context
    hierarchy = _walk_hierarchy(jira, issue_key)
    task = hierarchy["task"]
    epic = hierarchy["epic"]
    feature = hierarchy["feature"]

    # Fetch issue links at all levels
    task_full = _cached_issue(jira, issue_key, _HIERARCHY_FIELDS + ",issuelinks," + CF_GIT_PR)
    task_dict = _issue_to_dict(task_full, include_links=True, include_pr=True)
    task_dict["pr_bodies"] = _fetch_pr_bodies(task_dict.get("pr_urls", []))

    epic_dict = None
    if epic:
        epic_full = _cached_issue(jira, epic.key, _HIERARCHY_FIELDS + ",issuelinks")
        epic_dict = _issue_to_dict(epic_full, include_links=True)

    feature_dict = None
    if feature:
        feat_full = _cached_issue(jira, feature.key, _HIERARCHY_FIELDS + ",issuelinks")
        feature_dict = _issue_to_dict(feat_full, include_links=True)

    # Sibling epics with team-based classification
    sibling_epics = []
    eng_metrics = []
    if feature:
        raw_siblings = _fetch_sibling_tasks(jira, feature.key)
        for entry in raw_siblings:
            epic_d = _issue_to_dict(entry["epic"])
            tasks = []
            for te in entry["tasks"]:
                t = te["issue"]
                td = _issue_to_dict(t, include_pr=True)
                if _is_eng_task(t):
                    td["is_eng"] = True
                tasks.append(td)
            sibling_epics.append({"epic": epic_d, "tasks": tasks})
        eng_metrics = _collect_eng_pr_metrics(raw_siblings)

    # Walk linked issues at all levels
    all_links = []
    for source_key, links in [
        (issue_key, task_dict.get("links", [])),
        (epic.key if epic else None, (epic_dict or {}).get("links", [])),
        (feature.key if feature else None, (feature_dict or {}).get("links", [])),
    ]:
        if not source_key:
            continue
        for link in links:
            # Skip links to issues already in the hierarchy
            hierarchy_keys = {issue_key, epic.key if epic else None, feature.key if feature else None}
            if link["key"] in hierarchy_keys:
                continue
            walked = _walk_linked_issue(jira, link)
            walked["source"] = source_key
            all_links.append(walked)

    sp_range = _suggest_sp_range(eng_metrics)
    if len(eng_metrics) >= 5:
        quality = "strong"
    elif len(eng_metrics) >= 2:
        quality = "weak"
    else:
        quality = "none"

    result = {
        "task": task_dict,
        "epic": epic_dict,
        "feature": feature_dict,
        "sibling_epics": sibling_epics,
        "linked_trees": all_links,
        "eng_metrics": [
            {"url": m["url"], "sp": m["sp"], "reason": m["reason"], "number": m["number"]}
            for m in eng_metrics
        ],
        "suggested_sp_range": list(sp_range) if sp_range else None,
        "data_quality": quality,
        "cache_age": "fresh",
    }

    # Write to cache
    write_cache(CACHE_DIR, "contexts", issue_key, result)

    return result
```

- [ ] **Step 6: Update `_HIERARCHY_FIELDS` to include team and size fields**

In `jirha/ops/context.py`, update line 13:

```python
_HIERARCHY_FIELDS = (
    f"summary,description,status,issuetype,parent,components,"
    f"{CF_STORY_POINTS},{CF_GIT_PR},{CF_TEAM},{CF_SIZE}"
)
```

- [ ] **Step 7: Update `_fetch_sibling_tasks` to include Team field**

In `_fetch_sibling_tasks`, update the task search fields to include `CF_TEAM`:

```python
tasks = jira.search_issues(
    f"parent = {epic.key} ORDER BY key",
    maxResults=100,
    fields=f"summary,status,components,{CF_STORY_POINTS},{CF_GIT_PR},{CF_TEAM}",
)
```

- [ ] **Step 8: Run all tests**

Run: `venv/bin/pytest -v`
Expected: all PASS

- [ ] **Step 9: Commit**

```bash
git add jirha/ops/context.py tests/unit/test_context.py
git commit -m "feat: add JSON context assembly with links, teams, and caching"
```

---

### Task 5: Add --json and --refresh flags to CLI

**Files:**
- Modify: `jirha/cli.py`
- Modify: `jirha/ops/context.py` — update `cmd_context`

- [ ] **Step 1: Update CLI parser**

In `jirha/cli.py`, update the context subparser (around line 125):

```python
p = sub.add_parser("context", help="Show hierarchy context for SP estimation")
p.add_argument("key", help="Issue key")
p.add_argument("--json", action="store_true", help="Output as JSON")
p.add_argument("--refresh", action="store_true", help="Force re-fetch (ignore cache)")
p.set_defaults(func=cmd_context)
```

- [ ] **Step 2: Update `cmd_context` in context.py**

Replace the existing `cmd_context` function:

```python
def cmd_context(args):
    """Show hierarchy context for SP estimation."""
    jira = get_jira()
    if getattr(args, "json", False):
        import json as json_mod
        ctx = assemble_context_json(jira, args.key, refresh=getattr(args, "refresh", False))
        print(json_mod.dumps(ctx, indent=2))
    else:
        ctx = assemble_context(jira, args.key)
        print(format_context(ctx))
```

- [ ] **Step 3: Run lint and tests**

Run: `venv/bin/ruff check . && venv/bin/pytest -v`
Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add jirha/cli.py jirha/ops/context.py
git commit -m "feat: add --json and --refresh flags to jirha context"
```

---

### Task 6: Update --sp auto fallback to output JSON

**Files:**
- Modify: `jirha/ops/issues.py`

- [ ] **Step 1: Update `_resolve_sp` no-PR path**

Replace the no-PR fallback block in `_resolve_sp()` (currently lines 168-177):

```python
        # No PR — fall back to context assembler (JSON for skill pickup)
        from jirha.ops.context import assemble_context_json, format_context, assemble_context
        import json as json_mod

        ctx_json = assemble_context_json(jira, args.key)
        print(json_mod.dumps(ctx_json, indent=2))
        if ctx_json["suggested_sp_range"]:
            low, high = ctx_json["suggested_sp_range"]
            print(f"\nNo PR linked. Suggested range: {low}–{high} SP")
        print(f"Use: jirha update {args.key} --sp <value>")
        return None
```

- [ ] **Step 2: Run tests**

Run: `venv/bin/pytest tests/unit/test_issues.py -v`
Expected: all PASS

- [ ] **Step 3: Commit**

```bash
git add jirha/ops/issues.py
git commit -m "feat: output JSON context in --sp auto fallback"
```

---

### Task 7: Update hygiene to use JSON context

**Files:**
- Modify: `jirha/ops/hygiene.py`

- [ ] **Step 1: Update `_report_context_suggestions`**

Replace the function body to use `assemble_context_json`:

```python
def _report_context_suggestions(jira, issue_gaps, dry_run=False):
    """Report hierarchy context for tasks missing SP that have no PR."""
    candidates = []
    for key, entry in issue_gaps.items():
        if "SP" not in entry["missing"]:
            continue
        issue = entry["issue"]
        pr_url = getattr(issue.fields, CF_GIT_PR, None)
        if pr_url:
            continue
        candidates.append(issue)

    if not candidates:
        return

    from jirha.ops.context import assemble_context_json

    print("\n## SP Context (no PR linked)\n")
    for issue in candidates:
        ctx = assemble_context_json(jira, issue.key)
        assignee = _assignee_name(issue)
        print(f"- {_jira_url(issue.key)} @{assignee} — {issue.fields.summary}")
        if ctx.get("cache_age") and ctx["cache_age"] != "fresh":
            print(f"  (cached {ctx['cache_age']} ago)")
        if ctx["suggested_sp_range"]:
            low, high = ctx["suggested_sp_range"]
            quality = ctx["data_quality"]
            n = len(ctx["eng_metrics"])
            print(f"  Suggested: {low}–{high} SP ({quality}, {n} eng PRs)")
        elif ctx.get("feature"):
            feat = ctx["feature"]
            size = feat.get("size", "")
            size_str = f" [{size}]" if size else ""
            print(f"  Feature: {_jira_url(feat['key'])}{size_str} — {feat['summary']}")
            print("  No eng PRs found — estimate manually")
        elif ctx.get("epic"):
            epic = ctx["epic"]
            print(f"  Epic: {_jira_url(epic['key'])} — {epic['summary']}")
            print("  No feature parent — estimate manually")
        else:
            print("  Standalone task — estimate manually")
        if dry_run:
            print(f"  To set: jirha update {issue.key} --sp <value>")
        print()
```

- [ ] **Step 2: Run tests**

Run: `venv/bin/pytest tests/unit/test_hygiene.py -v`
Expected: all PASS

- [ ] **Step 3: Commit**

```bash
git add jirha/ops/hygiene.py
git commit -m "feat: use JSON context in hygiene SP suggestions"
```

---

### Task 8: Create the estimate slash command

**Files:**
- Create: `.claude/commands/jirha-estimate.md`

- [ ] **Step 1: Create the skill file**

```markdown
**Step 1:** Fetch the hierarchy context for the issue:

\```bash
jirha context $ARGUMENTS --json
\```

**Step 2:** Analyze the JSON context and estimate story points.

Use this SP reference table to reason across each dimension independently:

| SP | Complexity | Risk | Uncertainty | Effort |
|---|---|---|---|---|
| 1 | Simple task, minimal work | Low | None | Very little effort needed |
| 2 | Simple task, minimal work, short acceptance criteria | Low | None | Little effort needed |
| 3 | Simple task. Longer acceptance criteria, though clear | Low | Small — may need to consult peers | Will take some time |
| 5 | Some difficulty but feasible. Criteria mostly clear | Medium — may need mitigation plan | Small — may need to consult peers | Significant amount of sprint needed |
| 8 | Difficult and complicated. Lots of work | High — must have mitigation plan | Medium — may need a spike | High effort, whole sprint |
| 13 | Too big, should be broken down if spillover possible | High — should not be in sprint alone | Large — create a spike | Entire sprint as dedicated effort |

**Guidelines:**
- Never suggest 21 SP — recommend splitting the task instead.
- Cap auto-suggest at 13 SP.
- When `data_quality` is "strong" (5+ eng PRs), weight the `suggested_sp_range` heavily.
- When `data_quality` is "weak" or "none", rely more on description analysis.
- Weight PR body content and upstream doc links for scope assessment.
- Consider feature size (T-shirt) as a scope multiplier.
- If `cache_age` is more than 7 days, note that context may be stale.

**Output format:** Present your assessment as:

```
Complexity: <level> — <reasoning>
Risk: <level> — <reasoning>
Uncertainty: <level> — <reasoning>
Effort: <level> — <reasoning>

Suggested: <N> SP
```

**Step 3:** Ask the user: `Accept <N> SP? [Y/n/adjust]`

**Step 4:** If confirmed, run:

\```bash
jirha update <KEY> --sp <N> -c "SP estimated from hierarchy context"
\```

If the user wants to adjust, ask for their preferred value and use that instead.
```

Note: remove the backslashes before the triple backticks — they are escaping artifacts for this plan document.

- [ ] **Step 2: Verify the command is loadable**

The command should appear as `/jirha:estimate` in Claude Code. Verify by checking the plugin cache refreshes (may need `claude plugins update`).

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/jirha-estimate.md
git commit -m "feat: add /jirha:estimate slash command for SP estimation"
```

---

### Task 9: Run lint, full test suite, and integration test

**Files:** none (verification only)

- [ ] **Step 1: Run linter**

Run: `venv/bin/ruff check . && venv/bin/ruff format --check .`
Expected: all clean. If not, fix and re-run.

- [ ] **Step 2: Run full test suite**

Run: `venv/bin/pytest -v`
Expected: all PASS

- [ ] **Step 3: Integration test — jirha context with JSON**

Run: `jirha context RHIDP-9256 --json | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Keys: {list(d.keys())}'); print(f'Feature: {d.get(\"feature\",{}).get(\"key\",\"none\")}'); print(f'Links: {len(d.get(\"linked_trees\",[]))}'); print(f'Cache age: {d.get(\"cache_age\",\"?\")}')"`

Expected: valid JSON with task, epic, feature, sibling_epics, linked_trees, eng_metrics, suggested_sp_range, data_quality, cache_age keys.

- [ ] **Step 4: Integration test — cached re-fetch**

Run: `jirha context RHIDP-9256 --json | python3 -c "import sys,json; print(json.load(sys.stdin)['cache_age'])"`

Expected: should show a non-"fresh" cache age (e.g., "2s", "1m").

- [ ] **Step 5: Integration test — refresh**

Run: `jirha context RHIDP-9256 --json --refresh | python3 -c "import sys,json; print(json.load(sys.stdin)['cache_age'])"`

Expected: "fresh"

- [ ] **Step 6: Fix any issues found, commit if needed**

```bash
git add -A && git commit -m "fix: address integration test findings"
```

---

### Task 10: Add size field to `jirha show`

**Files:**
- Modify: `jirha/ops/issues.py`

- [ ] **Step 1: Add CF_SIZE to imports**

In `jirha/ops/issues.py`, add `CF_SIZE` to the config imports:

```python
from jirha.config import (
    CF_GIT_PR,
    CF_RN_STATUS,
    CF_RN_TEXT,
    CF_RN_TYPE,
    CF_SIZE,
    CF_SPRINT,
    CF_STORY_POINTS,
    CF_TEAM,
    DEFAULT_TEAM,
    SERVER,
    SP_VALUES,
    TEAM_RHDH_DOCS_ID,
)
```

- [ ] **Step 2: Add CF_SIZE to the fields fetched in cmd_show**

In `cmd_show`, update the `all_fields` string (around line 96) to include `CF_SIZE`:

```python
all_fields = (
    "summary,status,issuetype,priority,fixVersions,components,labels,"
    "reporter,versions,assignee,issuelinks,description,comment,"
    f"{CF_TEAM},{CF_SPRINT},{CF_STORY_POINTS},{CF_GIT_PR},"
    f"{CF_RN_STATUS},{CF_RN_TYPE},{CF_RN_TEXT},{CF_SIZE}"
)
```

- [ ] **Step 3: Display size in the Classification group**

After the `Labels` line (around line 117), add:

```python
size = getattr(f, CF_SIZE, None)
print(f"{'Size:':<{W}}{size or 'unset'}")
```

- [ ] **Step 4: Run tests**

Run: `venv/bin/pytest tests/unit/test_issues.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add jirha/ops/issues.py
git commit -m "feat: show size field in jirha show"
```

---

### Task 11: Update documentation

**Files:**
- Modify: `docs/sp-heuristics.md`
- Modify: `.claude/CLAUDE.md`

- [ ] **Step 1: Update sp-heuristics.md context assembler section**

Update the "Context assembler" section to document the JSON mode, caching, team-based classification, and link walking. Add the `/jirha:estimate KEY` entry point.

- [ ] **Step 2: Update .claude/CLAUDE.md command table**

Add the `context` command's new flags and the `estimate` command to the command table:

```
| `jirha context KEY [--json] [--refresh]` | Show hierarchy context (markdown or JSON) |
```

Add `/jirha:estimate KEY` to the slash commands list.

- [ ] **Step 3: Commit**

```bash
git add docs/sp-heuristics.md .claude/CLAUDE.md
git commit -m "docs: update SP heuristics and CLAUDE.md for estimate skill"
```
