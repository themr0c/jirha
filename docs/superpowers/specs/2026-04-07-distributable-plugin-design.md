# Distributable Claude Code Plugin — Design Spec

**Date**: 2026-04-07
**Status**: Draft

## Problem

jirha is a working Claude Code plugin but requires cloning the git repository to use it. Teammates cannot install it without manual git clone + setup steps. There is no update mechanism.

## Goal

Make jirha installable with a single command (`claude plugins add --git-url ...`), with automatic setup on first use and automatic updates when changes are pushed to `main`.

## Target Audience

Red Hat RHDH documentation team — a handful of writers who use the same Jira projects, field IDs, and conventions. No generalization needed.

## Approach

Register the `themr0c/jirha` GitHub repo as a git URL marketplace (same pattern as `redhat-docs-agent-tools` and `pantheon-cli`). Claude Code clones it into its plugin cache, tracks commits, and auto-updates. A before-hook triggers `setup.sh` on first use to bootstrap the Python venv and prompt for Jira credentials.

## Changes

### 1. Marketplace & Plugin Manifests

**Modified**: `.claude-plugin/marketplace.json`

```json
{
  "name": "jirha",
  "description": "Jira workflow helper for RHDH documentation",
  "owner": { "name": "Fabrice Flore-Thébault" },
  "plugins": [
    {
      "name": "jirha",
      "source": ".",
      "description": "List, show, update, create, transition issues and sprint status",
      "version": "1.0.0"
    }
  ]
}
```

**Modified**: `.claude-plugin/plugin.json`

```json
{
  "name": "jirha",
  "description": "Jira workflow helper for RHDH documentation — list, show, update, create, transition issues and sprint status",
  "author": { "name": "themr0c" },
  "version": "1.0.0"
}
```

### 2. Auto-setup Hook

**New file**: `.claude-plugin/hooks.json`

```json
{
  "hooks": [
    {
      "event": "before",
      "matcher": "Bash(jirha*)",
      "command": "bash \"$PLUGIN_DIR/scripts/setup.sh\"",
      "description": "Bootstrap venv, dependencies, and Jira credentials on first use"
    }
  ]
}
```

- Fires before every `jirha` Bash call
- `setup.sh` is idempotent — exits quickly (~100ms) after first bootstrap
- `$PLUGIN_DIR` resolves to the cached plugin directory

### 3. Directory Layout

Three user-space directories outside the plugin cache:

| Path | Purpose | Created by |
|---|---|---|
| `~/.cache/jirha/venv/` | Python venv with `jira` + `openpyxl` | setup.sh |
| `~/.config/jirha/.env` | `JIRA_EMAIL` and `JIRA_API_TOKEN` | setup.sh (interactive prompt) |
| `~/bin/jirha` | Symlink to cached `scripts/jirha` | setup.sh |

Venv and config survive plugin cache wipes (which happen on update). Symlink gets re-pointed to the new cache path on each setup.sh run.

### 4. Adapted `scripts/setup.sh`

**Find itself without git:**
```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
```

**External directories:**
```bash
CACHE_DIR="$HOME/.cache/jirha"
VENV_DIR="$CACHE_DIR/venv"
CONFIG_DIR="$HOME/.config/jirha"
ENV_FILE="$CONFIG_DIR/.env"
```

**Idempotency logic (fast exit path):**
1. If `$ENV_FILE` exists AND `$VENV_DIR/bin/jirha` works (`--help` exits 0) → re-point symlink, exit
2. If `$ENV_FILE` missing → interactive prompt for email + token
3. If venv missing or `jirha --help` fails (dangling editable install after cache wipe) → create/rebuild venv, `pip install -r requirements.txt && pip install -e "$PLUGIN_DIR"`
4. Always re-point `~/bin/jirha` symlink to `$SCRIPT_DIR/jirha` (handles cache path changes on update)

**First-run interactive prompt:**
```
jirha: first-time setup

Enter your Jira email (e.g., user@redhat.com): 

Create a Jira API token at:
  https://id.atlassian.com/manage-profile/security/api-tokens
  (Click "Create API token", give it a name like "jirha", copy the value)

Enter your Jira API token: 

✓ Credentials saved to ~/.config/jirha/.env
✓ Venv created at ~/.cache/jirha/venv/
✓ Symlinked ~/bin/jirha
```

