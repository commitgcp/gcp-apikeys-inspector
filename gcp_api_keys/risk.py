"""Classify each API Key into a severity + list of findings.

Rubric is intentionally explicit and self-contained — easy to tweak without
touching anything else. Highest severity wins; OK only if no findings.
"""

from __future__ import annotations

from typing import Any

from .models import SEVERITY_RANK, ApiKey, Finding

# Services where a missing `methods` filter means "the key can do anything in that product".
BROAD_SERVICES = {
    "compute.googleapis.com",
    "storage.googleapis.com",
    "aiplatform.googleapis.com",
    "cloudfunctions.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
    "bigquery.googleapis.com",
    "pubsub.googleapis.com",
    "translate.googleapis.com",
    "speech.googleapis.com",
}

CLIENT_RESTRICTION_KEYS = (
    "browserKeyRestrictions",
    "serverKeyRestrictions",
    "androidKeyRestrictions",
    "iosKeyRestrictions",
)


def _max(a: str, b: str) -> str:
    return a if SEVERITY_RANK[a] < SEVERITY_RANK[b] else b


def classify(key: ApiKey) -> None:
    """Mutates `key.severity` and `key.findings` in place."""
    findings: list[Finding] = []
    severity = "OK"

    if key.is_deleted:
        findings.append(
            Finding("INFO", "Soft-deleted key — permanently purged 30 days after deleteTime.")
        )
        severity = _max(severity, "INFO")

    restrictions: dict[str, Any] = key.restrictions or {}
    has_api_targets = bool(restrictions.get("apiTargets"))
    has_client_restriction = any(restrictions.get(k) for k in CLIENT_RESTRICTION_KEYS)

    if not restrictions or (not has_api_targets and not has_client_restriction):
        findings.append(
            Finding(
                "CRITICAL",
                "Key has no restrictions — usable from any caller for any enabled API.",
            )
        )
        severity = _max(severity, "CRITICAL")
    else:
        if has_client_restriction and not has_api_targets:
            findings.append(
                Finding(
                    "HIGH",
                    "No API target restriction — key can call any API enabled on the project.",
                )
            )
            severity = _max(severity, "HIGH")
        if has_api_targets and not has_client_restriction:
            findings.append(
                Finding(
                    "MEDIUM",
                    "No client restriction (IP/referrer/app) — key is usable from anywhere if leaked.",
                )
            )
            severity = _max(severity, "MEDIUM")

    referrers = (restrictions.get("browserKeyRestrictions") or {}).get("allowedReferrers") or []
    if any(r.strip() in ("*", "*/*", "*.*", "*.*.*") for r in referrers):
        findings.append(Finding("HIGH", "Wildcard HTTP referrer accepts any origin."))
        severity = _max(severity, "HIGH")

    allowed_ips = (restrictions.get("serverKeyRestrictions") or {}).get("allowedIps") or []
    if any(ip.strip() in ("0.0.0.0/0", "::/0") for ip in allowed_ips):
        findings.append(Finding("HIGH", "Server IP allowlist is open to the entire internet."))
        severity = _max(severity, "HIGH")

    for target in restrictions.get("apiTargets", []) or []:
        service = target.get("service", "")
        if service in BROAD_SERVICES and not target.get("methods"):
            findings.append(
                Finding(
                    "INFO",
                    f"Broad service scope on '{service}' with no method filter.",
                )
            )
            severity = _max(severity, "INFO")

    key.severity = severity
    key.findings = findings
