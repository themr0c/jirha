"""Batch SP estimation: find issues missing SP or reasoning comments."""

from jirha.config import CF_STORY_POINTS, SERVER

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
