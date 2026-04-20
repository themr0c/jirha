---
description: PR action dashboard — show sprint board with actionable PR checklists, then deep-dive into specific issues
---

**If plan mode is active, exit plan mode first.** This is an operational command, not a code planning task.

## Step 1: Dashboard

Run the sprint-status command to get the full board with PR checklists:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha sprint-status $ARGUMENTS
```

Show the complete output. This includes per-issue PR checklists (unresolved comments, failing checks, pending reviewers, merge conflicts) and a "Pending Reviews" section for PRs awaiting your review.

## Step 2: Deep-dive

After showing the dashboard, ask which issue or PR the user wants to focus on.

For the selected issue, offer these actions:

1. **View PR comments** — run `gh pr view <number> --repo <repo> --comments` to show unresolved review comments
2. **View failing checks** — run `gh run view` to show failing check details
3. **Open in browser** — run `gh pr view <number> --repo <repo> --web`
4. **Update Jira** — run `${CLAUDE_PLUGIN_ROOT}/scripts/jirha update <KEY> -c "PR status: ..."` to add a status comment
5. **Transition Jira** — if the PR is merged, offer to transition the issue via `${CLAUDE_PLUGIN_ROOT}/scripts/jirha transition <KEY>`

## Step 3: Iterate

After addressing one issue, return to the dashboard summary and ask which issue to tackle next. Continue until the user is done.
