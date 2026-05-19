"""Render the standalone HTML report."""

from __future__ import annotations

import base64
import json
from collections import Counter
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import SEVERITY_ORDER, ApiKey, OrgMeta

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
NO_API_TARGET_VALUE = "__NO_API_TARGET__"
NO_CLIENT_RESTRICTION_VALUE = "__NO_CLIENT_RESTRICTION__"
NO_API_TARGET_LABEL = "No API target restriction"
NO_CLIENT_RESTRICTION_LABEL = "No client restriction"


def _asset_data_uri(filename: str) -> str | None:
    path = ASSET_DIR / filename
    try:
        payload = base64.b64encode(path.read_bytes()).decode("ascii")
    except FileNotFoundError:
        return None
    return f"data:image/png;base64,{payload}"


def _project_label(key: ApiKey) -> str:
    display = key.project.display_name
    project_id = key.project.project_id
    number = key.project.project_number
    if display and project_id and display != project_id:
        return f"{display} ({project_id})"
    return display or project_id or number or "Unknown project"


def _api_services(restrictions: dict[str, Any]) -> list[str]:
    services: list[str] = []
    for target in restrictions.get("apiTargets", []) or []:
        service = target.get("service") or "unknown API service"
        if service not in services:
            services.append(service)
    return services


def _client_restrictions(restrictions: dict[str, Any]) -> list[dict[str, str]]:
    clients: list[dict[str, str]] = []
    browser = restrictions.get("browserKeyRestrictions") or {}
    server = restrictions.get("serverKeyRestrictions") or {}
    android = restrictions.get("androidKeyRestrictions") or {}
    ios = restrictions.get("iosKeyRestrictions") or {}
    if browser:
        clients.append({"value": "browser", "label": "HTTP referrer"})
    if server:
        clients.append({"value": "server", "label": "Server IP"})
    if android:
        clients.append({"value": "android", "label": "Android app"})
    if ios:
        clients.append({"value": "ios", "label": "iOS bundle"})
    return clients


def _restriction_chips(restrictions: dict[str, Any]) -> list[dict[str, str]]:
    chips: list[dict[str, str]] = []
    for target in restrictions.get("apiTargets", []) or []:
        svc = target.get("service") or "?"
        methods = target.get("methods") or []
        label = f"api: {svc}" + (f" ({len(methods)} methods)" if methods else "")
        chips.append({"kind": "api", "label": label})
    referrers = (restrictions.get("browserKeyRestrictions") or {}).get("allowedReferrers") or []
    for r in referrers:
        chips.append({"kind": "browser", "label": f"referrer: {r}"})
    ips = (restrictions.get("serverKeyRestrictions") or {}).get("allowedIps") or []
    for ip in ips:
        chips.append({"kind": "server", "label": f"ip: {ip}"})
    apps = (restrictions.get("androidKeyRestrictions") or {}).get("allowedApplications") or []
    for app in apps:
        chips.append({"kind": "android", "label": f"android: {app.get('packageName', '?')}"})
    bundles = (restrictions.get("iosKeyRestrictions") or {}).get("allowedBundleIds") or []
    for b in bundles:
        chips.append({"kind": "ios", "label": f"ios: {b}"})
    return chips


def _key_to_view(key: ApiKey) -> dict[str, Any]:
    restrictions = key.restrictions or {}
    api_services = _api_services(restrictions)
    api_filter_values = api_services or [NO_API_TARGET_VALUE]
    api_group = (
        api_services[0]
        if len(api_services) == 1
        else "Multiple API targets"
        if len(api_services) > 1
        else NO_API_TARGET_LABEL
    )
    clients = _client_restrictions(restrictions)
    client_filter_values = [c["value"] for c in clients] or [NO_CLIENT_RESTRICTION_VALUE]
    client_labels = [c["label"] for c in clients]
    client_group = (
        client_labels[0]
        if len(client_labels) == 1
        else "Multiple client restrictions"
        if len(client_labels) > 1
        else NO_CLIENT_RESTRICTION_LABEL
    )
    project_label = _project_label(key)
    findings = [{"severity": f.severity, "message": f.message} for f in key.findings]
    chips = _restriction_chips(restrictions)
    search_text = " ".join(
        [
            key.display_name or "",
            key.uid,
            key.name,
            project_label,
            key.project.project_id or "",
            key.project.project_number or "",
            key.project.display_name or "",
            key.service_account_email or "",
            " ".join(api_services),
            " ".join(client_labels),
            " ".join(f["message"] for f in findings),
            " ".join(chip["label"] for chip in chips),
        ]
    ).lower()
    return {
        "name": key.name,
        "uid": key.uid,
        "display_name": key.display_name or "(unnamed)",
        "project_number": key.project.project_number,
        "project_id": key.project.project_id,
        "project_display_name": key.project.display_name,
        "project_label": project_label,
        "project_error": key.project.error,
        "create_time": key.create_time,
        "update_time": key.update_time,
        "delete_time": key.delete_time,
        "service_account_email": key.service_account_email,
        "folders": key.folders,
        "restrictions": restrictions,
        "restrictions_json": json.dumps(restrictions, indent=2, sort_keys=True),
        "chips": chips,
        "api_services": api_services,
        "api_filter_values": api_filter_values,
        "api_filter": "|".join(api_filter_values),
        "api_group": api_group,
        "client_restrictions": clients,
        "client_filter_values": client_filter_values,
        "client_filter": "|".join(client_filter_values),
        "client_group": client_group,
        "search_text": search_text,
        "severity": key.severity,
        "findings": findings,
    }


