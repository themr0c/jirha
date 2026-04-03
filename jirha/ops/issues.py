"""Issue commands: list, show, create, update, transition, close_subtasks."""

import sys

from jirha.api import (
    SP_TIERS,
    _assess_pr_sp,
    _createmeta,
    _issue_sp,
    get_jira,
    parse_fields,
)
from jirha.config import (
    CF_GIT_PR,
    CF_RN_STATUS,
    CF_RN_TEXT,
    CF_RN_TYPE,
    CF_SPRINT,
    CF_STORY_POINTS,
    CF_TEAM,
    DEFAULT_TEAM,
    SERVER,
    SP_VALUES,
    TEAM_RHDH_DOCS_ID,
)


def _fmt_versions(versions):
    """Format a list of Jira version objects."""
    if not versions:
        return "unset"
    return ", ".join(v.name for v in versions)


def _fmt_components(components):
    """Format a list of Jira component objects."""
    if not components:
        return "unset"
    return ", ".join(c.name for c in components)


def _fmt_team(team):
    """Format Jira team field."""
    if not team:
        return "unset"
    return getattr(team, "name", str(team))


def _fmt_labels(labels):
    """Format a list of labels."""
    if not labels:
        return "unset"
    return ", ".join(labels)


def _fmt_sprint(sprints):
    """Format sprint field (list of sprint objects)."""
    if not sprints:
        return "unset"
    active = [s for s in sprints if getattr(s, "state", "") == "active"]
    if active:
        return active[-1].name
    return sprints[-1].name


def _fmt_links(links):
    """Format issue links."""
    if not links:
        return "none"
    parts = []
    for link in links:
        if hasattr(link, "outwardIssue") and link.outwardIssue:
            parts.append(f"{link.type.outward} {link.outwardIssue.key}")
        elif hasattr(link, "inwardIssue") and link.inwardIssue:
            parts.append(f"{link.type.inward} {link.inwardIssue.key}")
    return ", ".join(parts) if parts else "none"


def cmd_list(args):
    """List issues assigned to me."""
    jira = get_jira()
    jql = args.jql or "assignee = currentUser() ORDER BY updated DESC"
    if args.open:
        jql = "assignee = currentUser() AND status != Closed ORDER BY updated DESC"
    issues = jira.search_issues(jql, maxResults=args.max)
    for issue in issues:
        sp = _issue_sp(issue)
        sp_str = f" [{int(sp)}SP]" if sp else ""
        print(f"{issue.key:20s} [{issue.fields.status}]{sp_str} {issue.fields.summary}")


