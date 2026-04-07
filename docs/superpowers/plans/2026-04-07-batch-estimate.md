# Batch SP Estimation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `jirha estimate` CLI command that finds open issues missing SP or SP reasoning comments, with an interactive mode and JSON output for a companion `/jirha:estimate-batch` slash command.

**Architecture:** New `jirha/ops/estimate.py` module with query logic, comment reasoning detection, and context summary formatting. Reuses `assemble_context_json` from `context.py`. New slash command `commands/estimate-batch.md` calls the CLI in JSON mode then layers LLM reasoning.

**Tech Stack:** Python (jira library), argparse, existing jirha infrastructure

---

## File Structure

| File | Responsibility |
|---|---|
| `jirha/ops/estimate.py` | New — `cmd_estimate`, `_has_reasoning_comment`, `_format_context_summary`, JSON output |
| `jirha/cli.py` | Add `estimate` subcommand to argparse |
| `commands/estimate-batch.md` | New slash command template for LLM-powered batch estimation |
| `.claude/CLAUDE.md` | Add `estimate` to command table and slash command list |
| `docs/jira-reference.md` | Document the `estimate` command |
| `tests/unit/test_estimate.py` | New — unit tests for reasoning detection and output formatting |

---

### Task 1: Reasoning comment detection

**Files:**
- Create: `tests/unit/test_estimate.py`
- Create: `jirha/ops/estimate.py`

- [ ] **Step 1: Write failing tests for `_has_reasoning_comment`**

Create `tests/unit/test_estimate.py`:

```python
from jirha.ops.estimate import _has_reasoning_comment


def test_has_reasoning_all_four_dimensions():
    comments = [
        _mock_comment("Complexity: Low — simple task\nRisk: Low\nUncertainty: None\nEffort: Minimal")
    ]
    assert _has_reasoning_comment(comments) is True


def test_missing_one_dimension():
    comments = [
        _mock_comment("Complexity: Low — simple task\nRisk: Low\nUncertainty: None")
    ]
    assert _has_reasoning_comment(comments) is False


def test_no_comments():
    assert _has_reasoning_comment([]) is False


def test_reasoning_in_second_comment():
    comments = [
        _mock_comment("Updated SP: 3 → 5"),
        _mock_comment("Complexity: Medium\nRisk: Low\nUncertainty: Small\nEffort: Moderate"),
    ]
    assert _has_reasoning_comment(comments) is True


def test_sp_reassessed_without_dimensions():
    """hygiene-style 'SP reassessed from PRs' comments don't count as reasoning."""
    comments = [
        _mock_comment("SP reassessed from PRs: 2 PRs, 28 .adoc files, +108/-117 lines")
    ]
    assert _has_reasoning_comment(comments) is False


def test_dimensions_spread_across_comments():
    """All four dimensions must be in a single comment, not spread across multiple."""
    comments = [
        _mock_comment("Complexity: Low\nRisk: Low"),
        _mock_comment("Uncertainty: None\nEffort: Minimal"),
    ]
    assert _has_reasoning_comment(comments) is False


class _mock_comment:
    def __init__(self, body):
        self.body = body
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/.cache/jirha/venv/bin/pytest tests/unit/test_estimate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'jirha.ops.estimate'`

- [ ] **Step 3: Implement `_has_reasoning_comment`**

Create `jirha/ops/estimate.py`:

```python
"""Batch SP estimation: find issues missing SP or reasoning comments."""

_REASONING_KEYWORDS = ("Complexity", "Risk", "Uncertainty", "Effort")


def _has_reasoning_comment(comments):
    """Check if any comment contains all four SP reasoning dimensions.

    A comment counts as reasoning if its body contains all four strings:
    Complexity, Risk, Uncertainty, Effort (case-sensitive).
    All four must appear in a single comment.
    """
    for comment in comments:
        body = comment.body
        if all(kw in body for kw in _REASONING_KEYWORDS):
            return True
    return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `~/.cache/jirha/venv/bin/pytest tests/unit/test_estimate.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_estimate.py jirha/ops/estimate.py
git commit -m "feat: add reasoning comment detection for SP estimation"
```

---

### Task 2: Core estimate command — query and classify issues

**Files:**
- Modify: `jirha/ops/estimate.py`
- Modify: `tests/unit/test_estimate.py`

- [ ] **Step 1: Write failing tests for `_classify_issues`**

Add to `tests/unit/test_estimate.py`:

```python
from unittest.mock import MagicMock
from jirha.ops.estimate import _classify_issues


