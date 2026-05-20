#!/usr/bin/env python3
"""Org-wide GCP API Key scanner.

Usage:
    uv run python discover.py --organization 105196367825 --output report.html
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

from gcp_api_keys import __version__
from gcp_api_keys.auth import AuthError, load_credentials
from gcp_api_keys.inventory import InventoryError, iter_api_keys
from gcp_api_keys.models import ApiKey, OrgMeta
from gcp_api_keys.projects import ProjectResolver, fetch_org_display_name
from gcp_api_keys.report import build_json_report, render
from gcp_api_keys.risk import classify


def _project_number_from_search_result(result: dict[str, Any]) -> str | None:
    project_field = result.get("project") or ""
    if project_field.startswith("projects/"):
        return project_field.split("/", 1)[1]
    return None


def _project_id_from_parent(result: dict[str, Any]) -> str | None:
    parent = result.get("parentFullResourceName") or ""
    marker = "/projects/"
    idx = parent.find(marker)
    if idx == -1:
        return None
    return parent[idx + len(marker):]


def _to_api_key(result: dict[str, Any], resolver: ProjectResolver) -> ApiKey:
    versioned = (result.get("versionedResources") or [{}])[0]
    resource = versioned.get("resource") or {}

    project_number = _project_number_from_search_result(result)
    project_id_hint = _project_id_from_parent(result)
    project_info = resolver.resolve(project_number, project_id_hint)
    if not project_info.project_id and project_id_hint:
        project_info.project_id = project_id_hint

    return ApiKey(
        name=result.get("name", ""),
        uid=resource.get("uid") or result.get("name", "").rsplit("/", 1)[-1],
        display_name=resource.get("displayName") or result.get("displayName") or "",
        project=project_info,
        create_time=resource.get("createTime") or result.get("createTime"),
        update_time=resource.get("updateTime") or result.get("updateTime"),
        delete_time=resource.get("deleteTime"),
        service_account_email=resource.get("serviceAccountEmail"),
        restrictions=resource.get("restrictions") or {},
        folders=list(result.get("folders") or []),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--organization",
        "--org",
        required=True,
        help="GCP organization numeric ID (e.g. 105196367825).",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="report.html",
        type=Path,
        help="Path to write the HTML report (default: report.html).",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional path to write sanitized machine-readable report data.",
    )
    parser.add_argument(
        "--quota-project",
        help=(
            "Project used for user-project quota/billing headers. Recommended "
            "when using user credentials."
        ),
    )
    parser.add_argument(
        "--use-gcloud-auth",
        action="store_true",
        help=(
            "Use the active gcloud account access token instead of Application "
            "Default Credentials. Useful in Cloud Shell."
        ),
    )
    parser.add_argument(
        "--no-resolve-projects",
        action="store_true",
        help="Skip Resource Manager calls. Faster but loses project displayName.",
    )
    parser.add_argument(
        "--exit-zero",
        action="store_true",
        help="Always exit 0, even if CRITICAL findings are present (CI override).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    org_id = args.organization.strip()
    if org_id.startswith("organizations/"):
        org_id = org_id.split("/", 1)[1]

    print(f"Scanning organizations/{org_id} for API keys via Cloud Asset Inventory…", file=sys.stderr)
    if args.use_gcloud_auth:
        print("Using active gcloud account credentials.", file=sys.stderr)
    if args.quota_project:
        print(f"Using quota project: {args.quota_project}", file=sys.stderr)

    try:
        credentials = load_credentials(
            quota_project=args.quota_project,
            use_gcloud_auth=args.use_gcloud_auth,
        )
    except AuthError as exc:
        print(f"\nerror: {exc}", file=sys.stderr)
        return 2

    resolver = _NoopResolver() if args.no_resolve_projects else ProjectResolver(credentials=credentials)

    keys: list[ApiKey] = []
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "INFO": 0, "OK": 0, "deleted": 0}
    try:
        for result in iter_api_keys(org_id, credentials=credentials):
            key = _to_api_key(result, resolver)
            classify(key)
            keys.append(key)
            counts[key.severity] += 1
            if key.is_deleted:
                counts["deleted"] += 1
            print(
                f"  [{len(keys):>4}] {key.severity:<8} {key.display_name or '(unnamed)'} "
                f"— {key.project.display_name or key.project.project_id or key.project.project_number}",
                file=sys.stderr,
            )
    except InventoryError as exc:
        print(f"\nerror: {exc}", file=sys.stderr)
        return 2

    org_meta = OrgMeta(
        org_id=org_id,
        display_name=None if args.no_resolve_projects else fetch_org_display_name(org_id, credentials=credentials),
        scan_time_utc=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        tool_version=__version__,
    )

    summary = render(keys, org_meta, args.output)
    if args.json_output:
        payload = build_json_report(keys, org_meta)
        args.json_output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        print(f"JSON report written to {args.json_output.resolve()}", file=sys.stderr)

    print(
        f"\nDone. {len(keys)} keys total "
        f"({counts['deleted']} soft-deleted). Severity: "
        + ", ".join(f"{s}={summary.get(s, 0)}" for s in ["CRITICAL", "HIGH", "MEDIUM", "INFO", "OK"]),
        file=sys.stderr,
    )
    print(f"Report written to {args.output.resolve()}", file=sys.stderr)

    if not args.exit_zero and summary.get("CRITICAL", 0) > 0:
        return 1
    return 0


class _NoopResolver:
    """Stub used when --no-resolve-projects is set."""

    def resolve(self, project_number, project_id):
        from gcp_api_keys.models import ProjectInfo

        return ProjectInfo(project_number=project_number, project_id=project_id)


if __name__ == "__main__":
    sys.exit(main())