def cmd_show(args):
    """Show issue details."""
    jira = get_jira()
    all_fields = (
        "summary,status,issuetype,priority,fixVersions,components,labels,"
        "reporter,versions,assignee,issuelinks,description,comment,"
        f"{CF_TEAM},{CF_SPRINT},{CF_STORY_POINTS},{CF_GIT_PR},"
        f"{CF_RN_STATUS},{CF_RN_TYPE},{CF_RN_TEXT}"
    )
    issue = jira.issue(args.key, fields=all_fields)
    f = issue.fields
    W = 18  # label width

    # Group 1: Identity
    print(f"{'Status:':<{W}}{f.status}")
    print(f"{'Type:':<{W}}{f.issuetype}")
    print(f"{'Key:':<{W}}{issue.key}")
    print(f"{'Summary:':<{W}}{f.summary}")

    # Group 2: Classification
    print()
    print(f"{'Priority:':<{W}}{f.priority}")
    print(f"{'Fix versions:':<{W}}{_fmt_versions(f.fixVersions)}")
    print(f"{'Components:':<{W}}{_fmt_components(f.components)}")
    print(f"{'Team:':<{W}}{_fmt_team(getattr(f, CF_TEAM, None))}")
    print(f"{'Labels:':<{W}}{_fmt_labels(f.labels)}")
    print(f"{'Reporter:':<{W}}{f.reporter or 'unset'}")
    print(f"{'Affects versions:':<{W}}{_fmt_versions(f.versions)}")

    # Group 3: Work tracking
    print()
    print(f"{'Assignee:':<{W}}{f.assignee or 'unassigned'}")
    print(f"{'Sprint:':<{W}}{_fmt_sprint(getattr(f, CF_SPRINT, None))}")
    sp = getattr(f, CF_STORY_POINTS, None)
    print(f"{'SP:':<{W}}{str(int(sp)) if sp else 'unset'}")
    print(f"{'PR:':<{W}}{getattr(f, CF_GIT_PR, None) or 'unset'}")
    print(f"{'Links:':<{W}}{_fmt_links(f.issuelinks)}")

    # Group 4: Release notes
    print()
    print(f"{'RN Status:':<{W}}{getattr(f, CF_RN_STATUS, None) or 'unset'}")
    print(f"{'RN Type:':<{W}}{getattr(f, CF_RN_TYPE, None) or 'unset'}")
    print(f"{'RN Text:':<{W}}{getattr(f, CF_RN_TEXT, None) or 'unset'}")

    # Link
    print(f"\n{'Link:':<{W}}{SERVER}/browse/{issue.key}")

    # Description
    desc = f.description or "(empty)"
    print(f"\nDescription:\n{desc}")

    # Comments
    if f.comment and f.comment.comments:
        comments = f.comment.comments
        if args.comments:
            print(f"\nComments ({len(comments)}):")
            for c in comments:
                print(f"  {c.author.displayName}: {c.body}")
        else:
            print(f"\nComments ({len(comments)}):")
            for c in comments[-3:]:
                print(f"  {c.author.displayName}: {c.body[:200]}")


def _resolve_sp(args, jira):
    """Resolve --sp value. Returns (float_val, change_msg) or None."""
    if not args.sp:
        return None
    if args.sp == "auto":
        pr_url = args.pr or getattr(jira.issue(args.key, fields=CF_GIT_PR).fields, CF_GIT_PR, None)
        if pr_url:
            result = _assess_pr_sp(pr_url)
            if not result:
                sys.exit(f"Error: could not assess SP from PR: {pr_url}")
            sp_val, reason, _ = result
            return float(sp_val), f"Story points: {sp_val} (auto: {reason})"
        # No PR — fall back to context assembler (JSON for skill pickup)
        import json as json_mod

        from jirha.ops.context import assemble_context_json

        ctx_json = assemble_context_json(jira, args.key)
        print(json_mod.dumps(ctx_json, indent=2))
        if ctx_json["suggested_sp_range"]:
            low, high = ctx_json["suggested_sp_range"]
            print(f"\nNo PR linked. Suggested range: {low}–{high} SP")
        print(f"Use: jirha update {args.key} --sp <value>")
        return None
    sp_val = int(args.sp)
    if sp_val not in SP_TIERS:
        sys.exit(f'Error: SP must be {", ".join(str(s) for s in SP_VALUES)}, or "auto".')
    return float(sp_val), f"Story points: {sp_val}"


def _modify_label(labels, label, add=True):
    """Add or remove a label. Returns change message or None."""
    if add:
        if label in labels:
            return None
        labels.append(label)
        return f"Label added: {label}"
    if label not in labels:
        return None
    labels.remove(label)
    return f"Label removed: {label}"


def _resolve_labels(jira, key, fields, add_label, remove_label):
    """Handle --add-label and --remove-label. Mutates fields, returns changes list."""
    if not add_label and not remove_label:
        return []
    labels = fields.get("labels") or list(jira.issue(key, fields="labels").fields.labels or [])
    changes = []
    for label, add in [(add_label, True), (remove_label, False)]:
        if not label:
            continue
        change = _modify_label(labels, label, add)
        if change:
            changes.append(change)
        else:
            print(f"{key} {'already has' if add else 'does not have'} label {label}")
    if changes:
        fields["labels"] = labels
    return changes