def _make_issue(key, summary, sp=None, comments=None):
    """Create a mock Jira issue."""
    issue = MagicMock()
    issue.key = key
    issue.fields.summary = summary
    issue.fields.status = MagicMock(__str__=lambda self: "New")
    issue.fields.assignee = MagicMock()
    issue.fields.assignee.displayName = "Test User"
    # SP field
    from jirha.config import CF_STORY_POINTS
    setattr(issue.fields, CF_STORY_POINTS, sp)
    # Comments
    if comments is None:
        comments = []
    comment_obj = MagicMock()
    comment_obj.comments = [_mock_comment(c) for c in comments]
    issue.fields.comment = comment_obj
    return issue


def test_classify_missing_sp():
    issues = [_make_issue("RHIDP-1", "Some task", sp=None)]
    result = _classify_issues(issues)
    assert len(result) == 1
    assert result[0]["missing"] == "sp"


def test_classify_missing_reasoning():
    issues = [_make_issue("RHIDP-1", "Some task", sp=3.0, comments=["just a note"])]
    result = _classify_issues(issues)
    assert len(result) == 1
    assert result[0]["missing"] == "reasoning"


def test_classify_has_both():
    reasoning = "Complexity: Low\nRisk: Low\nUncertainty: None\nEffort: Minimal"
    issues = [_make_issue("RHIDP-1", "Some task", sp=3.0, comments=[reasoning])]
    result = _classify_issues(issues)
    assert len(result) == 0


def test_classify_sp_zero_is_valid():
    """0 SP is a valid value, not 'missing'."""
    issues = [_make_issue("RHIDP-1", "Some task", sp=0.0, comments=["no reasoning"])]
    result = _classify_issues(issues)
    assert len(result) == 1
    assert result[0]["missing"] == "reasoning"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/.cache/jirha/venv/bin/pytest tests/unit/test_estimate.py::test_classify_missing_sp -v`
Expected: FAIL with `ImportError: cannot import name '_classify_issues'`

- [ ] **Step 3: Implement `_classify_issues`**

Add to `jirha/ops/estimate.py`:

```python
from jirha.config import CF_STORY_POINTS, SERVER


def _classify_issues(issues):
    """Classify issues as missing SP, missing reasoning, or OK.

    Returns list of dicts: {key, summary, status, current_sp, missing, issue}.
    """
    results = []
    for issue in issues:
        raw_sp = getattr(issue.fields, CF_STORY_POINTS, None)
        current_sp = int(raw_sp) if raw_sp is not None else None
        summary = issue.fields.summary or ""
        status = str(issue.fields.status)

        # Check what's missing
        comment_obj = getattr(issue.fields, "comment", None)
        comments = comment_obj.comments if comment_obj and comment_obj.comments else []

        if current_sp is None:
            missing = "sp"
        elif not _has_reasoning_comment(comments):
            missing = "reasoning"
        else:
            continue  # Has SP and reasoning — skip

        results.append({
            "key": issue.key,
            "summary": summary,
            "status": status,
            "current_sp": current_sp,
            "missing": missing,
            "issue": issue,
        })
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `~/.cache/jirha/venv/bin/pytest tests/unit/test_estimate.py -v`
Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add jirha/ops/estimate.py tests/unit/test_estimate.py
git commit -m "feat: add issue classification for batch SP estimation"
```

---

### Task 3: Context summary formatting and text output

**Files:**
- Modify: `jirha/ops/estimate.py`

- [ ] **Step 1: Implement `_format_context_summary` and `_print_results`**

Add to `jirha/ops/estimate.py`:

```python
import json

from jirha.ops.context import assemble_context_json


def _format_context_summary(ctx):
    """Format a one-line context summary from assemble_context_json output."""
    parts = []
    epic = ctx.get("epic")
    if epic:
        parts.append(f"  Epic: {epic['key']} — {epic['summary']}")

    feature = ctx.get("feature")
    if feature:
        size = feature.get("size", "")
        size_str = f" [{size}]" if size else ""
        parts.append(f"  Feature: {feature['key']}{size_str} — {feature['summary']}")

    eng_metrics = ctx.get("eng_metrics", [])
    sp_range = ctx.get("suggested_sp_range")
    quality = ctx.get("data_quality", "none")
    if eng_metrics:
        n = len(eng_metrics)
        if sp_range:
            parts.append(f"  Eng PRs: {n} (suggested {sp_range[0]}-{sp_range[1]} SP, {quality})")
        else:
            parts.append(f"  Eng PRs: {n} (no range)")
    else:
        parts.append("  No eng PRs — estimate manually")

    return "\n".join(parts)


