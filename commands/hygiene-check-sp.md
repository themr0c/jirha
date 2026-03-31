---
description: Reassess SP from linked PRs and apply chosen changes
---

Run this command and capture the output:

```bash
jirha hygiene --check-sp --dry-run $ARGUMENTS
```

If there are **no mismatches**, report "No SP mismatches" and stop.

If there **are mismatches**, present them in a table and ask the user which to apply. Options:
- **all** — apply all suggested changes
- **none** — skip
- **1,2,...** — apply specific numbered entries
- **1=5** — apply entry 1 but override SP to 5 instead of the suggestion

For each accepted mismatch, run:

```bash
jirha update KEY --sp SUGGESTED_SP -c "SP reassessed from PR: REASON"
```

If the user provided an override (e.g., `1=5`), use the override SP instead of the suggested one.

Report each applied change.