def _build_fields(args, jira):
    """Build Jira fields dict and changes list from args. Returns (fields, changes)."""
    fields = {}
    changes = []

    # Simple scalar fields
    simple = [
        ("summary", "summary", lambda v: (v, f"Summary: {v}")),
        ("issue_type", "issuetype", lambda v: ({"name": v}, f"Type: {v}")),
        ("pr", CF_GIT_PR, lambda v: (v, f"PR: {v}")),
        ("priority", "priority", lambda v: ({"name": v}, f"Priority: {v}")),
        ("assignee", "assignee", lambda v: ({"name": v}, f"Assignee: {v}")),
        ("rn_status", CF_RN_STATUS, lambda v: (v, f"RN Status: {v}")),
        ("rn_type", CF_RN_TYPE, lambda v: (v, f"RN Type: {v}")),
        ("rn_text", CF_RN_TEXT, lambda v: (v, f"RN Text: {v}")),
    ]
    for attr, field_key, transform in simple:
        val = getattr(args, attr, None)
        if val:
            fval, msg = transform(val)
            fields[field_key] = fval
            changes.append(msg)

    # Description (text or file)
    if args.desc:
        fields["description"] = args.desc
        changes.append("Description updated")
    elif args.desc_file:
        with open(args.desc_file) as f:
            fields["description"] = f.read()
        changes.append("Description updated from file")

    # Story points
    sp = _resolve_sp(args, jira)
    if sp:
        fields[CF_STORY_POINTS] = sp[0]
        changes.append(sp[1])

    # Fix version (append, not replace)
    if args.fix_version:
        existing = [
            {"name": v.name} for v in jira.issue(args.key, fields="fixVersions").fields.fixVersions
        ]
        if not any(v["name"] == args.fix_version for v in existing):
            existing.append({"name": args.fix_version})
            fields["fixVersions"] = existing
            changes.append(f"Fix version: {args.fix_version}")
        else:
            print(f"{args.key} already has fix version {args.fix_version}")

    # Affects version (append, not replace)
    if getattr(args, "affects_version", None):
        existing = [
            {"name": v.name} for v in jira.issue(args.key, fields="versions").fields.versions
        ]
        if not any(v["name"] == args.affects_version for v in existing):
            existing.append({"name": args.affects_version})
            fields["versions"] = existing
            changes.append(f"Affects version: {args.affects_version}")
        else:
            print(f"{args.key} already has affects version {args.affects_version}")

    # Component (append, not replace)
    if args.component:
        existing = [
            {"name": c.name} for c in jira.issue(args.key, fields="components").fields.components
        ]
        if not any(c["name"] == args.component for c in existing):
            existing.append({"name": args.component})
            fields["components"] = existing
            changes.append(f"Component: {args.component}")
        else:
            print(f"{args.key} already has component {args.component}")

    # Team (use known ID for default team, otherwise look up from an existing issue)
    if args.team:
        if args.team == DEFAULT_TEAM:
            team_id = TEAM_RHDH_DOCS_ID
        else:
            ref = jira.search_issues(f'Team = "{args.team}"', maxResults=1, fields=CF_TEAM)
            if not ref:
                sys.exit(f'Error: Could not find team "{args.team}"')
            team_id = getattr(ref[0].fields, CF_TEAM).id
        fields[CF_TEAM] = team_id
        changes.append(f"Team: {args.team}")

    # Labels
    changes += _resolve_labels(jira, args.key, fields, args.add_label, args.remove_label)

    return fields, changes


def _build_comment(args, changes):
    """Assemble comment text from changes list and user-provided comment. Returns str or None."""
    parts = []
    if changes:
        parts.append("Updated:\n- " + "\n- ".join(changes))
    if args.comment_file:
        with open(args.comment_file) as f:
            parts.append(f.read())
    if args.comment:
        parts.append(args.comment)
    return "\n\n".join(parts) if parts else None


