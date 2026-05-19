"""Plain data models passed through the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "INFO", "OK"]
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITY_ORDER)}


@dataclass
class Finding:
    severity: str
    message: str


@dataclass
class ProjectInfo:
    project_number: str | None = None
    project_id: str | None = None
    display_name: str | None = None
    error: str | None = None


@dataclass
class ApiKey:
    name: str
    uid: str
    display_name: str
    project: ProjectInfo
    create_time: str | None
    update_time: str | None
    delete_time: str | None
    service_account_email: str | None
    restrictions: dict[str, Any]
    folders: list[str]
    severity: str = "OK"
    findings: list[Finding] = field(default_factory=list)

    @property
    def is_deleted(self) -> bool:
        return bool(self.delete_time)


@dataclass
class OrgMeta:
    org_id: str
    display_name: str | None
    scan_time_utc: str
    tool_version: str
