---
name: gcp-api-keys-discover
description: Run and analyze this repository's Google Cloud API key discovery utility. Use when asked to scan a GCP organization for API keys, generate Commit-branded HTML/JSON reports, validate required authentication and IAM, or summarize API key findings by severity, project, API target, and client restriction.
---

# GCP API Keys Discover

Use this skill from the repository root. Always use `uv` for Python dependencies
and commands. Do not use `pip`.

## Inputs to Confirm

Confirm these before running a scan:

- `ORG_ID`: numeric Google Cloud organization ID, or `organizations/<id>`.
- `QUOTA_PROJECT`: project used for Cloud Asset Inventory quota/billing.
- Output location. Default to a timestamped file under `reports/`.

If `ORG_ID` is missing, ask for it. If `QUOTA_PROJECT` is missing, inspect
`gcloud config get-value project`; if that is empty, ask for it.

## Required Access

The authenticated principal needs:

- `cloudasset.assets.searchAllResources` on the organization, commonly
  `roles/cloudasset.viewer`.
- `serviceusage.services.use` on the quota project, commonly
  `roles/serviceusage.serviceUsageConsumer`.
- Optional for richer labels: `resourcemanager.projects.get` and
  `resourcemanager.organizations.get`, commonly `roles/browser` on the
  hierarchy.

## Preflight

Run:

```bash
uv sync
gcloud auth list --filter="status:ACTIVE" --format="value(account)"
gcloud auth application-default print-access-token >/dev/null
gcloud auth application-default set-quota-project "$QUOTA_PROJECT"
gcloud services list --enabled --project "$QUOTA_PROJECT" --filter="config.name=cloudasset.googleapis.com" --format="value(config.name)"
gcloud asset search-all-resources --scope="organizations/$ORG_ID" --asset-types="apikeys.googleapis.com/Key" --limit=1 --billing-project="$QUOTA_PROJECT" --format="table(name,assetType,project)"
```

If Cloud Asset Inventory is not enabled and the user has permission, run:

```bash
gcloud services enable cloudasset.googleapis.com --project "$QUOTA_PROJECT"
```

If ADC is not configured, ask the user to complete:

```bash
gcloud auth application-default login
```

## Run

Generate both HTML and JSON unless the user asks for HTML only:

```bash
mkdir -p reports
RUN_ID="$(date -u +%Y%m%d-%H%M%S)"
uv run python discover.py \
  --organization "$ORG_ID" \
  --output "reports/api-keys-${ORG_ID}-${RUN_ID}.html" \
  --json-output "reports/api-keys-${ORG_ID}-${RUN_ID}.json"
```

Exit code `1` means the scan succeeded and found at least one CRITICAL active
key. Treat that as a successful run with urgent findings, not as a tool failure.
Exit code `2` means the scan did not complete.

## Analyze

Prefer the JSON report for analysis. Summarize:

- Total active and soft-deleted keys.
- Severity counts.
- CRITICAL and HIGH keys first, grouped by project and then API target.
- Keys with no API target restriction.
- Keys with no client restriction.
- Wildcard HTTP referrers or open server IP ranges.
- Projects or APIs with concentrated findings.
- Permission gaps, if project or organization display names could not be resolved.

Do not claim that the secret API key values were checked; this utility only
reads metadata and restrictions from Cloud Asset Inventory.

## Report Back

Return:

- Paths to the generated HTML and JSON files.
- Whether the run completed, and the exit code if non-zero.
- A concise risk summary.
- Concrete remediation next steps, preserving uncertainty where ownership or
  business intent is not visible from the report.
