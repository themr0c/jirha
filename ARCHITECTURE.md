# jirha — Architecture

## Overview

jirha is a Jira workflow helper CLI for the RHDH documentation team. It automates issue tracking, sprint management, effort estimation, hygiene auditing, and release notes authoring. Runs as a standalone CLI (`jirha`) and as a plugin for Claude Code and OpenCode (slash commands).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python >= 3.11 |
| Build | setuptools (`pyproject.toml`) |
| Jira | `python-jira` >= 3.5 (via `jira` package) |
| GitHub | `gh` CLI (subprocess) — PR metrics, file fetches, search |
| Excel | `openpyxl` >= 3.1 (quarterly reports) |
| Linter | ruff (select: E, F, I; line-length: 100) |
| Tests | pytest (MagicMock-based unit tests) |
| CI | GitHub Actions (ruff lint + format check + pytest) |

---

## Directory Structure

```
jirha/
├── jirha/                           # Main Python package
│   ├── __init__.py                  # Package marker
│   ├── config.py                    # Constants, field IDs, .env loading
│   ├── api.py                       # Jira connection, PR metrics, shared query helpers
│   ├── cache.py                     # Sprint data disk cache
│   ├── cli.py                       # Argparse entry point (jirha.cli:main)
│   └── ops/                         # CLI subcommand implementations
│       ├── __init__.py
│       ├── context.py               # jirha context KEY (hierarchy walk)
│       ├── daily.py                 # jirha daily (daily workflow)
│       ├── estimate.py              # jirha estimate (SP gap finder)
│       ├── hygiene.py               # jirha hygiene (sprint audit)
│       ├── issues.py                # jirha list/show/create/update/transition/close-subtasks
│       ├── meta.py                  # jirha meta PROJECT (metadata discovery)
│       ├── quarterly.py             # jirha quarterly (activity report)
│       ├── release_notes.py         # jirha release-notes VERSION
│       └── sprint.py                # jirha sprint-status / short-sprint-status
├── tests/
│   ├── unit/                        # 12 test files, MagicMock-based
│   └── integration/                 # Placeholder (no tests yet)
├── scripts/
│   ├── jirha                        # CLI entry point shim (auto-bootstraps venv)
│   ├── setup.sh                     # Dev environment setup
│   ├── derive_thresholds.py         # SP tier threshold derivation
│   └── hooks/                       # Git hooks (pre-commit, post-pr)
├── commands/                        # OpenCode slash command defs (15 .md files)
├── docs/                            # Reference docs, specs, plans
├── skills/                          # OpenCode skills (release-notes/)
├── .claude-plugin/                  # Claude Code plugin manifest + marketplace
├── .github/workflows/ci.yml        # CI pipeline
└── pyproject.toml                   # Package definition + tool config
```

---

## Core Components

### `jirha/config.py` — Configuration Layer
- Loads `.env` from repo root (JIRA_EMAIL, JIRA_API_TOKEN)
- Defines Jira custom field IDs (CF_STORY_POINTS, CF_GIT_PR, CF_RN_TEXT, etc.)
- Swimlane definitions: ordered `(name, predicate)` tuples for sprint board
- Constants: SP_VALUES, STATUS_ORDER, CACHE_DIR, DEFAULT_COMPONENT

### `jirha/api.py` — Jira & GitHub Integration
- `get_jira()` — Authenticated JIRA client factory (exits on missing creds)
- `_pr_metrics()` — SP tier from PR file stats (adoc/tooling/mixed classification)
- `_assess_multi_pr_sp()` — Aggregate SP from multiple PRs with cherry-pick dedup
- `_pr_status()` / `_fetch_pr_checklist()` — PR review/CI status via `gh` CLI
- `_fetch_user_prs()` — PR search by date range for quarterly reports
- `_extract_jira_keys()` — Regex-based Jira key extraction from text
- Session cache: `_pr_checklist_cache` dict for PR data

### `jirha/cli.py` — CLI Entry Point
- argparse-based, registers all subcommands with `set_defaults(func=...)`
- 14 subcommands: list, show, jql, hygiene, sprint-status, short-sprint-status, update, transition, create, meta, context, close-subtasks, estimate, quarterly, release-notes
- Each subcommand dispatches to `cmd_*` functions in `ops/`

### `jirha/cache.py` — Disk Cache
- JSON-based sprint metadata cache at `~/.cache/jirha/`
- `read_sprint_cache()` / `write_sprint_cache()` — used by `get_sprint_info()`
- No TTL; callers pass `refresh=True` to force re-fetch

### `jirha/ops/` — Subcommand Handlers

| Module | Commands | Key Functions |
|--------|----------|---------------|
| `issues.py` | list, show, create, update, transition, close-subtasks | `cmd_list()`, `cmd_show()`, `cmd_update()`, `_fmt_*()` display helpers |
| `sprint.py` | sprint-status, short-sprint-status | `cmd_sprint_status()`, `_assign_swimlane()`, `_blended_velocity()` |
| `hygiene.py` | hygiene | `cmd_hygiene()`, `_status_cross_check()`, `_assess_pr_sp()` |
| `context.py` | context | `cmd_context()`, `assemble_context_json()` |
| `estimate.py` | estimate | `cmd_estimate()` |
| `meta.py` | meta | `cmd_meta()` |
| `release_notes.py` | release-notes | `cmd_release_notes()` |
| `quarterly.py` | quarterly | `cmd_quarterly()` |
| `daily.py` | daily | `cmd_daily()` |

