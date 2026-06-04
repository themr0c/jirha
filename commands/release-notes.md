---
description: Release notes checklist with interactive batch authoring — displays the checklist, then optionally fans out parallel agents to draft, review, and update Jira
---

**If plan mode is active, exit plan mode first.** This is an operational command, not a code planning task.

## Phase 1: Display checklist

Run the release notes checklist command. Display the output to the user:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha release-notes $ARGUMENTS
```

If `$ARGUMENTS` is empty, ask the user: "Which version? (e.g., `1.10`)"

After displaying the checklist, provide this recommendation:

"For manual authoring, use [Renoa](https://renoa.corp.redhat.com/) as the primary drafting tool. Follow the [Red Hat SSG release notes guidelines](https://redhat-documentation.github.io/supplementary-style-guide/#release-notes).

For AI-assisted batch authoring, say **draft all** to launch parallel drafting agents for all actionable items, or name a specific **KEY** for single-item drafting."

**If the user does NOT say "draft all"** (or similar like "author all", "batch draft"), go to **Phase 2B: Single-item flow** below.

**If the user says "draft all"**, continue to Phase 2.

---

## Phase 2: Build work queue

Parse the checklist output already displayed in Phase 1. Extract all `[ ]` actionable items (skip `[x]` done and `[-]` not required items).

For each `[ ]` item, extract:
- **KEY**: from the URL (e.g., `https://redhat.atlassian.net/browse/RHDHPLAN-385` → `RHDHPLAN-385`)
- **Section**: from the section header context above the item (e.g., `1. New features and enhancements` → section 1, "Feature/Enhancement"). Items under `── Unclassified` have no section.
- **Action type**: from the TODO text:
  - `TODO: Review draft proposed by SME` → **review** (Tier 1)
  - `TODO: Review RN text submitted by Docs team` → **review** (Tier 1)
  - `TODO: Author release notes` → **author** (Tier 2)
  - `TODO: Set RN Type and RN Text` → **classify_and_author** (Tier 3)

### Sorting into tiers

Build three ordered tiers:

**Tier 1 — Review existing drafts** (quickest wins: text exists, just needs validation)
Items with `TODO: Review draft proposed by SME` or `TODO: Review RN text submitted by Docs team`.
Order by section number (1 → 7).

**Tier 2 — Author from scratch** (type is known, need to write text)
Items with `TODO: Author release notes`.
Order by section number (1 → 7).

**Tier 3 — Classify and author** (no type set, need to classify first then write)
Items with `TODO: Set RN Type and RN Text` (from the Unclassified section).
Order as they appear in the checklist.

Report to user:
```
Work queue: N items
  Tier 1 (review existing drafts): X items
  Tier 2 (author from scratch): Y items
  Tier 3 (classify + author): Z items
Launching parallel agents...
```

Continue to Phase 3.

---

## Phase 3: Parallel drafting

Launch **one Agent subagent per actionable item**, all in parallel. Send all Agent tool calls in a single message so they run concurrently. Use `subagent_type: "general-purpose"` for each agent.

**Important:** All agents run independently. Do NOT wait for one agent before launching the next.

### Determine RN Type from section context

Map the section number from Phase 2 to the default RN Type for agent prompts:
- Section 1 → "Enhancement" (unless the item is clearly a new Feature — the agent will refine)
- Section 2 → "Technology Preview"
- Section 3 → "Developer Preview"
- Section 4 → "Deprecated Functionality"
- Section 5 → "Removed Functionality"
- Section 6 → "Known Issue"
- Section 7 → "Bug Fix"
- Unclassified → agent must classify

### Agent prompt for Tier 1 items (review)

For each Tier 1 item, use this prompt (substitute KEY and SECTION_TITLE):

