"""Minimal Microsoft Graph v1.0 metadata adapter for OneDrive Personal."""
from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

import httpx

from app.modules.m365_integration.domain.graph_gateway import GraphDrive, GraphDriveItem


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


class MicrosoftGraphError(RuntimeError):
    """Sanitized Graph failure that never carries provider response bodies."""


class MicrosoftGraphGateway:
    def __init__(self, *, timeout_seconds: float = 10.0) -> None:
        self._timeout_seconds = timeout_seconds

    def _get(self, *, access_token: str, path: str, params: dict | None = None) -> dict:
        try:
            response = httpx.get(
                f"{GRAPH_BASE_URL}{path}",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
                timeout=self._timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise MicrosoftGraphError("Microsoft Graph is unavailable.") from exc
        if response.status_code == 404:
            raise MicrosoftGraphError("Microsoft Graph item was not found.")
        if response.status_code in {401, 403}:
            raise MicrosoftGraphError("Microsoft Graph access was denied.")
        if response.status_code >= 400:
            raise MicrosoftGraphError("Microsoft Graph request failed.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise MicrosoftGraphError("Microsoft Graph response is invalid.") from exc
        if not isinstance(payload, dict):
            raise MicrosoftGraphError("Microsoft Graph response is invalid.")
        return payload

    def get_default_drive(self, *, access_token: str) -> GraphDrive:
        payload = self._get(
            access_token=access_token,
            path="/me/drive",
            params={"$select": "id,driveType"},
        )
        drive_id = payload.get("id")
        drive_type = payload.get("driveType")
        if not isinstance(drive_id, str) or drive_type != "personal":
            raise MicrosoftGraphError("Microsoft account does not expose OneDrive Personal.")
        return GraphDrive(drive_id=drive_id, drive_type=drive_type)

    def get_drive_item(
        self, *, access_token: str, drive_id: str, drive_item_id: str
    ) -> GraphDriveItem:
        safe_drive_id = quote(drive_id, safe="")
        safe_item_id = quote(drive_item_id, safe="")
        payload = self._get(
            access_token=access_token,
            path=f"/drives/{safe_drive_id}/items/{safe_item_id}",
            params={
                "$select": (
                    "id,name,size,eTag,cTag,lastModifiedDateTime,webUrl,file,parentReference"
                )
            },
        )
        parent = payload.get("parentReference") or {}
        if payload.get("id") != drive_item_id or parent.get("driveId") != drive_id:
            raise MicrosoftGraphError("Microsoft Graph returned mismatched file identity.")
        if not isinstance(payload.get("file"), dict):
            raise MicrosoftGraphError("Microsoft Graph item is not a file.")

        try:
            modified_at = datetime.fromisoformat(
                str(payload["lastModifiedDateTime"]).replace("Z", "+00:00")
            )
            size_bytes = int(payload["size"])
            name = str(payload["name"])
            e_tag = str(payload["eTag"])
            web_url = str(payload["webUrl"])
        except (KeyError, TypeError, ValueError) as exc:
            raise MicrosoftGraphError("Microsoft Graph file metadata is incomplete.") from exc
        if size_bytes < 0 or not name or not e_tag or not web_url:
            raise MicrosoftGraphError("Microsoft Graph file metadata is incomplete.")
        return GraphDriveItem(
            drive_id=drive_id,
            drive_item_id=drive_item_id,
            # DriveItem has no inline version ID; PR-06 may query /versions separately.
            graph_version_id=None,
            e_tag=e_tag,
            c_tag=payload.get("cTag"),
            last_modified_at=modified_at,
            size_bytes=size_bytes,
            name=name,
            path=parent.get("path"),
            web_url=web_url,
        )
