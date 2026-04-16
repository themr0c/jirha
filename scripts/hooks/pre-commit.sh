#!/usr/bin/env bash
# Pre-commit hook: run ruff check, ruff format, and pytest before each commit.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
VENV="$REPO_ROOT/venv"

# Skip if dev venv is not set up
if [[ ! -x "$VENV/bin/ruff" ]] || [[ ! -x "$VENV/bin/pytest" ]]; then
  echo "pre-commit: dev venv not found, skipping checks (run 'bash scripts/setup.sh --dev' to enable)"
  exit 0
fi

RUFF="$VENV/bin/ruff"
PYTEST="$VENV/bin/pytest"
FAILED=0

echo "pre-commit: running checks..."

if ! "$RUFF" check "$REPO_ROOT"; then
  echo ""
  echo "pre-commit: ruff check failed — fix lint errors before committing"
  FAILED=1
fi

if ! "$RUFF" format --check "$REPO_ROOT"; then
  echo ""
  echo "pre-commit: ruff format failed — run 'ruff format .' before committing"
  FAILED=1
fi

if ! "$PYTEST" "$REPO_ROOT/tests/unit/" -q; then
  echo ""
  echo "pre-commit: pytest failed — fix test failures before committing"
  FAILED=1
fi

if [[ $FAILED -ne 0 ]]; then
  echo ""
  echo "pre-commit: commit blocked — fix the issues above"
  exit 1
fi

echo "pre-commit: all checks passed"
