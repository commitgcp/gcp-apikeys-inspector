"""Resource Manager wrapper: resolve project number/id -> displayName, cached."""

from __future__ import annotations

from google.api_core import exceptions as gax
from google.cloud import resourcemanager_v3

from .models import ProjectInfo


class ProjectResolver:
    def __init__(self) -> None:
        self._client = resourcemanager_v3.ProjectsClient()
        self._cache: dict[str, ProjectInfo] = {}

    def resolve(self, project_number: str | None, project_id: str | None) -> ProjectInfo:
        """Return display name for a project.

        Looks up by project number (preferred — that's what CAI returns in `project`)
        and falls back to the project ID embedded in `parentFullResourceName` if
        the number lookup is denied. Never raises; failures are reported via
        `ProjectInfo.error`.
        """
        cache_key = project_number or project_id or ""
        if cache_key in self._cache:
            return self._cache[cache_key]

        info = ProjectInfo(project_number=project_number, project_id=project_id)
        target = f"projects/{project_number}" if project_number else f"projects/{project_id}"
        try:
            project = self._client.get_project(name=target)
            info.project_id = project.project_id
            info.display_name = project.display_name or project.project_id
        except gax.PermissionDenied:
            info.error = "permission_denied"
        except gax.NotFound:
            info.error = "not_found"
        except gax.GoogleAPICallError as exc:
            info.error = f"api_error:{exc.code.name if exc.code else 'unknown'}"

        self._cache[cache_key] = info
        return info


def fetch_org_display_name(org_id: str) -> str | None:
    """Best-effort lookup of organization displayName. Returns None on any error."""
    try:
        client = resourcemanager_v3.OrganizationsClient()
        org = client.get_organization(name=f"organizations/{org_id}")
        return org.display_name or None
    except gax.GoogleAPICallError:
        return None
