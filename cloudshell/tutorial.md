# Scan GCP API Keys with Commit Report

This tutorial runs `gcp-api-keys-discover` from Cloud Shell and creates a
Commit-branded HTML report for a Google Cloud organization.

## Confirm Your Inputs

Set the organization ID and quota project:

```bash
export ORG_ID="123456789012"
export QUOTA_PROJECT="my-quota-project"
```

Replace both values before continuing. `ORG_ID` is the numeric organization ID,
not the display name.

## Confirm Your Identity

Cloud Shell normally starts with a signed-in Google account. Confirm the active
account:

```bash
gcloud auth list --filter="status:ACTIVE" --format="value(account)"
```

Confirm Application Default Credentials can issue a token:

```bash
gcloud auth application-default print-access-token >/dev/null && echo "ADC token OK"
```

If that fails, run:

```bash
gcloud auth application-default login
```

Set the quota project used by Google client libraries:

```bash
gcloud auth application-default set-quota-project "$QUOTA_PROJECT"
gcloud config set project "$QUOTA_PROJECT"
```

## Enable Cloud Asset Inventory

Enable the required API on the quota project:

```bash
gcloud services enable cloudasset.googleapis.com --project "$QUOTA_PROJECT"
```

Validate that it is enabled:

```bash
gcloud services list \
  --enabled \
  --project "$QUOTA_PROJECT" \
  --filter="config.name=cloudasset.googleapis.com" \
  --format="value(config.name)"
```

The command should print `cloudasset.googleapis.com`.

## Validate Permissions

The signed-in principal must have:

- `roles/cloudasset.viewer` on `organizations/$ORG_ID`.
- `roles/serviceusage.serviceUsageConsumer` on `$QUOTA_PROJECT`.
- Optional: `roles/browser` on the organization, folder, or projects for display names.

Run a one-result Cloud Asset Inventory query:

```bash
gcloud asset search-all-resources \
  --scope="organizations/$ORG_ID" \
  --asset-types="apikeys.googleapis.com/Key" \
  --limit=1 \
  --billing-project="$QUOTA_PROJECT" \
  --format="table(name,assetType,project)"
```

No rows can be valid. Permission, quota, or API errors must be fixed before the
scan can run.

## Prepare Python Dependencies

Install `uv` if Cloud Shell does not already have it:

```bash
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
uv --version
```

Sync this repository's Python environment:

```bash
uv sync
```

## Run the Scan

Create a timestamped output directory and run the scanner:

```bash
mkdir -p reports
RUN_ID="$(date -u +%Y%m%d-%H%M%S)"

uv run python discover.py \
  --organization "$ORG_ID" \
  --output "reports/api-keys-${ORG_ID}-${RUN_ID}.html" \
  --json-output "reports/api-keys-${ORG_ID}-${RUN_ID}.json"
```

The scan returns exit code `1` when CRITICAL active-key findings exist. That
means the report was generated successfully and remediation is needed.

## View the HTML Report

Start a local web server:

```bash
python3 -m http.server 8080
```

Use Cloud Shell Web Preview on port `8080`, then open the generated file under
the `reports/` directory.

## Review the Findings

Use the HTML report controls to:

- Filter by severity for urgent remediation.
- Group by project to identify owners.
- Group by API target to find broad product exposure.
- Group by client restriction to find keys missing IP, referrer, Android, or iOS restrictions.
- Expand a row to inspect the raw restrictions JSON.

Use the JSON file for agent-assisted or scripted analysis.

## Finish

The report files are in `reports/`. Download or share them according to your
organization's security process.
