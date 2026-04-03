# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
bash scripts/setup.sh           # Create venv, install deps, symlink ~/bin/jirha
bash scripts/setup.sh --global  # Also install the post-PR hook globally
```

Prerequisites: GitHub CLI (`gh auth login`), `.env` with `JIRA_EMAIL` and `JIRA_API_TOKEN` (copy from `.env.example`).

## Running jirha

The script auto-bootstraps into the repo venv. Run it as:

```bash
jirha <command>           # via ~/bin/jirha symlink (works from any directory)
scripts/jirha <command>   # directly from repo root
```

## Architecture

**Package structure** — `jirha/` Python package with a clean dependency chain:

- `config.py` — constants, field IDs, `.env` loading
- `api.py` — Jira connection (`get_jira()`), PR metrics (`_pr_metrics()`), shared query helpers
- `ops/issues.py` — list, show, create, update, transition, close_subtasks commands
- `ops/meta.py` — metadata discovery (issue types, fields per project)
- `ops/sprint.py` — sprint_status, swimlane assignment, velocity/risk assessment
- `ops/hygiene.py` — hygiene checks, SP reassessment
- `cli.py` — argparse entry point (`jirha = jirha.cli:main`)

**scripts/jirha** is a thin shim: bootstraps the repo venv, then delegates to `venv/bin/jirha`.

**Slash commands** are in `.claude/commands/jirha-*.md` and invoke `jirha <subcommand> $ARGUMENTS`.

**Jira conventions skill** is at `skills/jira-workflow.md`.

## Key reference

- **Command reference**: `.claude/CLAUDE.md`
- **Custom field IDs, JQL templates, description templates, sprint status format**: `docs/jira-reference.md`
- **SP reference, auto-suggest heuristics, threshold methodology**: `docs/sp-heuristics.md`

## Inline python-jira (for queries jirha doesn't cover)

```python
from jira import JIRA
import os
jira = JIRA(server='https://redhat.atlassian.net',
            basic_auth=(os.environ['JIRA_EMAIL'], os.environ['JIRA_API_TOKEN']))
```
