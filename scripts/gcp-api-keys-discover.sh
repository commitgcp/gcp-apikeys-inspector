#!/usr/bin/env bash
set -euo pipefail

ORG_ID=""
QUOTA_PROJECT=""

usage() {
  cat <<'EOF'
Usage: scripts/gcp-api-keys-discover.sh [--organization ORG_ID] [--quota-project PROJECT_ID]

Runs the GCP API keys report from an authenticated gcloud shell. This Cloud
Shell path intentionally uses the active gcloud account and does not require
Application Default Credentials.
EOF
}

normalize_org() {
  local value="$1"
  value="${value#organizations/}"
  case "$value" in
    "" | "(unset)" | "ORG_ID" | "ORGANIZATION_ID" | "CURRENT_ORG" | "<"*) return 1 ;;
  esac
  printf '%s\n' "$value"
}

valid_project() {
  local value="$1"
  case "$value" in
    "" | "(unset)" | "CURRENT_PROJECT" | "PROJECT_ID" | "YOUR_PROJECT_ID" | "<"*) return 1 ;;
  esac
  case "$value" in
    *" "* | *$'\t'* | *"<"* | *">"*) return 1 ;;
  esac
  printf '%s\n' "$value"
}

discover_org_for_project() {
  local project="$1"
  gcloud projects get-ancestors "$project" \
    --format="csv[no-heading](type,id)" 2>/dev/null |
    awk -F, 'tolower($1) == "organization" {print $2; exit}'
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --organization | --org)
      ORG_ID="$(normalize_org "${2:-}")"
      shift 2
      ;;
    --organization=* | --org=*)
      ORG_ID="$(normalize_org "${1#*=}")"
      shift
      ;;
    --quota-project | --project)
      QUOTA_PROJECT="$(valid_project "${2:-}")"
      shift 2
      ;;
    --quota-project=* | --project=*)
      QUOTA_PROJECT="$(valid_project "${1#*=}")"
      shift
      ;;
    --help | -h)
      usage
      exit 0
      ;;
    *)
      if [ -z "$ORG_ID" ] && printf '%s' "$1" | grep -Eq '^(organizations/)?[0-9]+$'; then
        ORG_ID="$(normalize_org "$1")"
      elif [ -z "$QUOTA_PROJECT" ] && valid_project "$1" >/dev/null; then
        QUOTA_PROJECT="$(valid_project "$1")"
      else
        echo "Ignoring unrecognized argument: $1" >&2
      fi
      shift
      ;;
  esac
done

ACTIVE_ACCOUNT="$(gcloud auth list --filter="status:ACTIVE" --format="value(account)" | head -n 1)"
if [ -z "$ACTIVE_ACCOUNT" ]; then
  echo "No active gcloud account found. Run: gcloud auth login" >&2
  exit 2
fi

CURRENT_PROJECT="$(gcloud config get-value project 2>/dev/null || true)"
BILLING_QUOTA_PROJECT="$(gcloud config get-value billing/quota_project 2>/dev/null || true)"

if [ -z "$QUOTA_PROJECT" ]; then
  for candidate in \
    "$CURRENT_PROJECT" \
    "$BILLING_QUOTA_PROJECT" \
    "${GOOGLE_CLOUD_PROJECT:-}" \
    "${CLOUDSDK_CORE_PROJECT:-}" \
    "${DEVSHELL_PROJECT_ID:-}" \
    "${GCLOUD_PROJECT:-}"; do
    if valid="$(valid_project "$candidate")"; then
      QUOTA_PROJECT="$valid"
      break
    fi
  done
fi

if [ -z "$ORG_ID" ] && [ -n "$QUOTA_PROJECT" ]; then
  ORG_ID="$(discover_org_for_project "$QUOTA_PROJECT" || true)"
fi

if [ -z "$ORG_ID" ]; then
  VISIBLE_ORGS="$(gcloud organizations list --format="value(name)" 2>/dev/null | sed 's#^organizations/##' || true)"
  ORG_COUNT="$(printf '%s\n' "$VISIBLE_ORGS" | sed '/^$/d' | wc -l | tr -d ' ')"
  if [ "$ORG_COUNT" = "1" ]; then
    ORG_ID="$(printf '%s\n' "$VISIBLE_ORGS" | sed '/^$/d' | head -n 1)"
  fi
fi

PROJECT_ORG_LINES=""
if [ -z "$ORG_ID" ] || [ -z "$QUOTA_PROJECT" ]; then
  while IFS= read -r project_id; do
    if ! valid_project "$project_id" >/dev/null; then
      continue
    fi
    project_org="$(discover_org_for_project "$project_id" || true)"
    if [ -n "$project_org" ]; then
      PROJECT_ORG_LINES="${PROJECT_ORG_LINES}${project_id} ${project_org}"$'\n'
    fi
  done < <(gcloud projects list --filter="lifecycleState=ACTIVE" --format="value(projectId)" --limit=25 2>/dev/null || true)
