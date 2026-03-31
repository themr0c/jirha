---
name: hygiene-check-sp
description: Reassess story points from linked PRs — run dry-run, present mismatches, apply chosen changes via jirha update
user_invocable: true
---

# SP Reassessment Workflow

This skill reassesses story points by comparing current SP against what the linked PR suggests.

## Step 1: Run dry-run

Run this command and capture the output:

```bash
jirha hygiene --check-sp --dry-run $ARGUMENTS
```

## Step 2: Parse mismatches

From the output, extract each mismatch entry. Each mismatch has this format:

```
N. KEY currentSP → suggested suggestedSP
   reason
   https://redhat.atlassian.net/browse/KEY
   PR_URL
```

Or for empty SP:

```
N. KEY no SP → suggested suggestedSP
   reason
   https://redhat.atlassian.net/browse/KEY
   PR_URL
```

If no mismatches are found, report "No SP mismatches" and stop.

## Step 3: Present to user

Show the mismatches and ask the user which to apply. Options:
- **all** — apply all suggested changes
- **none** — skip
- **1,2,...** — apply specific numbered entries
- **1=5** — apply entry 1 but override SP to 5 instead of the suggestion

## Step 4: Apply changes

For each accepted mismatch, run:

```bash
jirha update KEY --sp SUGGESTED_SP -c "SP reassessed from PR: REASON"
```

If the user provided an override (e.g., `1=5`), use the override SP instead of the suggested one.

Report each applied change.
