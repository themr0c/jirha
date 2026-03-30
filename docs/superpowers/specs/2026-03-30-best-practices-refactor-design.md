# jirha: Best Practices Refactor + Claude Plugin

**Date:** 2026-03-30
**Approach:** Option C — Package with plugin integration (middle ground)

## Goals

- Refactor `scripts/jirha` (1,068-line monolith) into a proper Python package with focused modules
- Add Claude plugin with slash commands wrapping the CLI
- Add `ruff` linting and `pytest` unit tests
- Preserve full backward compatibility: `~/bin/jirha` symlink and all subcommand behavior unchanged; behavior changes acceptable where they improve UX

---

## Package Structure

```
jirha/               ← Python package (replaces scripts/jirha monolith)
  __init__.py
  config.py          ← env loading, SERVER, EMAIL, custom field IDs, SP_VALUES, constants
  api.py             ← get_jira(), gh CLI subprocess wrapper, _pr_metrics()
  ops/
    __init__.py
    issues.py        ← list, show, create, update, transition, close_subtasks
    sprint.py        ← sprint_status, swimlane assignment, velocity/risk, business day counting
    hygiene.py       ← hygiene checks, --check-sp logic
  cli.py             ← argparse entry point, dispatches to ops modules

scripts/jirha        ← thin shim: venv auto-bootstrap, then exec jirha.cli:main
pyproject.toml       ← package definition, entry_point jirha = jirha.cli:main, ruff config, pytest config
requirements.txt     ← kept for direct venv installs (pip install -r)
```

### Module responsibilities

| Module | Owns |
|---|---|
| `config.py` | All constants: `SERVER`, `EMAIL`, `CF_*` field IDs, `SWIMLANES` definition, `SP_VALUES`, `STATUS_ORDER`, defaults |
| `api.py` | `get_jira()` connection factory, `gh_pr_view()` subprocess call, `_pr_metrics()` tier calculation |
| `ops/issues.py` | `cmd_list`, `cmd_show`, `cmd_create`, `cmd_update`, `cmd_transition`, `cmd_close_subtasks` |
| `ops/sprint.py` | `cmd_sprint_status`, `_assign_swimlanes`, `_business_days`, velocity/risk logic |
| `ops/hygiene.py` | `cmd_hygiene`, `_check_sp_mismatch` |
| `cli.py` | `main()`, argparse setup, subparser wiring, exit codes |

### scripts/jirha shim

```python
#!/usr/bin/env python3
# Re-exec under repo venv if needed, then delegate to installed CLI
import os, sys
from pathlib import Path
_venv_python = Path(__file__).resolve().parent.parent / 'venv' / 'bin' / 'python'
if _venv_python.is_file() and Path(sys.executable).resolve() != _venv_python.resolve():
    os.execv(str(_venv_python), [str(_venv_python), str(_venv_python.parent / 'jirha')] + sys.argv[1:])
# If already in venv, the entry point handles it
from jirha.cli import main
main()
```

---

## Claude Plugin

### plugin.json

Registers the plugin and its slash commands. Each command invokes `jirha <subcommand>` via Bash.

```json
{
  "name": "jirha",
  "description": "Jira workflow automation for RHDH docs",
  "version": "1.0.0",
  "commands": [
    { "name": "jirha-list", "description": "List my Jira issues", "bash": "jirha list $ARGS" },
    { "name": "jirha-show", "description": "Show issue details", "bash": "jirha show $ARGS" },
    ...
  ],
  "skills": ["skills/jira-workflow.md"]
}
```

The exact `plugin.json` schema (field names, arg passing convention) will be confirmed against the installed Claude plugin spec during implementation.

### Slash commands

| Command | Invokes | Description |
|---|---|---|
| `/jirha-list [--open]` | `jirha list [--open]` | List my Jira issues |
| `/jirha-show KEY` | `jirha show KEY` | Show issue details |
| `/jirha-sprint-status [--team]` | `jirha sprint-status [--team]` | Sprint board with velocity/risk |
| `/jirha-hygiene [--check-sp]` | `jirha hygiene [--check-sp]` | Flag issues with missing metadata |
| `/jirha-update KEY ...` | `jirha update KEY ...` | Batch-update issue fields |
| `/jirha-transition KEY [STATUS]` | `jirha transition KEY [STATUS]` | Transition issue status |
| `/jirha-create PROJECT SUMMARY ...` | `jirha create PROJECT SUMMARY ...` | Create a new issue |

Commands run `jirha` via Bash and return stdout directly to Claude. No output reformatting needed — the existing text output is Claude-readable.

### Skill: skills/jira-workflow.md

A single skill file providing context Claude needs to reason about jirha output:
- Custom field IDs and their meaning
- SP heuristics (tier thresholds, complexity bumps, mechanical discount)
- Jira description templates (Task, Epic)
- Sprint status swimlane order and risk assessment format
- Post-PR workflow (link PR, auto-assess SP, populate description)

This avoids Claude re-reading `docs/jira-reference.md` each session.

---

## Testing

### Unit tests (`tests/unit/`)

Mock the Jira client (`jira.JIRA`) and `subprocess` (for `gh` calls). Cover pure-logic paths:

| Test file | Covers |
|---|---|
| `test_sp.py` | `_pr_metrics()`: tier thresholds, complexity bumps, mechanical discount |
| `test_swimlanes.py` | `_assign_swimlanes()`: each swimlane predicate with fabricated issue objects |
| `test_hygiene.py` | Hygiene flag logic: missing fields, SP mismatch detection |
| `test_config.py` | Env loading: present/missing `JIRA_EMAIL`, `.env` parsing |

### Integration smoke tests (`tests/integration/`)

Marked `@pytest.mark.integration`, skipped by default. Require real credentials in `.env`. Cover `jirha list` and `jirha show` against the real Jira instance to catch API drift.

### Running tests

```bash
pytest                          # unit tests only (default)
pytest -m integration           # smoke tests (requires .env with real creds)
pytest tests/unit/test_sp.py    # single file
```

---

## Linting

`ruff` configured in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I"]   # pycodestyle errors, pyflakes, isort
```

Run: `ruff check .` and `ruff format .`

---

## CI (GitHub Actions)

`.github/workflows/ci.yml` — runs on push to any branch:

1. Set up Python 3.11
2. Install package + dev deps (`pip install -e ".[dev]"`)
3. `ruff check .`
4. `pytest` (unit tests only)

---

## pyproject.toml structure

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "jirha"
version = "1.0.0"
dependencies = ["jira>=3.5", "openpyxl>=3.1"]

[project.scripts]
jirha = "jirha.cli:main"

[project.optional-dependencies]
dev = ["pytest", "ruff"]

[tool.pytest.ini_options]
testpaths = ["tests/unit"]
markers = ["integration: requires real Jira credentials"]
```

---

## Migration notes

- `setup.sh` gains a step: `pip install -e .` to install the package into the venv (so both the `jirha` entry point and the `scripts/jirha` shim work)
- `~/bin/jirha` symlink to `scripts/jirha` is unchanged
- All existing subcommand flags and output formats are preserved (behavior changes acceptable but not required)
- `.claude/CLAUDE.md` and `CLAUDE.md` updated to reference the new structure