```
You are reviewing an existing release note draft for Jira issue <KEY>.
This item is in the "<SECTION_TITLE>" section.

Step 1: Fetch issue context (includes RN fields: Release Note Type, Release Note Text, Release Note Status).
Run: <PLUGIN_ROOT>/scripts/jirha context <KEY>

Step 2: Read the style guide and AsciiDoc templates.
Run: cat <PLUGIN_ROOT>/commands/release-notes-style-guide.md
Run: cat <PLUGIN_ROOT>/commands/release-notes-asciidoc-templates.md

Step 3: Review the existing RN text against the style guide for this type.
Check: heading format (sentence case, <120 chars, no gerund start, mentions component),
tenses (present default, past for "before this update"), no future tense or "should"/"might"/"now".
For Bug Fix: verify CCFR pattern (Before this update / As a consequence / With this release / As a result).
For Known Issue: verify Cause-Consequence-Workaround-Result structure.
For Deprecated/Removed: verify feature + purpose + alternative.
For Technology Preview: heading ends "(Technology Preview)", body mentions it.

Step 4: If the text needs changes, produce a revised version. If acceptable, keep as-is.

Step 5: Return EXACTLY this format (no extra text before or after):
KEY: <KEY>
ACTION: review
PROPOSED_RN_TYPE: <the RN Type>
PROPOSED_RN_TEXT: |
  <heading>::
  +
  --
  <body text>
  --
ORIGINAL_RN_TEXT: |
  <original text as found>
CHANGES: <bulleted list of changes made, or "none">
CONFIDENCE: high|medium|low
NOTES: <any concerns or ambiguities, or "none">
```

### Agent prompt for Tier 2 items (author)

For each Tier 2 item, use this prompt (substitute KEY and RN_TYPE):

```
You are drafting a release note for Jira issue <KEY>.
The Release Note Type is: <RN_TYPE>

Step 1: Fetch issue context.
Run: <PLUGIN_ROOT>/scripts/jirha context <KEY>

Step 2: Read the style guide and AsciiDoc templates.
Run: cat <PLUGIN_ROOT>/commands/release-notes-style-guide.md
Run: cat <PLUGIN_ROOT>/commands/release-notes-asciidoc-templates.md

Step 3: Draft the release note text using the template for "<RN_TYPE>".
Use the Renoa AsciiDoc format (description list heading + open block body):
- Feature/Enhancement: "<Heading>::" + "<Feature>. <Reason>. As a result, <result>."
- Technology Preview: "<Feature> (Technology Preview)::" + text mentioning Technology Preview
- Deprecated Functionality: "<feature> is deprecated::" + purpose + alternative
- Removed Functionality: "<feature> is removed::" + purpose + alternative
- Known Issue: "<Heading>::" + "<Cause>. As a consequence, <consequence>." + workaround
- Bug Fix: "<Heading>::" + "Before this update, <cause>. As a consequence, <consequence>. With this release, <fix>. As a result, <result>."
Step 4: Self-review against:
- Heading: sentence case, <120 chars, no gerund, mentions component
- Tense: present default, no future, no "should"/"might"/"now"
- Type-specific rules from the style guide

Step 5: Return EXACTLY this format (no extra text before or after):
KEY: <KEY>
ACTION: author
PROPOSED_RN_TYPE: <RN_TYPE>
PROPOSED_RN_TEXT: |
  <heading>::
  +
  --
  <body text>
  --
CONFIDENCE: high|medium|low
NOTES: <any concerns or ambiguities, or "none">
```

### Agent prompt for Tier 3 items (classify + author)

For each Tier 3 item, use this prompt (substitute KEY):

```
You are drafting a release note for Jira issue <KEY>.
This item has no Release Note Type set yet — you must classify it first.

Step 1: Fetch issue context.
Run: <PLUGIN_ROOT>/scripts/jirha context <KEY>

Step 2: Classify — propose an RN Type from this list:
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

Step 3: If you classified as "Release Note Not Required", skip Steps 4-5 and go directly to Step 6.

Step 4: Read the style guide and AsciiDoc templates.
Run: cat <PLUGIN_ROOT>/commands/release-notes-style-guide.md
Run: cat <PLUGIN_ROOT>/commands/release-notes-asciidoc-templates.md

Step 5: Draft the release note text using the correct template for the classified type.
Use the Renoa AsciiDoc format (description list heading + open block body) from the templates reference.
Self-review against the style guide rules.

Step 6: Return EXACTLY this format (no extra text before or after):
KEY: <KEY>
ACTION: classify_and_author
PROPOSED_RN_TYPE: <classified type>
PROPOSED_RN_TEXT: |
  <heading>::
  +
  --
  <body text>
  --
CONFIDENCE: high|medium|low
NOTES: <classification reasoning + any concerns>
```

