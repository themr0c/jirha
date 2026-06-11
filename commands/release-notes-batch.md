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

Read the **Action summary** table at the end of the checklist output to understand the work queue breakdown (Classify, Author, Review, Done counts per section). Then extract all `[ ]` actionable items from the checklist (skip `[x]` done and `[-]` not required items).

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
cat ${CLAUDE_PLUGIN_ROOT}/skills/release-notes/references/type-mapping.md
```

## Phase 3: Parallel drafting

Launch **one Agent subagent per actionable item**, all in parallel. Send all Agent tool calls in a single message. Use `subagent_type: "general-purpose"` for each agent.

Replace `<PLUGIN_ROOT>` in all prompts with the actual value of `${CLAUDE_PLUGIN_ROOT}`.

### Agent prompt for Tier 1 items (review)

```
Read and follow the ## Review section of the skill at <PLUGIN_ROOT>/skills/release-notes/SKILL.md for issue <KEY>.

Do NOT present to the user or push to Jira. Instead, return EXACTLY this format:
KEY: <KEY>
ACTION: review
PROPOSED_RN_TYPE: <the RN Type>
PROPOSED_RN_TEXT: |
  <revised or original text in Renoa AsciiDoc format>
ORIGINAL_RN_TEXT: |
  <original text as found>
CHANGES: <bulleted list of changes made, or "none">
CONFIDENCE: high|medium|low
NOTES: <any concerns or ambiguities, or "none">
```

### Agent prompt for Tier 2 items (author)

```
Read and follow the ## Draft section of the skill at <PLUGIN_ROOT>/skills/release-notes/SKILL.md for issue <KEY>.
The Release Note Type is: <RN_TYPE>

Do NOT present to the user or push to Jira. Instead, return EXACTLY this format:
KEY: <KEY>
ACTION: author
PROPOSED_RN_TYPE: <RN_TYPE>
PROPOSED_RN_TEXT: |
  <text in Renoa AsciiDoc format>
CONFIDENCE: high|medium|low
NOTES: <any concerns or ambiguities, or "none">
```

### Agent prompt for Tier 3 items (classify only)

Tier 3 agents **only classify** — they do NOT draft text. Once the user approves the classification, the item is promoted to Tier 2 for authoring.

```
Read and follow Steps 1-2 of the ## Classify section of the skill at <PLUGIN_ROOT>/skills/release-notes/SKILL.md for issue <KEY>.

Do NOT present to the user or update Jira. Instead, return EXACTLY this format:
KEY: <KEY>
ACTION: classify
PROPOSED_RN_TYPE: <classified type>
CONFIDENCE: high|medium|low
NOTES: <classification reasoning>
```

## Phase 4: Sequential review loop

As agents complete, collect their results. Present them to the user **in tier order** (Tier 1 first, then Tier 2, then Tier 3 — within each tier, in section order).

Do NOT present results in FIFO order. If the next item in order hasn't completed yet, present the next available item from the same or lower tier.

**Re-confirmation rule:** When the user provides free-text feedback instead of selecting an option (e.g., corrections, additional context, or changed requirements), incorporate the feedback, present your revised proposal, and ask for confirmation using AskUserQuestion before proceeding. Never push to Jira or move to the next item without explicit user approval. This applies to all tiers.

**Full URLs:** Always display Jira issue keys as full URLs (e.g., `https://redhat.atlassian.net/browse/RHDHPLAN-385`) in all headings and output, so they are clickable in terminal.

### Tier 1 (review) and Tier 2 (author) items

**1. Present the draft:**

For **author** items:
```
### https://redhat.atlassian.net/browse/<KEY> — <summary from checklist>
**Type:** <PROPOSED_RN_TYPE>  |  **Confidence:** <CONFIDENCE>

<PROPOSED_RN_TEXT>

<If NOTES is not "none": display notes>
```

For **review** items, also show what changed:
```
### https://redhat.atlassian.net/browse/<KEY> — <summary from checklist>
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

- **Edit**: Let the user provide modified text. Present the revised text back and ask for confirmation before pushing.

- **Skip**: Do not update Jira. Move to the next item.

- **Stop**: End the review loop immediately. Report the final summary.

### Tier 3 (classify) items

**1. Present the classification:**

```
### https://redhat.atlassian.net/browse/<KEY> — <summary from checklist>
**Proposed type:** <PROPOSED_RN_TYPE>  |  **Confidence:** <CONFIDENCE>
**Reasoning:** <NOTES>
```

For **Release Note Not Required** proposals:
```
### https://redhat.atlassian.net/browse/<KEY> — <summary from checklist>
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