fi

if [ -z "$ORG_ID" ] && [ -n "$PROJECT_ORG_LINES" ]; then
  UNIQUE_ORGS="$(printf '%s' "$PROJECT_ORG_LINES" | awk '{print $2}' | sort -u)"
  UNIQUE_ORG_COUNT="$(printf '%s\n' "$UNIQUE_ORGS" | sed '/^$/d' | wc -l | tr -d ' ')"
  if [ "$UNIQUE_ORG_COUNT" = "1" ]; then
    ORG_ID="$(printf '%s\n' "$UNIQUE_ORGS" | sed '/^$/d' | head -n 1)"
  fi
fi

if [ -z "$QUOTA_PROJECT" ] && [ -n "$PROJECT_ORG_LINES" ]; then
  QUOTA_PROJECT="$(printf '%s' "$PROJECT_ORG_LINES" | awk 'NF {print $1; exit}')"
fi

if [ -z "$ORG_ID" ] || [ -z "$QUOTA_PROJECT" ]; then
  echo "Could not determine all required inputs non-interactively." >&2
  echo "Discovered account: ${ACTIVE_ACCOUNT:-none}" >&2
  echo "Discovered organization: ${ORG_ID:-none}" >&2
  echo "Discovered quota project: ${QUOTA_PROJECT:-none}" >&2
  echo "Retry with: scripts/gcp-api-keys-discover.sh --organization ORG_ID --quota-project PROJECT_ID" >&2
  exit 2
fi

echo "Using gcloud account: $ACTIVE_ACCOUNT"
echo "Using organization: organizations/$ORG_ID"
echo "Using quota project: $QUOTA_PROJECT"

gcloud auth print-access-token >/dev/null

if ! gcloud services list --enabled \
  --project "$QUOTA_PROJECT" \
  --filter="config.name=cloudasset.googleapis.com" \
  --format="value(config.name)" | grep -qx "cloudasset.googleapis.com"; then
  echo "Cloud Asset Inventory API is not enabled on $QUOTA_PROJECT. Enabling it now."
  gcloud services enable cloudasset.googleapis.com --project "$QUOTA_PROJECT"
fi

echo "Validating organization scan access."
gcloud asset search-all-resources \
  --scope="organizations/$ORG_ID" \
  --asset-types="apikeys.googleapis.com/Key" \
  --limit=1 \
  --billing-project="$QUOTA_PROJECT" \
  --format="table(name,assetType,project)"

uv sync
mkdir -p reports

RUN_ID="$(date -u +%Y%m%d-%H%M%S)"
HTML_REPORT="reports/api-keys-${ORG_ID}-${RUN_ID}.html"
JSON_REPORT="reports/api-keys-${ORG_ID}-${RUN_ID}.json"

set +e
uv run --no-sync python discover.py \
  --organization "$ORG_ID" \
  --quota-project "$QUOTA_PROJECT" \
  --use-gcloud-auth \
  --output "$HTML_REPORT" \
  --json-output "$JSON_REPORT"
SCAN_STATUS="$?"
set -e

if [ "$SCAN_STATUS" = "2" ]; then
  exit 2
fi
if [ "$SCAN_STATUS" != "0" ] && [ "$SCAN_STATUS" != "1" ]; then
  exit "$SCAN_STATUS"
fi

PORT=""
for candidate in 8080 8081 8082 8083 8084; do
  if ! lsof -iTCP:"$candidate" -sTCP:LISTEN >/dev/null 2>&1; then
    PORT="$candidate"
    break
  fi
done

if [ -n "$PORT" ]; then
  nohup python3 -m http.server "$PORT" > "reports/web-preview-${PORT}.log" 2>&1 &
  echo $! > "reports/web-preview-${PORT}.pid"
fi

python3 - "$JSON_REPORT" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
summary = data["summary"]
severity = summary["severity_counts"]
print("Report summary:")
print(f"  Active keys: {summary['total_active']}")
print(f"  Soft-deleted keys: {summary['total_deleted']}")
print(
    "  Severity: "
    + ", ".join(f"{name}={severity.get(name, 0)}" for name in ("CRITICAL", "HIGH", "MEDIUM", "INFO", "OK"))
)
PY

echo "HTML report: $HTML_REPORT"
echo "JSON report: $JSON_REPORT"
if [ -n "$PORT" ]; then
  echo "Cloud Shell preview port: $PORT"
fi
echo "Download command: cloudshell download \"$HTML_REPORT\" \"$JSON_REPORT\""

if [ "$SCAN_STATUS" = "1" ]; then
  echo "Scanner status: report generated with CRITICAL active-key findings."
else
  echo "Scanner status: report generated without CRITICAL active-key findings."
fi

exit 0
