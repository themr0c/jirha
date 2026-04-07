"""Batch SP estimation: find issues missing SP or reasoning comments."""

import json

from jirha.config import CF_STORY_POINTS, SERVER
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
