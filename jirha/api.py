"""Jira connection factory, PR metrics, and shared query helpers."""

import json
import os
import re
import subprocess
import sys
from datetime import datetime

from jirha.cache import read_sprint_cache, write_sprint_cache
from jirha.config import (
    CACHE_DIR,
    CF_GIT_PR,
    CF_SPRINT,
    CF_STORY_POINTS,
    DEFAULT_TEAM,
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

_REVIEW_SUMMARIES = ("Peer Review", "Technical Review")
REVIEW_FILTER = "".join(f' AND NOT summary ~ "{s}"' for s in _REVIEW_SUMMARIES)


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


def _get_active_sprint(jira):
    """Return active sprint info dict or None.

    Finds one issue in an open sprint and extracts sprint metadata from it.
    """
    issues = jira.search_issues(
        "assignee = currentUser() AND sprint in openSprints()", maxResults=1, fields=CF_SPRINT
    )
    if not issues:
        return None
    sprint_data = getattr(issues[0].fields, CF_SPRINT, None) or []
    for s in sprint_data:
        if getattr(s, "state", "") == "active":
            start = _parse_jira_date(s.startDate)
            end = _parse_jira_date(s.endDate)
            return {
                "id": s.id,
                "name": s.name,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "board_id": getattr(s, "boardId", None),
            }
    return None


def _get_next_sprint(jira, board_id):
    """Return the earliest future sprint on the board, or None."""
    if not board_id:
        return None
    try:
        future_sprints = jira.sprints(board_id, state="future")
        if not future_sprints:
            return None
        s = future_sprints[0]
        start = _parse_jira_date(s.startDate) if getattr(s, "startDate", None) else None
        end = _parse_jira_date(s.endDate) if getattr(s, "endDate", None) else None
        return {
            "id": s.id,
            "name": s.name,
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
            "board_id": board_id,
        }
    except Exception:
        return None


def get_sprint_info(jira, refresh=False):
    """Return sprint metadata dict with current_sprint, next_sprint, team_name.

    Uses disk cache when valid (sprint hasn't ended). Pass refresh=True to force re-fetch.
    """
    if not refresh:
        cached = read_sprint_cache(CACHE_DIR)
        if cached:
            return cached

    current = _get_active_sprint(jira)
    next_sprint = _get_next_sprint(jira, current["board_id"]) if current else None

    data = {
        "current_sprint": current,
        "next_sprint": next_sprint,
        "team_name": DEFAULT_TEAM,
    }
    if current:
        write_sprint_cache(CACHE_DIR, data)
    return data


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
    """Compute PR metrics and return (tier, reason, pr_type).

    pr_type is 'doc', 'tooling', or 'mixed' based on adoc line share.
    """
    adoc_files = [f for f in files if f["path"].endswith(".adoc")]
    adoc_lines = sum(f["additions"] + f["deletions"] for f in adoc_files)
    new_adoc = sum(1 for f in adoc_files if f["deletions"] == 0 and f["additions"] > 5)
    mechanical_files = sum(1 for f in adoc_files if f["additions"] + f["deletions"] <= 4)
    is_mechanical = len(adoc_files) > 3 and mechanical_files / len(adoc_files) > 0.8

    adds = sum(f["additions"] for f in files)
    dels = sum(f["deletions"] for f in files)
    total_lines = adds + dels

    # Classify task type
    if not adoc_files:
        pr_type = "tooling"
    elif total_lines > 0 and adoc_lines > total_lines * 0.5:
        pr_type = "doc"
    else:
        pr_type = "mixed"

    parts = [f"{len(adoc_files)} .adoc files", f"+{adds}/-{dels} lines"]
    if new_adoc:
        parts.append(f"{new_adoc} new topics")
    if is_mechanical:
        parts.append("mechanical")
    parts.append(pr_type)

    # Primary tier from adoc lines
    tier = 6
    for threshold, t in _ADOC_TIER_THRESHOLDS:
        if adoc_lines < threshold:
            tier = t
            break

    # Total-lines tier
    total_tier = 6
    for threshold, t in _TOTAL_TIER_THRESHOLDS:
        if total_lines < threshold:
            total_tier = t
            break

    if pr_type == "tooling":
        # Tooling: total-lines is primary, skip complexity bump
        tier = total_tier
    else:
        # Doc/mixed: adoc primary, total-lines as floor
        tier = max(tier, total_tier)
        # Complexity bump: +1 tier if 2+ structural signals present (cap at 13 SP)
        if sum([new_adoc >= 2, len(adoc_files) >= 12, commits >= 12]) >= 2:
            tier = min(tier + 1, 5)

    # Mechanical discount only when adoc is the dominant change
    if is_mechanical and adoc_lines > total_lines * 0.5:
        tier = max(tier - 1, 0)

    return tier, ", ".join(parts), pr_type


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

    tier, reason, _ = _pr_metrics(data.get("files", []), len(data.get("commits", [])))
    return _TIER_TO_SP[tier], reason, number


def _parse_pr_url(pr_url):
    """Parse a GitHub PR URL into (repo, number) or None."""
    m = re.match(r"https://github\.com/([^/]+/[^/]+)/pull/(\d+)", pr_url)
    return (m.group(1), m.group(2)) if m else None


def _is_doc_repo(pr_url):
    """Return True if the PR URL points to a documentation repo."""
    return "red-hat-developers-documentation-" in pr_url


def _assess_multi_pr_sp(pr_field):
    """Assess SP from all PRs linked to a Jira.

    Splits pr_field by newlines, fetches file-level data for each valid
    GitHub PR URL, deduplicates cherry-picks, aggregates metrics, and
    returns (sp, reason, pr_numbers) or None.
    """
    if not pr_field:
        return None
    urls = [u.strip() for u in pr_field.strip().splitlines() if u.strip()]
    pr_data = []  # list of dicts

    for url in urls:
        parsed = _parse_pr_url(url)
        if not parsed:
            continue
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
                    "additions,deletions,changedFiles,commits,files,title",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode != 0:
                continue
            data = json.loads(result.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            continue
        files = data.get("files", [])
        commits = len(data.get("commits", []))
        title = data.get("title", "")
        total_lines = sum(f["additions"] + f["deletions"] for f in files)
        pr_data.append(
            {
                "number": number,
                "repo": repo,
                "files": files,
                "commits": commits,
                "title": title,
                "total_lines": total_lines,
            }
        )

    if not pr_data:
        return None

    # Detect cherry-picks
    cherry_picks = set()
    for i, pr in enumerate(pr_data):
        if pr["title"].startswith("[release-"):
            cherry_picks.add(i)
            continue
        for j, other in enumerate(pr_data):
            if j <= i or j in cherry_picks:
                continue
            if pr["total_lines"] == other["total_lines"] and pr["total_lines"] > 0:
                # Check file overlap > 80%
                paths_i = {f["path"] for f in pr["files"]}
                paths_j = {f["path"] for f in other["files"]}
                if paths_i and paths_j:
                    overlap = len(paths_i & paths_j) / max(len(paths_i), len(paths_j))
                    if overlap > 0.8:
                        cherry_picks.add(j)

    # Aggregate files from non-cherry-pick PRs
    aggregated = {}  # path → {path, additions, deletions}
    max_commits = 0
    for i, pr in enumerate(pr_data):
        if i in cherry_picks:
            continue
        max_commits = max(max_commits, pr["commits"])
        for f in pr["files"]:
            path = f["path"]
            if path in aggregated:
                aggregated[path]["additions"] += f["additions"]
                aggregated[path]["deletions"] += f["deletions"]
            else:
                aggregated[path] = {
                    "path": path,
                    "additions": f["additions"],
                    "deletions": f["deletions"],
                }

    files_list = list(aggregated.values())
    tier, reason, pr_type = _pr_metrics(files_list, max_commits)

    # Build reason string
    n_prs = len(pr_data)
    n_cherry = len(cherry_picks)
    pr_count = f"{n_prs} PR{'s' if n_prs != 1 else ''}"
    if n_cherry:
        pr_count += f" ({n_cherry} cherry-pick{'s' if n_cherry != 1 else ''})"
    reason = f"{pr_count}, {reason}"

    pr_numbers = [pr["number"] for pr in pr_data]
    return _TIER_TO_SP[tier], reason, pr_numbers


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
    start_str = start_date.isoformat() if hasattr(start_date, "isoformat") else str(start_date)
    query = f"updated:>={start_str}"
    if end_date:
        end_str = end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date)
        query = f"updated:{start_str}..{end_str}"
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


_pr_checklist_cache = {}


def _fetch_pr_checklist(pr_url):
    """Fetch structured PR checklist data. Returns dict or None.

    Session-cached: repeated calls for the same URL return cached result.
    """
    if pr_url in _pr_checklist_cache:
        return _pr_checklist_cache[pr_url]

    parsed = _parse_pr_url(pr_url)
    if not parsed:
        return None
    repo, number = parsed
    try:
        result = subprocess.run(
            [
                "gh", "pr", "view", number, "--repo", repo,
                "--json",
                "state,reviewDecision,statusCheckRollup,"
                "reviewRequests,latestReviews,comments,"
                "mergeable,url,author",
            ],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return None

    state = data.get("state", "UNKNOWN").lower()
    review = data.get("reviewDecision", "")
    checks = data.get("statusCheckRollup", []) or []
    mergeable = data.get("mergeable", "UNKNOWN")

    failing = [
        c.get("name", c.get("context", "unknown"))
        for c in checks
        if c.get("conclusion") == "FAILURE"
    ]
    pending_reviewers = [
        r.get("login", r.get("name", ""))
        for r in (data.get("reviewRequests", []) or [])
        if r.get("login") or r.get("name")
    ]

    # Count unresolved comments (approximation: total comments
    # minus comments from author)
    comments = data.get("comments", []) or []
    author_login = data.get("author", {}).get("login", "")
    unresolved = sum(
        1 for c in comments
        if c.get("author", {}).get("login") != author_login
    )

    checklist = {
        "url": data.get("url", pr_url),
        "state": state,
        "review_decision": review,
        "failing_checks": failing,
        "pending_reviewers": pending_reviewers,
        "unresolved_comments": unresolved,
        "has_conflicts": mergeable == "CONFLICTING",
        "is_author": True,
    }
    _pr_checklist_cache[pr_url] = checklist
    return checklist


def _format_pr_checklist(checklist):
    """Format a PR checklist dict as a status summary string."""
    parts = [checklist["state"]]
    review_map = {
        "APPROVED": "approved",
        "CHANGES_REQUESTED": "changes requested",
        "REVIEW_REQUIRED": "review required",
    }
    if checklist["review_decision"] in review_map:
        parts.append(review_map[checklist["review_decision"]])

    if checklist["failing_checks"]:
        parts.append("CI fail")
    elif checklist["state"] in ("open", "draft"):
        parts.append("CI pass")

    return f"PR: {', '.join(parts)} — {checklist['url']}"


def _checklist_items(checklist):
    """Return list of actionable checklist item strings for a PR."""
    items = []
    if checklist["unresolved_comments"]:
        n = checklist["unresolved_comments"]
        items.append(f"{n} unresolved review comment{'s' if n != 1 else ''}")
    if checklist["failing_checks"]:
        items.append(f"Failing: {', '.join(checklist['failing_checks'])}")
    if checklist["pending_reviewers"]:
        items.append(
            f"Awaiting review: {', '.join(checklist['pending_reviewers'])}"
        )
    if checklist["has_conflicts"]:
        items.append("Merge conflict")
    return items


def _fetch_pr_checklists(issues):
    """Return dict of issue key -> checklist dict for non-closed issues with PRs."""
    checklists = {}
    for issue in issues:
        if str(issue.fields.status) == "Closed":
            continue
        pr_field = getattr(issue.fields, CF_GIT_PR, None)
        if not pr_field:
            continue
        first_url = pr_field.strip().splitlines()[0].strip()
        checklist = _fetch_pr_checklist(first_url)
        if checklist:
            checklists[issue.key] = checklist
    return checklists


def _fetch_reviewer_prs():
    """Fetch open PRs where the current user is requested as reviewer."""
    try:
        result = subprocess.run(
            [
                "gh", "search", "prs",
                "--review-requested=@me",
                "--state=open",
                "--limit=25",
                "--json",
                "number,title,url,repository,createdAt",
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return []
        prs = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return []
    return prs


def _fetch_pr_statuses(issues):
    """Return dict of issue key -> formatted PR status string for non-closed issues."""
    checklists = _fetch_pr_checklists(issues)
    return {
        key: _format_pr_checklist(cl) for key, cl in checklists.items()
    }
