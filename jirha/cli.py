"""CLI entry point for jirha."""

import argparse

from jirha.config import DEFAULT_COMPONENT, DEFAULT_TEAM, SP_VALUES
from jirha.ops.context import cmd_context
from jirha.ops.estimate import cmd_estimate
from jirha.ops.hygiene import cmd_hygiene
from jirha.ops.issues import (
    cmd_close_subtasks,
    cmd_create,
    cmd_list,
    cmd_show,
    cmd_transition,
    cmd_update,
)
from jirha.ops.meta import cmd_meta
from jirha.ops.quarterly import cmd_quarterly
from jirha.ops.sprint import cmd_short_sprint_status, cmd_sprint_status


def _cmd_jql(args):
    from jirha.api import get_jira

    jira = get_jira()
    issues = jira.search_issues(args.query, maxResults=args.max)
    for issue in issues:
        print(f"{issue.key:20s} [{issue.fields.status}] {issue.fields.summary}")


def main():
    parser = argparse.ArgumentParser(description="Jira helper for RHDH docs")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="List my issues")
    p.add_argument("--open", action="store_true", help="Only open issues")
    p.add_argument("--jql", help="Custom JQL query")
    p.add_argument("--max", type=int, default=50)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="Show issue details")
    p.add_argument("key", help="Issue key")
    p.add_argument("--comments", action="store_true", help="Show all comments (default: last 3)")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("jql", help="Run arbitrary JQL")
    p.add_argument("query", help="JQL query string")
    p.add_argument("--max", type=int, default=50)
    p.set_defaults(func=_cmd_jql)

    p = sub.add_parser("hygiene", help="Full sprint hygiene audit")
    p.add_argument("--max", type=int, default=50)
    p.add_argument("--team", action="store_true", help="Report for entire RHDH Documentation team")
    p.add_argument("--dry-run", action="store_true", help="Report only, no interactive prompts")
    p.set_defaults(func=cmd_hygiene)

    p = sub.add_parser("sprint-status", help="Sprint status by priority swimlanes")
    p.add_argument("--team", action="store_true", help="Report for entire RHDH Documentation team")
    p.add_argument("--refresh", action="store_true", help="Force re-fetch sprint metadata")
    p.set_defaults(func=cmd_sprint_status)

    p = sub.add_parser("short-sprint-status", help="Sprint status showing only open issues")
    p.add_argument("--team", action="store_true", help="Report for entire RHDH Documentation team")
    p.add_argument("--refresh", action="store_true", help="Force re-fetch sprint metadata")
    p.set_defaults(func=cmd_short_sprint_status)

    p = sub.add_parser("update", help="Update fields on an issue with comment")
    p.add_argument("key", help="Issue key")
    p.add_argument("--summary", "-s", help="New summary/title")
    p.add_argument("--type", dest="issue_type", help="Issue type (e.g., Task, Bug, Story)")
    p.add_argument("--desc", help="Description text")
    p.add_argument("--desc-file", help="Read description from file")
    sp_help = ", ".join(str(s) for s in SP_VALUES)
    p.add_argument("--sp", help=f'Story points ({sp_help}, or "auto" to assess from linked PR)')
    p.add_argument("--pr", help="Git Pull Request URL")
    p.add_argument("--priority", choices=["Blocker", "Critical", "Major", "Normal", "Minor"])
    p.add_argument("--fix-version", help="Add fix version (e.g., 1.10.0)")
    p.add_argument("--affects-version", help="Add affects version (e.g., 1.9.0)")
    p.add_argument("--component", help=f"Add component (e.g., {DEFAULT_COMPONENT})")
    p.add_argument("--team", help=f'Set team (e.g., "{DEFAULT_TEAM}")')
    p.add_argument("--add-label", help="Add a label")
    p.add_argument("--remove-label", help="Remove a label")
    p.add_argument("--assignee", help="Set assignee (Jira username)")
    p.add_argument("--link-to", help="Link to another issue key")
    p.add_argument("--link-type", default="relates to", help='Link type (default: "relates to")')
    p.add_argument(
        "--sprint",
        nargs="?",
        const="",
        default=None,
        help="Add to sprint (default: active sprint, or specify name)",
    )
    p.add_argument("--rn-status", help="Release note status")
    p.add_argument("--rn-type", help="Release note type")
    p.add_argument("--rn-text", help="Release note text")
    p.add_argument("--attach", help="Attach a file to the issue")
    p.add_argument("--comment", "-c", help="Comment explaining the changes")
    p.add_argument("--comment-file", "-f", help="Read comment from file")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("transition", help="Transition issue (or list transitions if no status)")
    p.add_argument("key", help="Issue key")
    p.add_argument("status", nargs="?", help="Target status (omit to list available)")
    p.set_defaults(func=cmd_transition)

    p = sub.add_parser("create", help="Create a new issue")
    p.add_argument("project", help="Project key (e.g., RHIDP, RHDHBUGS)")
    p.add_argument("summary", nargs="?", help="Issue summary (required unless --interactive)")
    p.add_argument("--type", default="Task", help="Issue type (default: Task)")
    p.add_argument("--component", help="Component name")
    p.add_argument("--priority", help="Priority name")
    p.add_argument("--parent", help="Parent issue key (for sub-tasks)")
    p.add_argument("--desc", help="Description text")
    p.add_argument("--file", "-f", help="Read description from file")
    p.add_argument("--affects-version", help="Affects version (e.g., 1.10.0)")
    p.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Walk through fields interactively",
    )
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("meta", help="Show project issue types and fields")
    p.add_argument("project", help="Project key (e.g., RHIDP)")
    p.add_argument("--type", help="Show fields for this issue type")
    p.set_defaults(func=cmd_meta)

    p = sub.add_parser("context", help="Show hierarchy context for SP estimation")
    p.add_argument("key", help="Issue key")
    p.add_argument("--json", action="store_true", help="Output as JSON")
    p.add_argument("--refresh", action="store_true", help="Force re-fetch (ignore cache)")
    p.set_defaults(func=cmd_context)

    p = sub.add_parser("close-subtasks", help="Close open subtasks of closed parents")
    p.add_argument("--dry-run", action="store_true", help="Show what would be closed")
    p.set_defaults(func=cmd_close_subtasks)

    p = sub.add_parser("estimate", help="Find issues missing SP or reasoning comments")
    p.add_argument("--max", type=int, default=50)
    p.set_defaults(func=cmd_estimate)

    p = sub.add_parser("quarterly", help="Quarterly activity report for connections review")
    p.add_argument(
        "--quarter",
        help="Target quarter (e.g., Q1-2026). Default: previous quarter.",
    )
    p.add_argument(
        "--level",
        type=int,
        help="Job profile level (1-5). Default: from JOB_PROFILE env.",
    )
    p.set_defaults(func=cmd_quarterly)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
