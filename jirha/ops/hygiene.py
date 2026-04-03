"""Hygiene check command: sprint audit with optional interactive apply."""

import re
from collections import Counter

from jirha.api import (
    REVIEW_FILTER,
    SP_TIERS,
    _assess_pr_sp,
    _assignee_filter,
    _assignee_name,
    _extract_jira_keys,
    _fetch_user_prs,
    _issue_sp,
    _pr_body,
    _pr_details,
    _warn_in_progress_no_sprint,
    get_jira,
)
from jirha.config import (
    CF_GIT_PR,
    CF_STORY_POINTS,
    DEFAULT_COMPONENT,
    SERVER,
)


def _jira_url(key):
    """Return full Jira browse URL for a key."""
    return f"{SERVER}/browse/{key}"


def _prompt_choice(prompt_text):
    """Prompt user for a choice. Returns lowercase string or None on EOF/interrupt."""
    try:
        return input(prompt_text).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nSkipped.")
        return None


def _parse_indices(choice, count):
    """Parse a user choice string into a set of 0-based indices."""
    if choice in ("a", "all"):
        return set(range(count))
    indices = set()
    for part in choice.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < count:
                indices.add(idx)
    return indices


def _print_hygiene_report(issue_gaps, team=False):
    """Print hygiene report for issues with missing metadata."""
    if not issue_gaps:
        print("All issues have complete metadata.")
        return
    sorted_issues = sorted(issue_gaps.values(), key=lambda x: -len(x["missing"]))
    print(f"Found {len(sorted_issues)} issues with incomplete metadata:\n")
    for entry in sorted_issues:
        issue = entry["issue"]
        missing = entry["missing"]
        sp = _issue_sp(issue)
        sp_str = f" {int(sp)}SP" if sp else ""
        priority = getattr(issue.fields, "priority", None) or "unset"
        components = ", ".join(c.name for c in (issue.fields.components or [])) or "none"
        assignee_str = ""
        if team:
            assignee_str = f" @{_assignee_name(issue)}"
        summary = issue.fields.summary
        status = issue.fields.status
        print(f"{_jira_url(issue.key)}{sp_str}{assignee_str} [{status}] [{priority}] — {summary}")
        print(f"  Components: {components}")
        print(f"  Missing: {', '.join(missing)}")
        print()

    gap_counts = Counter(m for e in sorted_issues for m in e["missing"])
    print("Summary:")
    for gap, count in gap_counts.most_common():
        print(f"  {gap}: {count} issues")
    print(f"  Total: {len(sorted_issues)} issues need attention")


def _fill_missing_descriptions(jira, issue_gaps, dry_run=False):
    """Report/fix issues missing a description that have a linked PR with a body."""
    candidates = []
    for key, entry in issue_gaps.items():
        if "description" not in entry["missing"]:
            continue
        issue = entry["issue"]
        pr_url = getattr(issue.fields, CF_GIT_PR, None)
        if not pr_url:
            continue
        first_url = pr_url.strip().splitlines()[0].strip()
        body = _pr_body(first_url)
        if not body or len(body.strip()) < 10:
            continue
        candidates.append(
            {
                "key": key,
                "summary": issue.fields.summary,
                "pr_url": first_url,
                "body": body.strip(),
            }
        )

    if not candidates:
        return

    print("\n## Missing Descriptions (from PRs)\n")
    for i, c in enumerate(candidates, 1):
        preview = c["body"][:200] + ("..." if len(c["body"]) > 200 else "")
        print(f"{i}. {_jira_url(c['key'])} — {c['summary']}")
        print(f"   PR: {c['pr_url']}")
        print(f"   Preview: {preview}")
        print()

    if dry_run:
        print("To update: jirha update KEY --desc-file <file>")
        return

    choice = _prompt_choice("Update descriptions from PR? [a]ll / [n]one / [1,2,...]: ")
    if not choice or choice in ("n", "none"):
        return

    for idx in sorted(_parse_indices(choice, len(candidates))):
        c = candidates[idx]
        jira.issue(c["key"]).update(fields={"description": c["body"]})
        print(f"  → {_jira_url(c['key'])}: description updated from PR")


