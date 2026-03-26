# Pantheon CLI Reference

`pantheon-cli` automates Red Hat Pantheon docs publishing operations: listing titles, updating build configurations, triggering rebuilds, and publishing releases.

## Prerequisites

1. **Kerberos ticket** — SSO authentication uses Kerberos SPNEGO. Obtain a ticket before running:
   ```bash
   kinit your-id@REDHAT.COM
   ```
   Verify with `klist`. The ticket typically lasts 10 hours.

2. **VPN** — Requires Red Hat VPN for access to `pantheon.cee.redhat.com` and `reef.corp.redhat.com`.

3. **Playwright Firefox** — Installed automatically by `setup.sh`. If needed manually:
   ```bash
   cd ~/src/gh/themr0c/jirha
   venv/bin/playwright install firefox
   ```

4. **JIRA_EMAIL** — Set in `.env` (also used by `jirha`). This email is used for the SSO login form.

## How authentication works

Pantheon uses SAML SSO backed by Kerberos. The script:

1. Launches Firefox with Kerberos SPNEGO enabled (`network.negotiate-auth.trusted-uris: .redhat.com`)
2. Navigates to Pantheon, clicks Login
3. Redirects to `sso.redhat.com`, enters your email, clicks "Log in with company single sign-on"
4. Kerberos auto-completes the authentication
5. Redirects back to Pantheon with a session cookie

The browser session is persisted at `/tmp/pantheon-session/` so subsequent runs reuse the auth. Use `--fresh` to clear it.

A TrustArc cookie consent overlay can block UI interactions. The script force-removes it via JavaScript.

## Commands

### `list` — Discover titles

```bash
pantheon-cli list --version 1.9
pantheon-cli list --version 1.9 --title "Customizing"
pantheon-cli list --version 1.10 --product red_hat_developer_hub
```

Shows all titles with their job states, branches, and content directories.

### `update` — Change build configuration

```bash
# Dry run (default) — shows what would change
pantheon-cli update --version 1.9 --env preview --branch release-1.10

# Execute
pantheon-cli update --version 1.9 --env preview --branch release-1.10 --exec

# Change branch + directory for a specific title, enable, and rebuild
pantheon-cli update --version 1.9 --title "Customizing" --env preview \
  --branch release-1.10 --directory titles/configure_customizing-rhdh \
  --enable --rebuild --exec
```

Options:
- `--branch BRANCH` — Target git branch
- `--directory DIR` — Content directory (keeps current if omitted)
- `--enable` — Enable disabled jobs
- `--rebuild` — Trigger rebuild after config change

### `rebuild` — Trigger builds

```bash
# Dry run
pantheon-cli rebuild --version 1.9 --env preview

# Rebuild all, enabling disabled jobs first
pantheon-cli rebuild --version 1.9 --env preview --enable --exec

# Rebuild one title and wait for completion
pantheon-cli rebuild --version 1.9 --title "About" --env preview --exec --wait

# Custom timeout (seconds)
pantheon-cli rebuild --version 1.9 --env preview --exec --wait --timeout 600
```

### `publish` — Enable and rebuild stage

```bash
# Dry run — show disabled stage jobs
pantheon-cli publish --version 1.9

# Enable all stage jobs
pantheon-cli publish --version 1.9 --exec

# Enable and rebuild
pantheon-cli publish --version 1.9 --exec --rebuild-first --wait
```

## Common options

| Option | Default | Description |
|--------|---------|-------------|
| `--product` | `red_hat_developer_hub` | Pantheon product slug |
| `--version` | (required) | Product version |
| `--env` | `preview` | Environment: `preview` or `stage` |
| `--title` | all | Substring filter (repeatable, OR) |
| `--exec` | off | Execute changes (default is dry-run) |
| `--fresh` | off | Clear session, re-authenticate |
| `--email` | from `JIRA_EMAIL` | SSO email override |

## Architecture

The script drives a real Firefox browser via Playwright to interact with Pantheon's AngularJS frontend. All data operations go through the **Reef API** (`reef.corp.redhat.com/api`) via XHR calls executed in the browser context.

Write operations use Angular's `reefService`, injected via:
```javascript
angular.element(document.body).injector().get('reefService')
```

### Key API methods

| Method | Signature | Notes |
|--------|-----------|-------|
| `updateTitleEnvBuildConfig` | `(uuid, lang, env, {branch, content_directory, content_type})` | Update API uses **snake_case** fields |
| `toggleJenkinsJob` | `(name, disabled)` | `disabled` is boolean: `false` = enable, `true` = disable |
| `startJenkinsJob` | `({jobName: name})` | Takes job name as object property |

### Known gotchas

- **snake_case vs camelCase**: The update API expects `content_directory` and `content_type` (snake_case), but GET responses return `contentDirectory` and `contentType` (camelCase).
- **TrustArc overlay**: A cookie consent overlay from `consent-pref.trustarc.com` blocks UI clicks. The script removes it via `document.querySelectorAll('[class*="truste"]').forEach(e => e.remove())`.
- **Session expiry**: The persistent session at `/tmp/pantheon-session/` may expire. Use `--fresh` to force re-authentication.
- **Headless mode**: Kerberos SPNEGO requires a headed browser. The script always runs headed.
- **Verification lag**: After updating a build config, the GET endpoint may return stale data for a few seconds.