def _find_sprint_id(jira, sprint_name=None):
    """Find sprint ID by name or return active sprint."""
    if not sprint_name:
        from jirha.ops.sprint import _get_active_sprint

        sprint = _get_active_sprint(jira)
        return sprint["id"] if sprint else None
    issues = jira.search_issues(
        "assignee = currentUser() AND sprint in openSprints()", maxResults=1, fields=CF_SPRINT
    )
    if not issues:
        return None
    for s in getattr(issues[0].fields, CF_SPRINT, None) or []:
        if sprint_name.lower() in s.name.lower():
            return s.id
    return None


def cmd_update(args):
    """Update one or more fields on an issue, with optional comment."""
    jira = get_jira()
    fields, changes = _build_fields(args, jira)

    # Link
    if args.link_to:
        jira.create_issue_link(args.link_type, args.key, args.link_to)
        changes.append(f"Linked —[{args.link_type}]→ {args.link_to}")

    # Sprint
    sprint_name = args.sprint
    if sprint_name is not None:
        sprint_id = _find_sprint_id(jira, sprint_name or None)
        if not sprint_id:
            sys.exit(f'Error: Could not find sprint "{sprint_name or "active"}"')
        jira.add_issues_to_sprint(sprint_id, [args.key])
        changes.append(f"Sprint: {sprint_name or 'active'}")

    comment = _build_comment(args, changes)

    if not fields and not comment and sprint_name is None and not args.link_to and not args.attach:
        sys.exit("Error: nothing to update.")

    if fields:
        jira.issue(args.key).update(fields=fields)
        for c in changes:
            print(f"  {c}")

    # Attachment
    if args.attach:
        jira.add_attachment(issue=args.key, attachment=args.attach)
        changes.append(f"Attached: {args.attach}")

    if comment:
        jira.add_comment(args.key, comment)
        print(f"Updated {args.key} with comment")
    else:
        print(f"Updated {args.key}")


def _find_close_transition(jira, issue):
    """Find a close/done transition ID for an issue, or None."""
    return next(
        (
            t["id"]
            for t in jira.transitions(issue)
            if t["name"].lower() in ("close", "closed", "done")
        ),
        None,
    )


def cmd_transition(args):
    """Transition an issue, or list available transitions if no status given."""
    jira = get_jira()
    issue = jira.issue(args.key)
    transitions = jira.transitions(issue)
    if not args.status:
        print(f"{issue.key} [{issue.fields.status}] — available transitions:")
        for t in transitions:
            print(f"  {t['name']}")
        return
    match = next((t for t in transitions if t["name"].lower() == args.status.lower()), None)
    if not match:
        names = ", ".join(t["name"] for t in transitions)
        sys.exit(f"Error: '{args.status}' not available. Options: {names}")
    jira.transition_issue(issue, match["id"])
    print(f"Transitioned {args.key} to {match['name']}")


def _validate_create(jira, project_key, type_name):
    """Validate issue type for a project. Returns canonical type name.

    Exits with actionable error listing valid types if invalid.
    """
    proj = _createmeta(jira, project_key)
    if not proj:
        sys.exit(f"Error: project {project_key} not found or not accessible.")
    match = next(
        (t for t in proj["issuetypes"] if t["name"].lower() == type_name.lower()),
        None,
    )
    if not match:
        names = ", ".join(t["name"] for t in proj["issuetypes"])
        sys.exit(
            f"Error: '{type_name}' is not a valid issue type for {project_key}.\n"
            f"Available types: {names}\n"
            f"Run: jirha meta {project_key}"
        )
    return match["name"]


def cmd_create(args):
    """Create a new issue."""
    jira = get_jira()

    if getattr(args, "interactive", False):
        fields = _interactive_create(jira, args.project)
    else:
        if not args.summary:
            sys.exit("Error: summary is required. Use --interactive for guided creation.")
        resolved_type = _validate_create(jira, args.project, args.type)
        fields = {
            "project": {"key": args.project},
            "summary": args.summary,
            "issuetype": {"name": resolved_type},
        }
        if args.component:
            fields["components"] = [{"name": args.component}]
        if args.priority:
            fields["priority"] = {"name": args.priority}
        if args.parent:
            fields["parent"] = {"key": args.parent}
        if args.file:
            with open(args.file) as f:
                fields["description"] = f.read()
        elif args.desc:
            fields["description"] = args.desc
        if args.affects_version:
            fields["versions"] = [{"name": args.affects_version}]

    issue = jira.create_issue(fields=fields)
    summary = fields.get("summary", getattr(args, "summary", ""))
    print(f"Created {issue.key}: {summary}")
    print(f"{SERVER}/browse/{issue.key}")