def _auto_link_prs(jira, sprint_issues, user_prs):
    """Match unlinked PRs to sprint Jiras and auto-update the PR field.

    Matches by Jira key found in PR title, body, or branch name.
    Returns count of links added.
    """
    sprint_keys = {i.key for i in sprint_issues}
    issue_pr_urls = {}
    for issue in sprint_issues:
        pr_field = getattr(issue.fields, CF_GIT_PR, None) or ""
        issue_pr_urls[issue.key] = pr_field

    linked = 0
    print("\n## Auto-link PRs\n")
    for pr in user_prs:
        pr_url = pr.get("url", "")
        if not pr_url:
            continue
        candidates = set()
        candidates |= _extract_jira_keys(pr.get("title", ""))
        candidates |= _extract_jira_keys(pr.get("headRefName", ""))
        candidates |= _extract_jira_keys(pr.get("body", ""))
        matched_keys = candidates & sprint_keys
        for key in matched_keys:
            current_pr = issue_pr_urls.get(key, "")
            if pr_url in current_pr:
                continue
            updated_pr = (current_pr.rstrip() + "\n" + pr_url).strip()
            jira.issue(key).update(fields={CF_GIT_PR: updated_pr})
            issue_pr_urls[key] = updated_pr
            print(f"  + {_jira_url(key)} ← {pr_url}")
            linked += 1

    if not linked:
        print("  All PRs already linked.")
    else:
        print(f"\n  Linked {linked} PR(s).")
    return linked


def _sp_reassessment(jira, scope, max_results, team=False, dry_run=False):
    """Report and optionally fix SP mismatches between Jira and linked PRs."""
    print("\n## SP Reassessment (from PRs)\n")
    sp_issues = jira.search_issues(
        f"{scope} AND sprint in openSprints() AND type not in (Epic, Feature){REVIEW_FILTER}",
        maxResults=max_results,
        fields=f"summary,status,assignee,{CF_STORY_POINTS},{CF_GIT_PR}",
    )

    mismatches, confirmed, skipped = [], 0, 0
    for issue in sp_issues:
        pr_url = getattr(issue.fields, CF_GIT_PR, None)
        if not pr_url:
            skipped += 1
            continue
        raw_sp = getattr(issue.fields, CF_STORY_POINTS, None)
        current_sp = int(raw_sp) if raw_sp is not None else None
        result = _assess_pr_sp(pr_url)
        if not result:
            skipped += 1
            continue
        suggested_sp, reason, pr_number = result
        is_mismatch = (
            current_sp is None
            or current_sp not in SP_TIERS
            or abs(SP_TIERS[current_sp] - SP_TIERS[suggested_sp]) >= 2
        )
        if is_mismatch:
            mismatches.append(
                {
                    "key": issue.key,
                    "current_sp": current_sp,
                    "suggested_sp": suggested_sp,
                    "reason": reason,
                    "pr_url": pr_url,
                    "pr_number": pr_number,
                    "assignee": _assignee_name(issue),
                }
            )
        else:
            confirmed += 1

    if not mismatches:
        print(f"No SP mismatches found. ({confirmed} confirmed, {skipped} skipped/no PR)")
        return

    for i, m in enumerate(mismatches, 1):
        assignee_str = f" @{m['assignee']}" if team else ""
        current_label = f"{m['current_sp']}SP" if m["current_sp"] is not None else "no SP"
        suggested = m["suggested_sp"]
        print(f"{i}. {_jira_url(m['key'])} {current_label} → suggested {suggested}SP{assignee_str}")
        print(f"   {m['reason']}")
        for url in m["pr_url"].strip().splitlines():
            url = url.strip()
            if url:
                print(f"   {url}")
        print()
    print(f"({confirmed} confirmed, {skipped} skipped/no PR)\n")

    if dry_run:
        print("To update: jirha update KEY --sp N")
        return

    choice = _prompt_choice("Apply SP? [a]ll / [n]one / [1,2,...] / [1=5] override: ")
    if not choice or choice in ("n", "none"):
        return

    apply_indices, overrides = _parse_sp_choice(choice, mismatches)
    for idx in sorted(apply_indices):
        m = mismatches[idx]
        new_sp = overrides.get(idx, m["suggested_sp"])
        comment = f"SP reassessed from PR #{m['pr_number']}: {m['reason']}"
        jira.issue(m["key"]).update(fields={CF_STORY_POINTS: float(new_sp)})
        old_label = f"{m['current_sp']}" if m["current_sp"] is not None else "empty"
        jira.add_comment(m["key"], f"Updated SP: {old_label} → {new_sp}\n\n{comment}")
        print(f"  → {_jira_url(m['key'])}: {old_label} → {new_sp}SP")


