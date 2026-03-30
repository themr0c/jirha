# jirha Best Practices Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the 1,068-line `scripts/jirha` monolith into a proper Python package, add a Claude plugin with `/jirha-*` slash commands, and add pytest unit tests + ruff linting.

**Architecture:** Extract `jirha/` package with a clean dependency chain: `config.py` → `api.py` → `ops/*.py` → `cli.py`. `scripts/jirha` becomes a thin venv-bootstrap shim. Slash commands live in `.claude/commands/` as markdown files.

**Tech Stack:** Python 3.11, jira>=3.5, pytest, ruff, GitHub Actions.

---

## File Map

| Action | File | Purpose |
|---|---|---|
| Create | `pyproject.toml` | Package definition, entry point, ruff + pytest config |
| Create | `jirha/__init__.py` | Package marker (empty) |
| Create | `jirha/config.py` | Constants, field IDs, env loading |
| Create | `jirha/api.py` | Jira connection, PR metrics, shared query helpers |
| Create | `jirha/ops/__init__.py` | Package marker (empty) |
| Create | `jirha/ops/issues.py` | list, show, create, update, transition, close_subtasks |
| Create | `jirha/ops/sprint.py` | sprint_status, swimlane assignment, velocity/risk |
| Create | `jirha/ops/hygiene.py` | hygiene checks, SP reassessment |
| Create | `jirha/cli.py` | argparse entry point |
| Modify | `scripts/jirha` | Replace with thin venv-bootstrap shim |
| Modify | `scripts/setup.sh` | Add `pip install -e .` step |
| Create | `tests/__init__.py` | Package marker |
| Create | `tests/unit/__init__.py` | Package marker |
| Create | `tests/unit/test_config.py` | Tests for `_load_env_file` |
| Create | `tests/unit/test_sp.py` | Tests for `_pr_metrics` tier/bump/discount logic |
| Create | `tests/unit/test_sprint.py` | Tests for `_assign_swimlanes`, `_business_days`, `_blended_velocity` |
| Create | `tests/unit/test_hygiene.py` | Tests for `_parse_sp_choice` |
| Create | `tests/unit/test_issues.py` | Tests for `_fmt_*`, `_modify_label`, `_build_comment` |
| Create | `tests/integration/__init__.py` | Package marker |
| Create | `.claude/commands/jirha-list.md` | `/jirha-list` slash command |
| Create | `.claude/commands/jirha-show.md` | `/jirha-show` slash command |
| Create | `.claude/commands/jirha-sprint-status.md` | `/jirha-sprint-status` slash command |
| Create | `.claude/commands/jirha-hygiene.md` | `/jirha-hygiene` slash command |
| Create | `.claude/commands/jirha-update.md` | `/jirha-update` slash command |
| Create | `.claude/commands/jirha-transition.md` | `/jirha-transition` slash command |
| Create | `.claude/commands/jirha-create.md` | `/jirha-create` slash command |
| Create | `skills/jira-workflow.md` | Jira conventions skill for Claude |
| Create | `.github/workflows/ci.yml` | CI: ruff + pytest on push |
| Modify | `CLAUDE.md` | Update for new package structure |
| Modify | `.claude/CLAUDE.md` | Add note about slash commands |

---

## Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `jirha/__init__.py`
- Create: `jirha/ops/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/integration/__init__.py`
- Modify: `scripts/setup.sh`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "jirha"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = ["jira>=3.5", "openpyxl>=3.1"]

[project.scripts]
jirha = "jirha.cli:main"

[project.optional-dependencies]
dev = ["pytest", "ruff"]

