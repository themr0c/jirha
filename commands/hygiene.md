---
description: Full sprint hygiene — metadata, PR linking, SP reassessment, and status cross-check
---

**If plan mode is active, exit plan mode first.** This is an operational command, not a code planning task.

**Step 1:** Run the audit in dry-run mode and capture its output:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha hygiene --dry-run $ARGUMENTS
```

**Step 2:** Present findings to the user, grouped by section. For each actionable finding, ask the user what to do. When mentioning a Jira issue, always include the URL (`https://redhat.atlassian.net/browse/KEY`). When mentioning a GitHub PR, always include the full URL.

**Step 3:** For each accepted action, run the corresponding `jirha` command:

- **Missing description (from PR)** → `${CLAUDE_PLUGIN_ROOT}/scripts/jirha update KEY --desc "TEXT_FROM_PR_BODY"`
- **SP mismatch** → `${CLAUDE_PLUGIN_ROOT}/scripts/jirha update KEY --sp N -c "SP reassessed: REASON"`
- **Open Jira, all PRs merged/closed** → `${CLAUDE_PLUGIN_ROOT}/scripts/jirha transition KEY Closed` then `${CLAUDE_PLUGIN_ROOT}/scripts/jirha update KEY -c "All PRs merged, closing."`
- **Closed Jira, open PR** → `${CLAUDE_PLUGIN_ROOT}/scripts/jirha transition KEY "In Progress"` then `${CLAUDE_PLUGIN_ROOT}/scripts/jirha update KEY -c "Reopened: open PR found — URL"`
- **Open review subtasks on closed Jiras** → `${CLAUDE_PLUGIN_ROOT}/scripts/jirha transition KEY Closed`

Do NOT re-run `${CLAUDE_PLUGIN_ROOT}/scripts/jirha hygiene` to apply changes.
