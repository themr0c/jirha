#!/usr/bin/env bash
set -euo pipefail

# --- Paths ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

CACHE_DIR="$HOME/.cache/jirha"
VENV_DIR="$CACHE_DIR/venv"
CONFIG_DIR="$HOME/.config/jirha"
ENV_FILE="$CONFIG_DIR/.env"

# --- Fast exit: already set up? ---
if [[ -f "$ENV_FILE" ]] && [[ -x "$VENV_DIR/bin/jirha" ]]; then
  # Verify venv works (catches dangling editable installs after cache wipe)
  if "$VENV_DIR/bin/jirha" --help >/dev/null 2>&1; then
    # Re-point ~/bin symlink to current cache path (may change on update)
    mkdir -p ~/bin
    ln -sf "$SCRIPT_DIR/jirha" ~/bin/jirha
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

# --- gh CLI check (warn, don't block) ---
if ! command -v gh &>/dev/null; then
  echo "⚠ gh CLI not found — SP auto-assessment will not work"
  echo "  Install: https://cli.github.com/ then run 'gh auth login'"
elif ! gh auth status &>/dev/null 2>&1; then
  echo "⚠ gh CLI not authenticated — run 'gh auth login'"
fi

echo "Setup OK."
