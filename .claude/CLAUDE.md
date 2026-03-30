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

## Slash commands

Each `jirha` subcommand is also available as a slash command in Claude:
`/jirha-list`, `/jirha-show KEY`, `/jirha-sprint-status`, `/jirha-hygiene`,
`/jirha-update KEY ...`, `/jirha-transition KEY`, `/jirha-create PROJECT SUMMARY`

## pantheon-cli (moved)

pantheon-cli and visual-diff have moved to their own repository:
**Repository:** https://github.com/themr0c/pantheon-cli
**Setup:** Clone the repo, then run `bash scripts/setup.sh`

## After PR create/update

1. `jirha update KEY --pr <PR_URL> --sp auto -c "summary of changes"` — link the PR, auto-assess SP, and comment.
2. If Jira description is empty or boilerplate, populate using the matching template from [docs/jira-reference.md](../docs/jira-reference.md).