def _status_cross_check(jira, sprint_issues, team=False, dry_run=False):
    """Report and optionally fix PR/Jira status mismatches."""
    from jirha.ops.issues import _find_close_transition

    print("\n## PR/Jira Status Cross-check\n")
    reopen_candidates = []
    close_candidates = []
    review_subtasks = []

    for issue in sprint_issues:
        pr_field = getattr(issue.fields, CF_GIT_PR, None)
        if not pr_field:
            continue
        status = str(issue.fields.status)
        pr_urls = [u.strip() for u in pr_field.strip().splitlines() if u.strip()]
        if not pr_urls:
            continue

        pr_states = []
        for url in pr_urls:
            details = _pr_details(url)
            if details:
                pr_states.append((url, details.get("state", "").upper()))

        if not pr_states:
            continue

        has_open = any(s == "OPEN" for _, s in pr_states)
        all_closed = all(s in ("MERGED", "CLOSED") for _, s in pr_states)

        if status in ("Closed", "Resolved") and has_open:
            open_prs = [url for url, s in pr_states if s == "OPEN"]
            reopen_candidates.append(
                {
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "status": status,
                    "open_prs": open_prs,
                }
            )
        elif status not in ("Closed", "Resolved") and all_closed:
            close_candidates.append(
                {
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "status": status,
                    "pr_states": pr_states,
                }
            )

    # Check for open review subtasks on closed issues
    closed_issues = [i for i in sprint_issues if str(i.fields.status) in ("Closed", "Resolved")]
    for issue in closed_issues:
        subtasks = getattr(issue.fields, "subtasks", None) or []
        for st in subtasks:
            if "Review" in st.fields.summary and str(st.fields.status) != "Closed":
                review_subtasks.append(
                    {
                        "parent_key": issue.key,
                        "key": st.key,
                        "summary": st.fields.summary,
                    }
                )

    if not reopen_candidates and not close_candidates and not review_subtasks:
        print("PR and Jira statuses are consistent.")
        return

    # Reopen candidates
    if reopen_candidates:
        print("### Open PRs on Closed Jiras (propose reopen):\n")
        for i, item in enumerate(reopen_candidates, 1):
            print(f"{i}. {_jira_url(item['key'])} [{item['status']}] — {item['summary']}")
            for url in item["open_prs"]:
                print(f"   PR open: {url}")
            print()

        if dry_run:
            print('To reopen: jirha transition KEY "In Progress"\n')
        else:
            choice = _prompt_choice("Reopen? [a]ll / [n]one / [1,2,...]: ")
            if choice and choice not in ("n", "none"):
                for idx in sorted(_parse_indices(choice, len(reopen_candidates))):
                    item = reopen_candidates[idx]
                    issue_obj = jira.issue(item["key"])
                    transitions = jira.transitions(issue_obj)
                    reopen_id = next(
                        (
                            t["id"]
                            for t in transitions
                            if t["name"].lower() in ("in progress", "reopen", "open", "new")
                        ),
                        None,
                    )
                    if reopen_id:
                        jira.transition_issue(issue_obj, reopen_id)
                        pr_list = ", ".join(item["open_prs"])
                        jira.add_comment(item["key"], f"Reopened: open PR(s) found — {pr_list}")
                        print(f"  → {_jira_url(item['key'])}: reopened")
                    else:
                        print(f"  → {_jira_url(item['key'])}: no reopen transition available")

    # Close candidates
    if close_candidates:
        print("### All PRs merged/closed on Open Jiras (propose close):\n")
        for i, item in enumerate(close_candidates, 1):
            print(f"{i}. {_jira_url(item['key'])} [{item['status']}] — {item['summary']}")
            for url, state in item["pr_states"]:
                print(f"   PR {state.lower()}: {url}")
            print()

        if dry_run:
            print("To close: jirha transition KEY Closed\n")
        else:
            choice = _prompt_choice("Close? [a]ll / [n]one / [1,2,...]: ")
            if choice and choice not in ("n", "none"):
                for idx in sorted(_parse_indices(choice, len(close_candidates))):
                    item = close_candidates[idx]
                    issue_obj = jira.issue(item["key"])
                    close_id = _find_close_transition(jira, issue_obj)
                    if close_id:
                        jira.transition_issue(issue_obj, close_id)
                        pr_summary = ", ".join(
                            f"{url} ({state.lower()})" for url, state in item["pr_states"]
                        )
                        jira.add_comment(
                            item["key"],
                            f"All PRs merged/closed ({pr_summary}), transitioning to Closed.",
                        )
                        print(f"  → {_jira_url(item['key'])}: closed")
                        # Close review subtasks of this issue
                        _close_review_subtasks(jira, item["key"])
                    else:
                        print(f"  → {_jira_url(item['key'])}: no close transition available")

    # Review subtasks
    if review_subtasks:
        print("### Open review subtasks on Closed Jiras:\n")
        for i, item in enumerate(review_subtasks, 1):
            print(f"{i}. {_jira_url(item['key'])} — {item['summary']}")
            print(f"   Parent: {_jira_url(item['parent_key'])}")
            print()

        if dry_run:
            print("To close: jirha transition KEY Closed")
        else:
            choice = _prompt_choice("Close review subtasks? [a]ll / [n]one / [1,2,...]: ")
            if choice and choice not in ("n", "none"):
                for idx in sorted(_parse_indices(choice, len(review_subtasks))):
                    item = review_subtasks[idx]
                    issue_obj = jira.issue(item["key"])
                    close_id = _find_close_transition(jira, issue_obj)
                    if close_id:
                        jira.transition_issue(issue_obj, close_id)
                        print(f"  → {_jira_url(item['key'])}: closed")
                    else:
                        print(f"  → {_jira_url(item['key'])}: no close transition available")