[tool.pytest.ini_options]
testpaths = ["tests/unit"]
markers = ["integration: requires real Jira credentials (skipped by default)"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I"]
```

- [ ] **Step 2: Create package skeleton**

```bash
touch jirha/__init__.py jirha/ops/__init__.py tests/__init__.py tests/unit/__init__.py tests/integration/__init__.py
```

- [ ] **Step 3: Update setup.sh to install the package**

In `scripts/setup.sh`, replace the venv setup block:
```bash
# OLD
if [[ ! -f venv/bin/activate ]] || [[ requirements.txt -nt venv/bin/activate ]]; then
  python3 -m venv venv
  venv/bin/pip install -q -r requirements.txt
  touch venv/bin/activate
fi
```

With:
```bash
# NEW
if [[ ! -f venv/bin/activate ]] || [[ requirements.txt -nt venv/bin/activate ]] || [[ pyproject.toml -nt venv/bin/activate ]]; then
  python3 -m venv venv
  venv/bin/pip install -q -r requirements.txt
  venv/bin/pip install -q -e .
  touch venv/bin/activate
fi
```

- [ ] **Step 4: Install the package into the venv**

```bash
venv/bin/pip install -e ".[dev]"
```

Expected: `Successfully installed jirha-1.0.0` (or similar). The `jirha` entry point does not yet exist (no `jirha/cli.py`) — that's expected.

- [ ] **Step 5: Verify pytest is available**

```bash
venv/bin/pytest --version
```

Expected: `pytest 8.x.x` (or similar, no errors).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml jirha/__init__.py jirha/ops/__init__.py tests/__init__.py tests/unit/__init__.py tests/integration/__init__.py scripts/setup.sh
git commit -m "chore: scaffold jirha package structure and pyproject.toml"
```

---

## Task 2: config module

**Files:**
- Create: `jirha/config.py`
- Create: `tests/unit/test_config.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_config.py`:
```python
from pathlib import Path

from jirha.config import _load_env_file


def test_load_env_file(tmp_path):
    env = tmp_path / '.env'
    env.write_text('JIRA_EMAIL=test@example.com\nJIRA_API_TOKEN=token123\n')
    result = _load_env_file(env)
    assert result == {'JIRA_EMAIL': 'test@example.com', 'JIRA_API_TOKEN': 'token123'}


def test_load_env_file_missing(tmp_path):
    result = _load_env_file(tmp_path / 'nonexistent.env')
    assert result == {}


def test_load_env_file_skips_comments_and_blanks(tmp_path):
    env = tmp_path / '.env'
    env.write_text('# comment\n\nKEY=value\nANOTHER=val=with=equals\n')
    result = _load_env_file(env)
    assert result == {'KEY': 'value', 'ANOTHER': 'val=with=equals'}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/unit/test_config.py -v
```

Expected: `ImportError: cannot import name '_load_env_file' from 'jirha.config'` (module doesn't exist yet).

- [ ] **Step 3: Create jirha/config.py**

Extract all constants and env-loading from `scripts/jirha` lines 31–71:

```python
"""Constants, field IDs, and environment loading for jirha."""

import os
import sys
from pathlib import Path


SERVER = 'https://redhat.atlassian.net'

# Custom field IDs
CF_STORY_POINTS = 'customfield_10028'
CF_RN_TEXT = 'customfield_10783'
CF_RN_STATUS = 'customfield_10807'
CF_RN_TYPE = 'customfield_10785'
CF_GIT_PR = 'customfield_10875'
CF_TEAM = 'customfield_10001'
CF_SPRINT = 'customfield_10020'
TEAM_RHDH_DOCS_ID = 'ec74d716-af36-4b3c-950f-f79213d08f71-3319'

# Jira conventions
DEFAULT_COMPONENT = 'Documentation'
DEFAULT_TEAM = 'RHDH Documentation'
SP_VALUES = (1, 3, 5, 8, 13)

# Status display ordering
STATUS_ORDER = {'New': 0, 'In Progress': 1, 'Review': 2, 'Closed': 3}

# Swimlane definitions (ordered; first match wins)
SWIMLANES = [
    ('Blocker', lambda i: str(i.fields.priority) == 'Blocker'),
    ('AEM migration', lambda i: 'CQreview_pre-migration' in (i.fields.labels or []) or
        any(c.name == 'AEM Migration' for c in (i.fields.components or []))),
    ('Test-day', lambda i: bool(set(i.fields.labels or []) & {'test-day', 'rhdh-testday'})),
    ('Customer', lambda i: bool(set(i.fields.labels or []) & {'customer', 'RHDH-Customer'})),
    ('Must-have', lambda i: 'must-have' in (i.fields.labels or [])),
    ('Nice-to-have', lambda i: 'nice-to-have' in (i.fields.labels or [])),
    ('Critical', lambda i: str(i.fields.priority) == 'Critical'),
    ('Doc sprint (lower priority)', lambda i: str(i.fields.issuetype) != 'Sub-task'
        and 'Review' not in i.fields.summary),
    ('Reviews', lambda i: str(i.fields.issuetype) == 'Sub-task' and 'Review' in i.fields.summary),
    ('Other', lambda i: True),
]


def _load_env_file(path: Path) -> dict:
    """Parse a .env file and return a dict of key=value pairs."""
    if not path.is_file():
        return {}
    result = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            result[k.strip()] = v.strip()
    return result


# Load .env from repo root and populate os.environ (setdefault: don't override existing)
_repo_root = Path(__file__).resolve().parent.parent
for _k, _v in _load_env_file(_repo_root / '.env').items():
    os.environ.setdefault(_k, _v)

EMAIL = os.environ.get('JIRA_EMAIL')
# Note: EMAIL may be None if JIRA_EMAIL is unset; get_jira() will exit with an error.
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/unit/test_config.py -v
```

Expected:
```
PASSED tests/unit/test_config.py::test_load_env_file
PASSED tests/unit/test_config.py::test_load_env_file_missing
PASSED tests/unit/test_config.py::test_load_env_file_skips_comments_and_blanks
3 passed
```

- [ ] **Step 5: Commit**

```bash
git add jirha/config.py tests/unit/test_config.py
git commit -m "feat: extract config module with constants and env loading"
```

---

## Task 3: api module

**Files:**
- Create: `jirha/api.py`
- Create: `tests/unit/test_sp.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_sp.py`:
```python
from jirha.api import _pr_metrics


def _adoc(path, additions, deletions):
    return {'path': path, 'additions': additions, 'deletions': deletions}


def test_tier_0_under_30_lines():
    files = [_adoc('docs/file.adoc', 10, 5)]
    tier, reason = _pr_metrics(files, commits=1)
    assert tier == 0
    assert '1 .adoc files' in reason


def test_tier_1_30_to_149_lines():
    files = [_adoc('docs/file.adoc', 50, 20)]
    tier, reason = _pr_metrics(files, commits=1)
    assert tier == 1  # 70 lines


def test_tier_2_150_to_399_lines():
    files = [_adoc('docs/file.adoc', 200, 0)]
    tier, reason = _pr_metrics(files, commits=1)
    assert tier == 2


def test_tier_3_400_to_799_lines():
    files = [_adoc('docs/file.adoc', 500, 0)]
    tier, reason = _pr_metrics(files, commits=1)
    assert tier == 3


def test_tier_4_800_plus_lines():
    files = [_adoc('docs/file.adoc', 900, 0)]
    tier, reason = _pr_metrics(files, commits=1)
    assert tier == 4


def test_non_adoc_files_ignored():
    files = [
        {'path': 'images/img.png', 'additions': 0, 'deletions': 0},
        _adoc('docs/file.adoc', 10, 5),
    ]
    tier, reason = _pr_metrics(files, commits=1)
    assert tier == 0


def test_complexity_bump_two_signals():
    # 2 new adoc files + 2 assembly files = 2 signals → tier+1
    files = [
        _adoc('assemblies/a1.adoc', 50, 0),  # new + assembly
        _adoc('assemblies/a2.adoc', 50, 0),  # new + assembly
    ]
    # base: 100 lines = tier 1; 2 new adocs + 2 assemblies → bump to tier 2
    tier, reason = _pr_metrics(files, commits=1)
    assert tier == 2


def test_complexity_bump_six_commits():
    files = [_adoc('docs/f.adoc', 50, 0), _adoc('docs/g.adoc', 50, 0)]
    # base: 100 lines = tier 1; 6 commits alone is 1 signal, need 1 more
    tier_without, _ = _pr_metrics(files, commits=5)
    tier_with, _ = _pr_metrics(files, commits=6)
    # With 2 new adoc files + 6 commits = 2 signals → bump
    assert tier_with == tier_without + 1 or tier_with == 4  # capped at 4


def test_mechanical_discount():
    # 10 files × 4 lines each = 40 lines (tier 1), all mechanical → tier 0
    files = [_adoc(f'docs/file{i}.adoc', 2, 2) for i in range(10)]
    tier, reason = _pr_metrics(files, commits=1)
    assert tier == 0
    assert 'mechanical' in reason


def test_mechanical_requires_more_than_3_files():
    # Only 3 files → not mechanical even if all <= 4 lines
    files = [_adoc(f'docs/file{i}.adoc', 2, 2) for i in range(3)]
    tier, reason = _pr_metrics(files, commits=1)
    assert 'mechanical' not in reason


def test_images_counted():
    files = [
        _adoc('docs/file.adoc', 50, 0),
        {'path': 'images/a.png', 'additions': 0, 'deletions': 0},
        {'path': 'images/b.svg', 'additions': 0, 'deletions': 0},
        {'path': 'images/c.jpg', 'additions': 0, 'deletions': 0},
    ]
    # base: 50 lines = tier 1; 1 new adoc + 3 images = 2 signals → bump to tier 2
    tier, reason = _pr_metrics(files, commits=1)
    assert tier == 2
    assert '3 images' in reason
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/unit/test_sp.py -v
```

Expected: `ImportError: cannot import name '_pr_metrics' from 'jirha.api'`

- [ ] **Step 3: Create jirha/api.py**

Extract from `scripts/jirha` lines 97–210:

```python
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
    CF_TEAM,
    DEFAULT_COMPONENT,
    EMAIL,
    SERVER,
    SP_VALUES,
    STATUS_ORDER,
    TEAM_RHDH_DOCS_ID,
)

# SP tier mapping
_SP_TIERS = dict(zip(SP_VALUES, range(len(SP_VALUES))))
_TIER_TO_SP = dict(enumerate(SP_VALUES))
_ADOC_TIER_THRESHOLDS = [(30, 0), (150, 1), (400, 2), (800, 3)]
_IMAGE_EXTS = ('.png', '.svg', '.jpg', '.gif')

_REVIEW_SUMMARIES = ('[DOC] Peer Review', '[DOC] Technical Review')
REVIEW_FILTER = ''.join(f' AND summary !~ "{s}"' for s in _REVIEW_SUMMARIES)


def get_jira():
    """Return an authenticated JIRA client. Exits if credentials are missing."""
    from jira import JIRA
    if not EMAIL:
        sys.exit('Error: JIRA_EMAIL not set. Add it to .env or export it.')
    token = os.environ.get('JIRA_API_TOKEN')
    if not token:
        sys.exit('Error: JIRA_API_TOKEN not set')
    return JIRA(server=SERVER, basic_auth=(EMAIL, token))


def _parse_jira_date(iso_str):
    """Parse Jira ISO date string (may end with Z) to date."""
    return datetime.fromisoformat(iso_str.replace('Z', '+00:00')).date()


def _issue_sp(issue):
    """Get story points for an issue, or 0."""
    return getattr(issue.fields, CF_STORY_POINTS, None) or 0


def _assignee_name(issue):
    """Return assignee display name or 'Unassigned'."""
    return issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned'


def _assignee_filter(team=False):
    """Return JQL fragment for team-wide or current-user scope."""
    if team:
        return f'Team = "{TEAM_RHDH_DOCS_ID}"'
    return 'assignee = currentUser()'


def _status_sort_key(s):
    return STATUS_ORDER.get(s, len(STATUS_ORDER))


def _warn_in_progress_no_sprint(jira, team=False):
    """Print warning for In Progress issues not in the current sprint."""
    scope = _assignee_filter(team)
    issues = jira.search_issues(
        f'{scope} AND status = "In Progress" AND sprint not in openSprints(){REVIEW_FILTER}',
        maxResults=50,
        fields=f'summary,status,priority,assignee,{CF_STORY_POINTS},{CF_SPRINT}')
    if not issues:
        return
    print('\n## WARNING: In Progress but not in current sprint\n')
    for issue in issues:
        sp = _issue_sp(issue)
        sp_str = f' {int(sp)}SP' if sp else ''
        assignee_str = f' @{_assignee_name(issue)}' if team else ''
        sprints = getattr(issue.fields, CF_SPRINT, None) or []
        future = [s for s in sprints if getattr(s, 'state', '') == 'future']
        closed = [s for s in sprints if getattr(s, 'state', '') == 'closed']
        if future:
            tag = f'FUTURE ({future[0].name})'
        elif closed:
            tag = f'STALE (last: {closed[-1].name}, {len(closed)} prev sprints)'
        else:
            tag = 'BACKLOG (no sprint)'
        print(f'- {issue.key}{sp_str}{assignee_str} [{tag}] — {issue.fields.summary}')
        print(f'  {SERVER}/browse/{issue.key}')


def _pr_metrics(files, commits):
    """Compute PR metrics and return (tier, reason) for SP assessment."""
    adoc_files = [f for f in files if f['path'].endswith('.adoc')]
    adoc_lines = sum(f['additions'] + f['deletions'] for f in adoc_files)
    new_adoc = sum(1 for f in adoc_files if f['deletions'] == 0 and f['additions'] > 5)
    assemblies = sum(1 for f in adoc_files
                     if '/assemblies/' in f['path'] or f['path'].startswith('assemblies/'))
    images = sum(1 for f in files if f['path'].endswith(_IMAGE_EXTS))
    mechanical_files = sum(1 for f in adoc_files if f['additions'] + f['deletions'] <= 4)
    is_mechanical = len(adoc_files) > 3 and mechanical_files / len(adoc_files) > 0.8

    adds = sum(f['additions'] for f in files)
    dels = sum(f['deletions'] for f in files)
    parts = [f'{len(adoc_files)} .adoc files', f'+{adds}/-{dels} lines']
    for val, label in [(new_adoc, 'new topics'), (assemblies, 'assemblies'), (images, 'images')]:
        if val:
            parts.append(f'{val} {label}')
    if is_mechanical:
        parts.append('mechanical')

    tier = 4
    for threshold, t in _ADOC_TIER_THRESHOLDS:
        if adoc_lines < threshold:
            tier = t
            break

    if sum([new_adoc >= 2, assemblies >= 2, images >= 3, commits >= 6]) >= 2:
        tier = min(tier + 1, 4)
    if is_mechanical:
        tier = max(tier - 1, 0)

    return tier, ', '.join(parts)


def _assess_pr_sp(pr_url):
    """Assess suggested SP from a GitHub PR URL. Returns (sp, reason, pr_number) or None."""
    m = re.match(r'https://github\.com/([^/]+/[^/]+)/pull/(\d+)', pr_url)
    if not m:
        return None
    repo, number = m.group(1), m.group(2)
    try:
        result = subprocess.run(
            ['gh', 'pr', 'view', number, '--repo', repo,
             '--json', 'additions,deletions,changedFiles,commits,files'],
            capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return None

    tier, reason = _pr_metrics(data.get('files', []), len(data.get('commits', [])))
    return _TIER_TO_SP[tier], reason, number
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/unit/test_sp.py -v
```

Expected:
```
PASSED tests/unit/test_sp.py::test_tier_0_under_30_lines
PASSED tests/unit/test_sp.py::test_tier_1_30_to_149_lines
PASSED tests/unit/test_sp.py::test_tier_2_150_to_399_lines
PASSED tests/unit/test_sp.py::test_tier_3_400_to_799_lines
PASSED tests/unit/test_sp.py::test_tier_4_800_plus_lines
PASSED tests/unit/test_sp.py::test_non_adoc_files_ignored
PASSED tests/unit/test_sp.py::test_complexity_bump_two_signals
PASSED tests/unit/test_sp.py::test_complexity_bump_six_commits
PASSED tests/unit/test_sp.py::test_mechanical_discount
PASSED tests/unit/test_sp.py::test_mechanical_requires_more_than_3_files
PASSED tests/unit/test_sp.py::test_images_counted
11 passed
```

- [ ] **Step 5: Commit**

```bash
git add jirha/api.py tests/unit/test_sp.py
git commit -m "feat: extract api module with Jira connection and PR metrics"
```

---

## Task 4: ops/sprint module

**Files:**
- Create: `jirha/ops/sprint.py`
- Create: `tests/unit/test_sprint.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_sprint.py`:
```python
import pytest
from datetime import date
from unittest.mock import MagicMock

from jirha.ops.sprint import _assign_swimlanes, _business_days, _blended_velocity


def _make_issue(priority='Normal', labels=None, components=None, issuetype='Task', summary='Test'):
    """Build a mock Jira issue."""
    issue = MagicMock()
    issue.fields.priority = priority         # str(priority) == priority
    issue.fields.labels = labels or []
    comps = []
    for c in (components or []):
        comp = MagicMock()
        comp.name = c
        comps.append(comp)
    issue.fields.components = comps
    issue.fields.issuetype = issuetype       # str(issuetype) == issuetype
    issue.fields.summary = summary
    return issue


class TestAssignSwimLanes:
    def test_blocker(self):
        issue = _make_issue(priority='Blocker')
        result = _assign_swimlanes([issue])
        assert issue in result['Blocker']

    def test_aem_migration_by_label(self):
        issue = _make_issue(labels=['CQreview_pre-migration'])
        result = _assign_swimlanes([issue])
        assert issue in result['AEM migration']

    def test_aem_migration_by_component(self):
        issue = _make_issue(components=['AEM Migration'])
        result = _assign_swimlanes([issue])
        assert issue in result['AEM migration']

    def test_test_day(self):
        issue = _make_issue(labels=['test-day'])
        result = _assign_swimlanes([issue])
        assert issue in result['Test-day']

    def test_rhdh_testday_label(self):
        issue = _make_issue(labels=['rhdh-testday'])
        result = _assign_swimlanes([issue])
        assert issue in result['Test-day']

    def test_customer(self):
        issue = _make_issue(labels=['customer'])
        result = _assign_swimlanes([issue])
        assert issue in result['Customer']

    def test_must_have(self):
        issue = _make_issue(labels=['must-have'])
        result = _assign_swimlanes([issue])
        assert issue in result['Must-have']

    def test_nice_to_have(self):
        issue = _make_issue(labels=['nice-to-have'])
        result = _assign_swimlanes([issue])
        assert issue in result['Nice-to-have']

    def test_critical_priority(self):
        issue = _make_issue(priority='Critical')
        result = _assign_swimlanes([issue])
        assert issue in result['Critical']

    def test_review_subtask(self):
        issue = _make_issue(issuetype='Sub-task', summary='[DOC] Peer Review: something')
        result = _assign_swimlanes([issue])
        assert issue in result['Reviews']

    def test_other_fallthrough(self):
        issue = _make_issue()
        result = _assign_swimlanes([issue])
        assert issue in result['Other']

    def test_first_match_wins(self):
        # Blocker priority + must-have label → Blocker wins (first swimlane)
        issue = _make_issue(priority='Blocker', labels=['must-have'])
        result = _assign_swimlanes([issue])
        assert issue in result['Blocker']
        assert issue not in result['Must-have']

    def test_all_swimlanes_present_in_result(self):
        result = _assign_swimlanes([])
        expected = ['Blocker', 'AEM migration', 'Test-day', 'Customer', 'Must-have',
                    'Nice-to-have', 'Critical', 'Doc sprint (lower priority)', 'Reviews', 'Other']
        assert list(result.keys()) == expected


class TestBusinessDays:
    def test_same_day_weekday(self):
        monday = date(2024, 3, 11)
        assert _business_days(monday, monday) == 1

    def test_full_week(self):
        monday = date(2024, 3, 11)
        friday = date(2024, 3, 15)
        assert _business_days(monday, friday) == 5

    def test_skips_weekend(self):
        friday = date(2024, 3, 15)
        monday = date(2024, 3, 18)
        assert _business_days(friday, monday) == 2

    def test_two_weeks(self):
        monday = date(2024, 3, 11)
        friday2 = date(2024, 3, 22)
        assert _business_days(monday, friday2) == 10


class TestBlendedVelocity:
    def test_no_history_returns_current(self):
        result = _blended_velocity([], current_velocity=5.0, elapsed_days=5, total_days=10)
        assert result == 5.0

    def test_early_sprint_weights_history_heavily(self):
        # <25% elapsed: 90% historical, 10% current
        hist = [('Sprint 1', 50, 10, 5.0)]
        result = _blended_velocity(hist, current_velocity=10.0, elapsed_days=2, total_days=10)
        assert result == pytest.approx(0.9 * 5.0 + 0.1 * 10.0)

    def test_mid_sprint_balanced(self):
        # 25-50% elapsed: 70% historical, 30% current
        hist = [('Sprint 1', 50, 10, 5.0)]
        result = _blended_velocity(hist, current_velocity=10.0, elapsed_days=3, total_days=10)
        assert result == pytest.approx(0.7 * 5.0 + 0.3 * 10.0)

    def test_late_sprint_weights_current(self):
        # >50% elapsed: 40% historical, 60% current
        hist = [('Sprint 1', 50, 10, 5.0)]
        result = _blended_velocity(hist, current_velocity=10.0, elapsed_days=6, total_days=10)
        assert result == pytest.approx(0.4 * 5.0 + 0.6 * 10.0)

    def test_multiple_history_entries_averaged(self):
        hist = [('S1', 40, 10, 4.0), ('S2', 60, 10, 6.0)]  # avg = 5.0
        result = _blended_velocity(hist, current_velocity=0.0, elapsed_days=1, total_days=10)
        assert result == pytest.approx(0.9 * 5.0 + 0.1 * 0.0)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/unit/test_sprint.py -v
```

Expected: `ImportError: cannot import name '_assign_swimlanes' from 'jirha.ops.sprint'`

- [ ] **Step 3: Create jirha/ops/sprint.py**

Extract from `scripts/jirha` lines 575–767:

```python
"""Sprint status command: swimlane assignment, velocity, risk assessment."""

from collections import Counter
from datetime import date, timedelta

from jirha.api import (
    _assignee_filter,
    _assignee_name,
    _issue_sp,
    _parse_jira_date,
    _status_sort_key,
    _warn_in_progress_no_sprint,
    get_jira,
)
from jirha.config import CF_SPRINT, CF_STORY_POINTS, DEFAULT_COMPONENT, SERVER, SWIMLANES


def _assign_swimlanes(issues):
    """Assign each issue to its first matching swimlane. Returns dict of name -> issue list."""
    result = {name: [] for name, _ in SWIMLANES}
    for issue in issues:
        for name, match_fn in SWIMLANES:
            if match_fn(issue):
                result[name].append(issue)
                break
    return result


def _business_days(start, end):
    """Count weekdays (Mon–Fri) between two dates, inclusive of end."""
    return sum(1 for i in range((end - start).days + 1)
               if (start + timedelta(days=i)).weekday() < 5)


def _blended_velocity(hist_velocities, current_velocity, elapsed_days, total_days):
    """Blend historical and current velocity, weighted by sprint progress."""
    if not hist_velocities:
        return current_velocity
    hist_avg = sum(v for _, _, _, v in hist_velocities) / len(hist_velocities)
    elapsed_pct = elapsed_days / total_days if total_days else 0
    if elapsed_pct < 0.25:
        return 0.9 * hist_avg + 0.1 * current_velocity
    elif elapsed_pct < 0.5:
        return 0.7 * hist_avg + 0.3 * current_velocity
    else:
        return 0.4 * hist_avg + 0.6 * current_velocity


def _get_active_sprint(jira):
    """Return active sprint info dict or None."""
    issues = jira.search_issues(
        'assignee = currentUser() AND sprint in openSprints()',
        maxResults=1, fields=CF_SPRINT)
    if not issues:
        return None
    sprint_data = getattr(issues[0].fields, CF_SPRINT, None) or []
    for s in sprint_data:
        if getattr(s, 'state', '') == 'active':
            start = _parse_jira_date(s.startDate)
            end = _parse_jira_date(s.endDate)
            today = date.today()
            return {
                'id': s.id,
                'name': s.name,
                'start': start,
                'end': end,
                'board_id': getattr(s, 'boardId', None),
                'remaining_days': _business_days(today, end),
                'total_days': _business_days(start, end),
            }
    return None


def _historical_velocities(jira, board_id):
    """Return list of (name, closed_sp, days, velocity) for last 3 Documentation sprints."""
    if not board_id:
        return []
    try:
        closed_sprints = jira.sprints(board_id, state='closed')
        doc_sprints = [s for s in closed_sprints if DEFAULT_COMPONENT in s.name][-3:]
        result = []
        for s in doc_sprints:
            s_start = _parse_jira_date(s.startDate)
            s_end = _parse_jira_date(s.endDate)
            s_days = _business_days(s_start, s_end)
            s_issues = jira.search_issues(
                f'assignee = currentUser() AND sprint = {s.id} AND status = Closed',
                maxResults=200, fields=CF_STORY_POINTS)
            s_closed_sp = sum(_issue_sp(i) for i in s_issues)
            s_vel = s_closed_sp / s_days if s_days else 0
            result.append((s.name, int(s_closed_sp), s_days, s_vel))
        return result
    except Exception:
        return []


def _format_issue_line(issue, team=False):
    """Format a single issue as a markdown list item."""
    sp = _issue_sp(issue)
    sp_str = f' {int(sp)}SP' if sp else ''
    labels = issue.fields.labels or []
    label_str = f' [{", ".join(labels)}]' if labels else ''
    assignee_str = f' @{_assignee_name(issue)}' if team else ''
    return f'- {issue.key}{sp_str}{assignee_str}{label_str} — {issue.fields.summary}'


def _print_swimlanes(swimlane_issues, team=False):
    """Print swimlane sections and return (total_by_status, sp_by_status) dicts."""
    total_by_status = {}
    sp_by_status = {}
    for name, _ in SWIMLANES:
        lane_issues = swimlane_issues[name]
        if not lane_issues:
            continue
        lane_total_sp = sum(_issue_sp(i) for i in lane_issues)
        lane_closed_sp = sum(_issue_sp(i) for i in lane_issues if str(i.fields.status) == 'Closed')
        lane_pct = (lane_closed_sp / lane_total_sp * 100) if lane_total_sp else 0
        print(f'\n## {name} — {int(lane_closed_sp)}/{int(lane_total_sp)} SP ({lane_pct:.0f}%)\n')

        by_status = {}
        for issue in lane_issues:
            status = str(issue.fields.status)
            by_status.setdefault(status, []).append(issue)

        for status in sorted(by_status.keys(), key=_status_sort_key):
            print(f'### {status}')
            for issue in by_status[status]:
                print(_format_issue_line(issue, team))
                total_by_status[status] = total_by_status.get(status, 0) + 1
                sp_by_status[status] = sp_by_status.get(status, 0) + _issue_sp(issue)
            print()
    return total_by_status, sp_by_status


def _drop_candidates(swimlane_issues):
    """Return candidate issues to drop, sorted by priority (lowest first) then status."""
    from jirha.api import _status_sort_key
    from jirha.api import _REVIEW_SUMMARIES  # noqa: F401 — imported for clarity

    _REVIEW_SUMMARIES_LOCAL = ('[DOC] Peer Review', '[DOC] Technical Review')
    candidates = []
    for name, _ in reversed(SWIMLANES):
        for issue in swimlane_issues[name]:
            if str(issue.fields.status) == 'Closed':
                continue
            summary = issue.fields.summary or ''
            if any(r in summary for r in _REVIEW_SUMMARIES_LOCAL):
                continue
            sp = _issue_sp(issue)
            candidates.append((_status_sort_key(str(issue.fields.status)), name, issue, sp))
    candidates.sort(key=lambda x: x[0])
    return candidates


def _print_risk_assessment(jira, sprint, closed_sp, remaining_sp, swimlane_issues):
    """Print risk assessment section."""
    if not sprint or not sprint['remaining_days'] or remaining_sp <= 0:
        return
    remaining_days = sprint['remaining_days']
    total_days = sprint['total_days']
    elapsed_days = total_days - remaining_days
    current_velocity = closed_sp / elapsed_days if elapsed_days > 0 else 0

    hist_velocities = _historical_velocities(jira, sprint.get('board_id'))
    velocity = _blended_velocity(hist_velocities, current_velocity, elapsed_days, total_days)
    projected_sp = velocity * remaining_days
    shortfall = remaining_sp - projected_sp

    print('\n## Risk Assessment')
    print(f'**Current sprint velocity:** {current_velocity:.1f} SP/day '
          f'({int(closed_sp)} SP in {elapsed_days} days)')
    if hist_velocities:
        hist_avg = sum(v for _, _, _, v in hist_velocities) / len(hist_velocities)
        print('**Historical velocity (last 3 sprints):**')
        for name, sp, days, vel in hist_velocities:
            print(f'  - {name}: {sp} SP in {days} days = {vel:.1f} SP/day')
        print(f'  - Average: {hist_avg:.1f} SP/day')
    print(f'**Blended velocity:** {velocity:.1f} SP/day')
    print(f'**Projected:** {projected_sp:.0f} SP completable in {remaining_days} remaining days')

    if shortfall <= 0:
        print(f'**Status:** ON TRACK — projected to complete {int(projected_sp)} SP, '
              f'{int(remaining_sp)} SP remaining')
        return

    print(f'**Status:** AT RISK — {int(shortfall)} SP shortfall '
          f'({int(remaining_sp)} SP remaining, ~{int(projected_sp)} SP projected)')
    print(f'\n### Suggested issues to remove ({int(shortfall)}+ SP to cut):')
    cut_sp = 0
    for _, lane, issue, sp in _drop_candidates(swimlane_issues):
        if cut_sp >= shortfall:
            break
        sp_str = f' {int(sp)}SP' if sp else ''
        print(f'- {issue.key}{sp_str} [{lane}] [{issue.fields.status}] — {issue.fields.summary}')
        cut_sp += sp


def cmd_sprint_status(args):
    """Show sprint status grouped by priority swimlanes."""
    jira = get_jira()
    issues = jira.search_issues(
        f'{_assignee_filter(args.team)} AND sprint in openSprints() ORDER BY status ASC',
        maxResults=200,
        fields=f'summary,status,priority,labels,issuetype,components,assignee,'
               f'{CF_STORY_POINTS},{CF_SPRINT}')

    sprint = _get_active_sprint(jira)
    if sprint:
        print(f'# {sprint["name"]}')
        print(f'**Dates:** {sprint["start"]} → {sprint["end"]}  '
              f'**Working days:** {sprint["remaining_days"]} remaining / {sprint["total_days"]} total')

    swimlane_issues = _assign_swimlanes(issues)
    total_by_status, sp_by_status = _print_swimlanes(swimlane_issues, args.team)

    total_sp = sum(sp_by_status.values())
    closed_sp = sp_by_status.get('Closed', 0)
    pct = (closed_sp / total_sp * 100) if total_sp else 0
    parts = ', '.join(
        f'{c} {s}' for s, c in sorted(total_by_status.items(), key=lambda x: _status_sort_key(x[0])))
    sp_parts = ', '.join(
        f'{int(sp)} {s}' for s, sp in sorted(sp_by_status.items(),
                                               key=lambda x: _status_sort_key(x[0])) if sp)
    print(f'**Total:** {sum(total_by_status.values())} issues — {parts}')
    print(f'**SP:** {int(total_sp)} total — {sp_parts}')
    print(f'**Progress:** {int(closed_sp)}/{int(total_sp)} SP ({pct:.0f}%)')

    _print_risk_assessment(jira, sprint, closed_sp, total_sp - closed_sp, swimlane_issues)
    _warn_in_progress_no_sprint(jira, args.team)
```

> **Note on `_drop_candidates`:** The function references `_REVIEW_SUMMARIES` which lives in `api.py`. Import it from there instead of the local definition shown above. Replace the `_REVIEW_SUMMARIES_LOCAL` approach with:
> ```python
> from jirha.api import REVIEW_FILTER  # already accounts for review summaries
> ```
> And filter using the same logic as the rest of the codebase. Simplest fix: hardcode the tuple inline as shown, or import `_REVIEW_SUMMARIES` if you expose it from `api.py`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/unit/test_sprint.py -v
```

Expected: all 17 tests pass.

- [ ] **Step 5: Commit**

```bash
git add jirha/ops/sprint.py tests/unit/test_sprint.py
git commit -m "feat: extract ops/sprint module with swimlanes, velocity, and risk logic"
```

---

## Task 5: ops/hygiene module

**Files:**
- Create: `jirha/ops/hygiene.py`
- Create: `tests/unit/test_hygiene.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_hygiene.py`:
```python
from jirha.ops.hygiene import _parse_sp_choice


def test_parse_all():
    mismatches = [{'key': 'RHIDP-1'}, {'key': 'RHIDP-2'}]
    apply, overrides = _parse_sp_choice('a', mismatches)
    assert apply == {0, 1}
    assert overrides == {}


def test_parse_all_word():
    mismatches = [{'key': 'RHIDP-1'}, {'key': 'RHIDP-2'}]
    apply, overrides = _parse_sp_choice('all', mismatches)
    assert apply == {0, 1}
    assert overrides == {}


def test_parse_individual():
    mismatches = [{'key': 'RHIDP-1'}, {'key': 'RHIDP-2'}]
    apply, overrides = _parse_sp_choice('1', mismatches)
    assert apply == {0}
    assert overrides == {}


def test_parse_multiple():
    mismatches = [{'key': 'RHIDP-1'}, {'key': 'RHIDP-2'}, {'key': 'RHIDP-3'}]
    apply, overrides = _parse_sp_choice('1,3', mismatches)
    assert apply == {0, 2}
    assert overrides == {}


def test_parse_override():
    mismatches = [{'key': 'RHIDP-1'}]
    apply, overrides = _parse_sp_choice('1=5', mismatches)
    assert apply == {0}
    assert overrides == {0: 5}


def test_parse_none_or_unknown():
    mismatches = [{'key': 'RHIDP-1'}]
    apply, overrides = _parse_sp_choice('n', mismatches)
    assert apply == set()
    assert overrides == {}


def test_parse_out_of_range_ignored():
    mismatches = [{'key': 'RHIDP-1'}]
    apply, overrides = _parse_sp_choice('99', mismatches)
    assert apply == set()
    assert overrides == {}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/unit/test_hygiene.py -v
```

Expected: `ImportError: cannot import name '_parse_sp_choice' from 'jirha.ops.hygiene'`

- [ ] **Step 3: Create jirha/ops/hygiene.py**

Extract from `scripts/jirha` lines 813–968:

```python
"""Hygiene check command: missing metadata and SP reassessment."""

import re
import sys
from collections import Counter

from jirha.api import (
    _assess_pr_sp,
    _assignee_filter,
    _assignee_name,
    _issue_sp,
    _warn_in_progress_no_sprint,
    get_jira,
)
from jirha.config import (
    CF_GIT_PR,
    CF_STORY_POINTS,
    DEFAULT_COMPONENT,
    REVIEW_FILTER,
    SERVER,
    SP_VALUES,
)

# Import SP tier mapping from api
from jirha.api import _SP_TIERS  # noqa: F401


def _print_hygiene_report(issue_gaps, team=False):
    """Print hygiene report for issues with missing metadata."""
    if not issue_gaps:
        print('All issues have complete metadata.')
        return
    sorted_issues = sorted(issue_gaps.values(), key=lambda x: -len(x['missing']))
    print(f'Found {len(sorted_issues)} issues with incomplete metadata:\n')
    for entry in sorted_issues:
        issue = entry['issue']
        missing = entry['missing']
        sp = _issue_sp(issue)
        sp_str = f' {int(sp)}SP' if sp else ''
        priority = getattr(issue.fields, 'priority', None) or 'unset'
        components = ', '.join(c.name for c in (issue.fields.components or [])) or 'none'
        assignee_str = f' @{_assignee_name(issue)}' if team else ''
        print(f'{issue.key}{sp_str}{assignee_str} [{issue.fields.status}] '
              f'[{priority}] — {issue.fields.summary}')
        print(f'  {SERVER}/browse/{issue.key}')
        print(f'  Components: {components}')
        print(f'  Missing: {", ".join(missing)}')
        print()

    gap_counts = Counter(m for e in sorted_issues for m in e['missing'])
    print('Summary:')
    for gap, count in gap_counts.most_common():
        print(f'  {gap}: {count} issues')
    print(f'  Total: {len(sorted_issues)} issues need attention')


def _find_sp_mismatches(jira, scope, max_results):
    """Scan issues for SP mismatches against linked PRs. Returns (mismatches, confirmed, skipped)."""
    sp_issues = jira.search_issues(
        f'{scope} AND status not in (Closed, Resolved) AND "Story Points" is not EMPTY'
        f'{REVIEW_FILTER}',
        maxResults=max_results,
        fields=f'summary,status,assignee,{CF_STORY_POINTS},{CF_GIT_PR}')

    mismatches, confirmed, skipped = [], 0, 0
    for issue in sp_issues:
        pr_url = getattr(issue.fields, CF_GIT_PR, None)
        if not pr_url:
            skipped += 1
            continue
        current_sp = int(_issue_sp(issue))
        if current_sp not in _SP_TIERS:
            skipped += 1
            continue
        result = _assess_pr_sp(pr_url)
        if not result:
            skipped += 1
            continue
        suggested_sp, reason, pr_number = result
        if abs(_SP_TIERS[current_sp] - _SP_TIERS[suggested_sp]) >= 2:
            mismatches.append({
                'key': issue.key, 'summary': issue.fields.summary,
                'current_sp': current_sp, 'suggested_sp': suggested_sp,
                'reason': reason, 'pr_url': pr_url, 'pr_number': pr_number,
                'assignee': _assignee_name(issue),
            })
        else:
            confirmed += 1
    return mismatches, confirmed, skipped


def _parse_sp_choice(choice, mismatches):
    """Parse user choice for SP reassessment. Returns (apply_indices, overrides)."""
    if choice in ('a', 'all'):
        return set(range(len(mismatches))), {}
    apply_indices = set()
    overrides = {}
    for part in choice.split(','):
        part = part.strip()
        m = re.match(r'(\d+)=(\d+)', part)
        if m:
            idx, sp_val = int(m.group(1)) - 1, int(m.group(2))
            if sp_val in _SP_TIERS and 0 <= idx < len(mismatches):
                apply_indices.add(idx)
                overrides[idx] = sp_val
        elif part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(mismatches):
                apply_indices.add(idx)
    return apply_indices, overrides


def _sp_reassessment(jira, scope, max_results, team=False, dry_run=False):
    """Reassess story points from linked PRs and optionally apply changes."""
    print('\n## SP Reassessment (from PRs)\n')
    mismatches, confirmed, skipped = _find_sp_mismatches(jira, scope, max_results)

    if not mismatches:
        print(f'No SP mismatches found. ({confirmed} confirmed, {skipped} skipped/no PR)')
        return

    print('### Mismatches found:\n')
    for i, m in enumerate(mismatches, 1):
        assignee_str = f' @{m["assignee"]}' if team else ''
        print(f'{i}. {m["key"]} {m["current_sp"]}SP → suggested {m["suggested_sp"]}SP{assignee_str}')
        print(f'   {m["reason"]}')
        print(f'   {SERVER}/browse/{m["key"]}')
        print(f'   {m["pr_url"]}')
        print()
    print(f'({confirmed} confirmed, {skipped} skipped/no PR)\n')

    if dry_run:
        return

    try:
        choice = input(
            'Apply changes? [a]ll / [n]one / [1,2,...] individual / [1=5] override: '
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print('\nSkipped.')
        return
    if not choice or choice in ('n', 'none'):
        print('No changes applied.')
        return

    apply_indices, overrides = _parse_sp_choice(choice, mismatches)
    for idx in sorted(apply_indices):
        m = mismatches[idx]
        new_sp = overrides.get(idx, m['suggested_sp'])
        comment = f'SP reassessed from PR #{m["pr_number"]}: {m["reason"]}'
        jira.issue(m['key']).update(fields={CF_STORY_POINTS: float(new_sp)})
        jira.add_comment(m['key'], f'Updated SP: {m["current_sp"]} → {new_sp}\n\n{comment}')
        print(f'  → {m["key"]}: {m["current_sp"]}SP → {new_sp}SP')
    print(f'\nApplied {len(apply_indices)} change(s).')


def cmd_hygiene(args):
    """List all issues with missing metadata and summarize what needs fixing."""
    jira = get_jira()
    scope = _assignee_filter(args.team)
    base = f'{scope} AND status not in (Closed, Resolved){REVIEW_FILTER}'
    fields_base = f'summary,status,priority,assignee,components,{CF_STORY_POINTS}'
    checks = [
        ('component',
         f'{base} AND component not in ({DEFAULT_COMPONENT}, "AEM Migration")', fields_base),
        ('team', f'{base} AND Team is EMPTY', fields_base),
        ('priority', f'{base} AND priority is EMPTY', fields_base),
        ('SP', f'{base} AND "Story Points" is EMPTY AND priority != Undefined '
         f'AND type not in (Epic, Feature)', f'{fields_base},issuetype'),
        ('description', f'{base} AND description is EMPTY', fields_base),
    ]

    issue_gaps = {}
    for gap_name, jql, fields in checks:
        issues = jira.search_issues(jql, maxResults=args.max, fields=fields)
        for issue in issues:
            if issue.key not in issue_gaps:
                issue_gaps[issue.key] = {'issue': issue, 'missing': []}
            issue_gaps[issue.key]['missing'].append(gap_name)

    _warn_in_progress_no_sprint(jira, args.team)
    _print_hygiene_report(issue_gaps, args.team)

    if args.check_sp:
        _sp_reassessment(jira, scope, args.max, args.team, args.dry_run)
```

> **Note:** `_SP_TIERS` is a private name in `api.py`. Either expose it as a public `SP_TIERS` dict in `api.py`, or replicate it inline: `_SP_TIERS = {1: 0, 3: 1, 5: 2, 8: 3, 13: 4}`. Use whichever is consistent with what you chose for `api.py`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/unit/test_hygiene.py -v
```

Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add jirha/ops/hygiene.py tests/unit/test_hygiene.py
git commit -m "feat: extract ops/hygiene module with SP reassessment"
```

---

## Task 6: ops/issues module

**Files:**
- Create: `jirha/ops/issues.py`
- Create: `tests/unit/test_issues.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_issues.py`:
```python
from unittest.mock import MagicMock, mock_open, patch

from jirha.ops.issues import (
    _build_comment,
    _fmt_components,
    _fmt_labels,
    _fmt_links,
    _fmt_sprint,
    _fmt_versions,
    _modify_label,
)


class TestFmtVersions:
    def test_empty(self):
        assert _fmt_versions([]) == 'unset'

    def test_single(self):
        v = MagicMock()
        v.name = '1.10.0'
        assert _fmt_versions([v]) == '1.10.0'

    def test_multiple(self):
        v1, v2 = MagicMock(), MagicMock()
        v1.name, v2.name = '1.9.0', '1.10.0'
        assert _fmt_versions([v1, v2]) == '1.9.0, 1.10.0'


class TestFmtComponents:
    def test_empty(self):
        assert _fmt_components([]) == 'unset'

    def test_single(self):
        c = MagicMock()
        c.name = 'Documentation'
        assert _fmt_components([c]) == 'Documentation'


class TestFmtLabels:
    def test_empty(self):
        assert _fmt_labels([]) == 'unset'

    def test_multiple(self):
        assert _fmt_labels(['must-have', 'customer']) == 'must-have, customer'


class TestFmtSprint:
    def test_empty(self):
        assert _fmt_sprint([]) == 'unset'
        assert _fmt_sprint(None) == 'unset'

    def test_active_sprint(self):
        s = MagicMock()
        s.state = 'active'
        s.name = 'Doc Sprint 2024-1'
        assert _fmt_sprint([s]) == 'Doc Sprint 2024-1'

    def test_no_active_returns_last(self):
        s = MagicMock()
        s.state = 'closed'
        s.name = 'Doc Sprint 2024-0'
        assert _fmt_sprint([s]) == 'Doc Sprint 2024-0'


class TestFmtLinks:
    def test_empty(self):
        assert _fmt_links([]) == 'none'

    def test_outward_link(self):
        link = MagicMock()
        link.outwardIssue.key = 'RHIDP-456'
        link.type.outward = 'relates to'
        link.inwardIssue = None
        assert _fmt_links([link]) == 'relates to RHIDP-456'

    def test_inward_link(self):
        link = MagicMock()
        link.outwardIssue = None
        link.inwardIssue.key = 'RHIDP-789'
        link.type.inward = 'is blocked by'
        assert _fmt_links([link]) == 'is blocked by RHIDP-789'


class TestModifyLabel:
    def test_add_new_label(self):
        labels = ['existing']
        result = _modify_label(labels, 'new', add=True)
        assert result == 'Label added: new'
        assert 'new' in labels

    def test_add_existing_label_noop(self):
        labels = ['existing']
        result = _modify_label(labels, 'existing', add=True)
        assert result is None
        assert labels == ['existing']

    def test_remove_label(self):
        labels = ['existing', 'other']
        result = _modify_label(labels, 'existing', add=False)
        assert result == 'Label removed: existing'
        assert 'existing' not in labels

    def test_remove_missing_label_noop(self):
        labels = ['existing']
        result = _modify_label(labels, 'gone', add=False)
        assert result is None


class TestBuildComment:
    def _args(self, comment=None, comment_file=None):
        args = MagicMock()
        args.comment = comment
        args.comment_file = comment_file
        return args

    def test_changes_only(self):
        result = _build_comment(self._args(), ['SP: 5', 'PR: https://example.com'])
        assert 'SP: 5' in result
        assert 'PR: https://example.com' in result

    def test_comment_appended(self):
        result = _build_comment(self._args(comment='my note'), ['SP: 5'])
        assert 'SP: 5' in result
        assert 'my note' in result

    def test_empty_changes_no_comment_returns_none(self):
        result = _build_comment(self._args(), [])
        assert result is None

    def test_comment_file(self):
        args = self._args(comment_file='/tmp/note.txt')
        with patch('builtins.open', mock_open(read_data='file content')):
            result = _build_comment(args, [])
        assert result == 'file content'
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/bin/pytest tests/unit/test_issues.py -v
```

Expected: `ImportError: cannot import name '_fmt_versions' from 'jirha.ops.issues'`

- [ ] **Step 3: Create jirha/ops/issues.py**

Extract from `scripts/jirha` lines 213–571 (all issue commands and their helpers):

```python
"""Issue commands: list, show, create, update, transition, close_subtasks."""

import sys

from jirha.api import (
    _assess_pr_sp,
    _assignee_filter,
    _issue_sp,
    _SP_TIERS,
    _TIER_TO_SP,
    get_jira,
)
from jirha.config import (
    CF_GIT_PR,
    CF_RN_STATUS,
    CF_RN_TEXT,
    CF_RN_TYPE,
    CF_SPRINT,
    CF_STORY_POINTS,
    CF_TEAM,
    DEFAULT_COMPONENT,
    DEFAULT_TEAM,
    SERVER,
    SP_VALUES,
    TEAM_RHDH_DOCS_ID,
)


def _fmt_versions(versions):
    if not versions:
        return 'unset'
    return ', '.join(v.name for v in versions)


def _fmt_components(components):
    if not components:
        return 'unset'
    return ', '.join(c.name for c in components)


def _fmt_team(team):
    if not team:
        return 'unset'
    return getattr(team, 'name', str(team))


def _fmt_labels(labels):
    if not labels:
        return 'unset'
    return ', '.join(labels)


def _fmt_sprint(sprints):
    if not sprints:
        return 'unset'
    active = [s for s in sprints if getattr(s, 'state', '') == 'active']
    if active:
        return active[-1].name
    return sprints[-1].name


def _fmt_links(links):
    if not links:
        return 'none'
    parts = []
    for link in links:
        if hasattr(link, 'outwardIssue') and link.outwardIssue:
            parts.append(f'{link.type.outward} {link.outwardIssue.key}')
        elif hasattr(link, 'inwardIssue') and link.inwardIssue:
            parts.append(f'{link.type.inward} {link.inwardIssue.key}')
    return ', '.join(parts) if parts else 'none'


def _modify_label(labels, label, add=True):
    """Add or remove a label. Returns change message or None."""
    if add:
        if label in labels:
            return None
        labels.append(label)
        return f'Label added: {label}'
    if label not in labels:
        return None
    labels.remove(label)
    return f'Label removed: {label}'


def _resolve_labels(jira, key, fields, add_label, remove_label):
    """Handle --add-label and --remove-label. Mutates fields, returns changes list."""
    if not add_label and not remove_label:
        return []
    labels = fields.get('labels') or list(jira.issue(key, fields='labels').fields.labels or [])
    changes = []
    for label, add in [(add_label, True), (remove_label, False)]:
        if not label:
            continue
        change = _modify_label(labels, label, add)
        if change:
            changes.append(change)
        else:
            print(f'{key} {"already has" if add else "does not have"} label {label}')
    if changes:
        fields['labels'] = labels
    return changes


def _resolve_sp(args, jira):
    """Resolve --sp value. Returns (float_val, change_msg) or None."""
    if not args.sp:
        return None
    if args.sp == 'auto':
        pr_url = args.pr or getattr(jira.issue(args.key, fields=CF_GIT_PR).fields, CF_GIT_PR, None)
        if not pr_url:
            sys.exit('Error: --sp auto requires a PR URL (use --pr or set it on the issue first).')
        result = _assess_pr_sp(pr_url)
        if not result:
            sys.exit(f'Error: could not assess SP from PR: {pr_url}')
        sp_val, reason, _ = result
        return float(sp_val), f'Story points: {sp_val} (auto: {reason})'
    sp_val = int(args.sp)
    if sp_val not in _SP_TIERS:
        sys.exit(f'Error: SP must be {", ".join(str(s) for s in SP_VALUES)}, or "auto".')
    return float(sp_val), f'Story points: {sp_val}'


def _build_comment(args, changes):
    """Assemble comment text from changes list and user-provided comment. Returns str or None."""
    parts = []
    if changes:
        parts.append('Updated:\n- ' + '\n- '.join(changes))
    if args.comment_file:
        with open(args.comment_file) as f:
            parts.append(f.read())
    if args.comment:
        parts.append(args.comment)
    return '\n\n'.join(parts) if parts else None


def _build_fields(args, jira):
    """Build Jira fields dict and changes list from args. Returns (fields, changes)."""
    fields = {}
    changes = []

    simple = [
        ('summary', 'summary', lambda v: (v, f'Summary: {v}')),
        ('issue_type', 'issuetype', lambda v: ({'name': v}, f'Type: {v}')),
        ('pr', CF_GIT_PR, lambda v: (v, f'PR: {v}')),
        ('priority', 'priority', lambda v: ({'name': v}, f'Priority: {v}')),
        ('assignee', 'assignee', lambda v: ({'name': v}, f'Assignee: {v}')),
        ('rn_status', CF_RN_STATUS, lambda v: (v, f'RN Status: {v}')),
        ('rn_type', CF_RN_TYPE, lambda v: (v, f'RN Type: {v}')),
        ('rn_text', CF_RN_TEXT, lambda v: (v, f'RN Text: {v}')),
    ]
    for attr, field_key, transform in simple:
        val = getattr(args, attr, None)
        if val:
            fval, msg = transform(val)
            fields[field_key] = fval
            changes.append(msg)

    if args.desc:
        fields['description'] = args.desc
        changes.append('Description updated')
    elif args.desc_file:
        with open(args.desc_file) as f:
            fields['description'] = f.read()
        changes.append('Description updated from file')

    sp = _resolve_sp(args, jira)
    if sp:
        fields[CF_STORY_POINTS] = sp[0]
        changes.append(sp[1])

    if args.fix_version:
        existing = [{'name': v.name} for v in
                    jira.issue(args.key, fields='fixVersions').fields.fixVersions]
        if not any(v['name'] == args.fix_version for v in existing):
            existing.append({'name': args.fix_version})
            fields['fixVersions'] = existing
            changes.append(f'Fix version: {args.fix_version}')
        else:
            print(f'{args.key} already has fix version {args.fix_version}')

    if getattr(args, 'affects_version', None):
        existing = [{'name': v.name} for v in
                    jira.issue(args.key, fields='versions').fields.versions]
        if not any(v['name'] == args.affects_version for v in existing):
            existing.append({'name': args.affects_version})
            fields['versions'] = existing
            changes.append(f'Affects version: {args.affects_version}')
        else:
            print(f'{args.key} already has affects version {args.affects_version}')

    if args.component:
        existing = [{'name': c.name} for c in
                    jira.issue(args.key, fields='components').fields.components]
        if not any(c['name'] == args.component for c in existing):
            existing.append({'name': args.component})
            fields['components'] = existing
            changes.append(f'Component: {args.component}')
        else:
            print(f'{args.key} already has component {args.component}')

    if args.team:
        if args.team == DEFAULT_TEAM:
            team_id = TEAM_RHDH_DOCS_ID
        else:
            ref = jira.search_issues(f'Team = "{args.team}"', maxResults=1, fields=CF_TEAM)
            if not ref:
                sys.exit(f'Error: Could not find team "{args.team}"')
            team_id = getattr(ref[0].fields, CF_TEAM).id
        fields[CF_TEAM] = team_id
        changes.append(f'Team: {args.team}')

    changes += _resolve_labels(jira, args.key, fields, args.add_label, args.remove_label)
    return fields, changes


def _find_close_transition(jira, issue):
    return next(
        (t['id'] for t in jira.transitions(issue)
         if t['name'].lower() in ('close', 'closed', 'done')), None)


def _find_sprint_id(jira, sprint_name=None):
    if not sprint_name:
        from jirha.ops.sprint import _get_active_sprint
        sprint = _get_active_sprint(jira)
        return sprint['id'] if sprint else None
    issues = jira.search_issues(
        'assignee = currentUser() AND sprint in openSprints()',
        maxResults=1, fields=CF_SPRINT)
    if not issues:
        return None
    for s in (getattr(issues[0].fields, CF_SPRINT, None) or []):
        if sprint_name.lower() in s.name.lower():
            return s.id
    return None


def cmd_list(args):
    jira = get_jira()
    jql = args.jql or 'assignee = currentUser() ORDER BY updated DESC'
    if args.open:
        jql = 'assignee = currentUser() AND status != Closed ORDER BY updated DESC'
    issues = jira.search_issues(jql, maxResults=args.max)
    for issue in issues:
        sp = _issue_sp(issue)
        sp_str = f' [{int(sp)}SP]' if sp else ''
        print(f'{issue.key:20s} [{issue.fields.status}]{sp_str} {issue.fields.summary}')


def cmd_show(args):
    jira = get_jira()
    all_fields = (
        'summary,status,issuetype,priority,fixVersions,components,labels,'
        'reporter,versions,assignee,issuelinks,description,comment,'
        f'{CF_TEAM},{CF_SPRINT},{CF_STORY_POINTS},{CF_GIT_PR},'
        f'{CF_RN_STATUS},{CF_RN_TYPE},{CF_RN_TEXT}'
    )
    issue = jira.issue(args.key, fields=all_fields)
    f = issue.fields
    W = 18

    print(f'{"Status:":<{W}}{f.status}')
    print(f'{"Type:":<{W}}{f.issuetype}')
    print(f'{"Key:":<{W}}{issue.key}')
    print(f'{"Summary:":<{W}}{f.summary}')

    print()
    print(f'{"Priority:":<{W}}{f.priority}')
    print(f'{"Fix versions:":<{W}}{_fmt_versions(f.fixVersions)}')
    print(f'{"Components:":<{W}}{_fmt_components(f.components)}')
    print(f'{"Team:":<{W}}{_fmt_team(getattr(f, CF_TEAM, None))}')
    print(f'{"Labels:":<{W}}{_fmt_labels(f.labels)}')
    print(f'{"Reporter:":<{W}}{f.reporter or "unset"}')
    print(f'{"Affects versions:":<{W}}{_fmt_versions(f.versions)}')

    print()
    print(f'{"Assignee:":<{W}}{f.assignee or "unassigned"}')
    print(f'{"Sprint:":<{W}}{_fmt_sprint(getattr(f, CF_SPRINT, None))}')
    sp = getattr(f, CF_STORY_POINTS, None)
    print(f'{"SP:":<{W}}{str(int(sp)) if sp else "unset"}')
    print(f'{"PR:":<{W}}{getattr(f, CF_GIT_PR, None) or "unset"}')
    print(f'{"Links:":<{W}}{_fmt_links(f.issuelinks)}')

    print()
    print(f'{"RN Status:":<{W}}{getattr(f, CF_RN_STATUS, None) or "unset"}')
    print(f'{"RN Type:":<{W}}{getattr(f, CF_RN_TYPE, None) or "unset"}')
    print(f'{"RN Text:":<{W}}{getattr(f, CF_RN_TEXT, None) or "unset"}')
    print(f'\n{"Link:":<{W}}{SERVER}/browse/{issue.key}')

    desc = f.description or '(empty)'
    print(f'\nDescription:\n{desc}')

    if f.comment and f.comment.comments:
        comments = f.comment.comments
        if args.comments:
            print(f'\nComments ({len(comments)}):')
            for c in comments:
                print(f'  {c.author.displayName}: {c.body}')
        else:
            print(f'\nComments ({len(comments)}):')
            for c in comments[-3:]:
                print(f'  {c.author.displayName}: {c.body[:200]}')


def cmd_update(args):
    jira = get_jira()
    fields, changes = _build_fields(args, jira)

    if args.link_to:
        jira.create_issue_link(args.link_type, args.key, args.link_to)
        changes.append(f'Linked —[{args.link_type}]→ {args.link_to}')

    sprint_name = args.sprint
    if sprint_name is not None:
        sprint_id = _find_sprint_id(jira, sprint_name or None)
        if not sprint_id:
            sys.exit(f'Error: Could not find sprint "{sprint_name or "active"}"')
        jira.add_issues_to_sprint(sprint_id, [args.key])
        changes.append(f'Sprint: {sprint_name or "active"}')

    comment = _build_comment(args, changes)

    if not fields and not comment and sprint_name is None and not args.link_to:
        sys.exit('Error: nothing to update.')

    if fields:
        jira.issue(args.key).update(fields=fields)
        for c in changes:
            print(f'  {c}')

    if comment:
        jira.add_comment(args.key, comment)
        print(f'Updated {args.key} with comment')
    else:
        print(f'Updated {args.key}')


def cmd_transition(args):
    jira = get_jira()
    issue = jira.issue(args.key)
    transitions = jira.transitions(issue)
    if not args.status:
        print(f'{issue.key} [{issue.fields.status}] — available transitions:')
        for t in transitions:
            print(f"  {t['name']}")
        return
    match = next((t for t in transitions if t['name'].lower() == args.status.lower()), None)
    if not match:
        names = ', '.join(t['name'] for t in transitions)
        sys.exit(f"Error: '{args.status}' not available. Options: {names}")
    jira.transition_issue(issue, match['id'])
    print(f'Transitioned {args.key} to {match["name"]}')


def cmd_create(args):
    jira = get_jira()
    fields = {
        'project': {'key': args.project},
        'summary': args.summary,
        'issuetype': {'name': args.type},
    }
    if args.component:
        fields['components'] = [{'name': args.component}]
    if args.priority:
        fields['priority'] = {'name': args.priority}
    if args.parent:
        fields['parent'] = {'key': args.parent}
    if args.file:
        with open(args.file) as f:
            fields['description'] = f.read()
    elif args.desc:
        fields['description'] = args.desc

    issue = jira.create_issue(fields=fields)
    print(f'Created {issue.key}: {args.summary}')
    print(f'{SERVER}/browse/{issue.key}')


def cmd_close_subtasks(args):
    jira = get_jira()
    closed = jira.search_issues(
        'assignee = currentUser() AND status = Closed AND type not in (Sub-task)',
        maxResults=50)
    count = 0
    for parent in closed:
        for st in parent.fields.subtasks:
            st_issue = jira.issue(st.key)
            if str(st_issue.fields.status) == 'Closed':
                continue
            count += 1
            if args.dry_run:
                print(f'Would close {st_issue.key}: {st_issue.fields.summary}')
                continue
            close_id = _find_close_transition(jira, st_issue)
            if close_id:
                jira.transition_issue(st_issue, close_id)
                print(f'Closed {st_issue.key}: {st_issue.fields.summary}')
            else:
                print(f'No close transition for {st_issue.key}')
    if count == 0:
        print('No open subtasks found under closed parents.')
```

> **Note on `_SP_TIERS`:** This imports `_SP_TIERS` from `api.py`. Since the name starts with `_`, it's intentionally private. Either rename it to `SP_TIERS` in `api.py` when you create that module (making it semi-public), or import it with the underscore prefix as shown. Be consistent across ops/issues.py and ops/hygiene.py.

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/unit/test_issues.py -v
```

Expected: all 21 tests pass.

- [ ] **Step 5: Commit**

```bash
git add jirha/ops/issues.py tests/unit/test_issues.py
git commit -m "feat: extract ops/issues module with all issue commands and helpers"
```

---

## Task 7: cli module

**Files:**
- Create: `jirha/cli.py`

- [ ] **Step 1: Create jirha/cli.py**

Extract argparse wiring from `scripts/jirha` lines 979–1067:

```python
"""CLI entry point for jirha."""

import argparse

from jirha.config import DEFAULT_COMPONENT, DEFAULT_TEAM, SP_VALUES
from jirha.ops.hygiene import cmd_hygiene
from jirha.ops.issues import (
    cmd_close_subtasks,
    cmd_create,
    cmd_list,
    cmd_show,
    cmd_transition,
    cmd_update,
)
from jirha.ops.sprint import cmd_sprint_status


def _cmd_jql(args):
    from jirha.api import get_jira
    jira = get_jira()
    issues = jira.search_issues(args.query, maxResults=args.max)
    for issue in issues:
        print(f'{issue.key:20s} [{issue.fields.status}] {issue.fields.summary}')


def main():
    parser = argparse.ArgumentParser(description='Jira helper for RHDH docs')
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('list', help='List my issues')
    p.add_argument('--open', action='store_true', help='Only open issues')
    p.add_argument('--jql', help='Custom JQL query')
    p.add_argument('--max', type=int, default=50)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser('show', help='Show issue details')
    p.add_argument('key', help='Issue key')
    p.add_argument('--comments', action='store_true', help='Show all comments (default: last 3)')
    p.set_defaults(func=cmd_show)

    p = sub.add_parser('jql', help='Run arbitrary JQL')
    p.add_argument('query', help='JQL query string')
    p.add_argument('--max', type=int, default=50)
    p.set_defaults(func=_cmd_jql)

    p = sub.add_parser('hygiene', help='List issues with missing metadata')
    p.add_argument('--max', type=int, default=50)
    p.add_argument('--team', action='store_true',
                   help='Report for entire RHDH Documentation team')
    p.add_argument('--check-sp', action='store_true', help='Reassess SP from linked PRs')
    p.add_argument('--dry-run', action='store_true', help='Show SP mismatches without prompting')
    p.set_defaults(func=cmd_hygiene)

    p = sub.add_parser('sprint-status', help='Sprint status by priority swimlanes')
    p.add_argument('--team', action='store_true',
                   help='Report for entire RHDH Documentation team')
    p.set_defaults(func=cmd_sprint_status)

    p = sub.add_parser('update', help='Update fields on an issue with comment')
    p.add_argument('key', help='Issue key')
    p.add_argument('--summary', '-s', help='New summary/title')
    p.add_argument('--type', dest='issue_type', help='Issue type (e.g., Task, Bug, Story)')
    p.add_argument('--desc', help='Description text')
    p.add_argument('--desc-file', help='Read description from file')
    sp_help = ', '.join(str(s) for s in SP_VALUES)
    p.add_argument('--sp', help=f'Story points ({sp_help}, or "auto" to assess from linked PR)')
    p.add_argument('--pr', help='Git Pull Request URL')
    p.add_argument('--priority', choices=['Blocker', 'Critical', 'Major', 'Normal', 'Minor'])
    p.add_argument('--fix-version', help='Add fix version (e.g., 1.10.0)')
    p.add_argument('--affects-version', help='Add affects version (e.g., 1.9.0)')
    p.add_argument('--component', help=f'Add component (e.g., {DEFAULT_COMPONENT})')
    p.add_argument('--team', help=f'Set team (e.g., "{DEFAULT_TEAM}")')
    p.add_argument('--add-label', help='Add a label')
    p.add_argument('--remove-label', help='Remove a label')
    p.add_argument('--assignee', help='Set assignee (Jira username)')
    p.add_argument('--link-to', help='Link to another issue key')
    p.add_argument('--link-type', default='relates to', help='Link type (default: "relates to")')
    p.add_argument('--sprint', nargs='?', const='', default=None,
                   help='Add to sprint (default: active sprint, or specify name)')
    p.add_argument('--rn-status', help='Release note status')
    p.add_argument('--rn-type', help='Release note type')
    p.add_argument('--rn-text', help='Release note text')
    p.add_argument('--comment', '-c', help='Comment explaining the changes')
    p.add_argument('--comment-file', '-f', help='Read comment from file')
    p.set_defaults(func=cmd_update)

    p = sub.add_parser('transition', help='Transition issue (or list transitions if no status)')
    p.add_argument('key', help='Issue key')
    p.add_argument('status', nargs='?', help='Target status (omit to list available)')
    p.set_defaults(func=cmd_transition)

    p = sub.add_parser('create', help='Create a new issue')
    p.add_argument('project', help='Project key (e.g., RHIDP, RHDHBUG)')
    p.add_argument('summary', help='Issue summary')
    p.add_argument('--type', default='Task', help='Issue type (default: Task)')
    p.add_argument('--component', help='Component name')
    p.add_argument('--priority', help='Priority name')
    p.add_argument('--parent', help='Parent issue key (for sub-tasks)')
    p.add_argument('--desc', help='Description text')
    p.add_argument('--file', '-f', help='Read description from file')
    p.set_defaults(func=cmd_create)

    p = sub.add_parser('close-subtasks', help='Close open subtasks of closed parents')
    p.add_argument('--dry-run', action='store_true', help='Show what would be closed')
    p.set_defaults(func=cmd_close_subtasks)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Verify help output**

```bash
venv/bin/python -m jirha.cli --help
```

Expected:
```
usage: cli.py [-h] {list,show,jql,hygiene,sprint-status,update,transition,create,close-subtasks} ...

Jira helper for RHDH docs
...
```

- [ ] **Step 3: Verify subcommand help**

```bash
venv/bin/python -m jirha.cli update --help
```

Expected: shows all `update` flags including `--sp`, `--pr`, `--sprint`, etc.

- [ ] **Step 4: Commit**

```bash
git add jirha/cli.py
git commit -m "feat: extract cli module as thin argparse entry point"
```

---

## Task 8: Replace scripts/jirha shim

**Files:**
- Modify: `scripts/jirha`

- [ ] **Step 1: Reinstall package so entry point is available**

```bash
venv/bin/pip install -e .
```

Expected: `Successfully installed jirha-1.0.0` with no errors. `venv/bin/jirha` now exists.

- [ ] **Step 2: Verify the installed entry point works**

```bash
venv/bin/jirha --help
```

Expected: same help output as Task 7 Step 2.

- [ ] **Step 3: Replace scripts/jirha with shim**

Overwrite `scripts/jirha` entirely with:

```python
#!/usr/bin/env python3
"""Thin shim: bootstraps repo venv, then delegates to the installed jirha CLI."""

import os
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent
_venv_python = _repo_root / 'venv' / 'bin' / 'python'

if _venv_python.is_file() and Path(sys.executable).resolve() != _venv_python.resolve():
    # Re-exec under venv Python, running the installed jirha entry point
    _venv_jirha = _venv_python.parent / 'jirha'
    os.execv(str(_venv_python), [str(_venv_python), str(_venv_jirha)] + sys.argv[1:])

# Already running under venv — delegate directly
from jirha.cli import main  # noqa: E402

main()
```

Make it executable:
```bash
chmod +x scripts/jirha
```

- [ ] **Step 4: Smoke test via symlink**

```bash
~/bin/jirha --help
```

Expected: same help output as before.

- [ ] **Step 5: Run full unit test suite to confirm nothing broke**

```bash
venv/bin/pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/jirha
git commit -m "refactor: replace scripts/jirha monolith with thin venv-bootstrap shim"
```

---

## Task 9: Linting

**Files:**
- No new files; fix existing code.

- [ ] **Step 1: Check for lint errors**

```bash
venv/bin/ruff check .
```

Review all reported errors. Common issues to expect:
- `I001` — import order (ruff will auto-fix)
- `E501` — lines over 100 chars (fix manually)
- `F401` — unused imports (remove them)

- [ ] **Step 2: Auto-fix import ordering**

```bash
venv/bin/ruff check . --fix
```

- [ ] **Step 3: Format code**

```bash
venv/bin/ruff format .
```

- [ ] **Step 4: Re-run check to confirm clean**

```bash
venv/bin/ruff check .
```

Expected: no output (zero errors).

- [ ] **Step 5: Run tests to confirm formatting didn't break anything**

```bash
venv/bin/pytest -v
```

Expected: all tests still pass.

- [ ] **Step 6: Commit**

```bash
git add -u
git commit -m "style: apply ruff linting and formatting"
```

---

## Task 10: Claude slash commands and skill

**Files:**
- Create: `.claude/commands/jirha-list.md`
- Create: `.claude/commands/jirha-show.md`
- Create: `.claude/commands/jirha-sprint-status.md`
- Create: `.claude/commands/jirha-hygiene.md`
- Create: `.claude/commands/jirha-update.md`
- Create: `.claude/commands/jirha-transition.md`
- Create: `.claude/commands/jirha-create.md`
- Create: `skills/jira-workflow.md`

- [ ] **Step 1: Create command files**

Each file in `.claude/commands/` defines a slash command. `$ARGUMENTS` is replaced by whatever the user types after the command name.

`.claude/commands/jirha-list.md`:
```markdown
Run the following command and show its complete output:

```bash
jirha list $ARGUMENTS
```

If the command fails, show the error.
```

`.claude/commands/jirha-show.md`:
```markdown
Run the following command and show its complete output:

```bash
jirha show $ARGUMENTS
```

If the command fails, show the error.
```

`.claude/commands/jirha-sprint-status.md`:
```markdown
Run the following command and show its complete output:

```bash
jirha sprint-status $ARGUMENTS
```

If the command fails, show the error.
```

`.claude/commands/jirha-hygiene.md`:
```markdown
Run the following command and show its complete output:

```bash
jirha hygiene $ARGUMENTS
```

If the command fails, show the error.
```

`.claude/commands/jirha-update.md`:
```markdown
Run the following command and show its complete output:

```bash
jirha update $ARGUMENTS
```

If the command fails, show the error.
```

`.claude/commands/jirha-transition.md`:
```markdown
Run the following command and show its complete output:

```bash
jirha transition $ARGUMENTS
```

If the command fails, show the error.
```

`.claude/commands/jirha-create.md`:
```markdown
Run the following command and show its complete output:

```bash
jirha create $ARGUMENTS
```

If the command fails, show the error.
```

- [ ] **Step 2: Create skills/jira-workflow.md**

```bash
mkdir -p skills
```

Create `skills/jira-workflow.md`:
```markdown
---
name: jira-workflow
description: Jira conventions, field IDs, SP heuristics, and sprint format for RHDH docs workflow
type: reference
---

## Jira Instance

Server: https://redhat.atlassian.net
Project: RHIDP (tasks, epics), RHDHBUG (bugs)

## Custom Field IDs

| Field | ID | Notes |
|---|---|---|
| Story Points | `customfield_10028` | Float value |
| Release Note Text | `customfield_10783` | |
| Release Note Status | `customfield_10807` | |
| Release Note Type | `customfield_10785` | |
| Git Pull Request | `customfield_10875` | |
| Docs Pull Request | `customfield_10964` | |
| Team | `customfield_10001` | Requires `{id: ...}` format |
| Sprint | `customfield_10020` | List of PropertyHolder objects |

## Conventions

- Component: Documentation (default)
- Team: RHDH Documentation
- Story points: 1, 3, 5, 8, 13

## SP Heuristics (--sp auto)

Base tier from .adoc line volume (additions + deletions):

| Lines changed | Tier | SP |
|---|---|---|
| < 30 | 0 | 1 |
| 30–149 | 1 | 3 |
| 150–399 | 2 | 5 |
| 400–799 | 3 | 8 |
| 800+ | 4 | 13 |

**Complexity bumps** (tier +1 if 2+ signals present):
- 2+ new .adoc files (no deletions, >5 lines added)
- 2+ assembly files changed
- 3+ images added/changed
- 6+ commits

**Mechanical discount** (tier -1): if >80% of .adoc files have ≤4 lines changed and there are 4+ .adoc files.

SP mismatches of <2 tiers are ignored as noise (hygiene --check-sp).

## Sprint Status Swimlane Order

Blocker → AEM migration → Test-day → Customer → Must-have → Nice-to-have → Critical → Doc sprint (lower priority) → Reviews → Other

Each issue assigned to first matching swimlane. Risk assessment uses blended velocity (historical avg last 3 sprints + current, weighted by elapsed sprint %).

## Post-PR Workflow

After `gh pr create` or `gh pr edit`:
1. `jirha update KEY --pr <PR_URL> --sp auto -c "summary of changes"`
2. If Jira description is empty/boilerplate, populate with the template below.

## Jira Description Templates (wiki markup)

### Task (RHIDP project)
```
h3. Task
As a documentation engineer working on RHDH, I want to <ACTION> so that <OUTCOME>.

h3. Background
<DESCRIPTION OF CHANGES: what should be done and why>

h3. Dependencies and Blockers
<FROM PR OR "None.">

h3. QE impacted work
<FROM PR OR "None.">

h3. Documentation impacted work
<FILES CHANGED SUMMARY>

h3. Acceptance Criteria
<CHECKLIST ITEMS FROM PR, using (/) for completed>
```

### Epic (RHIDP project)
```
h1. EPIC Goal
<What are we trying to solve?>

h2. Background/Feature Origin
<Why is this important?>

h2. User Scenarios
<User scenarios>

h2. Dependencies (internal and external)
<Dependencies>

h2. Acceptance Criteria
(?) Release Enablement/Demo
(?) DEV - Upstream code and tests merged
(?) DEV - Upstream documentation merged
(?) DEV - Downstream build attached to advisory
(?) QE - Test plans in Playwright
(?) QE - Automated tests merged
(?) DOC - Downstream documentation merged
```
```

- [ ] **Step 3: Update .claude/settings.json to allow the commands directory**

The `settings.json` already allows `Bash(jirha:*)`. No changes needed — the slash commands call `jirha` via Bash, which is already allowed.

- [ ] **Step 4: Commit**

```bash
git add .claude/commands/ skills/
git commit -m "feat: add Claude slash commands and jira-workflow skill"
```

---

## Task 11: CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create .github/workflows/ci.yml**

```bash
mkdir -p .github/workflows
```

Create `.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
    branches: ["**"]
  pull_request:

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Lint (ruff)
        run: ruff check .

      - name: Format check (ruff)
        run: ruff format --check .

      - name: Test (unit tests only)
        run: pytest
```

- [ ] **Step 2: Verify CI config is valid YAML**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && echo "Valid YAML"
```

Expected: `Valid YAML`

- [ ] **Step 3: Run lint + tests locally to confirm CI will pass**

```bash
venv/bin/ruff check . && venv/bin/ruff format --check . && venv/bin/pytest
```

Expected: no errors, all tests pass.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow for ruff and pytest"
```

---

## Task 12: Update documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `.claude/CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md**

Replace the `## Architecture` section in `CLAUDE.md` to reflect the new package structure:

```markdown
## Architecture

**Package structure** — `jirha/` Python package with a clean dependency chain:
- `config.py` — constants, field IDs, `.env` loading
- `api.py` — Jira connection (`get_jira()`), PR metrics (`_pr_metrics()`), shared query helpers
- `ops/issues.py` — list, show, create, update, transition, close_subtasks commands
- `ops/sprint.py` — sprint_status, swimlane assignment, velocity/risk assessment
- `ops/hygiene.py` — hygiene checks, SP reassessment
- `cli.py` — argparse entry point (`jirha = jirha.cli:main`)

**scripts/jirha** is a thin shim: bootstraps the repo venv, then delegates to `venv/bin/jirha`.

**Slash commands** are in `.claude/commands/jirha-*.md` and invoke `jirha <subcommand> $ARGUMENTS`.

**Jira conventions skill** is at `skills/jira-workflow.md`.
```

- [ ] **Step 2: Update .claude/CLAUDE.md**

Add a note below the command table:

```markdown
## Slash commands

Each `jirha` subcommand is also available as a slash command in Claude:
`/jirha-list`, `/jirha-show KEY`, `/jirha-sprint-status`, `/jirha-hygiene`,
`/jirha-update KEY ...`, `/jirha-transition KEY`, `/jirha-create PROJECT SUMMARY`
```

- [ ] **Step 3: Run full test suite one final time**

```bash
venv/bin/pytest -v && venv/bin/ruff check .
```

Expected: all tests pass, no lint errors.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md .claude/CLAUDE.md
git commit -m "docs: update CLAUDE.md for new package structure and slash commands"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Refactor into Python package (config/api/ops/cli) | Tasks 2–7 |
| pyproject.toml with entry point | Task 1 |
| scripts/jirha → thin shim | Task 8 |
| setup.sh updated | Task 1 |
| pytest unit tests for SP heuristics | Task 3 |
| pytest unit tests for swimlane assignment | Task 4 |
| pytest unit tests for hygiene flag logic | Task 5 |
| pytest unit tests for issue helpers | Task 6 |
| pytest unit tests for env loading | Task 2 |
| Integration smoke tests skeleton | Task 1 (files created) |
| ruff linting | Task 9 |
| CI with ruff + pytest | Task 11 |
| Claude slash commands (/jirha-*) | Task 10 |
| Jira workflow skill | Task 10 |
| Update docs | Task 12 |

**All spec sections covered. No gaps.**
