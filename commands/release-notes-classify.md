---
description: Classify a Jira issue for release notes — propose an RN Type based on project, issue type, and content
---

**If plan mode is active, exit plan mode first.** This is an operational command, not a code planning task.

Classify Jira issue `$ARGUMENTS` for release notes.

If `$ARGUMENTS` is empty, ask the user: "Which issue? (e.g., `RHDHBUGS-1234`)"

**Step 1:** Fetch issue context.
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha show <KEY>
```

**Step 2:** Propose an RN Type from this list:
Feature, Enhancement, Technology Preview, Developer Preview,
Deprecated Functionality, Removed Functionality, Known Issue, Bug Fix,
Release Note Not Required.

Classification heuristics:
- RHDHBUGS project + Bug issue type → Bug Fix
- Summary or description contains "deprecat" → Deprecated Functionality
- Summary or description contains "remove" or "drop" (in context of feature removal) → Removed Functionality
- Summary contains "tech preview" or "technology preview" → Technology Preview
- Summary contains "dev preview" or "developer preview" → Developer Preview
- RHDHPLAN project + Feature issue type → Feature
- RHDHPLAN project + Enhancement issue type → Enhancement
- If the issue is purely internal tooling, testing, or infrastructure with no user-facing impact → Release Note Not Required
- Default for RHDHPLAN → Enhancement

**Step 3:** Present the classification to the user:
```
**Proposed type:** <TYPE>
**Reasoning:** <why this type fits>
```

**Step 4:** Ask the user to confirm using AskUserQuestion: **Accept**, **Change type**, **Skip**

- **Accept**: Set the RN Type in Jira:
  ```bash
  ${CLAUDE_PLUGIN_ROOT}/scripts/jirha update <KEY> --rn-type "<TYPE>"
  ```
  For "Release Note Not Required":
  ```bash
  ${CLAUDE_PLUGIN_ROOT}/scripts/jirha update <KEY> --rn-type "Release Note Not Required" --rn-status "Done"
  ```

- **Change type**: Let the user specify the correct type. Then set it in Jira.

- **Skip**: Do not update Jira.
