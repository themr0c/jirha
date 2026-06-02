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
