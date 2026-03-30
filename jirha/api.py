"""Jira connection factory, PR metrics, and shared query helpers."""

import json
import os
import re
import subprocess
import sys
from datetime import datetime

from jirha.config import (
    CF_SPRINT,
    CF_STORY_POINTS,
    EMAIL,
    SERVER,
    SP_VALUES,
    STATUS_ORDER,
    TEAM_RHDH_DOCS_ID,
)

# SP tier mapping
SP_TIERS = dict(zip(SP_VALUES, range(len(SP_VALUES))))
_TIER_TO_SP = dict(enumerate(SP_VALUES))
_ADOC_TIER_THRESHOLDS = [(30, 0), (150, 1), (400, 2), (800, 3)]
_IMAGE_EXTS = (".png", ".svg", ".jpg", ".gif")

_REVIEW_SUMMARIES = ("[DOC] Peer Review", "[DOC] Technical Review")
REVIEW_FILTER = "".join(f' AND summary !~ "{s}"' for s in _REVIEW_SUMMARIES)


def get_jira():
    """Return an authenticated JIRA client. Exits if credentials are missing."""
    from jira import JIRA

    if not EMAIL:
        sys.exit("Error: JIRA_EMAIL not set. Add it to .env or export it.")
    token = os.environ.get("JIRA_API_TOKEN")
    if not token:
        sys.exit("Error: JIRA_API_TOKEN not set")
    return JIRA(server=SERVER, basic_auth=(EMAIL, token))


def _parse_jira_date(iso_str):
    """Parse Jira ISO date string (may end with Z) to date."""
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).date()


def _issue_sp(issue):
    """Get story points for an issue, or 0."""
    return getattr(issue.fields, CF_STORY_POINTS, None) or 0


def _assignee_name(issue):
    """Return assignee display name or 'Unassigned'."""
    return issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"


def _assignee_filter(team=False):
    """Return JQL fragment for team-wide or current-user scope."""
    if team:
        return f'Team = "{TEAM_RHDH_DOCS_ID}"'
    return "assignee = currentUser()"


def _status_sort_key(s):
    return STATUS_ORDER.get(s, len(STATUS_ORDER))


def _warn_in_progress_no_sprint(jira, team=False):
    """Print warning for In Progress issues not in the current sprint."""
    scope = _assignee_filter(team)
    issues = jira.search_issues(
        f'{scope} AND status = "In Progress" AND sprint not in openSprints(){REVIEW_FILTER}',
        maxResults=50,
        fields=f"summary,status,priority,assignee,{CF_STORY_POINTS},{CF_SPRINT}",
    )
    if not issues:
        return
    print("\n## WARNING: In Progress but not in current sprint\n")
    for issue in issues:
        sp = _issue_sp(issue)
        sp_str = f" {int(sp)}SP" if sp else ""
        assignee_str = f" @{_assignee_name(issue)}" if team else ""
        sprints = getattr(issue.fields, CF_SPRINT, None) or []
        future = [s for s in sprints if getattr(s, "state", "") == "future"]
        closed = [s for s in sprints if getattr(s, "state", "") == "closed"]
        if future:
            tag = f"FUTURE ({future[0].name})"
        elif closed:
            tag = f"STALE (last: {closed[-1].name}, {len(closed)} prev sprints)"
        else:
            tag = "BACKLOG (no sprint)"
        print(f"- {issue.key}{sp_str}{assignee_str} [{tag}] — {issue.fields.summary}")
        print(f"  {SERVER}/browse/{issue.key}")


def _pr_metrics(files, commits):
    """Compute PR metrics and return (tier, reason) for SP assessment."""
    adoc_files = [f for f in files if f["path"].endswith(".adoc")]
    adoc_lines = sum(f["additions"] + f["deletions"] for f in adoc_files)
    new_adoc = sum(1 for f in adoc_files if f["deletions"] == 0 and f["additions"] > 5)
    assemblies = sum(
        1 for f in adoc_files if "/assemblies/" in f["path"] or f["path"].startswith("assemblies/")
    )
    images = sum(1 for f in files if f["path"].endswith(_IMAGE_EXTS))
    mechanical_files = sum(1 for f in adoc_files if f["additions"] + f["deletions"] <= 4)
    is_mechanical = len(adoc_files) > 3 and mechanical_files / len(adoc_files) > 0.8

    adds = sum(f["additions"] for f in files)
    dels = sum(f["deletions"] for f in files)
    parts = [f"{len(adoc_files)} .adoc files", f"+{adds}/-{dels} lines"]
    for val, label in [(new_adoc, "new topics"), (assemblies, "assemblies"), (images, "images")]:
        if val:
            parts.append(f"{val} {label}")
    if is_mechanical:
        parts.append("mechanical")

    tier = 4
    for threshold, t in _ADOC_TIER_THRESHOLDS:
        if adoc_lines < threshold:
            tier = t
            break

    if sum([new_adoc >= 1, assemblies >= 2, images >= 3, commits >= 6]) >= 2:
        tier = min(tier + 1, 4)
    if is_mechanical:
        tier = max(tier - 1, 0)

    return tier, ", ".join(parts)


def _assess_pr_sp(pr_url):
    """Assess suggested SP from a GitHub PR URL. Returns (sp, reason, pr_number) or None."""
    m = re.match(r"https://github\.com/([^/]+/[^/]+)/pull/(\d+)", pr_url)
    if not m:
        return None
    repo, number = m.group(1), m.group(2)
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "view",
                number,
                "--repo",
                repo,
                "--json",
                "additions,deletions,changedFiles,commits,files",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return None

    tier, reason = _pr_metrics(data.get("files", []), len(data.get("commits", [])))
    return _TIER_TO_SP[tier], reason, number
