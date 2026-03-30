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

There are no tests or lint configuration in this repo.

## Architecture

**Single-file CLI** — all logic lives in `scripts/jirha` (~1,100 lines of Python). No package structure.

**Venv auto-bootstrap** — the script detects if it's running outside the repo venv and re-execs itself under `venv/bin/python`. This means no `source venv/bin/activate` is needed before running.

**Environment loading** — reads `.env` from the repo root for `JIRA_EMAIL` and `JIRA_API_TOKEN`, using HTTP Basic auth against `https://redhat.atlassian.net`.

**Post-PR hook** (`scripts/hooks/post-pr.sh`) — a Claude `PostToolUse` hook that fires after `gh pr create` or `gh pr edit` in the content repository. It extracts the Jira issue key from the current branch name (pattern: `RHIDP-XXXX`) and auto-runs `jirha update KEY --pr <URL> --sp auto`.

**SP auto-assessment** (`--sp auto`) — fetches PR metadata via `gh pr view` and applies tier-based heuristics on `.adoc` line counts. Details in [docs/jira-reference.md](docs/jira-reference.md#sp-heuristics---check-sp).

## Key reference

- **Command reference**: `.claude/CLAUDE.md`
- **Custom field IDs, JQL templates, SP heuristics, description templates, sprint status format**: `docs/jira-reference.md`

## Inline python-jira (for queries jirha doesn't cover)

```python
from jira import JIRA
import os
jira = JIRA(server='https://redhat.atlassian.net',
            basic_auth=(os.environ['JIRA_EMAIL'], os.environ['JIRA_API_TOKEN']))
```