def _print_results(classified, jira):
    """Print text-format results with context summaries."""
    for entry in classified:
        sp_label = f"{entry['current_sp']}SP" if entry["current_sp"] is not None else "no SP"
        if entry["missing"] == "reasoning":
            tag = f"{sp_label}, no reasoning"
        else:
            tag = sp_label
        print(f"{entry['key']}  [{tag}]  {entry['summary']}")

        ctx = assemble_context_json(jira, entry["key"])
        entry["_ctx"] = ctx  # cache for JSON output
        print(_format_context_summary(ctx))
        print(f"  {SERVER}/browse/{entry['key']}")
        print()

    n_sp = sum(1 for e in classified if e["missing"] == "sp")
    n_reason = sum(1 for e in classified if e["missing"] == "reasoning")
    print(f"Found {len(classified)} issues: {n_sp} missing SP, {n_reason} missing reasoning.")
```

- [ ] **Step 2: Commit**

```bash
git add jirha/ops/estimate.py
git commit -m "feat: add context summary formatting for estimate output"
```

---

### Task 4: JSON output and interactive mode

**Files:**
- Modify: `jirha/ops/estimate.py`

- [ ] **Step 1: Implement `_print_json` and `_interactive_loop`**

Add to `jirha/ops/estimate.py`:

```python
def _print_json(classified):
    """Print JSON output for slash command consumption."""
    output = []
    for entry in classified:
        ctx = entry.get("_ctx", {})
        epic = ctx.get("epic")
        feature = ctx.get("feature")
        item = {
            "key": entry["key"],
            "summary": entry["summary"],
            "status": entry["status"],
            "current_sp": entry["current_sp"],
            "missing": entry["missing"],
        }
        if epic:
            item["epic"] = {"key": epic["key"], "summary": epic["summary"]}
        if feature:
            item["feature"] = {
                "key": feature["key"],
                "summary": feature["summary"],
                "size": feature.get("size"),
            }
        item["suggested_sp_range"] = ctx.get("suggested_sp_range")
        item["data_quality"] = ctx.get("data_quality", "none")
        item["eng_pr_count"] = len(ctx.get("eng_metrics", []))
        output.append(item)
    print(json.dumps(output, indent=2))


def _interactive_loop(classified, jira):
    """Prompt user to set SP for each issue."""
    for entry in classified:
        sp_label = f"{entry['current_sp']}SP" if entry["current_sp"] is not None else "no SP"
        prompt = f"{entry['key']} [{sp_label}] — Set SP? [value/skip/quit]: "
        try:
            choice = input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if choice == "quit" or choice == "q":
            break
        if choice == "skip" or choice == "s" or not choice:
            continue
        try:
            sp_val = int(choice)
        except ValueError:
            print(f"  Invalid value: {choice}")
            continue
        from jirha.config import SP_VALUES
        if sp_val not in SP_VALUES:
            print(f"  Invalid SP value. Valid: {', '.join(str(s) for s in SP_VALUES)}")
            continue
        jira.issue(entry["key"]).update(fields={CF_STORY_POINTS: float(sp_val)})
        print(f"  → Set {entry['key']} to {sp_val} SP")
```

- [ ] **Step 2: Commit**

```bash
git add jirha/ops/estimate.py
git commit -m "feat: add JSON output and interactive mode for estimate"
```

---

### Task 5: Wire up `cmd_estimate` and CLI subcommand

**Files:**
- Modify: `jirha/ops/estimate.py`
- Modify: `jirha/cli.py`

- [ ] **Step 1: Implement `cmd_estimate`**

Add to `jirha/ops/estimate.py`:

```python
from jirha.api import get_jira, REVIEW_FILTER


def cmd_estimate(args):
    """Find open issues missing SP or SP reasoning comments."""
    jira = get_jira()

    jql = (
        f'assignee = currentUser()'
        f' AND status not in (Closed, Resolved, "In Progress", "In Review")'
        f' AND type not in (Epic, Feature)'
        f'{REVIEW_FILTER}'
    )
    issues = jira.search_issues(
        jql,
        maxResults=args.max,
        fields=f"summary,status,assignee,comment,{CF_STORY_POINTS}",
    )

    classified = _classify_issues(issues)
    if not classified:
        print("All open issues have SP and reasoning comments.")
        return

    if args.json:
        # Fetch context for each issue before JSON output
        for entry in classified:
            entry["_ctx"] = assemble_context_json(jira, entry["key"])
        _print_json(classified)
        return

    _print_results(classified, jira)

    if not args.dry_run:
        print()
        _interactive_loop(classified, jira)
```

- [ ] **Step 2: Add `estimate` subcommand to `cli.py`**

Add to `jirha/cli.py`, after the existing imports at the top:

```python
from jirha.ops.estimate import cmd_estimate
```

Add after the `close-subtasks` parser block (before `args = parser.parse_args()`):

```python
    p = sub.add_parser("estimate", help="Find issues missing SP or reasoning comments")
    p.add_argument("--max", type=int, default=50)
    p.add_argument("--dry-run", action="store_true", help="Report only, no interactive prompts")
    p.add_argument("--json", action="store_true", help="Output as JSON (for slash command)")
    p.set_defaults(func=cmd_estimate)
