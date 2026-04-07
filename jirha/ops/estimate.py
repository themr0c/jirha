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
