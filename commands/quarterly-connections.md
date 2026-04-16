---
description: Draft quarterly connections response from Jira activity data
---

**If plan mode is active, exit plan mode first.** This is an operational command, not a code planning task.

**Step 1: Gather quarterly activity data**

Run the quarterly report command:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/jirha quarterly $ARGUMENTS
```

If no issues are found, inform the user and stop.

**Step 2: Read reference documents**

Extract the job profile level N from the `**Job profile level:** twN` line in the output.

The reference files directory is `~/.config/jirha/quarterly-connections/`. This directory is outside the plugin so files survive plugin updates. Check if the required files exist:

- `tw<N>-job-profile.md` (current level)
- `tw<N+1>-job-profile.md` (next level, skip if N=5)
- `quarterly-questions.md` (template)

**If any job profile files are missing**, stop and show the user these instructions:

> The job profile reference files are not set up yet. To create them:
>
> 1. Go to [Job Interests Catalog](https://wd5.myworkday.com/redhat/d/task/1422%24502.htmld)
> 2. In the **Job Profile Name** field, search for **"technical writer"**
> 3. Check all the boxes: "Technical Writer 1" through "Technical Writer 5", then click **OK**
> 4. When the table with all job descriptions appears, **select the entire web page** (Ctrl+A) and **paste it here**
>
> I will then create the job profile files locally.

When the user pastes the Workday table content, parse it and create one file per TW level at `~/.config/jirha/quarterly-connections/tw<N>-job-profile.md`. Each file should follow this structure:

```markdown
# Technical Writer N — Job Profile

## Job Profile Summary

[Job Profile Summary and Job Description text]

## Key Competencies

### [Competency Name]
[Competency description]

[repeat for each competency]

## Skills

- [skill list]

## Enterprise Competencies

- [competency] ([level])
```

After creating the files, continue from Step 2 (read the newly created files).

**If the `quarterly-questions.md` file is missing**, create it with this content:

```markdown
# Quarterly Connections — Questions Template

## Accomplishments

**Question:** What accomplishments are you most proud of last quarter? Reflect not only on WHAT you've accomplished but also on HOW you've accomplished it.

## Priorities

**Question:** What are your top priorities for this quarter?
```

Now read the reference files:

- Current level: `~/.config/jirha/quarterly-connections/tw<N>-job-profile.md`
- Next level: `~/.config/jirha/quarterly-connections/tw<N+1>-job-profile.md` (skip if N=5)
- Template: `~/.config/jirha/quarterly-connections/quarterly-questions.md`
- Previous draft (if exists): `~/.config/jirha/quarterly-connections/connections-draft.md`

**Step 3: Analyze and map data to competencies**

Before drafting, analyze the quarterly activity data:

1. **Identify 3-5 key accomplishment themes** by examining the epic groupings, issue volumes, and story points. Look for:
   - High-volume epics (many issues or high SP) — these are major workstreams
   - Cross-cutting themes that span multiple epics (e.g., quality, tooling, customer issues)
   - Strategically significant work even if low volume (e.g., mentoring, process changes)
   - **Self-reported issues** (marked `[self-reported]` in the data) — these indicate proactive risk identification rather than reactive work. Highlight this distinction in the narrative, especially for bug fixes: self-reported bugs demonstrate "anticipate and expose risks early" which is a key next-level competency signal

2. **Map each theme to current-level (twN) competencies** using the job profile — this is the baseline proof that you're meeting expectations at your level.

3. **Identify next-level (twN+1) evidence** — for each theme, check whether the work also demonstrates competencies from the next level. This signals growth and readiness for advancement.

4. **Note which competencies have strong evidence** and which are underrepresented. Do not fabricate evidence — if a competency lacks support from the data, note it honestly.

**Step 4: Draft the connections response**

Produce a draft following this structure:

### Accomplishments section

For each of the 3-5 themes, write a numbered section:

```
### N. [Theme title — concise, action-oriented]

[1-2 paragraph narrative: WHAT was accomplished, with specific issue counts, SP totals, and key Jira links from the data. Be concrete.]

**How:** [1 paragraph: HOW it was accomplished — working style, strategic approach, methodology. Reference specific patterns visible in the data: sustained delivery cadence, systematic approach, cross-workstream coordination, etc.]

**Current level (twN):** [1 sentence mapping to the specific twN competency this demonstrates]
**Next level (twN+1):** [1 sentence showing where this work reaches into twN+1 expectations, if applicable — omit if no genuine evidence]
```

Guidelines:
- Lead with the highest-impact accomplishment
- Use concrete numbers from the activity data (issue counts, SP totals)
- Include Jira links for key issues — use the full URL format: https://redhat.atlassian.net/browse/KEY
- Include PR links when available in the data
- Reference competencies naturally in the narrative, do not force-fit
- Match the tone of the example: confident but evidence-driven, not boastful
- Each accomplishment should be 150-250 words

### Priorities section

Use the "Current Quarter — Open Issues" section from the quarterly report output to identify the major workstreams ahead. Draft 3 forward-looking priorities:

```
### N. [Priority title]

[1 short paragraph: what, why, and how you will approach it. Reference specific Jira issues from the current backlog.]
```

Guidelines:
- Ground each priority in actual assigned issues from the current quarter backlog, with Jira links
- Show continuity from accomplishments where applicable (continuing, expanding, or pivoting work)
- Include at least one priority that targets a next-level competency gap visible in the data
- Keep each priority to 50-100 words

**Step 5: Present to the user**

Present the full draft. Then add:

> This is a draft based on your Jira activity data mapped to TW{N} (current) and TW{N+1} (next level) competencies. You should:
> 1. **Add context** the data cannot capture: informal mentoring, design decisions, cross-team collaboration, strategic choices
> 2. **Adjust emphasis** based on what matters most to your manager
> 3. **Strengthen next-level evidence** — the competency mapping shows where you have strong evidence and where you might want to add context
> 4. **Refine priorities** based on upcoming roadmap items you know about
>
> Want me to revise any section?
