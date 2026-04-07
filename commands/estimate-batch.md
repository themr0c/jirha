---
description: Batch estimate SP for all open issues missing SP or reasoning
---

**Step 1:** Fetch the list of issues needing SP attention (do not display the raw JSON — process it internally):

```bash
jirha estimate --json --dry-run
```

**Step 2:** If the list is empty, inform the user: "All open issues have SP and reasoning comments." and stop.

**Step 3:** Present a summary:
```
Found N issues needing SP attention:
- X missing SP
- Y missing reasoning comment
```

Then, for each issue in the list:

**Step 3a:** If the issue summary matches `[DOC] Peer Review` or `[DOC] Technical Review`, skip it silently.

**Step 3b:** Fetch hierarchy context (do not display the raw JSON):
```bash
jirha context <KEY> --json
```

**Step 3c:** Analyze the JSON context and estimate story points.

Use this SP reference table to reason across each dimension independently:

| SP | Complexity | Risk | Uncertainty | Effort |
|---|---|---|---|---|
| 1 | Simple task, minimal work | Low | None | Very little effort needed |
| 2 | Simple task, minimal work, short acceptance criteria | Low | None | Little effort needed |
| 3 | Simple task. Longer acceptance criteria, though clear | Low | Small — may need to consult peers | Will take some time |
| 5 | Some difficulty but feasible. Criteria mostly clear | Medium — may need mitigation plan | Small — may need to consult peers | Significant amount of sprint needed |
| 8 | Difficult and complicated. Lots of work | High — must have mitigation plan | Medium — may need a spike | High effort, whole sprint |
| 13 | Too big, should be broken down if spillover possible | High — should not be in sprint alone | Large — create a spike | Entire sprint as dedicated effort |

**Guidelines:**
- Never suggest 21 SP — recommend splitting the task instead.
- Cap auto-suggest at 13 SP.
- When `data_quality` is "strong" (5+ eng PRs), weight the `suggested_sp_range` heavily.
- When `data_quality` is "weak" or "none", rely more on description analysis.
- Weight PR body content and upstream doc links for scope assessment.
- Consider feature size (T-shirt) as a scope multiplier for doc-only features: S~2, L~5, XL~9.

**Presentation:**
- When mentioning a Jira issue, always include the URL: `https://redhat.atlassian.net/browse/KEY`
- When mentioning a GitHub PR, always include the full URL.

**Step 3d:** Present the assessment:

For issues **missing SP**:
```
RHIDP-12345 — Issue summary
https://redhat.atlassian.net/browse/RHIDP-12345

Complexity: <level> — <reasoning>
Risk: <level> — <reasoning>
Uncertainty: <level> — <reasoning>
Effort: <level> — <reasoning>

Suggested: <N> SP
```
Ask: `Accept <N> SP? [Y/n/adjust/skip-all]`

If accepted:
```bash
jirha update <KEY> --sp <N> -c "<compose a comment: one line per dimension with level and key reasoning>"
```
If adjust: ask for preferred value, use that instead.
If skip-all: stop processing remaining issues.

For issues **missing reasoning only** (SP already set):
```
RHIDP-12345 — Issue summary (currently <N> SP)
https://redhat.atlassian.net/browse/RHIDP-12345

Complexity: <level> — <reasoning>
Risk: <level> — <reasoning>
Uncertainty: <level> — <reasoning>
Effort: <level> — <reasoning>

Current SP (<N>) aligns with assessment.
```
Ask: `Add reasoning comment? [Y/n/adjust SP/skip-all]`

If yes:
```bash
jirha update <KEY> -c "<compose the reasoning comment>"
```
If adjust SP: ask for new value, then run:
```bash
jirha update <KEY> --sp <NEW> -c "<compose the reasoning comment>"
```

**Step 4:** After all issues are processed, print summary:
```
Done. X estimated, Y reasoning added, Z skipped.
```