If you classified as "Release Note Not Required", use `N/A` for PROPOSED_RN_TEXT.

### Replacing PLUGIN_ROOT in prompts

In all agent prompts above, replace `<PLUGIN_ROOT>` with the actual value of `${CLAUDE_PLUGIN_ROOT}`.

---

## Phase 4: Sequential review loop

As agents complete, collect their results. Present them to the user **in the tier order from Phase 2** (Tier 1 first, then Tier 2, then Tier 3 — within each tier, in section order).

Do NOT present results in FIFO order. Wait until you have enough results to present the next item in the sorted order. If the next item in order hasn't completed yet, you may present the next available item from the same or lower tier.

For each completed result:

**1. Present the draft:**

For **author** and **classify_and_author** items:
```
### <KEY> — <summary from checklist>
**Type:** <PROPOSED_RN_TYPE>  |  **Confidence:** <CONFIDENCE>

<PROPOSED_RN_TEXT>

<If NOTES is not "none": display notes>
```

For **review** items, also show what changed:
```
### <KEY> — <summary from checklist>
**Type:** <PROPOSED_RN_TYPE>  |  **Confidence:** <CONFIDENCE>

<PROPOSED_RN_TEXT>

**Changes from original:** <CHANGES>
<If NOTES is not "none": display notes>
```

For **Release Note Not Required** items:
```
### <KEY> — <summary from checklist>
**Proposed:** Release Note Not Required
**Reason:** <NOTES>
```

**2. Ask the user** what to do using AskUserQuestion:

For regular items, offer: **Accept**, **Edit**, **Skip**, **Stop**

- **Accept**: Run the update command:
  ```bash
  ${CLAUDE_PLUGIN_ROOT}/scripts/jirha update <KEY> --rn-text "<PROPOSED_RN_TEXT>" --rn-type "<PROPOSED_RN_TYPE>" --rn-status "Proposed"
  ```
  If the RN text contains quotes or special characters, escape them properly for the shell.

- **Edit**: Let the user provide modified text. Then run the update with the user's version.

- **Skip**: Do not update Jira. Move to the next item.

- **Stop**: End the review loop immediately. Report the final summary.

For "Release Note Not Required" items, offer: **Accept** (sets RN Type to "Release Note Not Required"), **Skip**, **Stop**.
When accepting "Not Required":
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha update <KEY> --rn-type "Release Note Not Required" --rn-status "Done"
```

**3. Move to next item** after each action.

**4. Summary** after all items are processed or user says Stop:
```
Done. X accepted, Y skipped, Z remaining.
```

---

## Phase 2B: Single-item flow

If the user asks for help drafting release note text for a **specific item** (not "draft all"):

1. Fetch the issue context:
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha show <KEY>
```

2. Read the bundled style guide and AsciiDoc templates:
```bash
cat ${CLAUDE_PLUGIN_ROOT}/commands/release-notes-style-guide.md
cat ${CLAUDE_PLUGIN_ROOT}/commands/release-notes-asciidoc-templates.md
```

3. Draft release note text following the style guide. Use the **Renoa AsciiDoc format** (description list + open block) from the AsciiDoc templates reference. Match the template to the RN Type.

4. Present the draft to the user for approval. Do not push without explicit approval.

5. Once approved, push the RN text and set the status:
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha update <KEY> --rn-text "<approved text>" --rn-type "<type>" --rn-status "Proposed"
```
