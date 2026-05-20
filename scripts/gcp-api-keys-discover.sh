#!/usr/bin/env bash
set -euo pipefail

ORG_ID=""
QUOTA_PROJECT=""
DISCOVER_ONLY="false"

usage() {
  cat <<'EOF'
Usage: scripts/gcp-api-keys-discover.sh [--organization ORG_ID] [--quota-project PROJECT_ID]
       scripts/gcp-api-keys-discover.sh --discover-only

Runs the GCP API keys report from an authenticated gcloud shell. This Cloud
Shell path intentionally uses the active gcloud account and does not require
Application Default Credentials.

Use --discover-only to print visible organization and quota-project candidates
without running the report.

Report mode overwrites reports/index.html and reports/report.json, then starts a
Cloud Shell Web Preview server rooted at reports/.
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

emit_project_candidate() {
  local project_id="$1"
  local source="$2"
  local org_id="${3:-}"

  if ! valid_project "$project_id" >/dev/null; then
    return 0
  fi

  printf 'PROJECT\t%s\t%s\t%s\n' "$project_id" "$source" "$org_id"
  if org_id="$(normalize_org "$org_id")"; then
    printf 'ORGANIZATION\t%s\tproject_ancestor\t%s\n' "$org_id" "$project_id"
  fi
}

emit_org_candidate() {
  local org_id="$1"
  local source="$2"
  local display_name="${3:-}"

  if ! org_id="$(normalize_org "$org_id")"; then
    return 0
  fi

  printf 'ORGANIZATION\t%s\t%s\t%s\n' "$org_id" "$source" "$display_name"
}

discover_candidates() {
  local active_account="$1"
  local current_project="$2"
  local billing_quota_project="$3"

  echo "DISCOVERY_FORMAT: TYPE<TAB>ID<TAB>SOURCE<TAB>DETAIL"
  printf 'ACCOUNT\t%s\tactive_gcloud_account\t\n' "$active_account"

  while IFS=, read -r org_name display_name; do
    emit_org_candidate "$org_name" "gcloud_organizations_list" "$display_name"
  done < <(gcloud organizations list --format="csv[no-heading](name,displayName)" 2>/dev/null || true)

  emit_project_candidate "$current_project" "gcloud_config_project" "$(discover_org_for_project "$current_project" || true)"
  emit_project_candidate "$billing_quota_project" "gcloud_billing_quota_project" "$(discover_org_for_project "$billing_quota_project" || true)"
  emit_project_candidate "${GOOGLE_CLOUD_PROJECT:-}" "GOOGLE_CLOUD_PROJECT" "$(discover_org_for_project "${GOOGLE_CLOUD_PROJECT:-}" || true)"
  emit_project_candidate "${CLOUDSDK_CORE_PROJECT:-}" "CLOUDSDK_CORE_PROJECT" "$(discover_org_for_project "${CLOUDSDK_CORE_PROJECT:-}" || true)"
  emit_project_candidate "${DEVSHELL_PROJECT_ID:-}" "DEVSHELL_PROJECT_ID" "$(discover_org_for_project "${DEVSHELL_PROJECT_ID:-}" || true)"
  emit_project_candidate "${GCLOUD_PROJECT:-}" "GCLOUD_PROJECT" "$(discover_org_for_project "${GCLOUD_PROJECT:-}" || true)"

  while IFS= read -r project_id; do
    emit_project_candidate "$project_id" "gcloud_projects_list" "$(discover_org_for_project "$project_id" || true)"
  done < <(gcloud projects list --filter="lifecycleState=ACTIVE" --format="value(projectId)" --limit=50 2>/dev/null || true)
}

stop_preview_servers() {
  local pid_file
  local pid
  local port
  local pids
  local command

  for pid_file in reports/web-preview-*.pid; do
    [ -e "$pid_file" ] || continue
    pid="$(cat "$pid_file" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
    rm -f "$pid_file"
  done

  for port in $(seq 8080 8099); do
    pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
    for pid in $pids; do
      command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
      case "$command" in
        *"python"*"-m http.server"*)
          kill "$pid" 2>/dev/null || true
          ;;
      esac
    done
  done
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
    --discover-only)
      DISCOVER_ONLY="true"
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

