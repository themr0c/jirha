# RHDH Docs Workflow

Workflow automation for the RHDH documentation team. Content lives in the [content repository](https://github.com/redhat-developer/red-hat-developers-documentation-rhdh).

## Install

```bash
claude plugins marketplace add git@github.com:themr0c/jirha.git
claude plugins install jirha@jirha
```

To update to the latest version:
```bash
claude plugins update jirha@jirha
```

First use auto-bootstraps: Python venv, dependencies, and Jira credentials.

**Prerequisites:**
- Python 3.11+
- Red Hat VPN (for Jira access)
- [GitHub CLI](https://cli.github.com/) (optional — needed for SP auto-assessment)

## Tools

### jirha

CLI for Jira operations. `~/bin/jirha` is a symlink created during setup, so it works from any terminal.

Run `jirha --help` for all commands. See [docs/jira-reference.md](docs/jira-reference.md) for details.

### Configuration

Credentials are stored in `~/.config/jirha/.env` (created on first use).
Python venv is at `~/.cache/jirha/venv/` (rebuilt automatically if needed).

To reconfigure credentials:
```
rm ~/.config/jirha/.env
jirha list  # triggers setup prompt
```
