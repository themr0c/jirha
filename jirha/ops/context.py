"""Context assembler: walk Jira hierarchy to build SP estimation context."""

import re

from jirha.api import (
    _assess_pr_sp,
    _is_doc_repo,
    _issue_sp,
    get_jira,
)
from jirha.config import CF_GIT_PR, CF_STORY_POINTS, CF_TEAM, DEFAULT_TEAM, SERVER, SP_VALUES

_HIERARCHY_FIELDS = (
    f"summary,description,status,issuetype,parent,components,{CF_STORY_POINTS},{CF_GIT_PR}"
)

# Session-scoped cache for hierarchy walks (shared across hygiene calls)
_cache = {}


def _is_eng_task(issue):
    """Return True if the issue belongs to an engineering (non-doc) team."""
    team = getattr(issue.fields, CF_TEAM, None)
    if not team:
        return False
    team_name = getattr(team, "name", str(team))
    return team_name != DEFAULT_TEAM


def _extract_links(issuelinks):
    """Extract issue links as list of dicts with key, link_type, direction."""
    if not issuelinks:
        return []
    result = []
    for link in issuelinks:
        if hasattr(link, "outwardIssue") and link.outwardIssue:
            result.append({
                "key": link.outwardIssue.key,
                "link_type": link.type.outward,
                "direction": "outward",
            })
        elif hasattr(link, "inwardIssue") and link.inwardIssue:
            result.append({
                "key": link.inwardIssue.key,
                "link_type": link.type.inward,
                "direction": "inward",
            })
    return result


def _cached_issue(jira, key, fields):
    """Fetch an issue, caching by (key, fields)."""
    cache_key = (key, fields)
    if cache_key not in _cache:
        _cache[cache_key] = jira.issue(key, fields=fields)
    return _cache[cache_key]


def _walk_hierarchy(jira, issue_key):
    """Walk task -> epic -> feature. Returns dict with task/epic/feature or None."""
    task = _cached_issue(jira, issue_key, _HIERARCHY_FIELDS)
    result = {"task": task, "epic": None, "feature": None}

    epic_parent = getattr(task.fields, "parent", None)
    if not epic_parent:
        return result
    epic = _cached_issue(jira, epic_parent.key, _HIERARCHY_FIELDS)
    result["epic"] = epic

    feat_parent = getattr(epic.fields, "parent", None)
    if not feat_parent:
        return result
    feature = _cached_issue(jira, feat_parent.key, _HIERARCHY_FIELDS)
    result["feature"] = feature
    return result


def _fetch_sibling_tasks(jira, feature_key):
    """Fetch all epics under a feature, then their child tasks with PR info.

    Returns list of dicts: [{epic, tasks: [{issue, pr_urls}]}].
    """
    epics = jira.search_issues(
        f"parent = {feature_key} ORDER BY key",
        maxResults=100,
        fields=f"summary,status,issuetype,components,{CF_STORY_POINTS}",
    )

    sibling_epics = []
    for epic in epics:
        tasks = jira.search_issues(
            f"parent = {epic.key} ORDER BY key",
            maxResults=100,
            fields=f"summary,status,components,{CF_STORY_POINTS},{CF_GIT_PR}",
        )
        task_list = []
        for t in tasks:
            pr_field = getattr(t.fields, CF_GIT_PR, None) or ""
            pr_urls = _extract_pr_urls(pr_field)
            task_list.append({"issue": t, "pr_urls": pr_urls})
        sibling_epics.append({"epic": epic, "tasks": task_list})

    return sibling_epics


def _extract_pr_urls(text):
    """Extract GitHub PR URLs from a text field (may contain wiki markup)."""
    if not text:
        return []
    return re.findall(r"https://github\.com/[^/]+/[^/]+/pull/\d+", str(text))


def _collect_eng_pr_metrics(sibling_epics):
    """Assess SP from engineering PRs across sibling epics.

    Returns list of (pr_url, sp, reason) for non-doc-repo PRs.
    """
    results = []
    seen_urls = set()
    for entry in sibling_epics:
        for task_entry in entry["tasks"]:
            for url in task_entry["pr_urls"]:
                if url in seen_urls or _is_doc_repo(url):
                    continue
                seen_urls.add(url)
                assessment = _assess_pr_sp(url)
                if assessment:
                    sp, reason, pr_number = assessment
                    results.append({"url": url, "sp": sp, "reason": reason, "number": pr_number})
    return results


def _suggest_sp_range(eng_metrics):
    """Suggest an SP range from engineering PR metrics. Returns (low, high) or None."""
    if len(eng_metrics) < 2:
        return None
    sps = sorted(m["sp"] for m in eng_metrics if m["sp"] > 0)
    if not sps:
        return None
    from statistics import median

    med = median(sps)
    # Find the SP values bracketing the median
    sp_list = [s for s in SP_VALUES if s > 0]
    low = max(s for s in sp_list if s <= med)
    high = min(s for s in sp_list if s >= med)
    # Widen by one step in each direction if possible
    low_idx = sp_list.index(low)
    high_idx = sp_list.index(high)
    if low_idx > 0:
        low = sp_list[low_idx - 1]
    if high_idx < len(sp_list) - 1:
        high = sp_list[high_idx + 1]
    return low, high