def _close_review_subtasks(jira, issue_key):
    """Close open review subtasks of an issue."""
    from jirha.ops.issues import _find_close_transition

    issue = jira.issue(issue_key)
    subtasks = getattr(issue.fields, "subtasks", None) or []
    for st in subtasks:
        st_issue = jira.issue(st.key)
        if str(st_issue.fields.status) == "Closed":
            continue
        if "Review" not in st_issue.fields.summary:
            continue
        close_id = _find_close_transition(jira, st_issue)
        if close_id:
            jira.transition_issue(st_issue, close_id)
            print(f"    Closed subtask {_jira_url(st_issue.key)}: {st_issue.fields.summary}")


def _parse_sp_choice(choice, mismatches):
    """Parse user choice for SP reassessment. Returns (apply_indices, overrides)."""
    if choice in ("a", "all"):
        return set(range(len(mismatches))), {}
    apply_indices = set()
    overrides = {}
    for part in choice.split(","):
        part = part.strip()
        m = re.match(r"(\d+)=(\d+)", part)
        if m:
            idx, sp_val = int(m.group(1)) - 1, int(m.group(2))
            if sp_val in SP_TIERS and 0 <= idx < len(mismatches):
                apply_indices.add(idx)
                overrides[idx] = sp_val
        elif part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(mismatches):
                apply_indices.add(idx)
    return apply_indices, overrides


