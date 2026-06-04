---
description: Release notes checklist for a version — shows what needs authoring, organized by publication section with validation
---

**If plan mode is active, exit plan mode first.** This is an operational command, not a code planning task.

Run the release notes checklist command. Display the output to the user:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha release-notes $ARGUMENTS
```

If `$ARGUMENTS` is empty, ask the user: "Which version? (e.g., `1.10`)"

After displaying the checklist, provide this recommendation:

"For manual authoring, use [Renoa](https://renoa.corp.redhat.com/) as the primary drafting tool. Follow the [Red Hat SSG release notes guidelines](https://redhat-documentation.github.io/supplementary-style-guide/#release-notes).

For AI-assisted authoring:
- **Single item:** `/jirha:release-notes-draft KEY`, `/jirha:release-notes-review KEY`, or `/jirha:release-notes-classify KEY`
- **Batch authoring:** say **draft all** to launch parallel agents for all actionable items"

**If the user says "draft all"** (or similar like "author all", "batch draft"), invoke `/jirha:release-notes-batch` with the same version argument.
