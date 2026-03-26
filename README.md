# RHDH Docs Workflow

Workflow automation for the RHDH documentation team. Content lives in the [content repository](https://github.com/redhat-developer/red-hat-developers-documentation-rhdh).

## Setup

1. Fork and clone this repository.
2. Install the [GitHub CLI](https://cli.github.com/) and run `gh auth login`.
3. [Create a Jira API token](https://id.atlassian.com/manage-profile/security/api-tokens) — use a personal API token (not OAuth or PAT). The `jirha` CLI uses HTTP Basic authentication with your email and this token.
4. Copy `.env.example` to `.env` and set `JIRA_API_TOKEN` and `JIRA_EMAIL`.
5. Run `bash scripts/setup.sh`.
6. (Optional) Run `bash scripts/setup.sh --global` to make `jirha` available to Claude in all your projects.

### Additional setup for `pantheon-cli`

`pantheon-cli` requires Kerberos authentication and Playwright Firefox:

1. Ensure you have a valid Kerberos ticket: `kinit your-id@REDHAT.COM` (verify with `klist`).
2. Connect to the Red Hat VPN.
3. `setup.sh` automatically installs Playwright Firefox. If needed manually: `venv/bin/playwright install firefox`.

## Tools

### jirha

CLI for Jira operations. Auto-bootstraps into the workspace venv and loads `.env`. `~/bin/jirha` is a symlink to `scripts/jirha`, so it works from any directory.

Run `jirha --help` for all commands. See [docs/jira-reference.md](docs/jira-reference.md) for details.

### pantheon-cli

CLI for [Pantheon](https://pantheon.cee.redhat.com/) docs publishing operations. Manages build configurations, triggers rebuilds, and publishes releases. Uses Playwright Firefox with Kerberos SPNEGO for authentication.

```bash
pantheon-cli list --version 1.9                                           # list titles
pantheon-cli update --version 1.9 --env preview --branch release-1.10     # dry-run (default)
pantheon-cli update --version 1.9 --env preview --branch release-1.10 --exec
pantheon-cli rebuild --version 1.9 --env preview --enable --exec          # enable + rebuild
pantheon-cli publish --version 1.9 --exec --rebuild-first                 # publish to stage
```

Dry-run by default — use `--exec` to apply changes. Run `pantheon-cli --help` for all options. See [docs/pantheon-reference.md](docs/pantheon-reference.md) for architecture details and gotchas.

### visual-diff

Visual diff between stage and preview docs builds. Scrapes title links from the splash pages, screenshots each title in both environments, and generates an HTML report with side-by-side comparisons and diff overlays.

```bash
visual-diff urls --version 1.9                                            # list stage/preview URLs
visual-diff diff --version 1.9 --output /tmp/rhdh-1.9-diff/              # generate diff report
visual-diff diff --version 1.9 --title "About" --output /tmp/rhdh-diff/  # diff a single title
```

Requires VPN and Kerberos (same as `pantheon-cli`).
