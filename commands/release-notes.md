---
description: Release notes checklist for a version — shows what needs authoring, organized by publication section with validation
---

**If plan mode is active, exit plan mode first.** This is an operational command, not a code planning task.

**Step 1:** Run the release notes checklist command. Display the output to the user:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha release-notes $ARGUMENTS
```

If `$ARGUMENTS` is empty, ask the user: "Which version? (e.g., `1.10`)"

**Step 2:** After displaying the checklist, provide this recommendation:

"For authoring release notes, use [Renoa](https://renoa.corp.redhat.com/) as the primary drafting tool. Follow the [Red Hat SSG release notes guidelines](https://redhat-documentation.github.io/supplementary-style-guide/#release-notes)."

**Step 3:** If the user explicitly asks for help drafting release note text for a specific item:

1. Fetch the issue context:
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha show <KEY>
```

2. Read the bundled style guide reference for the appropriate release note type:
```bash
cat ${CLAUDE_PLUGIN_ROOT}/commands/release-notes-style-guide.md
```

3. Draft release note text following the style guide. Determine the correct template based on the RN Type:
   - **Feature/Enhancement:** `<Heading>::` + `<Feature>. <Reason>. As a result, <result>.`
   - **Technology Preview:** `<Feature> (Technology Preview)::` + text, mention TP again in body
   - **Deprecated:** `<feature> is deprecated::` + purpose, alternative
   - **Removed:** `<feature> is removed::` + purpose, alternative
   - **Known Issue:** `<Heading>::` + `<Cause>. As a consequence, <consequence>.` + workaround
   - **Bug Fix:** `<Heading>::` + `Before this update, <cause>. As a consequence, <consequence>. With this release, <fix>. As a result, <result>.`

4. Present the draft to the user for approval. Do not push without explicit approval.

5. Once approved, push the RN text and set the status:
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha update <KEY> --rn-text "<approved text>" --rn-type "<type>" --rn-status "Proposed"
```
