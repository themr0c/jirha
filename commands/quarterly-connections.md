---
description: Draft quarterly connections response from Jira activity data
---

**If plan mode is active, exit plan mode first.** This is an operational command, not a code planning task.

## Step 1: Gather quarterly activity data

Run the quarterly report command with a **45-minute timeout** (the command fetches PR data from GitHub for each issue and can take 15-30 minutes for large quarters):

```bash
jirha quarterly $ARGUMENTS
```

If no issues are found, inform the user and stop.

The command produces three outputs:
1. **Summary report** (stdout) — structured markdown with stats, issues by epic, open backlog, and unassigned team/component issues
2. **Context file** (stderr path) — e.g. `Context file written to: data/quarterly-context-Q2-2026.md (140 contexts)`. Per-issue details for resolved issues: description, parent chain, PR URLs, PR bodies, reporter, self-reported flag
3. **Forward context file** (stderr path) — e.g. `Forward context file written to: data/quarterly-forward-Q3-2026.md (25 contexts)`. Manifest of open issues assigned to you and unassigned team/component issues for forward-looking analysis. Full per-issue data is in cache files at `~/.cache/jirha/contexts/<KEY>.json`

Read the summary report and both context files. The context file is the primary fact source for backward-looking sections. The forward context file is the primary source for forward-looking sections (priorities, goals).

## Step 2: Read reference documents

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

**If the `quarterly-questions.md` file is missing**, ask the user to create it manually at `~/.config/jirha/quarterly-connections/quarterly-questions.md` with their Workday Connections questions. Each section should have a `## Section Title` heading followed by a `**Question:**` line with the full question text. Stop and wait for the user to confirm the file is ready before continuing.

Now read the reference files:

- Current level: `~/.config/jirha/quarterly-connections/tw<N>-job-profile.md`
- Next level: `~/.config/jirha/quarterly-connections/tw<N+1>-job-profile.md` (skip if N=5)
- Template: `~/.config/jirha/quarterly-connections/quarterly-questions.md`
- Previous draft (if exists): check `docs/quarterly-connections/` first (look for the most recent file), then fall back to `~/.config/jirha/quarterly-connections/connections-draft.md`

The `quarterly-questions.md` file defines the sections to address. Each `## ` heading is a section with a `**Question:**` line. Do not assume what sections exist — read them from the file.

## Step 3: Identify and confirm themes — one section at a time

### 3a. Extract sections from template

Read `quarterly-questions.md`. Extract the list of `## ` section headings and their question text. These sections define the structure — do not add, skip, or rename any.

### 3b. Create the themes file

Create `~/.config/jirha/quarterly-connections/themes-<QUARTER>.md` with a header:

```markdown
# Quarterly Connections Themes — <QUARTER>
```

### 3c. Process each section sequentially

For each section from 3a, **one at a time in order**:

1. **Analyze** the quarterly data to identify candidate themes for this question. Look for:
    - Major workstreams — epics with broad scope or strategic importance
   - Cross-cutting themes that span multiple epics (e.g., quality, tooling, customer issues)
   - Strategically significant work even if low volume (e.g., mentoring, process changes)
   - **Self-reported issues** (marked `**[self-reported]**` in the context file) — proactive risk identification
   - For forward-looking sections (priorities, goals): use the **forward context file** for assigned open work and unassigned team/component issues that could be picked up. Read full cache from `~/.cache/jirha/contexts/<KEY>.json` for untruncated descriptions

 2. **Verify facts** from the context file before presenting:
    - Reporter names (use actual reporter from context)
    - PR URLs and descriptions (only from context file)
    - Parent/epic relationships (actual parent chain)
    - For key issues lacking detail, run `jirha context <KEY>` to fetch full context

 3. **Present** proposed themes for **this section only**:
    - Theme title and scope description
    - Key Jira issues included
    - Proposed competency mapping (current + next level)

4. **Ask the user** to confirm: merge, split, drop, or add themes. If the question requires personal input the data cannot answer, **ask the user directly** for their input and wait for their response.

5. **Write confirmed themes** for this section to the themes file. Append:

   ```markdown
   ## Section: [Section Title]

   **Question:** [Full question text from quarterly-questions.md]

   - [ ] **Theme: [title]**
     Jiras: KEY-1, KEY-2, KEY-3, ...
     [Brief scope description]

   - [ ] **Theme: [title]**
     Jiras: KEY-4, KEY-5, ...
     [Brief scope description]

   - [ ] **User input:** [User's verbatim response, if provided]
   ```

   The `- [ ]` items are a todo list — Step 4 processes each and marks it `- [x]` when drafted.

6. **Proceed to the next section.** Do not continue until the current section is confirmed and written to disk.

