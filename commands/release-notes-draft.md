---
description: Draft release note text for a Jira issue following the Red Hat SSG style guide and Renoa AsciiDoc format
---

**If plan mode is active, exit plan mode first.** This is an operational command, not a code planning task.

Draft a release note for Jira issue `$ARGUMENTS`.

If `$ARGUMENTS` is empty, ask the user: "Which issue? (e.g., `RHDHBUGS-1234`)"

**Step 1:** Fetch issue context and hierarchy.
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha context <KEY> --json --refresh
```
This provides the full hierarchy (Feature → child Epics → grandchild Tasks) with PR URLs, descriptions, and RN fields (Type, Text, Status) at each level. Use the child/grandchild details to understand what was actually implemented.

**Step 2:** Read the style guide, the type-specific reference for the RN Type, and the AsciiDoc templates.
```bash
cat ${CLAUDE_PLUGIN_ROOT}/commands/release-notes-style-guide.md
cat ${CLAUDE_PLUGIN_ROOT}/commands/release-notes-type-mapping.md
cat ${CLAUDE_PLUGIN_ROOT}/commands/<TYPE_FILE>
cat ${CLAUDE_PLUGIN_ROOT}/commands/release-notes-asciidoc-templates.md
```
Use the type mapping to select the correct `<TYPE_FILE>` for the issue's RN Type.

If the RN Type is not set, run `/jirha:release-notes-classify <KEY>` first.

**Step 3:** Draft the release note text using the template and examples from the type file.
Use the **Renoa AsciiDoc format** (description list heading + open block body) from the AsciiDoc templates reference.

**Step 4:** Self-review against:
- Heading: sentence case, <120 chars, no gerund, mentions component
- Tense: present default, no future, no "should"/"might"/"now"
- Type-specific rules from the style guide
- Links: use `{book-link}` attributes from the RHDH docs `artifacts/attributes.adoc`, never hardcoded URLs. Format: `For more information, see {book-link}#anchor[Section title].` — never append `in _{book-title}_` after the link. If no matching attribute exists, omit the link.
- Product attributes: use `{product}`, `{product-short}`, `{product-very-short}` — never `{ProductShortName}` or other non-standard attributes

**Step 5:** Present the draft to the user for approval. Do not push without explicit approval.

**Step 6:** Once approved, push the RN text and set the status:
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha update <KEY> --rn-text "<approved text>" --rn-type "<type>" --rn-status "Proposed"
```
