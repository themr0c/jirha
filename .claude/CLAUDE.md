# RHDH Docs Workflow

## jirha

CLI for Jira operations. Auto-bootstraps into the workspace venv and loads `.env`. `~/bin/jirha` is a symlink to `scripts/jirha`, so it works from any directory.

| Command | Description |
|---|---|
| `jirha list [--open] [--jql "..."] [--max N]` | List my issues |
| `jirha show KEY` | Show issue details (desc, comments, SP, PR, RN) |
| `jirha jql "QUERY" [--max N]` | Run arbitrary JQL |
| `jirha hygiene [--max N] [--team] [--check-sp] [--dry-run]` | List issues with missing metadata; `--check-sp` reassesses SP from linked PRs |
| `jirha sprint-status [--team]` | Sprint board by priority swimlanes |
| `jirha update KEY [-s SUMMARY] [--desc TEXT] [--desc-file FILE] [--sp N\|auto] [--pr URL] [--priority P] [--component C] [--team T] [--add-label L] [--remove-label L] [--link-to KEY] [--link-type TYPE] [--sprint [NAME]] [-c "comment"] [-f FILE]` | Batch-update issue fields, link, or add to sprint |
| `jirha transition KEY [STATUS]` | Transition issue, or list available transitions |
| `jirha create PROJECT SUMMARY [--type TYPE] [--component NAME] [--priority NAME] [--parent KEY] [--desc TEXT] [-f FILE]` | Create a new issue (use `--parent` for sub-tasks) |
| `jirha close-subtasks [--dry-run]` | Close open subtasks of closed parents |

For custom field IDs, JQL queries, description templates, SP heuristics, and sprint status format, see [docs/jira-reference.md](../docs/jira-reference.md).

## pantheon-cli

CLI for Pantheon docs publishing operations. Auto-bootstraps into the workspace venv and loads `.env` for `JIRA_EMAIL`. Requires a valid Kerberos ticket (`kinit`) and VPN.

| Command | Description |
|---|---|
| `pantheon-cli list --version 1.9` | List titles with job states, branches, content dirs |
| `pantheon-cli update --version 1.9 --env preview --branch BRANCH [--directory DIR] [--enable] [--rebuild] [--exec]` | Update build config (dry-run by default) |
| `pantheon-cli rebuild --version 1.9 --env preview [--enable] [--wait] [--exec]` | Trigger rebuilds |
| `pantheon-cli publish --version 1.9 [--rebuild-first] [--wait] [--exec]` | Enable + rebuild stage builds |

Common options: `--product` (default: `red_hat_developer_hub`), `--title FILTER` (repeatable substring), `--fresh` (clear session), `--email` (override).

For Reef API details, auth flow, and gotchas, see [docs/pantheon-reference.md](../docs/pantheon-reference.md).

## After PR create/update

1. `jirha update KEY --pr <PR_URL> --sp auto -c "summary of changes"` — link the PR, auto-assess SP, and comment.
2. If Jira description is empty or boilerplate, populate using the matching template from [docs/jira-reference.md](../docs/jira-reference.md).
