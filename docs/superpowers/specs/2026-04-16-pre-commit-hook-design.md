# Pre-commit Hook — Design Spec

## Problem

Lint, format, and test errors are caught after pushing, requiring multiple fix-up commits. A git pre-commit hook catches them before the commit happens.

## Design

### `scripts/hooks/pre-commit.sh`

Runs on every `git commit`. Three checks, in order:

1. `ruff check .` — lint errors
2. `ruff format --check .` — formatting violations
3. `pytest tests/unit/ -q` — unit test failures

If any check fails, the commit is blocked and the failing output is shown.

**Venv resolution:** The hook finds the repo root via `git rev-parse --show-toplevel` and looks for `venv/bin/ruff` and `venv/bin/pytest`. If the local dev venv is missing or lacks dev tools, the hook prints a warning and exits 0 (allows commit) — so it doesn't break for non-dev users or CI.

### `scripts/setup.sh` changes

Add a `--dev` flag that:

1. Creates a local `venv/` directory with dev dependencies: `pip install -e ".[dev]"`
2. Symlinks `.git/hooks/pre-commit` → `scripts/hooks/pre-commit.sh`

Without `--dev`, setup.sh behaves exactly as today (plugin install, cache venv, no hook).

### Worktree compatibility

Worktrees share the main repo's `.git/hooks/`. The hook uses `git rev-parse --show-toplevel` to resolve the correct working directory, so it runs checks from the right root regardless of which worktree triggers the commit.

## Files

| File | Action |
|------|--------|
| `scripts/hooks/pre-commit.sh` | Create |
| `scripts/setup.sh` | Add `--dev` flag |

## Verification

1. `bash scripts/setup.sh --dev` — creates local venv, installs hook
2. Introduce a ruff error, attempt commit — blocked
3. Fix error, commit — succeeds
4. `bash scripts/setup.sh` (without --dev) — no hook installed, existing behavior unchanged
