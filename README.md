# RHDH Docs Workflow

Workflow automation for the RHDH documentation team. Content lives in the [content repository](https://github.com/redhat-developer/red-hat-developers-documentation-rhdh).

## Setup

1. Fork and clone this repository.
2. Install the [GitHub CLI](https://cli.github.com/) and run `gh auth login`.
3. [Create a Jira API token](https://id.atlassian.com/manage-profile/security/api-tokens) — use a personal API token (not OAuth or PAT). The `jirha` CLI uses HTTP Basic authentication with your email and this token.
4. Copy `.env.example` to `.env` and set `JIRA_API_TOKEN` and `JIRA_EMAIL`.
5. Run `bash scripts/setup.sh`.
6. (Optional) Run `bash scripts/setup.sh --global` to make `jirha` available to Claude in all your projects.

## jirha

CLI for Jira operations. Auto-bootstraps into the workspace venv and loads `.env`. `~/bin/jirha` is a symlink to `scripts/jirha`, so it works from any directory.

Run `jirha --help` for all commands.
