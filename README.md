<p align="left">
  <img src="assets/commit-logo-dark.png" alt="Commit logo" width="142">
</p>

# Commit GCP API Keys Discover

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://ssh.cloud.google.com/cloudshell/open?cloudshell_git_repo=REPLACE_WITH_REPO_URL&cloudshell_tutorial=cloudshell/tutorial.md)

> Before publishing this README, replace `REPLACE_WITH_REPO_URL` in the Cloud
> Shell button with the HTTPS Git URL for this repository.

Discover every API Key (`apikeys.googleapis.com/Key`) across a Google Cloud
organization and produce a standalone Commit-branded HTML report with per-key
restrictions, inline security findings, and interactive filtering/grouping.

The generated report is intended for Commit-led Google Cloud security reviews:
it uses Commit visual branding, keeps all report assets self-contained, and
organizes API key risk by severity, project, API target, and client restriction.
The scanner reads metadata from Cloud Asset Inventory only; it never retrieves
API key secret values.

## Quick paths

| Need | Start here |
|---|---|
| Run in Cloud Shell | Use the **Open in Cloud Shell** button above after replacing the repository URL. |
| Run locally | Follow [Run](#run). |
| Understand required IAM and auth | Read [docs/USER_GUIDE.md](docs/USER_GUIDE.md). |
| Guide another user step-by-step | Launch [cloudshell/tutorial.md](cloudshell/tutorial.md). |
| Ask an agent to run and analyze it | Use `$gcp-api-keys-discover`; see [Agent skill](#agent-skill). |

## How it works

1. One call to **Cloud Asset Inventory** `searchAllResources` at organization
   scope returns every API Key in the org with full restriction data, project
   ancestry, and soft-delete state — no per-project fan-out.
2. **Resource Manager** v3 fills in human-readable project `displayName`
   (cached per project, tolerant of permission errors).
3. Each key is scored against a fixed rubric (`gcp_api_keys/risk.py`):
   CRITICAL when fully unrestricted, HIGH for missing API targets or wildcard
   referrer/IP, MEDIUM when no client restriction, INFO for broad service
   scopes and soft-deleted keys.
4. A Jinja2 template renders one self-contained HTML file (inlined Commit
   branding, CSS, and vanilla JS; no runtime external assets).
5. Optionally writes sanitized JSON for agent-assisted analysis and automation.

## Commit-branded report

The HTML report is a standalone artifact that can be shared with stakeholders
without requiring a web server or external CSS/JS. It includes:

- Embedded Commit logo and Commit-inspired red/charcoal styling.
- Executive summary cards for active keys, projects, soft-deleted keys, and severity counts.
- Priority findings for CRITICAL and HIGH risks.
- Search plus filters for severity, project, API target, and client restriction.
- Grouping by severity, project, API target, or client restriction.
- Expandable rows with raw restrictions JSON for remediation review.
- Optional JSON output for agents or downstream processing.

## Requirements

- Python 3.10+, `uv` installed.
- Application Default Credentials configured for a principal with:
  - `roles/cloudasset.viewer` on the target organization (required)
  - `roles/serviceusage.serviceUsageConsumer` on a quota project (required for user ADC)
  - `roles/browser` or equivalent Resource Manager read permissions (optional, for display names)
- Cloud Asset Inventory API enabled on the quota project:
  ```
  gcloud services enable cloudasset.googleapis.com --project <QUOTA_PROJECT>
  ```

For exact IAM, authentication, validation, and troubleshooting steps, see
[docs/USER_GUIDE.md](docs/USER_GUIDE.md).

## Run

```bash
cd gcp-api-keys-discover
uv sync
gcloud auth application-default login   # if not already done
gcloud auth application-default set-quota-project <QUOTA_PROJECT>
uv run python discover.py \
  --organization 105196367825 \
  --output report.html \
  --json-output report.json
open report.html
```

Flags:

- `--organization <id>` — numeric org ID (or `organizations/<id>`). Required.
- `--output <path>` — output HTML path. Defaults to `report.html`.
- `--json-output <path>` — optional sanitized machine-readable report.
- `--no-resolve-projects` — skip Resource Manager calls (faster, no displayName).
- `--exit-zero` — always exit 0 even when CRITICAL findings are present.

Exit codes:

| Code | Meaning |
|---|---|
| `0` | Scan succeeded, no CRITICAL findings (or `--exit-zero` set). |
| `1` | Scan succeeded, at least one CRITICAL finding. Useful as a CI gate. |
| `2` | Scan could not complete (auth, permission, or API-enablement error). |

## Cloud Shell tutorial

The included tutorial walks users through setting `ORG_ID`, validating ADC,
checking IAM/API access, syncing dependencies with `uv`, running the scanner,
and previewing the HTML report in Cloud Shell.

Launch it from an existing Cloud Shell checkout:

```bash
cloudshell launch-tutorial cloudshell/tutorial.md
```

For a hosted repository, use this button/link format in published docs:

```markdown
[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://ssh.cloud.google.com/cloudshell/open?cloudshell_git_repo=REPLACE_WITH_REPO_URL&cloudshell_tutorial=cloudshell/tutorial.md)
```

Equivalent plain URL:

```text
https://ssh.cloud.google.com/cloudshell/open?cloudshell_git_repo=REPLACE_WITH_REPO_URL&cloudshell_tutorial=cloudshell/tutorial.md
```

The `cloudshell_git_repo` value must be the hosted Git repository URL. The
`cloudshell_tutorial` value points to this repo's tutorial file.

## Agent skill

The repo-local skill lives at:

```text
.agents/skills/gcp-api-keys-discover/SKILL.md
```

An agent can be instructed with `$gcp-api-keys-discover` to validate auth/IAM,
run the scanner, generate HTML and JSON reports, and summarize findings.

## Layout

```
discover.py                  # CLI entry
gcp_api_keys/
  inventory.py               # Cloud Asset Inventory search
  projects.py                # Resource Manager displayName resolver
  risk.py                    # severity rubric
  models.py                  # dataclasses
  report.py                  # Jinja render
templates/report.html.j2     # self-contained HTML template
assets/commit-logo-*.png     # embedded Commit report branding
docs/USER_GUIDE.md           # exact runbook and permissions
cloudshell/tutorial.md       # Cloud Shell tutorial
.agents/skills/...           # repo-local agent skill
```
