---
description: Review an existing release note draft against the Red Hat SSG style guide — check CCFR, tenses, headings, and AsciiDoc format
---

**If plan mode is active, exit plan mode first.** This is an operational command, not a code planning task.

Review the release note draft for Jira issue `$ARGUMENTS`.

If `$ARGUMENTS` is empty, ask the user: "Which issue? (e.g., `RHDHBUGS-1234`)"

**Step 1:** Fetch issue context.
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha show <KEY>
```
Extract the existing Release Note Type and Release Note Text from the output.

**Step 2:** Read the style guide, the type-specific reference, and the AsciiDoc templates.
```bash
cat ${CLAUDE_PLUGIN_ROOT}/commands/release-notes-style-guide.md
cat ${CLAUDE_PLUGIN_ROOT}/commands/release-notes-type-mapping.md
cat ${CLAUDE_PLUGIN_ROOT}/commands/<TYPE_FILE>
cat ${CLAUDE_PLUGIN_ROOT}/commands/release-notes-asciidoc-templates.md
```
Use the type mapping to select the correct `<TYPE_FILE>` for the issue's RN Type.

**Step 3:** Review the existing RN text against the style guide and type-specific reference.
Check:
- Heading format: sentence case, <120 chars, no gerund start, mentions component
- Tenses: present default, past for "before this update", no future tense, no "should"/"might"/"now"
- Apply the type-specific template and guidelines from the type file
- AsciiDoc format: description list heading (`Heading::`) + open block (`--`)

**Step 4:** Present findings to the user.
If the text needs changes, produce a revised version in the Renoa AsciiDoc format. If acceptable, say so.

**Step 5:** If the user approves the revised text, push it:
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha update <KEY> --rn-text "<approved text>" --rn-type "<type>" --rn-status "Proposed"
```
