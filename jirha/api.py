"""Jira connection factory, PR metrics, and shared query helpers."""

import json
import os
import re
import subprocess
import sys
from datetime import datetime

from jirha.config import (
    CF_GIT_PR,
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
_ADOC_TIER_THRESHOLDS = [(5, 0), (30, 1), (60, 2), (120, 3), (300, 4), (550, 5), (1200, 6)]
# Floor for non-adoc-heavy PRs (tooling, scripts, config)
_TOTAL_TIER_THRESHOLDS = [(20, 0), (100, 1), (250, 2), (600, 3), (1500, 4), (5000, 5), (15000, 6)]

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
        url = f"{SERVER}/browse/{issue.key}"
        print(f"- {url}{sp_str}{assignee_str} [{tag}] — {issue.fields.summary}")


def _pr_metrics(files, commits):
    """Compute PR metrics and return (tier, reason) for SP assessment."""
    adoc_files = [f for f in files if f["path"].endswith(".adoc")]
    adoc_lines = sum(f["additions"] + f["deletions"] for f in adoc_files)
    new_adoc = sum(1 for f in adoc_files if f["deletions"] == 0 and f["additions"] > 5)
    mechanical_files = sum(1 for f in adoc_files if f["additions"] + f["deletions"] <= 4)
    is_mechanical = len(adoc_files) > 3 and mechanical_files / len(adoc_files) > 0.8

    adds = sum(f["additions"] for f in files)
    dels = sum(f["deletions"] for f in files)
    parts = [f"{len(adoc_files)} .adoc files", f"+{adds}/-{dels} lines"]
    if new_adoc:
        parts.append(f"{new_adoc} new topics")
    if is_mechanical:
        parts.append("mechanical")

    tier = 6
    for threshold, t in _ADOC_TIER_THRESHOLDS:
        if adoc_lines < threshold:
            tier = t
            break

    # Floor from total lines (catches tooling/script-heavy PRs)
    total_lines = adds + dels
    total_tier = 6
    for threshold, t in _TOTAL_TIER_THRESHOLDS:
        if total_lines < threshold:
            total_tier = t
            break
    tier = max(tier, total_tier)

    # Complexity bump: +1 tier if 2+ structural signals present (cap at 13 SP)
    if sum([new_adoc >= 2, len(adoc_files) >= 12, commits >= 12]) >= 2:
        tier = min(tier + 1, 5)
    # Mechanical discount only when adoc is the dominant change
    if is_mechanical and adoc_lines > total_lines * 0.5:
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


def _parse_pr_url(pr_url):
    """Parse a GitHub PR URL into (repo, number) or None."""
    m = re.match(r"https://github\.com/([^/]+/[^/]+)/pull/(\d+)", pr_url)
    return (m.group(1), m.group(2)) if m else None


def _is_doc_repo(pr_url):
    """Return True if the PR URL points to a documentation repo."""
    return "red-hat-developers-documentation-" in pr_url


def _pr_body(pr_url):
    """Fetch PR body/description text. Returns string or None."""
    parsed = _parse_pr_url(pr_url)
    if not parsed:
        return None
    repo, number = parsed
    try:
        result = subprocess.run(
            ["gh", "pr", "view", number, "--repo", repo, "--json", "body,title"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    return data.get("body") or None


def _pr_details(pr_url):
    """Fetch PR details: state, title, baseRefName, url. Returns dict or None."""
    parsed = _parse_pr_url(pr_url)
    if not parsed:
        return None
    repo, number = parsed
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
                "state,title,baseRefName,url,mergedAt",
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
    data["repo"] = repo
    data["number"] = number
    return data


def _find_cherry_picks(repo, pr_number):
    """Find cherry-pick PRs for a given PR number. Returns list of dicts."""
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                repo,
                "--state",
                "all",
                "--search",
                f"cherry-pick {pr_number}",
                "--json",
                "number,title,url,state,baseRefName",
                "--limit",
                "10",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return []
        prs = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return []
    # Filter out the original PR itself
    return [p for p in prs if str(p.get("number")) != str(pr_number)]


def _pr_status(pr_url):
    """Fetch PR status as a markdown link string. Returns formatted string or None."""
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
                "state,reviewDecision,statusCheckRollup,url",
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

    state = data.get("state", "UNKNOWN").lower()
    review = data.get("reviewDecision", "")
    checks = data.get("statusCheckRollup", [])
    url = data.get("url", pr_url)

    parts = [state]
    review_map = {
        "APPROVED": "approved",
        "CHANGES_REQUESTED": "changes requested",
        "REVIEW_REQUIRED": "review required",
    }
    if review in review_map:
        parts.append(review_map[review])

    if checks:
        conclusions = [c.get("conclusion", "") for c in checks]
        if all(c == "SUCCESS" for c in conclusions):
            parts.append("CI pass")
        elif any(c == "FAILURE" for c in conclusions):
            parts.append("CI fail")
        elif any(c == "" for c in conclusions):
            parts.append("CI running")

    return f"PR: {', '.join(parts)} — {url}"


def _extract_jira_keys(text):
    """Extract Jira issue keys (e.g., RHIDP-1234) from text."""
    if not text:
        return set()
    return set(re.findall(r"[A-Z][A-Z0-9]+-\d+", text))


def _fetch_user_prs(start_date, end_date=None):
    """Fetch PRs authored by current user, updated since start_date.

    Returns list of dicts with: number, title, url, state, baseRefName, headRefName, body.
    """
    query = f"updated:>={start_date.isoformat()}"
    if end_date:
        query = f"updated:{start_date.isoformat()}..{end_date.isoformat()}"
    try:
        result = subprocess.run(
            [
                "gh",
                "search",
                "prs",
                "--author=@me",
                "--limit=100",
                f"--updated={query.split('updated:')[1]}",
                "--json",
                "number,title,url,state,repository",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []
        prs = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return []

    # Fetch details (branch names, body) for each PR
    detailed = []
    for pr in prs:
        repo_name = pr.get("repository", {}).get("nameWithOwner", "")
        if not repo_name:
            continue
        try:
            detail_result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "view",
                    str(pr["number"]),
                    "--repo",
                    repo_name,
                    "--json",
                    "number,title,url,state,baseRefName,headRefName,body",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if detail_result.returncode == 0:
                data = json.loads(detail_result.stdout)
                data["repo"] = repo_name
                detailed.append(data)
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            continue
    return detailed


def _createmeta(jira, project_key):
    """Fetch createmeta for a project. Returns the project dict with issuetypes."""
    meta = jira.createmeta(projectKeys=project_key, expand="projects.issuetypes.fields")
    if not meta.get("projects"):
        return None
    return meta["projects"][0]


def parse_fields(issue_type_dict):
    """Extract field metadata from a createmeta issue type dict.

    Returns list of dicts with keys: key, name, required, schema_type, allowed_values.
    allowed_values is a list of strings or None for freeform fields.
    """
    result = []
    for key, f in issue_type_dict["fields"].items():
        allowed = None
        if "allowedValues" in f:
            allowed = [v.get("name") or v.get("value") or str(v) for v in f["allowedValues"]]
        result.append(
            {
                "key": key,
                "name": f.get("name", ""),
                "required": f.get("required", False),
                "schema_type": f.get("schema", {}).get("type", ""),
                "allowed_values": allowed,
            }
        )
    return result


def _fetch_pr_statuses(issues):
    """Return dict of issue key -> formatted PR status string for non-closed issues."""
    statuses = {}
    for issue in issues:
        if str(issue.fields.status) == "Closed":
            continue
        pr_url = getattr(issue.fields, CF_GIT_PR, None)
        if not pr_url:
            continue
        status = _pr_status(pr_url)
        if status:
            statuses[issue.key] = status
    return statuses
