<p align="left">
  <img src="assets/commit-logo-white-red-dot.png" alt="Commit logo" width="142">
</p>

# Commit GCP API Keys Discover

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://ssh.cloud.google.com/cloudshell/open?cloudshell_git_repo=https://github.com/commitgcp/gcp-apikeys-inspector&cloudshell_tutorial=cloudshell/tutorial.md)

Scan a Google Cloud organization for API keys and generate a standalone
Commit-branded HTML report plus optional JSON data. The scanner reads Cloud
Asset Inventory metadata and restrictions only; it never fetches API key secret
values.

## Run With Gemini CLI

This repo uses one agent entrypoint: the Gemini CLI project command
`/gcp-api-keys-discover`.

When Cloud Shell asks whether to trust this repository, approve it. In a trusted
Cloud Shell workspace, the command can use Cloud Shell's already-authenticated
gcloud session as the signed-in user.

Before starting Gemini, verify that gcloud has an active account:

```bash
gcloud auth list --filter="status:ACTIVE" --format="value(account)"
```

If this prints your user email, continue. If it prints nothing, authenticate
first:

```bash
gcloud auth login --update-adc
```

```bash
gemini
```

Then, inside Gemini CLI:

```text
/gcp-api-keys-discover
```

The command first runs a discovery-only check that lists visible organizations
and quota-project candidates from gcloud config, Cloud Shell environment
variables, visible organizations, and project ancestors. Gemini asks which
organization and quota project to use, then runs the scanner with those explicit
values. In Cloud Shell it uses the already-authenticated active gcloud account;
it does not run `gcloud auth application-default login`.

Reports are ephemeral and overwritten on every run:

- HTML report: `reports/index.html`
- JSON data: `reports/report.json`

If Gemini was already open before you pulled these files:

```text
/commands reload
/commands list
```

## Cloud Shell

Use the Open in Cloud Shell button above. When Cloud Shell asks whether to trust
the repository, approve it so the command can use Cloud Shell's
already-authenticated gcloud session. The tutorial asks you to verify auth, then
run:

```bash
gemini
```

Then:

```text
/gcp-api-keys-discover
```

After the report is generated, Gemini starts a local web server rooted at
`reports/`, so Cloud Shell Web Preview opens the HTML report directly instead of
showing the repository directory. If you are still inside Gemini CLI, prefix
shell commands with `!`. Download the files with:

```text
! cloudshell download reports/index.html reports/report.json
```

Or inspect the HTML report with Cloud Shell Web Preview using the port Gemini
prints.

## Required Access

The authenticated user needs:

- `roles/cloudasset.viewer` on the target organization
- `roles/serviceusage.serviceUsageConsumer` on the quota project
- optional: `roles/browser` or equivalent Resource Manager read access for
  project and organization display names

Cloud Asset Inventory must be enabled on the quota project:

```bash
gcloud services enable cloudasset.googleapis.com --project <QUOTA_PROJECT>
```

## Manual Run

From an authenticated Cloud Shell or gcloud session:

```bash
scripts/gcp-api-keys-discover.sh --organization <ORG_ID> --quota-project <QUOTA_PROJECT>
```

Or run the Python scanner directly with the active gcloud account:

```bash
uv sync
uv run python discover.py \
  --organization <ORG_ID> \
  --quota-project <QUOTA_PROJECT> \
  --use-gcloud-auth \
  --output report.html \
  --json-output report.json
```

For local runs that use Application Default Credentials instead:

```bash
uv sync
gcloud auth application-default login
gcloud auth application-default set-quota-project <QUOTA_PROJECT>
uv run python discover.py \
  --organization <ORG_ID> \
  --quota-project <QUOTA_PROJECT> \
  --output report.html \
  --json-output report.json
```

Exit codes:

| Code | Meaning |
|---|---|
| `0` | Scan succeeded without CRITICAL active-key findings. |
| `1` | Scan succeeded and found CRITICAL active-key findings. |
| `2` | Scan failed because of auth, permission, API, or organization issues. |

## Report Features

- Commit-branded standalone HTML
- severity, project, API, and client-restriction filters
- grouping by severity, project, API, or client restriction
- expandable rows with raw restrictions JSON
- optional sanitized JSON for follow-up analysis

## Files

```text
discover.py
gcp_api_keys/
scripts/gcp-api-keys-discover.sh
templates/report.html.j2
assets/commit-logo-*.png
.gemini/commands/gcp-api-keys-discover.toml
cloudshell/tutorial.md
```