---

## Data Flow

### CLI Call Flow
```
scripts/jirha (shell shim → bootstraps venv)
  └─ venv/bin/jirha (console_script from pyproject.toml)
       └─ jirha.cli:main()
            └─ argparse parses → args.func(args)
                 └─ cmd_*() in ops/
                      ├─ get_jira()  (from api.py)
                      ├─ jira.search_issues() / jira.issue() / etc.
                      ├─ gh pr view  (subprocess for PR data)
                      └─ print()     (markdown-formatted output to stdout)
```

### PR → SP Assessment Flow
```
jirha update KEY --sp auto
  └─ cmd_update()
       └─ _assess_multi_pr_sp(pr_field)
            ├─ Split PR field by newlines → per-URL
            ├─ gh pr view --json files,commits,additions,deletions
            ├─ _pr_metrics(files, commits)
            │    ├─ Classify: doc / tooling / mixed (by adoc line share)
            │    ├─ Primary tier from adoc lines (_ADOC_TIER_THRESHOLDS)
            │    ├─ Floor from total lines (_TOTAL_TIER_THRESHOLDS)
            │    ├─ Complexity bump (+1 if 2+ structural signals)
            │    └─ Mechanical discount (−1 if >80% adoc files are ≤4 line changes)
            └─ Return SP from _TIER_TO_SP[tier]
```

### Sprint Status Flow
```
jirha sprint-status
  └─ cmd_sprint_status()
       └─ get_sprint_info(jira)
            ├─ read_sprint_cache() → return if valid
            ├─ _get_active_sprint() → find via JQL "sprint in openSprints()"
            ├─ _get_next_sprint() → board's next future sprint
            └─ write_sprint_cache()
       └─ Search issues → per-issue:
            ├─ _assign_swimlane() → first matching (name, predicate) pair
            ├─ _pr_status() / _fetch_pr_checklist() → review/CI state
            └─ _blended_velocity() → SP/day calculation
       └─ print() swimlane-grouped, markdown-formatted board
```

---

## External Integrations

| Service | Interface | Purpose |
|---------|-----------|---------|
| Red Hat Jira (redhat.atlassian.net) | `python-jira` (REST API) | Issue CRUD, search, transitions, metadata |
| GitHub | `gh` CLI (subprocess) | PR file stats, review status, check runs, cherry-pick detection |
| Local disk | JSON file (`~/.cache/jirha/`) | Sprint metadata cache |
| Local env | `.env` file | JIRA_EMAIL, JIRA_API_TOKEN |

---

## Configuration

### Environment Variables
| Variable | Required | Source | Purpose |
|----------|----------|--------|---------|
| `JIRA_EMAIL` | Yes | `.env` or env | Jira auth username |
| `JIRA_API_TOKEN` | Yes | `.env` or env | Jira auth token |
| `JOB_PROFILE` | No (default: `tw3`) | env | Job level for quarterly reports |

### Config Files
| File | Purpose |
|------|---------|
| `pyproject.toml` | Package metadata, deps, ruff config, pytest config |
| `.editorconfig` | Editor settings (space indent, 2 spaces, LF) |
| `.env` | Jira credentials (gitignored) |
| `.env.example` | Credential template |
| `.github/dependabot.yml` | Dependency updates |
| `.github/workflows/ci.yml` | CI: version sync check, ruff lint/format, pytest |

---

## Build & Deploy

### Prerequisites
```bash
Python 3.11+  gh auth login  Red Hat VPN
```

### Setup
```bash
git clone git@github.com:themr0c/jirha.git && cd jirha
bash scripts/setup.sh          # Create venv, install deps, symlink ~/bin/jirha
```

### Run Tests
```bash
pytest                          # Unit tests only (integration tests are placeholder)
pip install -e ".[dev]"        # Install dev deps (pytest, ruff)
ruff check .                   # Lint
ruff format --check .          # Format check
```

### CI Pipeline (`.github/workflows/ci.yml`)
1. Check version sync across `plugin.json`, `marketplace.json`, `pyproject.toml`
2. ruff lint + format check
3. pytest unit tests

### Versioning
Three files carry the version and must always match:
- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `pyproject.toml`

Bump all three together (patch for fixes, minor for new features/commands).

---

## Plugin Interfaces

### Claude Code Plugin
- Manifest: `.claude-plugin/plugin.json`
- Marketplace: `.claude-plugin/marketplace.json`
- Commands registered as CLI tools with argument schemas
- Guidance in `AGENTS.md`

### OpenCode Integration
- Project config: `opencode.json` — registers `skills/` path, uses `AGENTS.md` as instructions
- Slash commands: `commands/*.md` (15 commands, symlinked to `~/.config/opencode/commands/` via `scripts/setup.sh`)
- Skills: `skills/release-notes/` (auto-discovered via `opencode.json`)
- Agent guidance: `AGENTS.md` (loaded via `"instructions"` in opencode.json)
- Entry point: `jirha = jirha.cli:main` in pyproject.toml

---

## Dependency Graph (within `jirha/`)

```
config.py  ←  api.py  ←  cache.py
                ↑
                │
cli.py ──→ ops/*.py  ←  (circular avoidance via inline imports)
                │
                └──→ api.py (shared helpers)
```

Circular dependencies between `ops/` modules are avoided by using inline (deferred) imports:
```python
# In jirha/ops/issues.py
def _resolve_sp(...):
    from jirha.ops.context import assemble_context_json  # inline
```