**`gh` CLI check (warn, don't block):**
```bash
if ! command -v gh &>/dev/null; then
    echo "⚠ gh CLI not found — SP auto-assessment will not work"
    echo "  Install: https://cli.github.com/ then run 'gh auth login'"
elif ! gh auth status &>/dev/null 2>&1; then
    echo "⚠ gh CLI not authenticated — run 'gh auth login'"
fi
```

**What gets removed from setup.sh:**
- `git rev-parse --show-toplevel` (not a git repo in cache)
- `--global` flag logic (injecting into `~/.claude/CLAUDE.md` and `~/.claude/settings.json` — the plugin system handles this)
- Post-PR hook installation (unrelated to plugin setup)

### 5. Adapted `scripts/jirha` (shim)

```python
#!/usr/bin/env python3
"""Thin shim: bootstraps cached venv, then delegates to jirha CLI."""

import os
import sys
from pathlib import Path

_venv_dir = Path.home() / ".cache" / "jirha" / "venv"
_venv_python = _venv_dir / "bin" / "python"
_venv_jirha = _venv_dir / "bin" / "jirha"

# Load .env from user config
_env_file = Path.home() / ".config" / "jirha" / ".env"
if _env_file.is_file():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

if _venv_python.is_file() and Path(sys.prefix).resolve() != _venv_dir.resolve():
    os.execv(str(_venv_python), [str(_venv_python), str(_venv_jirha)] + sys.argv[1:])

from jirha.cli import main
main()
```

Changes from current shim:
- Venv path: `~/.cache/jirha/venv/` instead of `<repo>/venv/`
- `.env` loading: `~/.config/jirha/.env` instead of `<repo>/.env`
- No `git rev-parse`, no repo-relative paths

### 6. Plugin Permissions

**Modified**: `.claude/settings.json`

```json
{
  "permissions": {
    "allow": [
      "Bash(jirha:*)",
      "Bash(~/bin/jirha:*)",
      "Bash(bash scripts/setup.sh:*)"
    ]
  }
}
```

Removed from current version:
- Hardcoded absolute paths from `additionalDirectories`
- Dev-only permissions: `Edit(.claude/**)`, `Write(.claude/**)`, `Skill(update-config)`, `python3 -c`, `pip install`

### 7. README Update

Replace manual setup instructions with:

```
## Install

claude plugins add --git-url https://github.com/themr0c/jirha.git

First use auto-bootstraps: venv, deps, Jira credentials.
Prerequisites: Python 3.11+, Red Hat VPN (for Jira access)
Optional: gh CLI (https://cli.github.com/) for SP auto-assessment
```

## What Stays the Same

- `commands/*.md` (11 slash commands) — already work, just call `jirha <subcommand>`
- `jirha/` Python package — no code changes
- `.claude/CLAUDE.md` — plugin docs already correct
- `docs/`, `tests/` — no impact
- All Jira field IDs, JQL templates, RHDH conventions

## Update Flow

1. You push to `main`
2. Claude Code detects new commits on next session start, re-caches
3. Next `jirha` call triggers hook → `setup.sh` runs → detects venv exists, credentials exist → re-points `~/bin/jirha` symlink to new cache path → exits fast
4. If `requirements.txt` changed (timestamp check), rebuilds venv
5. Version field in manifests is informational — git SHA tracks actual state

## Migration (current local setup)

- Unregister the `jirha-local` directory marketplace from `~/.claude/settings.json` `extraKnownMarketplaces`
- `claude plugins add --git-url https://github.com/themr0c/jirha.git`
- Move `.env` to `~/.config/jirha/.env`
- Remove old `venv/` from repo root

## Verification

1. **Clean install** — from a machine with no jirha clone, run `claude plugins add --git-url https://github.com/themr0c/jirha.git`, then `/jirha:list --open` — should trigger setup, prompt for credentials, bootstrap venv, then list issues
2. **Terminal use** — after setup, `jirha list --open` from any terminal should work via `~/bin/jirha`
3. **Update test** — push a trivial change to `main`, restart Claude, verify plugin updates and setup.sh re-runs idempotently (fast exit, no re-prompt)
4. **Missing gh** — on a machine without `gh`, verify warning is printed but commands that don't need it still work

## Files Modified

| File | Change |
|---|---|
| `.claude-plugin/marketplace.json` | Update name, add version |
| `.claude-plugin/plugin.json` | Add version field |
| `.claude-plugin/hooks.json` | New — before hook for auto-setup |
| `scripts/setup.sh` | Cache-aware paths, interactive credential prompt, gh warning, drop --global |
| `scripts/jirha` | Venv and .env at user-space paths |
| `.claude/settings.json` | Remove hardcoded paths and dev-only permissions |
| `README.md` | Update install instructions |