```

- [ ] **Step 3: Verify the command registers**

Run: `~/bin/jirha estimate --help`

Expected:
```
usage: jirha estimate [-h] [--max MAX] [--dry-run] [--json]

Find issues missing SP or reasoning comments

options:
  -h, --help  show this help message and exit
  --max MAX
  --dry-run   Report only, no interactive prompts
  --json      Output as JSON (for slash command)
```

- [ ] **Step 4: Reinstall and test with dry-run**

Run: `~/.cache/jirha/venv/bin/pip install -q -e . && ~/bin/jirha estimate --dry-run`

Expected: Lists open issues missing SP or reasoning, with context summaries. No prompts.

- [ ] **Step 5: Commit**

```bash
git add jirha/ops/estimate.py jirha/cli.py
git commit -m "feat: wire up jirha estimate CLI command

Queries open issues (not In Progress/In Review) missing SP or
reasoning comments. Supports --dry-run and --json modes."
```

---

### Task 6: Slash command `/jirha:estimate-batch`

**Files:**
- Create: `commands/estimate-batch.md`

- [ ] **Step 1: Create the slash command**

Create `commands/estimate-batch.md`:

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add commands/estimate-batch.md
git commit -m "feat: add /jirha:estimate-batch slash command

Calls jirha estimate --json for batch overview, then LLM reasoning
per issue with accept/adjust/skip-all flow."
```

---

### Task 7: Update docs

**Files:**
- Modify: `.claude/CLAUDE.md`
- Modify: `docs/jira-reference.md`

- [ ] **Step 1: Update `.claude/CLAUDE.md`**

Add `estimate` to the command table, after the `close-subtasks` row:

```
| `jirha estimate [--max N] [--dry-run] [--json]` | Find issues missing SP or reasoning comments |
```

Add `/jirha:estimate-batch` to the slash commands paragraph:

```
`/jirha:estimate-batch`
```

- [ ] **Step 2: Update `docs/jira-reference.md`**

Add a new section after the `close-subtasks` section. Read the file first to find the exact insertion point.

```markdown
### estimate

Find open issues assigned to the current user that are missing SP or missing an SP reasoning comment. Queries issues not in Closed, Resolved, In Progress, or In Review. Excludes Epics, Features, and review subtasks.

```
jirha estimate [--max N] [--dry-run] [--json]
```

| Flag | Default | Description |
|---|---|---|
| `--max` | 50 | Maximum results |
| `--dry-run` | false | Report only, no interactive prompts |
| `--json` | false | Output as JSON (for `/jirha:estimate-batch` slash command) |

**Two checks per issue:**

1. **Missing SP** — story_points field is None (0 SP is valid).
2. **Missing reasoning** — SP is set but no comment contains all four keywords: Complexity, Risk, Uncertainty, Effort (matching the format from `/jirha:estimate`).

**Interactive mode** (default): after listing issues, prompts per issue to set SP. Does not write reasoning comments — use `/jirha:estimate-batch` for LLM-generated reasoning.

**JSON mode** (`--json`): outputs a JSON array with issue details, context summary, and suggested SP range. Used by the `/jirha:estimate-batch` slash command.
```

- [ ] **Step 3: Commit**

```bash
git add .claude/CLAUDE.md docs/jira-reference.md
git commit -m "docs: document jirha estimate command and estimate-batch slash command"
```

---

### Task 8: End-to-end verification

**Files:** None modified — verification only.

- [ ] **Step 1: Run unit tests**

Run: `~/.cache/jirha/venv/bin/pytest tests/unit/test_estimate.py -v`
Expected: All tests PASS

- [ ] **Step 2: Test dry-run mode**

Run: `~/bin/jirha estimate --dry-run`
Expected: Lists issues with context summaries, no prompts.

- [ ] **Step 3: Test JSON output**

Run: `~/bin/jirha estimate --json --dry-run`
Expected: Valid JSON array with key, summary, status, current_sp, missing, epic, feature, suggested_sp_range, data_quality, eng_pr_count fields.

- [ ] **Step 4: Test that `--help` shows the new command**

Run: `~/bin/jirha --help`
Expected: `estimate` appears in the subcommands list.

- [ ] **Step 5: Test the slash command in Claude**

Run `/jirha:estimate-batch` in Claude Code.
Expected: Fetches JSON, presents each issue with LLM reasoning, accept/adjust/skip-all flow works.
