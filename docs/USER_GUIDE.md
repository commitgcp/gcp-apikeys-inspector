# GCP API Keys Discover User Guide

This utility scans a Google Cloud organization for `apikeys.googleapis.com/Key`
assets, scores each key by restriction posture, and writes a standalone
Commit-branded HTML report. It does not fetch API key secret values.

## What You Need

- Python 3.10 or newer.
- `uv` for Python dependency management.
- `gcloud` installed and initialized.
- A quota project where `cloudasset.googleapis.com` is enabled.
- The numeric Google Cloud organization ID to scan.

Set these variables before running the examples:

```bash
export ORG_ID="123456789012"
export QUOTA_PROJECT="my-quota-project"
```

## Required Permissions

The authenticated principal must have these permissions:

| Purpose | Required permission | Common predefined role |
|---|---|---|
| Search API key assets at organization scope | `cloudasset.assets.searchAllResources` on `organizations/$ORG_ID` | `roles/cloudasset.viewer` |
| Use the quota/billing project for API calls | `serviceusage.services.use` on `$QUOTA_PROJECT` | `roles/serviceusage.serviceUsageConsumer` |

For richer labels in the report, also grant:

| Purpose | Permission | Common predefined role |
|---|---|---|
| Resolve project IDs/display names | `resourcemanager.projects.get` on the relevant projects or parent hierarchy | `roles/browser` |
| Resolve organization display name | `resourcemanager.organizations.get` on the organization | `roles/resourcemanager.organizationViewer` or `roles/browser` |

If an administrator is granting access to a user account:

```bash
export MEMBER="user:person@example.com"

gcloud organizations add-iam-policy-binding "$ORG_ID" \
  --member="$MEMBER" \
  --role="roles/cloudasset.viewer"

gcloud projects add-iam-policy-binding "$QUOTA_PROJECT" \
  --member="$MEMBER" \
  --role="roles/serviceusage.serviceUsageConsumer"

# Optional, for project and organization display names.
gcloud organizations add-iam-policy-binding "$ORG_ID" \
  --member="$MEMBER" \
  --role="roles/browser"
```

## Enable the API

Enable Cloud Asset Inventory on the quota project:

```bash
gcloud services enable cloudasset.googleapis.com --project "$QUOTA_PROJECT"
```

Validate it is enabled:

```bash
gcloud services list \
  --enabled \
  --project "$QUOTA_PROJECT" \
  --filter="config.name=cloudasset.googleapis.com" \
  --format="value(config.name)"
```

The command should print `cloudasset.googleapis.com`.

## Authenticate Locally

The Python client libraries use Application Default Credentials (ADC), so run:

```bash
gcloud auth login
gcloud auth application-default login
gcloud auth application-default set-quota-project "$QUOTA_PROJECT"
gcloud config set project "$QUOTA_PROJECT"
```

Validate ADC can issue a token:

```bash
gcloud auth application-default print-access-token >/dev/null && echo "ADC token OK"
```

Validate the same account can search Cloud Asset Inventory:

```bash
gcloud asset search-all-resources \
  --scope="organizations/$ORG_ID" \
  --asset-types="apikeys.googleapis.com/Key" \
  --limit=1 \
  --billing-project="$QUOTA_PROJECT" \
  --format="table(name,assetType,project)"
```

No rows is still a valid result if the organization has no API keys. A
permission or API-enablement error must be fixed before running the utility.

## Run the Utility

From the repository root:

```bash
uv sync
uv run python discover.py \
  --organization "$ORG_ID" \
  --output "report.html" \
  --json-output "report.json"
```

Open the report:

```bash
open report.html
```

On Linux or Cloud Shell:

```bash
python3 -m http.server 8080
```

Then use Cloud Shell Web Preview or open `http://localhost:8080/report.html`.

## Output Files

- `report.html`: standalone Commit-branded report with search, filters, grouping,
  severity cards, project pivots, expandable rows, findings, and raw restrictions.
- `report.json`: optional sanitized data for agents or downstream analysis.

The JSON and HTML include metadata and restrictions, but not API key secret
values.

## Useful Flags

| Flag | Purpose |
|---|---|
| `--organization`, `--org` | Numeric org ID, or `organizations/<id>`. Required. |
| `--output` | HTML output path. Defaults to `report.html`. |
| `--json-output` | Optional sanitized JSON report path. |
| `--no-resolve-projects` | Skip Resource Manager calls if project-name lookup is denied or slow. |
| `--exit-zero` | Return exit code 0 even when CRITICAL findings are present. |

Exit codes:

| Code | Meaning |
|---|---|
| `0` | Scan succeeded, no CRITICAL active-key findings, or `--exit-zero` was used. |
| `1` | Scan succeeded and at least one active key is CRITICAL. |
| `2` | Scan failed due to auth, permission, invalid org, or API-enablement errors. |

## How to Review Results

Start with the severity cards:

- `CRITICAL`: unrestricted key. Treat as urgent.
- `HIGH`: no API target restriction, wildcard HTTP referrer, or open server IP range.
- `MEDIUM`: API targets exist, but no client restriction is set.
- `INFO`: soft-deleted key or broad service target with no method filter.
- `OK`: no findings from the current rubric.

Then use the report controls:

- Filter by severity to focus remediation.
- Filter or group by project to find owner teams.
- Filter or group by API to find broad product exposure.
- Filter or group by client restriction to find keys missing IP/referrer/app limits.
- Expand rows to inspect raw restriction JSON before changing a key.

## Cloud Shell Tutorial

This repository includes a Cloud Shell tutorial at
`cloudshell/tutorial.md`.

From Cloud Shell, launch it from this checkout:

```bash
cloudshell launch-tutorial cloudshell/tutorial.md
```

For a hosted repository, use an Open in Cloud Shell URL like this:

```text
https://ssh.cloud.google.com/cloudshell/open?cloudshell_git_repo=REPLACE_WITH_REPO_URL&cloudshell_tutorial=cloudshell/tutorial.md
```

Replace `REPLACE_WITH_REPO_URL` with the HTTPS Git URL of this repository.
