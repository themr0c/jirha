"""Metadata discovery: list issue types and fields for a project."""

import sys

from jirha.api import _createmeta, get_jira, parse_fields


def cmd_meta(args):
    """Show project metadata: issue types, or fields for a specific type."""
    jira = get_jira()

    try:
        proj = _createmeta(jira, args.project)
    except Exception as e:
        sys.exit(f"Error: could not fetch metadata for {args.project}: {e}")
    if not proj:
        sys.exit(f"Error: project {args.project} not found or not accessible.")

    types = proj["issuetypes"]

    if not args.type:
        print(f"Issue types for {args.project}:\n")
        for t in types:
            tag = " (subtask)" if t.get("subtask") else ""
            print(f"  {t['name']}{tag}")
        return

    # Resolve type name (case-insensitive)
    match = next(
        (t for t in types if t["name"].lower() == args.type.lower()),
        None,
    )
    if not match:
        names = ", ".join(t["name"] for t in types)
        sys.exit(f"Error: '{args.type}' is not valid for {args.project}. Available: {names}")

    fields = parse_fields(match)

    required = [f for f in fields if f["required"]]
    optional = [f for f in fields if not f["required"]]

    print(f"Fields for {args.project} / {match['name']}:\n")

    if required:
        print("Required:")
        for f in required:
            _print_field(f)

    if optional:
        print("\nOptional:")
        for f in optional:
            _print_field(f)


def _print_field(field):
    """Print a single field's metadata."""
    line = f"  {field['name']:<30s} ({field['key']})"
    if field["allowed_values"]:
        vals = field["allowed_values"]
        if len(vals) <= 10:
            line += f"  values: {', '.join(vals)}"
        else:
            line += f"  values: {', '.join(vals[:10])}... ({len(vals)} total)"
    print(line)
