"""Authentication helpers for Cloud Shell and ADC-based runs."""

from __future__ import annotations

import subprocess

import google.auth
from google.auth.credentials import Credentials
from google.auth.exceptions import DefaultCredentialsError
from google.oauth2.credentials import Credentials as OAuthCredentials

CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


class AuthError(RuntimeError):
    """Raised when scanner credentials cannot be created."""


def load_credentials(
    *,
    quota_project: str | None = None,
    use_gcloud_auth: bool = False,
) -> Credentials:
    """Build credentials for Google API clients.

    The normal manual workflow uses Application Default Credentials. The Gemini
    Cloud Shell workflow uses the active gcloud account's access token to avoid
    launching an interactive ADC browser-code flow inside the agent.
    """
    if use_gcloud_auth:
        credentials: Credentials = OAuthCredentials(
            token=_gcloud_access_token(),
            scopes=[CLOUD_PLATFORM_SCOPE],
        )
    else:
        try:
            credentials, _ = google.auth.default(
                scopes=[CLOUD_PLATFORM_SCOPE],
                quota_project_id=quota_project,
            )
        except DefaultCredentialsError as exc:
            raise AuthError(
                "Application Default Credentials are not configured. Run "
                "`gcloud auth application-default login`, or use "
                "`--use-gcloud-auth` from an already-authenticated gcloud shell."
            ) from exc

    if quota_project and hasattr(credentials, "with_quota_project"):
        credentials = credentials.with_quota_project(quota_project)

    return credentials


def _gcloud_access_token() -> str:
    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise AuthError("`gcloud` was not found on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        message = "Could not obtain an access token from the active gcloud account."
        if detail:
            message = f"{message} gcloud said: {detail}"
        raise AuthError(f"{message} Run `gcloud auth login` and retry.") from exc

    token = result.stdout.strip()
    if not token:
        raise AuthError("`gcloud auth print-access-token` returned an empty token.")
    return token
