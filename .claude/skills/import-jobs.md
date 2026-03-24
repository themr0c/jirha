# Import Jobs from Google Sheet

Import jobs from the "Phase 3 Jobs" tab of the JTBD spreadsheet into Jira as tasks.

## Prerequisites

The Google Sheet is private. You need the XLSX export saved locally.

### Step 1: Download the spreadsheet

Ask the user to download the entire Google Sheet as XLSX (all tabs included):

**Sheet URL:** https://docs.google.com/spreadsheets/d/1jVKNNUjUgHmhhTUH2wH2iX8pBlUgXaM9Je4pFlgs_9I/edit?gid=1406247735#gid=1406247735

1. Open the sheet in your browser
2. File → Download → Microsoft Excel (.xlsx)
3. Save to `data/` directory

### Step 2: Import

Run the import script:
```bash
scripts/import-jobs "data/[WIP] RHDH TOC mapping - JTBD Effort.xlsx"                          # preview (default)
scripts/import-jobs "data/[WIP] RHDH TOC mapping - JTBD Effort.xlsx" --parent RHIDP-XXXX --exec  # create issues
```

## Column Mapping

**Source:** XLSX tab "Phase 3 Jobs" (27 jobs, rows with empty `Job #` are skipped).

| Column | Jira Field | Mapping |
|---|---|---|
| `Job #` | Label | `job-<N>` for cross-reference |
| `Job` | Summary | Issue title, prefixed with `JTBD -` |
| `Job Statement` | Description | User story in wiki markup (Task template) |
| `Job Category` | Label | Lowercase: `discover`, `plan`, `install`, `configure`, `secure`, `extend`, `develop`, `administer`, `observe`, `upgrade`, `reference`, `get-started` |
| `Job Priority (calculated)` | Priority | Map: High→Major, Medium→Normal, Low→Minor. Empty→Normal |

## What the script creates

For each job row with a non-empty `Job #`:

- **Project:** RHIDP
- **Type:** Task (attached to a parent Epic via `--parent`)
- **Summary:** `JTBD - <Job>`
- **Description:** Job Statement wrapped in Task template
- **Component:** Documentation
- **Labels:** `jtbd`, `job-<N>`, `<category>`
- **Priority:** from `Job Priority` column, default Normal
