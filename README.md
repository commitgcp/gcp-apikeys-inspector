<p align="left">
  <img src="assets/commit-logo-dark.png" alt="Commit logo" width="142">
</p>

# Commit GCP API Keys Discover

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://ssh.cloud.google.com/cloudshell/open?cloudshell_git_repo=REPLACE_WITH_REPO_URL&cloudshell_tutorial=cloudshell/tutorial.md)

> Replace `REPLACE_WITH_REPO_URL` with this repository's hosted HTTPS Git URL.

Scan a Google Cloud organization for API keys and generate a standalone
Commit-branded HTML report plus optional JSON data. The scanner reads Cloud
Asset Inventory metadata and restrictions only; it never fetches API key secret
values.

## Run With Gemini CLI

This repo uses one agent entrypoint: the Gemini CLI project command
`/gcp-api-keys-discover`.

```bash
gemini
```

Then, inside Gemini CLI:

```text
/gcp-api-keys-discover
```

The command asks for the organization ID and quota project, validates Google
Cloud auth and Cloud Asset Inventory access, runs the scanner, explains the
findings, and offers to start Cloud Shell Web Preview for the HTML report.

If Gemini was already open before you pulled these files:

```text
/commands reload
/commands list
```

## Cloud Shell

Use the Open in Cloud Shell button above. The tutorial only asks you to run:

```bash
gemini
```

Then:

```text
/gcp-api-keys-discover
```

After the report is generated, Gemini will show exact paths under `reports/`.
Download them with:

```bash
cloudshell download reports/<report>.html reports/<report>.json
```

Or preview the HTML report with Cloud Shell Web Preview if Gemini starts the
local Python server.

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

```bash
uv sync
gcloud auth application-default login
gcloud auth application-default set-quota-project <QUOTA_PROJECT>
uv run python discover.py \
  --organization <ORG_ID> \
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
templates/report.html.j2
assets/commit-logo-*.png
.gemini/commands/gcp-api-keys-discover.toml
cloudshell/tutorial.md
```
