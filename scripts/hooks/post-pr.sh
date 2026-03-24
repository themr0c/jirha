#!/usr/bin/env bash
# PostToolUse hook: auto-sync Jira after gh pr create/edit.
set -euo pipefail

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

# Only match gh pr create/edit
echo "$CMD" | grep -qE 'gh pr (create|edit)' || exit 0

KEY=$(git branch --show-current | grep -oE 'RHIDP-[0-9]+' || true)
[[ -z "$KEY" ]] && exit 0

PR_URL=$(gh pr view --json url -q '.url' 2>/dev/null || true)
[[ -z "$PR_URL" ]] && exit 0

OUTPUT=$(jirha update "$KEY" --pr "$PR_URL" --sp auto 2>&1 || true)

# Escape for JSON
OUTPUT=$(echo "$OUTPUT" | sed 's/"/\\"/g' | tr '\n' ' ')

cat <<EOF
{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"$OUTPUT"}}
EOF
