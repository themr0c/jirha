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

Step 2: Read the style guide, the type-specific reference for "<SECTION_TITLE>", and the AsciiDoc templates.
Run: cat <PLUGIN_ROOT>/commands/release-notes-style-guide.md
Run: cat <PLUGIN_ROOT>/commands/<TYPE_FILE>
Run: cat <PLUGIN_ROOT>/commands/release-notes-asciidoc-templates.md

Type file mapping:
- New features / Enhancement / Feature → release-notes-type-features.md
- Rebase → release-notes-type-rebases.md
- Technology Preview → release-notes-type-tech-preview.md
- Deprecated Functionality → release-notes-type-deprecated.md
- Removed Functionality → release-notes-type-removed.md
- Known Issue → release-notes-type-known-issues.md
- Bug Fix → release-notes-type-fixed-issues.md

Step 3: Review the existing RN text against the style guide and type-specific reference.
Check: heading format (sentence case, <120 chars, no gerund start, mentions component),
tenses (present default, past for "before this update"), no future tense or "should"/"might"/"now".
Apply the type-specific template and guidelines from the type file.

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

Step 2: Read the style guide, the type-specific reference for "<RN_TYPE>", and the AsciiDoc templates.
Run: cat <PLUGIN_ROOT>/commands/release-notes-style-guide.md
Run: cat <PLUGIN_ROOT>/commands/<TYPE_FILE>
Run: cat <PLUGIN_ROOT>/commands/release-notes-asciidoc-templates.md

Type file mapping:
- Enhancement / Feature → release-notes-type-features.md
- Rebase → release-notes-type-rebases.md
- Technology Preview → release-notes-type-tech-preview.md
- Deprecated Functionality → release-notes-type-deprecated.md
- Removed Functionality → release-notes-type-removed.md
- Known Issue → release-notes-type-known-issues.md
- Bug Fix → release-notes-type-fixed-issues.md

Step 3: Draft the release note text using the template and examples from the type file.
Use the Renoa AsciiDoc format (description list heading + open block body) from the AsciiDoc templates reference.

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

### Agent prompt for Tier 3 items (classify only)

Tier 3 agents **only classify** — they do NOT draft text. Once the user approves the classification, the item is promoted to Tier 2 for authoring.

For each Tier 3 item, use this prompt (substitute KEY):

```
You are classifying Jira issue <KEY> for release notes.
This item has no Release Note Type set yet.

Step 1: Fetch issue context.
Run: <PLUGIN_ROOT>/scripts/jirha context <KEY>

Step 2: Propose an RN Type from this list:
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

Step 3: Return EXACTLY this format (no extra text before or after):
KEY: <KEY>
ACTION: classify
PROPOSED_RN_TYPE: <classified type>
CONFIDENCE: high|medium|low
NOTES: <classification reasoning>
```

### Replacing PLUGIN_ROOT in prompts

In all agent prompts above, replace `<PLUGIN_ROOT>` with the actual value of `${CLAUDE_PLUGIN_ROOT}`.

---

## Phase 4: Sequential review loop

As agents complete, collect their results. Present them to the user **in the tier order from Phase 2** (Tier 1 first, then Tier 2, then Tier 3 — within each tier, in section order).

Do NOT present results in FIFO order. Wait until you have enough results to present the next item in the sorted order. If the next item in order hasn't completed yet, you may present the next available item from the same or lower tier.

For each completed result:

### Tier 1 (review) and Tier 2 (author) items

**1. Present the draft:**

For **author** items:
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

**2. Ask the user** what to do using AskUserQuestion:

Offer: **Accept**, **Edit**, **Skip**, **Stop**

- **Accept**: Run the update command:
  ```bash
  ${CLAUDE_PLUGIN_ROOT}/scripts/jirha update <KEY> --rn-text "<PROPOSED_RN_TEXT>" --rn-type "<PROPOSED_RN_TYPE>" --rn-status "Proposed"
  ```
  If the RN text contains quotes or special characters, escape them properly for the shell.

- **Edit**: Let the user provide modified text. Then run the update with the user's version.

- **Skip**: Do not update Jira. Move to the next item.

- **Stop**: End the review loop immediately. Report the final summary.

### Tier 3 (classify) items

**1. Present the classification:**

```
### <KEY> — <summary from checklist>
**Proposed type:** <PROPOSED_RN_TYPE>  |  **Confidence:** <CONFIDENCE>
**Reasoning:** <NOTES>
```

For **Release Note Not Required** proposals:
```
### <KEY> — <summary from checklist>
**Proposed:** Release Note Not Required
**Reasoning:** <NOTES>
```

**2. Ask the user** what to do using AskUserQuestion:

Offer: **Accept type**, **Change type**, **Skip**, **Stop**

- **Accept type**: Set the RN Type in Jira, then **promote the item to Tier 2** — immediately launch a new Agent subagent to author the text (using the Tier 2 agent prompt with the accepted type). Present the authored draft when the agent completes.
  ```bash
  ${CLAUDE_PLUGIN_ROOT}/scripts/jirha update <KEY> --rn-type "<PROPOSED_RN_TYPE>"
  ```

- **Change type**: Let the user specify the correct type. Then set it in Jira and promote to Tier 2 for authoring (same as Accept).

- **Skip**: Do not update Jira. Move to the next item.

- **Stop**: End the review loop immediately. Report the final summary.

For "Release Note Not Required" acceptances:
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha update <KEY> --rn-type "Release Note Not Required" --rn-status "Done"
```
(No promotion to Tier 2 — item is done.)

### After each item

**3. Move to next item** after each action.

**4. Summary** after all items are processed or user says Stop:
```
Done. X accepted, Y skipped, Z remaining (N promoted to authoring).
```

---

## Phase 2B: Single-item flow

If the user asks for help drafting release note text for a **specific item** (not "draft all"):

1. Fetch the issue context:
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha show <KEY>
```

2. Read the bundled style guide, the type-specific reference for the RN Type, and the AsciiDoc templates:
```bash
cat ${CLAUDE_PLUGIN_ROOT}/commands/release-notes-style-guide.md
cat ${CLAUDE_PLUGIN_ROOT}/commands/<TYPE_FILE>
cat ${CLAUDE_PLUGIN_ROOT}/commands/release-notes-asciidoc-templates.md
```

Type file mapping:
- Enhancement / Feature → `release-notes-type-features.md`
- Rebase → `release-notes-type-rebases.md`
- Technology Preview → `release-notes-type-tech-preview.md`
- Deprecated Functionality → `release-notes-type-deprecated.md`
- Removed Functionality → `release-notes-type-removed.md`
- Known Issue → `release-notes-type-known-issues.md`
- Bug Fix → `release-notes-type-fixed-issues.md`

3. Draft release note text following the style guide and type-specific reference. Use the **Renoa AsciiDoc format** (description list + open block) from the AsciiDoc templates reference.

4. Present the draft to the user for approval. Do not push without explicit approval.

5. Once approved, push the RN text and set the status:
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha update <KEY> --rn-text "<approved text>" --rn-type "<type>" --rn-status "Proposed"
```
