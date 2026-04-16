"""Batch SP estimation: find issues missing SP or reasoning comments."""

import sys

from jirha.api import REVIEW_FILTER, get_jira
from jirha.cache import read_cache
from jirha.config import CACHE_DIR, CF_STORY_POINTS, SERVER
from jirha.ops.context import assemble_context_json

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


def _classify_issues(issues):
    """Classify issues as missing SP, missing reasoning, or OK.

    Returns (ok, needs_attention) where each is a list of dicts:
    {key, summary, status, current_sp, missing}.
    missing is "sp", "reasoning", or None (for ok issues).
    """
    ok = []
    needs_attention = []
    for issue in issues:
        raw_sp = getattr(issue.fields, CF_STORY_POINTS, None)
        current_sp = int(raw_sp) if raw_sp is not None else None
        summary = issue.fields.summary or ""
        status = str(issue.fields.status)

        comment_obj = getattr(issue.fields, "comment", None)
        comments = comment_obj.comments if comment_obj and comment_obj.comments else []

        if current_sp is None:
            missing = "sp"
        elif not _has_reasoning_comment(comments):
            missing = "reasoning"
        else:
            missing = None

        entry = {
            "key": issue.key,
            "summary": summary,
            "status": status,
            "current_sp": current_sp,
            "missing": missing,
        }
        if missing:
            needs_attention.append(entry)
        else:
            ok.append(entry)
    return ok, needs_attention


def _print_checklist(ok, needs_attention):
    """Print Phase 1 checklist: all issues with status."""
    for entry in ok:
        sp = entry["current_sp"]
        print(f"- [x] {SERVER}/browse/{entry['key']} - {sp} SP - reasoning explained")
    for entry in needs_attention:
        sp_part = (
            f"{entry['current_sp']} SP" if entry["current_sp"] is not None else "TODO: estimate SP"
        )
        reason_part = (
            "TODO: add SP reasoning"
            if entry["missing"] in ("sp", "reasoning")
            else "reasoning explained"
        )
        print(f"- [ ] {SERVER}/browse/{entry['key']} - {sp_part} - {reason_part}")
    total = len(ok) + len(needs_attention)
    print(f"\nFound {total} issues: {len(ok)} OK, {len(needs_attention)} need attention.")


def _warm_cache(needs_attention, jira):
    """Phase 2: warm context cache for issues needing attention."""
    if not needs_attention:
        return
    print("\nTODO:")
    cache_path = CACHE_DIR / "contexts"
    for entry in needs_attention:
        key = entry["key"]
        url = f"{SERVER}/browse/{key}"
        file_path = cache_path / f"{key}.json"
        sys.stdout.write(f"- [ ] {url} - ")
        sys.stdout.flush()
        cached = read_cache(CACHE_DIR, "contexts", key)
        if cached:
            sys.stdout.write(f"Use {file_path} to estimate SP and explain reasoning\n")
        else:
            sys.stdout.write("caching context ... ")
            sys.stdout.flush()
            assemble_context_json(jira, key)
            sys.stdout.write(f"done - Use {file_path} to estimate SP and explain reasoning\n")


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

    ok, needs_attention = _classify_issues(issues)
    _print_checklist(ok, needs_attention)

    if not needs_attention:
        return

    _warm_cache(needs_attention, jira)
