---
description: Batch-author release notes — fan out parallel agents to draft, review, classify, then present results for sequential approval
---

**If plan mode is active, exit plan mode first.** This is an operational command, not a code planning task.

## Phase 1: Display checklist

If the checklist has not been displayed yet, run it first:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha release-notes $ARGUMENTS
```

If `$ARGUMENTS` is empty, ask the user: "Which version? (e.g., `1.10`)"

## Phase 2: Build work queue

Parse the checklist output. Extract all `[ ]` actionable items (skip `[x]` done and `[-]` not required items).

For each `[ ]` item, extract:
- **KEY**: from the URL (e.g., `https://redhat.atlassian.net/browse/RHDHPLAN-385` → `RHDHPLAN-385`)
- **Section**: from the section header context above the item
- **Action type**: from the TODO text:
  - `TODO: Review draft proposed by SME` → **review** (Tier 1)
  - `TODO: Review RN text submitted by Docs team` → **review** (Tier 1)
  - `TODO: Author release notes` → **author** (Tier 2)
  - `TODO: Set RN Type and RN Text` → **classify** (Tier 3)

### Sorting into tiers

**Tier 1 — Review existing drafts** (text exists, needs validation)
Order by section number (1 → 7).

**Tier 2 — Author from scratch** (type is known, need to write text)
Order by section number (1 → 7).

**Tier 3 — Classify** (no type set, classify first)
Order as they appear in the checklist.

Report to user:
```
Work queue: N items
  Tier 1 (review existing drafts): X items
  Tier 2 (author from scratch): Y items
  Tier 3 (classify): Z items
Launching parallel agents...
```

### Determine RN Type from section context

Read the type mapping:
```bash
cat ${CLAUDE_PLUGIN_ROOT}/commands/release-notes-type-mapping.md
```

## Phase 3: Parallel drafting

Launch **one Agent subagent per actionable item**, all in parallel. Send all Agent tool calls in a single message. Use `subagent_type: "general-purpose"` for each agent.

Replace `<PLUGIN_ROOT>` in all prompts with the actual value of `${CLAUDE_PLUGIN_ROOT}`.

### Agent prompt for Tier 1 items (review)

```
You are reviewing an existing release note draft for Jira issue <KEY>.
This item is in the "<SECTION_TITLE>" section.

Step 1: Fetch issue context (includes RN fields).
Run: <PLUGIN_ROOT>/scripts/jirha context <KEY>

Step 2: Read the style guide, the type-specific reference, and the AsciiDoc templates.
Run: cat <PLUGIN_ROOT>/commands/release-notes-style-guide.md
Run: cat <PLUGIN_ROOT>/commands/release-notes-type-mapping.md
Run: cat <PLUGIN_ROOT>/commands/<TYPE_FILE>
Run: cat <PLUGIN_ROOT>/commands/release-notes-asciidoc-templates.md

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

```
You are drafting a release note for Jira issue <KEY>.
The Release Note Type is: <RN_TYPE>

Step 1: Fetch issue context.
Run: <PLUGIN_ROOT>/scripts/jirha context <KEY>

Step 2: Read the style guide, the type-specific reference, and the AsciiDoc templates.
Run: cat <PLUGIN_ROOT>/commands/release-notes-style-guide.md
Run: cat <PLUGIN_ROOT>/commands/release-notes-type-mapping.md
Run: cat <PLUGIN_ROOT>/commands/<TYPE_FILE>
Run: cat <PLUGIN_ROOT>/commands/release-notes-asciidoc-templates.md

Step 3: Draft the release note text using the template and examples from the type file.
Use the Renoa AsciiDoc format (description list heading + open block body).

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

## Phase 4: Sequential review loop

As agents complete, collect their results. Present them to the user **in tier order** (Tier 1 first, then Tier 2, then Tier 3 — within each tier, in section order).

Do NOT present results in FIFO order. If the next item in order hasn't completed yet, present the next available item from the same or lower tier.

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
  Escape quotes and special characters properly for the shell.

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

- **Accept type**: Set the RN Type in Jira, then **promote to Tier 2** — immediately launch a new Agent subagent to author the text (using the Tier 2 agent prompt with the accepted type). Present the authored draft when the agent completes.
  ```bash
  ${CLAUDE_PLUGIN_ROOT}/scripts/jirha update <KEY> --rn-type "<PROPOSED_RN_TYPE>"
  ```

- **Change type**: Let the user specify the correct type. Then set it and promote to Tier 2 (same as Accept).

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
