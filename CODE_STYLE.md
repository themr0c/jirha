# jirha — Code Style Guide

This document describes the coding conventions used in the jirha project. Follow these conventions when writing or modifying code.

---

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Files/directories | `snake_case` | `jirha/api.py`, `ops/sprint.py` |
| Test files | `test_*.py` | `test_issues.py`, `test_sprint.py` |
| Public functions | `snake_case` | `get_jira()`, `cmd_list()`, `parse_fields()` |
| Private functions | `_snake_case` (leading underscore) | `_issue_sp()`, `_pr_metrics()`, `_fmt_versions()` |
| CLI command handlers | `cmd_<verb>` | `cmd_list`, `cmd_show`, `cmd_update` |
| Test classes | `Test<FunctionName>` (CapWords) | `TestFmtVersions`, `TestSprintCache` |
| Test functions | `test_<scenario>` | `test_empty`, `test_add_new_label` |
| Module-level constants | `UPPER_CASE` | `SERVER`, `CF_STORY_POINTS`, `SP_VALUES` |
| Module-level private data | `_UPPER_CASE` | `_TIER_TO_SP`, `_ADOC_TIER_THRESHOLDS` |
| Local variables | `snake_case` | `sp_str`, `result`, `issue_gaps` |
| Formatting helpers | `_fmt_*` | `_fmt_versions()`, `_fmt_components()`, `_fmt_labels()` |

---

## File Organization

### Source files (`jirha/`)

- **One module per layer**, not per feature:
  - `config.py` — constants, env, field IDs
  - `api.py` — Jira connection, helpers, PR logic
  - `cache.py` — disk cache
  - `cli.py` — argparse, dispatch
- **One module per CLI domain** in `ops/`:
  - `issues.py` — everything issue CRUD
  - `sprint.py` — sprint board
  - `hygiene.py` — audit
  - etc.

### Test files (`tests/`)

Mirror the source layout exactly:
```
jirha/ops/issues.py  →  tests/unit/test_issues.py
jirha/api.py         →  tests/unit/test_api.py  (not yet created)
```

---

## Module Structure

Every `.py` file follows this order:

```python
"""One-line docstring describing the module's purpose."""
# Line 1: module-level docstring

import sys              # 1. Standard library
from pathlib import Path

from jirha.api import (  # 2. Third-party → internal (no third-party in source)
    get_jira,
    _assignee_name,
)
from jirha.config import (
    CF_STORY_POINTS,
    SP_VALUES,
)

# 3. Module-level constants / private data
STATUS_ORDER = {"New": 0, "In Progress": 1}
_SP_TIERS = dict(zip(SP_VALUES, range(len(SP_VALUES))))

# 4. Functions (public first, then private)
def public_function():
    ...

def _private_helper():
    ...
```

---

## Import Style

1. **Standard library first** — grouped, no empty line between members
2. **Internal absolute imports** — always `from jirha.xxx import yyy`
3. **No bare imports** — `import jirha.api` is not used; always `from jirha.api import X`
4. **Deferred imports** for circular dependency avoidance — import inside function body:

```python
# Good: inline import breaks circular dependency
def _resolve_sp(jira, issue_key):
    from jirha.ops.context import assemble_context_json
    ...

# Wrong: module-level import creates circular dependency
from jirha.ops.context import assemble_context_json  # DON'T if issues.py imports api.py
```

5. **Third-party imports are always deferred** (in function body):

```python
def get_jira():
    from jira import JIRA      # deferred, not at module level
    ...
```

---

## Code Patterns

### CLI Commands

Every CLI command follows this pattern:

```python
# 1. Register in cli.py (argparse)
p = sub.add_parser("command-name", help="One-line description")
p.add_argument("--flag", action="store_true")
p.set_defaults(func=cmd_command_name)

# 2. Implement in ops/xxx.py
def cmd_command_name(args):
    jira = get_jira()
    # ... logic ...
    print(...)  # output via print()
```

### Display Formatting Helpers (`_fmt_*`)

Pure functions that convert Jira API objects to display strings:

```python
def _fmt_versions(versions):
    if not versions:
        return "unset"
    return ", ".join(v.name for v in versions)

def _fmt_labels(labels):
    if not labels:
        return "unset"
    return ", ".join(labels)
```

