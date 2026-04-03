---
description: Estimate story points for a Jira doc task using hierarchy context
---

**Step 1:** Fetch the hierarchy context for the issue:

```bash
jirha context $ARGUMENTS --json
```

**Step 2:** Analyze the JSON context and estimate story points.

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
- If `cache_age` is more than 7 days, note that context may be stale.

**Output format:** Present your assessment as:

```
Complexity: <level> — <reasoning>
Risk: <level> — <reasoning>
Uncertainty: <level> — <reasoning>
Effort: <level> — <reasoning>

Suggested: <N> SP
```

**Step 3:** Ask the user: `Accept <N> SP? [Y/n/adjust]`

**Step 4:** If confirmed, run:

```bash
jirha update <KEY> --sp <N> -c "SP estimated from hierarchy context"
```

If the user wants to adjust, ask for their preferred value and use that instead.