if [ "$DISCOVER_ONLY" = "true" ]; then
  discover_candidates "$ACTIVE_ACCOUNT" "$CURRENT_PROJECT" "$BILLING_QUOTA_PROJECT" |
    awk -F '\t' '
      function friendly_source(source) {
        if (source == "gcloud_organizations_list") return "visible organization list"
        if (source == "project_ancestor") return "project ancestor"
        if (source == "gcloud_config_project") return "active gcloud project"
        if (source == "gcloud_billing_quota_project") return "gcloud quota project"
        if (source == "GOOGLE_CLOUD_PROJECT") return "Cloud Shell project"
        if (source == "CLOUDSDK_CORE_PROJECT") return "Cloud SDK project"
        if (source == "DEVSHELL_PROJECT_ID") return "Cloud Shell environment"
        if (source == "GCLOUD_PROJECT") return "gcloud environment"
        if (source == "gcloud_projects_list") return "visible project list"
        return source
      }
      $1 == "ACCOUNT" && account == "" {
        account = $2
        next
      }
      $1 == "ORGANIZATION" {
        id = $2
        if (!seen_org[id]++) {
          org_ids[++org_count] = id
          org_source[id] = $3
          org_detail[id] = $4
        } else if (org_detail[id] == "" && $4 != "") {
          org_detail[id] = $4
          org_source[id] = $3
        }
        next
      }
      $1 == "PROJECT" {
        id = $2
        if (!seen_project[id]++) {
          project_ids[++project_count] = id
          project_source[id] = $3
          project_org[id] = $4
        } else if (project_org[id] == "" && $4 != "") {
          project_org[id] = $4
        }
        next
      }
      END {
        print "Discovery complete."
        print ""
        print "Active gcloud account:"
        print "- " (account != "" ? account : "none")
        print ""
        print "Organizations:"
        if (org_count == 0) {
          print "- None visible from the active account."
        } else {
          for (i = 1; i <= org_count; i++) {
            id = org_ids[i]
            label = "organizations/" id
            if (org_detail[id] != "") {
              label = org_detail[id] " (" label ")"
            }
            print i ". " label " - " friendly_source(org_source[id])
          }
        }
        print ""
        print "Quota project candidates:"
        if (project_count == 0) {
          print "- None visible from the active account."
        } else {
          for (i = 1; i <= project_count; i++) {
            id = project_ids[i]
            org = project_org[id] != "" ? " (org organizations/" project_org[id] ")" : ""
            print i ". " id org " - " friendly_source(project_source[id])
          }
        }
        print ""
        print "Next step: choose one organization and one quota project for the API key report."
      }
    '
  exit 0
fi

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

mkdir -p reports
uv sync

HTML_REPORT="reports/index.html"
JSON_REPORT="reports/report.json"
rm -f "$HTML_REPORT" "$JSON_REPORT"

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

stop_preview_servers

sleep 1

PORT=""
for candidate in $(seq 8080 8099); do
  if ! lsof -iTCP:"$candidate" -sTCP:LISTEN >/dev/null 2>&1; then
    PORT="$candidate"
    break
  fi
done

if [ -z "$PORT" ]; then
  echo "Could not start Cloud Shell Web Preview: no free port found in 8080-8099." >&2
  exit 2
fi

(
  cd reports
  nohup python3 -m http.server "$PORT" > "web-preview-${PORT}.log" 2>&1 &
  echo $! > "web-preview-${PORT}.pid"
)

PREVIEW_PID="$(cat "reports/web-preview-${PORT}.pid")"
sleep 1
if ! kill -0 "$PREVIEW_PID" 2>/dev/null; then
  echo "Could not start Cloud Shell Web Preview on port $PORT." >&2
  echo "Preview log: reports/web-preview-${PORT}.log" >&2
  exit 2
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
echo "Cloud Shell preview port: $PORT"
echo "Cloud Shell preview root: reports/index.html"
echo "Download command: cloudshell download \"$HTML_REPORT\" \"$JSON_REPORT\""

if [ "$SCAN_STATUS" = "1" ]; then
  echo "Scanner status: report generated with CRITICAL active-key findings."
else
  echo "Scanner status: report generated without CRITICAL active-key findings."
fi

exit 0
