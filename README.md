# jirha

Jira workflow helper for RHDH documentation. Automates the repetitive parts of the documentation lifecycle — tracking issues, managing sprints, estimating effort, auditing hygiene, and authoring release notes — so writers spend less time in Jira and more time writing docs.

Works as a standalone CLI (`jirha`) and as a plugin for Claude Code and OpenCode (slash commands).

## Install

### As a Claude Code plugin

```bash
claude plugins marketplace add git@github.com:themr0c/jirha.git
claude plugins install jirha@jirha
```

To update:
```bash
claude plugins marketplace update jirha
claude plugins update jirha@jirha
```

### As an OpenCode plugin

Add to your `opencode.json` (global `~/.config/opencode/opencode.json` or project-level):

```json
{
  "plugin": ["jirha@git+https://github.com/themr0c/jirha.git"]
}
```

Restart OpenCode. The plugin installs automatically.

To update, change the ref to a specific version tag:

```json
{
  "plugin": ["jirha@git+https://github.com/themr0c/jirha.git#v1.12.0"]
}
```

### Standalone

```bash
git clone git@github.com:themr0c/jirha.git
cd jirha
bash scripts/setup.sh
```

First use auto-bootstraps: Python venv, dependencies, and Jira credentials at `~/.config/jirha/.env`.

**Prerequisites:** Python 3.11+, Red Hat VPN, [GitHub CLI](https://cli.github.com/) (for PR features).

## CLI commands

Run `jirha <command> --help` for full options. See [docs/jirha-reference.md](docs/jirha-reference.md) for custom field IDs, JQL templates, and description templates.

### Issue management

Day-to-day issue operations: list, inspect, create, update, and transition.

| Command | What it does |
|---------|-------------|
| `jirha list` | Your assigned issues. Filter with `--open` or `--jql`. |
| `jirha show KEY` | Full issue details: description, comments, SP, PRs, release note fields. |
| `jirha jql "QUERY"` | Run any JQL query. |
| `jirha create PROJECT SUMMARY` | Create an issue. Use `--parent` for sub-tasks, `-i` for interactive. |
| `jirha update KEY` | Batch-update fields in one call: SP, PR link, labels, components, sprint, RN fields, comment. Accepts `--sp auto` to assess from linked PRs. |
| `jirha transition KEY [STATUS]` | Move an issue to a new status, or list available transitions. |
| `jirha meta PROJECT` | Discover valid issue types and fields for a project. |

### Sprint management

Sprint visibility, hygiene, and effort estimation.

| Command | What it does |
|---------|-------------|
| `jirha sprint-status` | Sprint board organized by priority swimlanes with PR status. `--team` for the whole team. |
| `jirha short-sprint-status` | Compact view: open issues only, closed collapsed to a count. |
| `jirha hygiene` | Full sprint audit: metadata gaps, unlinked PRs, SP mismatches, status cross-checks. Interactive by default, `--dry-run` for report only. |
| `jirha estimate` | Find issues missing story points or SP reasoning comments. |
| `jirha context KEY` | Hierarchy walk (Feature > Epic > Task) with PR metrics, docs URLs, and SP suggestion. `--json` for structured output. |
| `jirha close-subtasks` | Close orphaned sub-tasks whose parents are already closed. |

For SP auto-suggest methodology, see [docs/sp-heuristics.md](docs/sp-heuristics.md).

### Release notes

Publication-ready release notes checklist and AI-assisted authoring.

| Command | What it does |
|---------|-------------|
| `jirha release-notes VERSION` | Checklist organized by publication section (features, tech preview, bug fixes, etc.) with validation warnings. `--all` for all assignees. |

### Other

| Command | What it does |
|---------|-------------|
| `jirha quarterly` | Generate a quarterly activity report for performance review connections. |

## Slash commands

Each CLI command has a corresponding slash command. Slash commands call the CLI and add AI-assisted interpretation — for example, `/jirha:release-notes-batch` fans out parallel agents to draft, review, and classify all actionable release note items.

Run `jirha <command> --help` for detailed options — slash commands accept the same arguments.

### Issue management

| Slash command | Description |
|---------------|-------------|
| `/jirha:list` | List your Jira issues |
| `/jirha:show KEY` | Show issue details |
| `/jirha:create PROJECT SUMMARY` | Create a new issue |
| `/jirha:update KEY [options]` | Update issue fields |
| `/jirha:transition KEY [STATUS]` | Transition issue status |
| `/jirha:meta PROJECT` | Show project issue types and fields |
| `/jirha:estimate` | Find issues missing SP |

### Sprint management

| Slash command | Description |
|---------------|-------------|
| `/jirha:sprint-status` | Sprint board by priority swimlanes |
| `/jirha:sprint-status-short` | Compact sprint board (open issues only) |
| `/jirha:hygiene` | Full sprint hygiene audit |
| `/jirha:hygiene-check-sp` | Reassess SP from linked PRs |
| `/jirha:pr-dashboard` | PR action dashboard with checklists |

### Release notes

| Slash command | Description |
|---------------|-------------|
| `/jirha:release-notes VERSION` | Release notes checklist for a version |
| `/jirha:release-notes-batch VERSION` | Batch-author all actionable items via parallel agents (draft, review, classify) |

### Other

| Slash command | Description |
|---------------|-------------|
| `/jirha:quarterly-connections` | Draft quarterly connections response |

## Reference

- [docs/jirha-reference.md](docs/jirha-reference.md) — Custom field IDs, JQL templates, description templates, sprint status format
- [docs/sp-heuristics.md](docs/sp-heuristics.md) — SP auto-suggest methodology and tier thresholds
