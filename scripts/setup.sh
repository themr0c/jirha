#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# Create/update venv if needed
if [[ ! -f venv/bin/activate ]] || [[ requirements.txt -nt venv/bin/activate ]]; then
  python3 -m venv venv
  venv/bin/pip install -q -r requirements.txt
  touch venv/bin/activate
fi

# Create ~/bin symlinks
mkdir -p ~/bin
ln -sf "$REPO_ROOT/scripts/jirha" ~/bin/jirha

if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
  if [[ -f "$HOME/.bashrc" ]]; then
    echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.bashrc"
    export PATH="$HOME/bin:$PATH"
  else
    echo "WARNING: ~/bin is not in PATH. Add to your shell profile:" >&2
    echo "  export PATH=\"\$HOME/bin:\$PATH\"" >&2
  fi
fi

ok=true

for cmd in jirha gh; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: $cmd is required" >&2
    ok=false
  fi
done

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  source .env
fi

[[ -z "${JIRA_API_TOKEN:-}" ]] && echo "WARNING: JIRA_API_TOKEN not set" >&2
[[ -z "${JIRA_EMAIL:-}" ]] && echo "WARNING: JIRA_EMAIL not set" >&2
gh auth status >/dev/null 2>&1 || echo "WARNING: gh auth required: run gh auth login" >&2
jirha list --max 1 >/dev/null 2>&1 || echo "WARNING: jirha could not fetch issues" >&2

[[ "$ok" == false ]] && exit 1
echo "Setup OK."

# --global: configure Claude to use jirha in all projects
if [[ "${1:-}" == "--global" ]]; then
  CLAUDE_DIR="$HOME/.claude"
  CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
  CLAUDE_SETTINGS="$CLAUDE_DIR/settings.json"

  mkdir -p "$CLAUDE_DIR"

  # Add jirha block to ~/.claude/CLAUDE.md if not present
  if [[ ! -f "$CLAUDE_MD" ]] || ! grep -q "scripts/jirha" "$CLAUDE_MD"; then
    cat >> "$CLAUDE_MD" <<EOF

# Jira Helper for RHDH Documentation

All Jira workflow knowledge is maintained in:

**Repository:** \`$REPO_ROOT\`
**Claude instructions:** \`.claude/CLAUDE.md\`
**Script:** \`scripts/jirha\` (runs from workspace venv)

Setup: \`cd $REPO_ROOT && bash scripts/setup.sh\`
EOF
    echo "Added jirha block to $CLAUDE_MD."
  else
    echo "jirha block already in $CLAUDE_MD."
  fi

  # Merge permissions into ~/.claude/settings.json
  if [[ ! -f "$CLAUDE_SETTINGS" ]]; then
    echo '{"permissions":{"allow":[]}}' > "$CLAUDE_SETTINGS"
  fi
  python3 -c "
import json
path = '$CLAUDE_SETTINGS'
with open(path) as f:
    data = json.load(f)
allow = data.setdefault('permissions', {}).setdefault('allow', [])
needed = ['Bash(jirha:*)', 'Bash(~/bin/jirha:*)']
added = []
for perm in needed:
    if perm not in allow:
        allow.append(perm)
        added.append(perm)
if added:
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
    for p in added:
        print(f'Added permission: {p}')
else:
    print('Permissions already configured.')
"
  # Install post-PR hook in content repo
  HOOK_SCRIPT="$REPO_ROOT/scripts/hooks/post-pr.sh"
  echo ""
  read -rp "Path to your clone of red-hat-developers-documentation-rhdh (leave empty to skip): " CONTENT_REPO
  if [[ -n "$CONTENT_REPO" ]]; then
    CONTENT_REPO="${CONTENT_REPO/#\~/$HOME}"
    if [[ ! -d "$CONTENT_REPO/.git" ]]; then
      echo "WARNING: $CONTENT_REPO does not look like a git repository. Skipping hook." >&2
    else
      LOCAL_SETTINGS="$CONTENT_REPO/.claude/settings.local.json"
      mkdir -p "$CONTENT_REPO/.claude"
      python3 -c "
import json, os

path = '$LOCAL_SETTINGS'
hook_cmd = 'bash $HOOK_SCRIPT'

if os.path.exists(path):
    with open(path) as f:
        data = json.load(f)
else:
    data = {}

hooks = data.setdefault('hooks', {})
post_tool = hooks.setdefault('PostToolUse', [])

# Check if hook already exists
already = any(
    h.get('matcher') == 'Bash' and
    any(hk.get('command', '') == hook_cmd for hk in h.get('hooks', []))
    for h in post_tool
)

if not already:
    post_tool.append({
        'matcher': 'Bash',
        'hooks': [{
            'type': 'command',
            'command': hook_cmd,
            'timeout': 30,
            'statusMessage': 'Syncing Jira...'
        }]
    })
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
    print(f'Installed post-PR hook in {path}.')
else:
    print(f'Post-PR hook already in {path}.')
"
      # Ensure settings.local.json is gitignored
      GITIGNORE="$CONTENT_REPO/.gitignore"
      if [[ ! -f "$GITIGNORE" ]] || ! grep -q 'settings.local.json' "$GITIGNORE"; then
        echo '.claude/settings.local.json' >> "$GITIGNORE"
      fi
    fi
  else
    echo "Skipping hook installation."
  fi

  echo "Global setup OK."
fi