def assemble_context(jira, issue_key):
    """Assemble full hierarchy context for SP estimation.

    Returns a dict with: task, epic, feature, sibling_epics, eng_metrics,
    suggested_sp_range, data_quality.
    """
    hierarchy = _walk_hierarchy(jira, issue_key)

    sibling_epics = []
    eng_metrics = []
    if hierarchy["feature"]:
        sibling_epics = _fetch_sibling_tasks(jira, hierarchy["feature"].key)
        eng_metrics = _collect_eng_pr_metrics(sibling_epics)

    sp_range = _suggest_sp_range(eng_metrics)
    if len(eng_metrics) >= 5:
        quality = "strong"
    elif len(eng_metrics) >= 2:
        quality = "weak"
    else:
        quality = "none"

    return {
        "task": hierarchy["task"],
        "epic": hierarchy["epic"],
        "feature": hierarchy["feature"],
        "sibling_epics": sibling_epics,
        "eng_metrics": eng_metrics,
        "suggested_sp_range": sp_range,
        "data_quality": quality,
    }


def _jira_url(key):
    return f"{SERVER}/browse/{key}"


def _desc_preview(issue, max_len=200):
    """Return a truncated description preview."""
    desc = issue.fields.description or ""
    if isinstance(desc, dict):
        desc = str(desc)
    if not desc.strip():
        return "(no description)"
    desc = desc.strip().replace("\n", " ")
    if len(desc) > max_len:
        return desc[:max_len] + "..."
    return desc


def _issue_comps(issue):
    """Return comma-separated component names."""
    return ", ".join(c.name for c in (issue.fields.components or []))


def format_context(ctx):
    """Render assembled context as a human-readable markdown string."""
    lines = []
    task = ctx["task"]
    lines.append(f"## Context: {task.key} — {task.fields.summary}")
    lines.append("")

    # Hierarchy
    lines.append("### Hierarchy")
    if ctx["feature"]:
        f = ctx["feature"]
        lines.append(f"- **Feature:** {_jira_url(f.key)} [{f.fields.status}] — {f.fields.summary}")
        lines.append(f"  {_desc_preview(f)}")
    if ctx["epic"]:
        e = ctx["epic"]
        lines.append(f"- **Epic:** {_jira_url(e.key)} [{e.fields.status}] — {e.fields.summary}")
        lines.append(f"  {_desc_preview(e)}")
    lines.append(f"- **Task:** {_jira_url(task.key)} [{task.fields.status}]")
    sp = _issue_sp(task)
    if sp:
        lines.append(f"  Current SP: {int(sp)}")
    lines.append(f"  {_desc_preview(task)}")
    lines.append("")

    # Sibling epics and their tasks
    if ctx["sibling_epics"]:
        lines.append("### Sibling Epics")
        for entry in ctx["sibling_epics"]:
            epic = entry["epic"]
            comps = _issue_comps(epic)
            sp = _issue_sp(epic)
            sp_str = f" {int(sp)}SP" if sp else ""
            title = f"{epic.key}{sp_str} [{epic.fields.status}] ({comps})"
            lines.append(f"\n#### {title} — {epic.fields.summary}")
            for te in entry["tasks"][:15]:
                t = te["issue"]
                t_sp = _issue_sp(t)
                t_sp_str = f" {int(t_sp)}SP" if t_sp else ""
                t_comps = _issue_comps(t)
                pr_info = ""
                if te["pr_urls"]:
                    non_doc = [u for u in te["pr_urls"] if not _is_doc_repo(u)]
                    doc = [u for u in te["pr_urls"] if _is_doc_repo(u)]
                    parts = []
                    if non_doc:
                        parts.append(f"{len(non_doc)} eng PR")
                    if doc:
                        parts.append(f"{len(doc)} doc PR")
                    pr_info = f" ({', '.join(parts)})"
                prefix = f"{t.key}{t_sp_str} [{t.fields.status}] ({t_comps}){pr_info}"
                lines.append(f"- {prefix} — {t.fields.summary}")
            if len(entry["tasks"]) > 15:
                lines.append(f"- ... and {len(entry['tasks']) - 15} more tasks")
        lines.append("")

    # Engineering PR metrics
    if ctx["eng_metrics"]:
        lines.append("### Engineering PRs (non-doc)")
        for m in ctx["eng_metrics"]:
            lines.append(f"- PR #{m['number']}: {m['sp']}SP ({m['reason']}) — {m['url']}")
        lines.append("")

    # Suggestion
    lines.append("### SP Suggestion")
    if ctx["suggested_sp_range"]:
        low, high = ctx["suggested_sp_range"]
        lines.append(f"Based on {len(ctx['eng_metrics'])} engineering PRs: **{low}–{high} SP**")
        lines.append(f"Data quality: {ctx['data_quality']}")
    elif ctx["feature"]:
        lines.append(
            "No engineering PRs found in this feature. Estimate manually from descriptions above."
        )
    elif ctx["epic"]:
        lines.append("No feature parent found. Estimate manually from epic/task context.")
    else:
        lines.append("Standalone task — no hierarchy context available.")

    return "\n".join(lines)


def cmd_context(args):
    """Show hierarchy context for SP estimation."""
    jira = get_jira()
    ctx = assemble_context(jira, args.key)
    print(format_context(ctx))
