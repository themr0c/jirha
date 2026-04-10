---
description: Create a new Jira issue (--type, --component, --parent)
---

**If plan mode is active, exit plan mode first.** This is an operational command, not a code planning task.

Before creating, discover valid issue types and fields for the target project:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha meta <PROJECT> --type <TYPE>
```

where `<PROJECT>` is the project key from the arguments and `<TYPE>` is the intended issue type (default: Task).

Review the output to confirm the type is valid and required fields are covered. Then run:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha create $ARGUMENTS
```

If the command fails, show the error.