def render(keys: list[ApiKey], org: OrgMeta, output_path: Path) -> dict[str, int]:
    """Write the HTML report. Returns the per-severity count summary."""
    active = [k for k in keys if not k.is_deleted]
    deleted = [k for k in keys if k.is_deleted]

    active_views = [_key_to_view(k) for k in active]
    deleted_views = [_key_to_view(k) for k in deleted]

    severity_counts: Counter[str] = Counter(k["severity"] for k in active_views)
    for sev in SEVERITY_ORDER:
        severity_counts.setdefault(sev, 0)

    projects_with_keys = {k.project.project_id or k.project.project_number for k in active}
    project_counts: Counter[str] = Counter(k["project_label"] for k in active_views)
    api_counts: Counter[str] = Counter()
    for key in active_views:
        if key["api_services"]:
            api_counts.update(key["api_services"])
        else:
            api_counts[NO_API_TARGET_LABEL] += 1

    top_findings: list[dict[str, Any]] = []
    for key in active:
        for finding in key.findings:
            if finding.severity in ("CRITICAL", "HIGH"):
                top_findings.append(
                    {
                        "severity": finding.severity,
                        "message": finding.message,
                        "uid": key.uid,
                        "key_display_name": key.display_name or "(unnamed)",
                        "project_display_name": key.project.display_name
                        or key.project.project_id
                        or key.project.project_number,
                    }
                )

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("report.html.j2")
    html = template.render(
        org=org,
        active_keys=active_views,
        deleted_keys=deleted_views,
        severity_order=SEVERITY_ORDER,
        severity_counts=dict(severity_counts),
        severity_rank={sev: idx for idx, sev in enumerate(SEVERITY_ORDER)},
        project_options=[
            {"value": project, "label": project, "count": count}
            for project, count in sorted(project_counts.items(), key=lambda item: item[0].lower())
        ],
        api_options=[
            {
                "value": NO_API_TARGET_VALUE if api == NO_API_TARGET_LABEL else api,
                "label": api,
                "count": count,
            }
            for api, count in sorted(api_counts.items(), key=lambda item: item[0].lower())
        ],
        projects_with_keys=len([p for p in projects_with_keys if p]),
        total_active=len(active),
        total_deleted=len(deleted),
        top_findings=top_findings[:20],
        top_findings_total=len(top_findings),
        commit_logo_data_uri=_asset_data_uri("commit-logo-white-red-dot.png"),
        no_api_target_value=NO_API_TARGET_VALUE,
        no_client_restriction_value=NO_CLIENT_RESTRICTION_VALUE,
    )
    output_path.write_text(html, encoding="utf-8")
    return dict(severity_counts)


def build_json_report(keys: list[ApiKey], org: OrgMeta) -> dict[str, Any]:
    """Return the same sanitized report data in a machine-readable shape."""
    active_views = [_key_to_view(k) for k in keys if not k.is_deleted]
    deleted_views = [_key_to_view(k) for k in keys if k.is_deleted]
    severity_counts: Counter[str] = Counter(k["severity"] for k in active_views)
    for sev in SEVERITY_ORDER:
        severity_counts.setdefault(sev, 0)

    project_counts: Counter[str] = Counter(k["project_label"] for k in active_views)
    api_counts: Counter[str] = Counter()
    for key in active_views:
        api_counts.update(key["api_services"] or [NO_API_TARGET_LABEL])

    return {
        "organization": {
            "org_id": org.org_id,
            "display_name": org.display_name,
            "scan_time_utc": org.scan_time_utc,
            "tool_version": org.tool_version,
        },
        "summary": {
            "total_active": len(active_views),
            "total_deleted": len(deleted_views),
            "severity_counts": dict(severity_counts),
            "project_counts": dict(sorted(project_counts.items())),
            "api_counts": dict(sorted(api_counts.items())),
        },
        "active_keys": active_views,
        "deleted_keys": deleted_views,
    }