Pattern: `None`/empty → `"unset"`, populated → `", ".join(...)`.

### Swimlane Predicates

Defined in `config.py` as `(name, lambda)` tuples. First match wins:

```python
SWIMLANES = [
    ("Blocker", lambda i: str(i.fields.priority) == "Blocker"),
    ("Customer", lambda i: bool(set(i.fields.labels or []) & {"customer", ...})),
    ("Other", lambda i: True),  # catch-all
]
```

### Test Structure

- **Pure function tests** with `MagicMock` for Jira objects
- **Group by class** (preferred) or **standalone functions** for simple modules:

```python
# Class grouping
class TestFmtVersions:
    def test_empty(self):
        assert _fmt_versions([]) == "unset"

    def test_single(self):
        v = MagicMock()
        v.name = "1.10.0"
        assert _fmt_versions([v]) == "1.10.0"

# Standalone (simpler modules)
def test_parse_all():
    mismatches = [{"key": "RHIDP-1"}, {"key": "RHIDP-2"}]
    apply, overrides = _parse_sp_choice("a", mismatches)
    assert apply == {0, 1}
```

---

## Error Handling

### User-facing errors — `sys.exit("Error: ...")`

```python
if not EMAIL:
    sys.exit("Error: JIRA_EMAIL not set. Add it to .env or export it.")
```

Pattern: `"Error: "` prefix, then actionable message. **Never raise custom exceptions** for CLI error paths.

### Transient failures — `return None`

```python
try:
    result = subprocess.run(..., timeout=15)
    data = json.loads(result.stdout)
except (subprocess.TimeoutExpired, json.JSONDecodeError):
    return None  # caller checks for None
```

Used for API timeouts, PR fetch failures, cache misses. The caller handles `None` gracefully.

### Exceptions

Python exceptions are **not used for control flow**. Only catch expected transient errors (`TimeoutExpired`, `JSONDecodeError`) and return `None`.

---

## Logging

**No `logging` module.** All output goes to stdout via `print()`.

Output is markdown-friendly:
- `##` for section headings
- `###` for sub-sections
- `- ` for bullet lists
- `|` for tables
- `## WARNING:` for warning sections

```python
print(f"\n## {name} — {int(lane_closed_sp)}/{int(lane_total_sp)} SP ({lane_pct:.0f}%)\n")
print(f"- {url}{sp_str}{assignee_str} [{tag}] — {issue.fields.summary}")
```

---

## Ruff Configuration (from `pyproject.toml`)

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I"]
```

| Rule | Meaning |
|------|---------|
| E | pycodestyle errors |
| F | pyflakes (logic errors) |
| I | isort (import order) |

**CI enforces both `ruff check .` and `ruff format --check .`.**

---

## EditorConfig (from `.editorconfig`)

```ini
[*]
charset = utf-8
end_of_line = lf
indent_style = space
indent_size = 2
insert_final_newline = true
trim_trailing_whitespace = true
```

---

## Do's and Don'ts

### Do
- Start every `.py` with a one-line docstring
- Use `sys.exit("Error: ...")` for user-facing CLI errors
- Use `return None` for transient API failures
- Import `jira.JIRA` and other third-party libs inside the function body
- Put internal imports at module level (`from jirha.api import X`)
- Use inline imports for cross-`ops/` references to avoid circular deps
- Name CLI handlers `cmd_<verb>`
- Name formatting helpers `_fmt_*`
- Name test classes `Test<FunctionName>` and test functions `test_<scenario>`
- Output markdown-friendly text via `print()`
- Keep file line length ≤ 100
- Indent with 2 spaces (per `.editorconfig`)

### Don't
- Don't use `logging` — use `print()`
- Don't raise custom exceptions for CLI errors — use `sys.exit()`
- Don't use bare `except:` — always specify exception types
- Don't create module-level circular imports between `ops/` modules
- Don't add emojis to code or output
- Don't add type annotations (project doesn't use them)
- Don't create `setup.py`, `setup.cfg`, or `MANIFEST.in` — use `pyproject.toml` only
- Don't commit with mismatched version in `plugin.json` / `marketplace.json` / `pyproject.toml`
