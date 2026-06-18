---
name: release-notes
description: Draft, review, and classify release notes for RHDH following the Red Hat SSG style guide and Renoa AsciiDoc format
license: MIT
compatibility: opencode
---

## Draft

Draft a release note for Jira issue `$ARGUMENTS`.

If `$ARGUMENTS` is empty, ask the user: "Which issue? (e.g., `RHDHBUGS-1234`)"

**Step 1:** Fetch issue context and hierarchy.
```bash
jirha context <KEY> --json --refresh
```
This provides the full hierarchy (Feature → child Epics → grandchild Tasks) with PR URLs, descriptions, and RN fields (Type, Text, Status) at each level. Use the child/grandchild details to understand what was actually implemented.

**Step 2:** Read the style guide, the type-specific reference for the RN Type, and the AsciiDoc templates.
```bash
cat skills/release-notes/references/style-guide.md
cat skills/release-notes/references/type-mapping.md
cat skills/release-notes/references/<TYPE_FILE>
cat skills/release-notes/references/asciidoc-templates.md
```
Use the type mapping to select the correct `<TYPE_FILE>` for the issue's RN Type.

If the RN Type is not set, run the ## Classify section of this skill first.

**Step 3:** Draft the release note text using the template and examples from the type file.
Use the **Renoa AsciiDoc format** (description list heading + open block body) from the AsciiDoc templates reference.

**Step 4:** Self-review against:
- Heading: sentence case, <120 chars, no gerund, mentions component
- Tense: present default, no future, no "should"/"might"/"now"
- Type-specific rules from the style guide
- Links: use the docs URLs from the context output (Step 1) for `For more information` links. The context provides `{book-link}#anchor` entries resolved from doc PRs. Format: `For more information, see {book-link}#anchor[Section title].` — never append `in _{book-title}_` after the link. Never web-fetch published docs URLs — they may point to older releases. If no docs URL is in the context, omit the link.
- Product attributes: use `{product}`, `{product-short}`, `{product-very-short}` — never `{ProductShortName}` or other non-standard attributes

**Step 5:** Present the draft to the user for approval. Do not push without explicit approval.

**Step 6:** Once approved, push the RN text and set the status:
```bash
jirha update <KEY> --rn-text "<approved text>" --rn-type "<type>" --rn-status "Proposed"
```

---

## Review

Review the release note draft for Jira issue `$ARGUMENTS`.

If `$ARGUMENTS` is empty, ask the user: "Which issue? (e.g., `RHDHBUGS-1234`)"

**Step 1:** Fetch issue context and hierarchy.
```bash
jirha context <KEY> --json --refresh
```
Extract the existing Release Note Type and Release Note Text from the `rn_type`, `rn_text`, and `rn_status` fields. Use the full hierarchy (Feature → child Epics → grandchild Tasks with PRs) to verify the RN text accurately describes what was implemented.

**Step 2:** Read the style guide, the type-specific reference, and the AsciiDoc templates.
```bash
cat skills/release-notes/references/style-guide.md
cat skills/release-notes/references/type-mapping.md
cat skills/release-notes/references/<TYPE_FILE>
cat skills/release-notes/references/asciidoc-templates.md
```
Use the type mapping to select the correct `<TYPE_FILE>` for the issue's RN Type.

**Step 3:** Review the existing RN text against the style guide and type-specific reference.
Check:
- Heading format: sentence case, <120 chars, no gerund start, mentions component
- Tenses: present default, past for "before this update", no future tense, no "should"/"might"/"now"
- Apply the type-specific template and guidelines from the type file
- AsciiDoc format: description list heading (`Heading::`) + open block (`--`)
- Links: use the docs URLs from the context output (Step 1) for `For more information` links. The context provides `{book-link}#anchor` entries resolved from doc PRs. Format: `For more information, see {book-link}#anchor[Section title].` — never append `in _{book-title}_` after the link. Never web-fetch published docs URLs — they may point to older releases. If no docs URL is in the context, omit the link.
- Product attributes: must use `{product}`, `{product-short}`, `{product-very-short}` — never `{ProductShortName}` or other non-standard attributes

**Step 4:** Present findings to the user.
If the text needs changes, produce a revised version in the Renoa AsciiDoc format. If acceptable, say so.

**Step 5:** If the user approves the revised text, push it:
```bash
jirha update <KEY> --rn-text "<approved text>" --rn-type "<type>" --rn-status "Done"
```

---

## Classify

Classify Jira issue `$ARGUMENTS` for release notes.

If `$ARGUMENTS` is empty, ask the user: "Which issue? (e.g., `RHDHBUGS-1234`)"

**Step 1:** Fetch issue context.
```bash
jirha show <KEY>
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
  jirha update <KEY> --rn-type "<TYPE>"
  ```
  For "Release Note Not Required":
  ```bash
  jirha update <KEY> --rn-type "Release Note Not Required" --rn-status "Done"
  ```

- **Change type**: Let the user specify the correct type. Then set it in Jira.

- **Skip**: Do not update Jira.
