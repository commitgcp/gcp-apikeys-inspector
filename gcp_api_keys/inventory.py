"""Cloud Asset Inventory wrapper: stream every API Key in an organization."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from google.auth.credentials import Credentials
from google.api_core import exceptions as gax
from google.cloud import asset_v1
from google.protobuf import field_mask_pb2
from google.protobuf.json_format import MessageToDict

API_KEY_ASSET_TYPE = "apikeys.googleapis.com/Key"


class InventoryError(RuntimeError):
    """Raised when Cloud Asset Inventory cannot be queried."""


def iter_api_keys(org_id: str, credentials: Credentials | None = None) -> Iterator[dict[str, Any]]:
    """Yield every API Key under `organizations/{org_id}` as a plain dict.

    Each yielded dict matches the ResourceSearchResult proto with `versionedResources`
    populated so the caller has the full Key payload (restrictions, etc.).
    """
    client = asset_v1.AssetServiceClient(credentials=credentials)
    request = asset_v1.SearchAllResourcesRequest(
        scope=f"organizations/{org_id}",
        asset_types=[API_KEY_ASSET_TYPE],
        read_mask=field_mask_pb2.FieldMask(paths=["*"]),
    )
    try:
        pager = client.search_all_resources(request=request)
        for result in pager:
            yield MessageToDict(result._pb, preserving_proto_field_name=False)
    except gax.PermissionDenied as exc:
        raise InventoryError(
            "Permission denied calling Cloud Asset Inventory. "
            f"Grant roles/cloudasset.viewer on organizations/{org_id} to "
            "your principal, then retry."
        ) from exc
    except gax.FailedPrecondition as exc:
        raise InventoryError(
            "Cloud Asset Inventory API is not enabled on your quota project. "
            "Enable it with: gcloud services enable cloudasset.googleapis.com "
            "--project <YOUR_QUOTA_PROJECT>"
        ) from exc
    except gax.InvalidArgument as exc:
        raise InventoryError(f"Invalid organization id or scope: {exc.message}") from exc