def _interactive_create(jira, project_key):
    """Interactive issue creation. Returns fields dict."""
    proj = _createmeta(jira, project_key)
    if not proj:
        sys.exit(f"Error: project {project_key} not found or not accessible.")

    types = proj["issuetypes"]
    print(f"Issue types for {project_key}:")
    for i, t in enumerate(types, 1):
        tag = " (subtask)" if t.get("subtask") else ""
        print(f"  {i}. {t['name']}{tag}")

    while True:
        choice = input("\nSelect type [1]: ").strip() or "1"
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(types):
                break
        except ValueError:
            match = next(
                (i for i, t in enumerate(types) if t["name"].lower() == choice.lower()),
                None,
            )
            if match is not None:
                idx = match
                break
        print("Invalid choice.")

    selected = types[idx]
    fields = {
        "project": {"key": project_key},
        "issuetype": {"name": selected["name"]},
    }

    summary = input("Summary: ").strip()
    if not summary:
        sys.exit("Error: summary is required.")
    fields["summary"] = summary

    # Parse field metadata
    skip_keys = {
        "project",
        "issuetype",
        "summary",
        "reporter",
        "attachment",
        "issuelinks",
        "comment",
        "worklog",
        "timetracking",
        "watches",
        "votes",
    }
    all_fields = [f for f in parse_fields(selected) if f["key"] not in skip_keys]

    required = [f for f in all_fields if f["required"]]
    optional = [f for f in all_fields if not f["required"]]

    for f in required:
        val = _prompt_field(f, required=True)
        if val is not None:
            fields[f["key"]] = val

    if optional:
        fill = input("\nFill optional fields? [y/N]: ").strip().lower() == "y"
        if fill:
            for f in optional:
                val = _prompt_field(f, required=False)
                if val is not None:
                    fields[f["key"]] = val

    return fields


def _prompt_field(field, required=True):
    """Prompt user for a field value. Returns formatted value or None."""
    if field["allowed_values"]:
        vals = field["allowed_values"]
        if len(vals) <= 10:
            print(f"  Values for {field['name']}: {', '.join(vals)}")
        else:
            print(f"  Values for {field['name']}: {', '.join(vals[:10])}... ({len(vals)} total)")

    suffix = "" if required else " (Enter to skip)"
    val = input(f"{field['name']}{suffix}: ").strip()

    if not val:
        return None

    if field["allowed_values"] and val not in field["allowed_values"]:
        print(f"  Invalid value '{val}'. Choose from the values listed above.")
        return _prompt_field(field, required)

    if field["schema_type"] == "array":
        return [{"name": val}]
    if field["allowed_values"]:
        return {"name": val}
    return val


def cmd_close_subtasks(args):
    """Close open subtasks of closed parent tasks."""
    jira = get_jira()
    closed = jira.search_issues(
        "assignee = currentUser() AND status = Closed AND type not in (Sub-task)", maxResults=50
    )
    count = 0
    for parent in closed:
        for st in parent.fields.subtasks:
            st_issue = jira.issue(st.key)
            if str(st_issue.fields.status) == "Closed":
                continue
            count += 1
            if args.dry_run:
                print(f"Would close {st_issue.key}: {st_issue.fields.summary}")
                continue
            close_id = _find_close_transition(jira, st_issue)
            if close_id:
                jira.transition_issue(st_issue, close_id)
                print(f"Closed {st_issue.key}: {st_issue.fields.summary}")
            else:
                print(f"No close transition for {st_issue.key}")
    if count == 0:
        print("No open subtasks found under closed parents.")
