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

# Version consistency: plugin.json, marketplace.json, and pyproject.toml must match
# CI uses jq + tomllib for robust parsing; here we use python for portability
V_PYPROJECT=$(sed -n 's/^version = "\(.*\)"/\1/p' "$REPO_ROOT/pyproject.toml")
V_PLUGIN=$(python3 -c "import json,sys; print(json.load(sys.stdin)['version'])" < "$REPO_ROOT/.claude-plugin/plugin.json")
V_MARKETPLACE=$(python3 -c "import json,sys; print(json.load(sys.stdin)['plugins'][0]['version'])" < "$REPO_ROOT/.claude-plugin/marketplace.json")

if [[ -z "$V_PYPROJECT" ]] || [[ -z "$V_PLUGIN" ]] || [[ -z "$V_MARKETPLACE" ]]; then
  echo "pre-commit: could not extract version from one or more files"
  FAILED=1
elif [[ "$V_PYPROJECT" != "$V_PLUGIN" ]] || [[ "$V_PYPROJECT" != "$V_MARKETPLACE" ]]; then
  echo ""
  echo "pre-commit: version mismatch — all three must match:"
  echo "  pyproject.toml:          $V_PYPROJECT"
  echo "  plugin.json:             $V_PLUGIN"
  echo "  marketplace.json:        $V_MARKETPLACE"
  FAILED=1
fi

if [[ $FAILED -ne 0 ]]; then
  echo ""
  echo "pre-commit: commit blocked — fix the issues above"
  exit 1
fi

echo "pre-commit: all checks passed"
