"""Release notes checklist: publication-section view with validation."""

_SECTION_MAP = {
    "Feature": (1, "New features and enhancements"),
    "Enhancement": (1, "New features and enhancements"),
    "Technology Preview": (2, "Technology Preview features"),
    "Developer Preview": (3, "Developer Preview features"),
    "Deprecated Functionality": (4, "Deprecated features"),
    "Removed Functionality": (5, "Removed features"),
    "Known Issue": (6, "Known issues"),
    "Bug Fix": (7, "Fixed issues"),
}

_SECTION_TITLES = {
    1: "New features and enhancements",
    2: "Technology Preview features",
    3: "Developer Preview features",
    4: "Deprecated features",
    5: "Removed features",
    6: "Known issues",
    7: "Fixed issues",
}


def _classify_rn_bucket(rn_status, rn_type):
    """Classify an issue into one of: done, not_required, in_progress, proposed, empty."""
    if rn_type == "Release Notes Not Required":
        return "not_required"
    if rn_status == "Rejected":
        return "not_required"
    if rn_status == "Done" and rn_type:
        return "done"
    if rn_status == "In Progress":
        return "in_progress"
    if rn_status == "Proposed":
        return "proposed"
    return "empty"


def _map_to_section(rn_type):
    """Map an RN Type string to (section_number, section_title), or None if unclassified."""
    if not rn_type:
        return None
    return _SECTION_MAP.get(rn_type)


def _todo_text(bucket, classified):
    """Return the TODO string for a given bucket."""
    if bucket == "done" or bucket == "not_required":
        return ""
    if bucket == "proposed":
        return "TODO: Review draft proposed by SME"
    if bucket == "in_progress":
        return "TODO: Review RN text submitted by Docs team"
    if not classified:
        return "TODO: Set RN Type and RN Text"
    return "TODO: Author release notes"


def _check_violations(items, minor_version):
    """Find issues that are fixed in this release but typed as Known Issue."""
    violations = []
    for item in items:
        if item.get("rn_type") == "Known Issue" and item.get("from_query") == 1:
            violations.append(
                {
                    "key": item["key"],
                    "message": (
                        f"VIOLATION: Known Issue but fixed in {minor_version}"
                        " — will publish as KI instead of Bug Fix."
                        f" Duplicate: keep one as KI for prior release,"
                        f" use other as Bug Fix for {minor_version}"
                    ),
                }
            )
    return violations


def _check_deduplication(rhidp_issues):
    """Find RHIDP issues with RN text that should live on parent RHDHPLAN."""
    dupes = []
    for item in rhidp_issues:
        if item.get("rn_text"):
            dupes.append(
                {
                    "key": item["key"],
                    "parent_key": item["parent_key"],
                    "message": f"TODO: Move Release Note Text to parent feature {item['parent_key']}",
                }
            )
    return dupes


def _check_warnings(items):
    """Find issues with security level set."""
    warnings = []
    for item in items:
        if item.get("security"):
            warnings.append(
                {
                    "key": item["key"],
                    "message": (
                        "WARNING: Security level set — remove restriction or"
                        " duplicate Jira and add RN to duplicate"
                    ),
                }
            )
    return warnings
