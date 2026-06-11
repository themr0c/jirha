#!/usr/bin/env bash
set -euo pipefail

# --- Flags ---
DEV_MODE=false
for arg in "$@"; do
  case "$arg" in
    --dev) DEV_MODE=true ;;
  esac
done

# --- Paths ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

CACHE_DIR="$HOME/.cache/jirha"
VENV_DIR="$CACHE_DIR/venv"
CONFIG_DIR="$HOME/.config/jirha"
ENV_FILE="$CONFIG_DIR/.env"

# --- OpenCode config dir ---
OPENCODE_CONFIG_DIR="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"
OPENCODE_COMMANDS_DIR="$OPENCODE_CONFIG_DIR/commands"
OPENCODE_SKILLS_DIR="$OPENCODE_CONFIG_DIR/skills"

# --- OpenCode integration ---
# Symlink each command as jirha-<name>.md in ~/.config/opencode/commands/
# and each skill dir into ~/.config/opencode/skills/.
# Idempotent: skips links that already point to the right target.
_setup_opencode_links() {
  if ! command -v opencode &>/dev/null; then
    return 0
  fi

  local changed=false

  # Commands: commands/<name>.md → ~/.config/opencode/commands/jirha-<name>.md
  mkdir -p "$OPENCODE_COMMANDS_DIR"
  for src in "$PLUGIN_DIR/commands/"*.md; do
    local base
    base="$(basename "$src")"
    local dst="$OPENCODE_COMMANDS_DIR/jirha-${base}"
    if [[ "$(readlink "$dst" 2>/dev/null)" != "$src" ]]; then
      ln -sf "$src" "$dst"
      changed=true
    fi
  done

  # Skills: skills/<name>/ → ~/.config/opencode/skills/<name>/
  mkdir -p "$OPENCODE_SKILLS_DIR"
  for src in "$PLUGIN_DIR/skills"/*/; do
    [[ -d "$src" ]] || continue
    local skill_path="${src%/}"
    local name
    name="$(basename "$skill_path")"
    local dst="$OPENCODE_SKILLS_DIR/$name"
    if [[ "$(readlink "$dst" 2>/dev/null)" != "$skill_path" ]]; then
      ln -sf "$skill_path" "$dst"
      changed=true
    fi
  done

  if [[ "$changed" == true ]]; then
    echo "✓ OpenCode commands and skills linked"
  fi
}

# --- Fast exit: already set up? ---
if [[ -f "$ENV_FILE" ]] && [[ -x "$VENV_DIR/bin/jirha" ]]; then
  # Verify venv works (catches dangling editable installs after cache wipe)
  if "$VENV_DIR/bin/jirha" --help >/dev/null 2>&1; then
    # Re-point ~/bin symlink to current cache path (may change on update)
    mkdir -p ~/bin
    ln -sf "$SCRIPT_DIR/jirha" ~/bin/jirha
    _setup_opencode_links
    exit 0
  fi
fi

echo "jirha: setting up..."

# --- Credentials ---
if [[ ! -f "$ENV_FILE" ]]; then
  if [[ ! -t 0 ]]; then
    echo "ERROR: Jira credentials not configured."
    echo "Create $ENV_FILE with:"
    echo "  JIRA_EMAIL=you@redhat.com"
    echo "  JIRA_API_TOKEN=your-token"
    echo ""
    echo "Or run setup interactively:"
    echo "  bash $SCRIPT_DIR/setup.sh"
    exit 1
  fi
  mkdir -p "$CONFIG_DIR"
  echo ""
  read -rp "Enter your Jira email (e.g., user@redhat.com): " jira_email
  echo ""
  echo "Create a Jira API token at:"
  echo "  https://id.atlassian.com/manage-profile/security/api-tokens"
  echo "  (Click \"Create API token\", give it a name like \"jirha\", copy the value)"
  echo ""
  read -rp "Enter your Jira API token: " jira_token
  cat > "$ENV_FILE" <<EOF
JIRA_EMAIL=$jira_email
JIRA_API_TOKEN=$jira_token
EOF
  chmod 600 "$ENV_FILE"
  echo "✓ Credentials saved to $ENV_FILE"
fi

# --- Venv ---
if [[ ! -x "$VENV_DIR/bin/jirha" ]] || ! "$VENV_DIR/bin/jirha" --help >/dev/null 2>&1; then
  echo "Creating venv at $VENV_DIR..."
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install -q -r "$PLUGIN_DIR/requirements.txt"
  "$VENV_DIR/bin/pip" install -q -e "$PLUGIN_DIR"
  echo "✓ Venv created"
fi

# --- Symlink ---
mkdir -p ~/bin
ln -sf "$SCRIPT_DIR/jirha" ~/bin/jirha
echo "✓ Symlinked ~/bin/jirha"

if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
  echo "  Note: ~/bin is not in your shell PATH."
  echo "  To use jirha from your terminal, run:"
  echo "    echo 'export PATH=\"\$HOME/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc"
  echo "  (Inside Claude Code, jirha works automatically via the plugin.)"
fi

# --- OpenCode integration ---
_setup_opencode_links

# --- gh CLI check (warn, don't block) ---
if ! command -v gh &>/dev/null; then
  echo "⚠ gh CLI not found — SP auto-assessment will not work"
  echo "  Install: https://cli.github.com/ then run 'gh auth login'"
elif ! gh auth status &>/dev/null 2>&1; then
  echo "⚠ gh CLI not authenticated — run 'gh auth login'"
fi

# --- Dev mode: local venv + pre-commit hook ---
if [[ "$DEV_MODE" == true ]]; then
  DEV_VENV="$PLUGIN_DIR/venv"
  if [[ ! -d "$DEV_VENV" ]]; then
    echo "Creating dev venv at $DEV_VENV..."
    python3 -m venv "$DEV_VENV"
  fi
  "$DEV_VENV/bin/pip" install -q -e "$PLUGIN_DIR[dev]"
  echo "✓ Dev venv ready (ruff + pytest)"

  # Install pre-commit hook
  GIT_DIR="$(cd "$PLUGIN_DIR" && git rev-parse --git-common-dir 2>/dev/null || echo ".git")"
  HOOK_TARGET="$GIT_DIR/hooks/pre-commit"
  HOOK_SOURCE="$SCRIPT_DIR/hooks/pre-commit.sh"
  if [[ -e "$HOOK_TARGET" ]] && [[ ! -L "$HOOK_TARGET" ]]; then
    echo "⚠ $HOOK_TARGET already exists (not a symlink) — skipping hook install"
  else
    ln -sf "$HOOK_SOURCE" "$HOOK_TARGET"
    echo "✓ Pre-commit hook installed"
  fi
fi

echo "Setup OK."
