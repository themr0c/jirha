"""Daily actionable checklist: sprint issues, estimate candidates, backlog."""

from jirha.config import SWIMLANES


def _determine_action(status, pr_checklist):
    """Return the recommended action string based on issue status and PR state."""
    if not pr_checklist:
        if status == "In Progress":
            return "Create PR or continue working"
        if status == "Review":
            return "Check review status"
        return "Start working on this issue"

    cl = pr_checklist
    if cl["state"] == "merged":
        return "Transition Jira to Closed"

    if cl["has_conflicts"]:
        return "Resolve merge conflict"
    if cl["failing_checks"]:
        names = ", ".join(cl["failing_checks"][:3])
        return f"Fix failing checks: {names}"
    if cl["review_decision"] == "CHANGES_REQUESTED":
        return "Address requested changes"
    if cl["unresolved_comments"]:
        n = cl["unresolved_comments"]
        return f"Address {n} unresolved review comment{'s' if n != 1 else ''}"

    if cl["pending_reviewers"]:
        names = ", ".join(cl["pending_reviewers"])
        return f"Waiting for review from {names}"
    if cl["review_decision"] == "APPROVED":
        return "Merge the PR"
    if cl["review_decision"] == "REVIEW_REQUIRED":
        return "Waiting for review"

    return "Check PR status"


def _build_action_menu(status, pr_checklist, sp):
    """Build contextual action menu. Returns list of (action_text, is_recommended).

    The recommended action is always first. Secondary actions follow.
    """
    recommended = _determine_action(status, pr_checklist)
    actions = [(recommended, True)]

    if pr_checklist:
        cl = pr_checklist
        if cl["state"] != "merged":
            if cl["unresolved_comments"] and "unresolved" not in recommended:
                n = cl["unresolved_comments"]
                actions.append(
                    (f"Address {n} unresolved review comment{'s' if n != 1 else ''}", False)
                )
            if cl["failing_checks"] and "failing checks" not in recommended:
                names = ", ".join(cl["failing_checks"][:3])
                actions.append((f"Fix failing checks: {names}", False))
            if cl["has_conflicts"] and "merge conflict" not in recommended.lower():
                actions.append(("Resolve merge conflict", False))
            if cl["review_decision"] == "APPROVED" and "Merge" not in recommended:
                actions.append(("Merge the PR", False))

    if not sp:
        actions.append(("Estimate SP", False))
    actions.append(("Update Jira", False))

    return actions


def _actionability_key(key, status, pr_checklists):
    """Sort key for secondary ordering: lower = more actionable."""
    cl = pr_checklists.get(key)
    if cl:
        has_author_action = (
            cl["unresolved_comments"]
            or cl["failing_checks"]
            or cl["has_conflicts"]
            or cl["review_decision"] == "CHANGES_REQUESTED"
        )
        if has_author_action:
            return 0
        return 1

    if status == "In Progress":
        return 2
    if status == "Review":
        return 3
    return 4


def _has_actionable_work(swimlane_issues):
    """Return True if any issue is New or In Progress (author still has active work)."""
    for name, _ in SWIMLANES:
        for issue in swimlane_issues[name]:
            status = str(issue.fields.status)
            if status not in ("Closed", "Review"):
                return True
    return False
