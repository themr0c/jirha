"""Constants, field IDs, and environment loading for jirha."""

import os
from pathlib import Path

SERVER = "https://redhat.atlassian.net"

# Custom field IDs
CF_STORY_POINTS = "customfield_10028"
CF_RN_TEXT = "customfield_10783"
CF_RN_STATUS = "customfield_10807"
CF_RN_TYPE = "customfield_10785"
CF_GIT_PR = "customfield_10875"
CF_TEAM = "customfield_10001"
CF_SPRINT = "customfield_10020"
TEAM_RHDH_DOCS_ID = "ec74d716-af36-4b3c-950f-f79213d08f71-3319"

# Jira conventions
DEFAULT_COMPONENT = "Documentation"
DEFAULT_TEAM = "RHDH Documentation"
SP_VALUES = (0, 1, 3, 5, 8, 13)

# Status display ordering
STATUS_ORDER = {"New": 0, "In Progress": 1, "Review": 2, "Closed": 3}

# Swimlane definitions (ordered; first match wins)
SWIMLANES = [
    ("Blocker", lambda i: str(i.fields.priority) == "Blocker"),
    (
        "AEM migration",
        lambda i: (
            "CQreview_pre-migration" in (i.fields.labels or [])
            or any(c.name == "AEM Migration" for c in (i.fields.components or []))
        ),
    ),
    ("Test-day", lambda i: bool(set(i.fields.labels or []) & {"test-day", "rhdh-testday"})),
    ("Customer", lambda i: bool(set(i.fields.labels or []) & {"customer", "RHDH-Customer"})),
    ("Must-have", lambda i: "must-have" in (i.fields.labels or [])),
    ("Nice-to-have", lambda i: "nice-to-have" in (i.fields.labels or [])),
    ("Critical", lambda i: str(i.fields.priority) == "Critical"),
    (
        "Doc sprint (lower priority)",
        lambda i: (
            str(i.fields.issuetype) != "Sub-task"
            and "Review" not in i.fields.summary
            and bool(i.fields.labels or i.fields.components)
        ),
    ),
    ("Reviews", lambda i: str(i.fields.issuetype) == "Sub-task" and "Review" in i.fields.summary),
    ("Other", lambda i: True),
]


def _load_env_file(path: Path) -> dict:
    """Parse a .env file and return a dict of key=value pairs."""
    if not path.is_file():
        return {}
    result = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            result[k.strip()] = v.strip()
    return result


# Load .env from repo root and populate os.environ (setdefault: don't override existing)
_repo_root = Path(__file__).resolve().parent.parent
for _k, _v in _load_env_file(_repo_root / ".env").items():
    os.environ.setdefault(_k, _v)

EMAIL = os.environ.get("JIRA_EMAIL")
# Note: EMAIL may be None if JIRA_EMAIL is unset; get_jira() will exit with an error.