**Do not proceed to Step 4 until all sections have been confirmed and written to the themes file.**

## Step 4: Draft the connections response

### Primary input

The themes file `~/.config/jirha/quarterly-connections/themes-<QUARTER>.md` is the sole source of structure for drafting. It contains: section headings, question text, confirmed themes with jira lists, and user input. Do not re-read `quarterly-questions.md` — the themes file already embeds the questions.

### STRICT FACTUAL ACCURACY RULES

These rules are non-negotiable:

1. **Never invent Jira issue keys** — only reference keys that appear in the themes file or cache files
2. **Never fabricate PR details** — only include PR URLs and descriptions from the cache files
3. **Never fabricate reporter names** — use the actual reporter from the cache files
4. **Never fabricate descriptions or acceptance criteria** — quote or paraphrase only what's in the cache files
5. **If data is insufficient**, mark with `<!-- UNVERIFIED: [what's missing] -->` and ask the user
6. **Self-reported vs assigned** — only mark issues as self-reported if the cache file confirms the reporter matches the current user
7. **No SP totals or issue counts in the draft** — the manager has Jira for metrics. The draft is a narrative, not a dashboard.

### Sequential drafting — one theme at a time

Read the themes file. For each unchecked `- [ ]` item, **sequentially**:

1. **Collect** the Jira keys listed in that theme
2. **Read full cache files** from `~/.cache/jirha/contexts/<KEY>.json` for each key. Extract from `data.task`: `key`, `summary`, `description`, `pr_urls`, `pr_bodies`, `reporter`, `issuetype`, `components`. Extract from `data.epic` / `data.feature`: parent chain context. This gives you the full, untruncated data for each issue.
3. **Draft** that theme's content using the full cache data and the question text from the themes file. Use this structure for each theme:

    ```
    ### [Theme title — concise, action-oriented]

    [1-2 paragraph narrative: WHAT was accomplished and HOW. Be concrete — reference key Jira issues and PRs, compare what the issue described vs what was delivered. Focus on the story, not metrics — the manager has Jira for SP and issue counts.]

    **Outcome:**
    - **Customer:** [concrete impact on end users / customers]
    - **CCS/Team:** [concrete impact on the team, org, or internal stakeholders]

    **Competencies demonstrated:**
    - **[Competency name from job profile]** ([current level]): [specific evidence from this theme]
    - **[Competency name from job profile]** ([next level]): [specific evidence, if applicable — omit if no genuine match]
    ```

    The **Outcome** and **Competencies** sections must be scannable — short lines, not buried in prose. Use the actual competency names from the job profile files read in Step 2.

4. **Append** the drafted section to the output file
5. **Mark** the theme as `- [x]` in the themes file
6. **Continue** to the next unchecked item

For `- [ ] **User input:**` items, incorporate the user's verbatim response from the themes file. If the input is insufficient, mark gaps with `<!-- TODO: Add your input -->`.

### Drafting guidelines

- Lead with the highest-impact themes per section
- Focus on narrative and impact, not metrics — no SP totals, no issue counts. The manager has Jira for that.
- Include Jira links: `https://redhat.atlassian.net/browse/KEY`
- Include PR links when available in the cache data
- Make **Outcome** (customer / CCS / team) and **Competencies demonstrated** scannable and prominent — these are the most important parts for the reader
- Map to competencies using the actual competency names from the job profile files read in Step 2 — do not force-fit
- Tone: confident, evidence-driven, not boastful
- Each theme should be 150-250 words
- Process one theme fully before starting the next — never hold multiple themes' cache data in context simultaneously

### Output

Write the draft to:
- `docs/quarterly-connections/<YEAR>-q<N>.md` if `docs/quarterly-connections/` exists (running from repo — create the directory if needed, it is gitignored)
- Otherwise: `~/.config/jirha/quarterly-connections/connections-draft-<QUARTER>.md`

## Step 5: Present and iterate

Present the full draft. Reference the files produced:
- **Themes file:** `~/.config/jirha/quarterly-connections/themes-<QUARTER>.md` — confirmed themes with jira lists and todo status
- **Draft file:** the output path from Step 4

Then:

1. **Flag any `<!-- UNVERIFIED -->` or `<!-- TODO -->` markers** and ask the user to provide the missing information
2. **Highlight which competencies have strong data support** and which rely on the user's additional context
3. **Ask targeted questions** about sections where the themes file shows gaps or where user input was thin

> This is a draft grounded in your Jira activity data, PR history, and job profile competencies. You should:
> 1. **Add context** the data cannot capture: informal mentoring, design decisions, cross-team collaboration
> 2. **Adjust emphasis** based on what matters most to your manager
> 3. **Strengthen next-level evidence** where competency mapping shows gaps
>
> Want me to revise any section?