def _report_context_suggestions(jira, issue_gaps, dry_run=False):
    """Report hierarchy context for tasks missing SP that have no PR."""
    candidates = []
    for key, entry in issue_gaps.items():
        if "SP" not in entry["missing"]:
            continue
        issue = entry["issue"]
        pr_url = getattr(issue.fields, CF_GIT_PR, None)
        if pr_url:
            continue  # Has PR — will be handled by SP reassessment
        candidates.append(issue)

    if not candidates:
        return

    from jirha.ops.context import assemble_context

    print("\n## SP Context (no PR linked)\n")
    for issue in candidates:
        ctx = assemble_context(jira, issue.key)
        assignee = _assignee_name(issue)
        print(f"- {_jira_url(issue.key)} @{assignee} — {issue.fields.summary}")
        if ctx["suggested_sp_range"]:
            low, high = ctx["suggested_sp_range"]
            quality = ctx["data_quality"]
            n = len(ctx["eng_metrics"])
            print(f"  Suggested: {low}–{high} SP ({quality}, {n} eng PRs)")
        elif ctx["feature"]:
            print(f"  Feature: {_jira_url(ctx['feature'].key)} — {ctx['feature'].fields.summary}")
            print("  No eng PRs found — estimate manually")
        elif ctx["epic"]:
            print(f"  Epic: {_jira_url(ctx['epic'].key)} — {ctx['epic'].fields.summary}")
            print("  No feature parent — estimate manually")
        else:
            print("  Standalone task — estimate manually")
        if dry_run:
            print(f"  To set: jirha update {issue.key} --sp <value>")
        print()


def cmd_hygiene(args):
    """Full sprint hygiene audit."""
    from jirha.ops.sprint import _get_active_sprint

    jira = get_jira()
    scope = _assignee_filter(args.team)
    dry_run = args.dry_run

    # Step 1: Detect current sprint
    sprint = _get_active_sprint(jira)
    if sprint:
        print(f"# Sprint Hygiene: {sprint['name']}")
        print(f"**Dates:** {sprint['start']} → {sprint['end']}\n")
    else:
        print("# Sprint Hygiene (no active sprint detected)\n")

    # All sprint issues (open AND closed) for full audit
    sprint_base = f"{scope} AND sprint in openSprints(){REVIEW_FILTER}"
    sprint_fields = (
        f"summary,status,priority,assignee,components,issuetype,subtasks,"
        f"{CF_STORY_POINTS},{CF_GIT_PR}"
    )
    sprint_issues = jira.search_issues(
        sprint_base,
        maxResults=args.max,
        fields=sprint_fields,
    )

    # Step 2: Metadata checks (on all sprint issues)
    fields_base = f"summary,status,priority,assignee,components,{CF_STORY_POINTS}"
    checks = [
        (
            "component",
            f'{sprint_base} AND component not in ({DEFAULT_COMPONENT}, "AEM Migration")',
            fields_base,
        ),
        ("team", f"{sprint_base} AND Team is EMPTY", fields_base),
        ("priority", f"{sprint_base} AND priority is EMPTY", fields_base),
        (
            "SP",
            f'{sprint_base} AND "Story Points" is EMPTY AND priority != Undefined '
            f"AND type not in (Epic, Feature)",
            f"{fields_base},issuetype",
        ),
        ("description", f"{sprint_base} AND description is EMPTY", f"{fields_base},{CF_GIT_PR}"),
        (
            "SP should be empty",
            f'{sprint_base} AND type in (Epic, Feature) AND "Story Points" is not EMPTY',
            fields_base,
        ),
    ]

    issue_gaps = {}
    for gap_name, jql, fields in checks:
        issues = jira.search_issues(jql, maxResults=args.max, fields=fields)
        for issue in issues:
            if issue.key not in issue_gaps:
                issue_gaps[issue.key] = {"issue": issue, "missing": []}
            issue_gaps[issue.key]["missing"].append(gap_name)

    _warn_in_progress_no_sprint(jira, args.team)
    _print_hygiene_report(issue_gaps, args.team)
    _fill_missing_descriptions(jira, issue_gaps, dry_run)

    # Step 2.5: Context assembly for SP-less, PR-less tasks
    _report_context_suggestions(jira, issue_gaps, dry_run)

    # Step 3: Fetch user PRs and auto-link (non-destructive, no confirmation needed)
    if sprint:
        user_prs = _fetch_user_prs(sprint["start"], sprint["end"])
        if user_prs:
            _auto_link_prs(jira, sprint_issues, user_prs)
            sprint_issues = jira.search_issues(
                sprint_base,
                maxResults=args.max,
                fields=sprint_fields,
            )

    # Step 4: SP reassessment
    _sp_reassessment(jira, scope, args.max, args.team, dry_run)

    # Step 5: PR/Jira status cross-check
    _status_cross_check(jira, sprint_issues, args.team, dry_run)
