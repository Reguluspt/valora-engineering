"""Minimal Microsoft Graph v1.0 metadata adapter for OneDrive Personal."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote, urljoin, urlparse

import httpx

from app.modules.m365_integration.domain.graph_gateway import (
    GraphDrive,
    GraphDriveChildren,
    GraphDriveEntry,
    GraphDriveItem,
)


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
MAX_DOWNLOAD_REDIRECTS = 3


def _validated_web_url(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise MicrosoftGraphError("Microsoft Graph file metadata is incomplete.")
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise MicrosoftGraphError(
            "Microsoft Graph returned an unsafe file URL.",
            category="invalid_provider_url",
            retryable=False,
        )
    return value


class MicrosoftGraphError(RuntimeError):
    """Sanitized Graph failure that never carries provider response bodies."""

    def __init__(
        self,
        message: str,
        *,
        category: str = "provider_unavailable",
        retryable: bool = True,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.retryable = retryable


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
            raise MicrosoftGraphError(
                "Microsoft Graph item was not found.",
                category="not_found",
                retryable=False,
            )
        if response.status_code in {401, 403}:
            raise MicrosoftGraphError(
                "Microsoft Graph access was denied.",
                category="access_denied",
                retryable=False,
            )
        if response.status_code >= 400:
            raise MicrosoftGraphError(
                "Microsoft Graph request failed.",
                category="provider_request_failed",
                retryable=response.status_code in {408, 409, 429} or response.status_code >= 500,
            )
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
            raise MicrosoftGraphError(
                "Microsoft Graph returned mismatched file identity.",
                category="identity_mismatch",
                retryable=False,
            )
        if not isinstance(payload.get("file"), dict):
            raise MicrosoftGraphError(
                "Microsoft Graph item is not a file.",
                category="not_a_file",
                retryable=False,
            )

        try:
            modified_at = datetime.fromisoformat(
                str(payload["lastModifiedDateTime"]).replace("Z", "+00:00")
            )
            size_bytes = int(payload["size"])
            name = str(payload["name"])
            e_tag = str(payload["eTag"])
            web_url = _validated_web_url(payload["webUrl"])
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

    def list_drive_children(
        self,
        *,
        access_token: str,
        drive_id: str,
        parent_item_id: str | None,
        limit: int,
    ) -> GraphDriveChildren:
        """List one bounded folder level using delegated read permission only."""
        bounded_limit = max(1, min(limit, 100))
        safe_drive_id = quote(drive_id, safe="")
        if parent_item_id is None:
            path = f"/drives/{safe_drive_id}/root/children"
        else:
            safe_parent_id = quote(parent_item_id, safe="")
            path = f"/drives/{safe_drive_id}/items/{safe_parent_id}/children"
        payload = self._get(
            access_token=access_token,
            path=path,
            params={
                "$top": str(bounded_limit),
                "$select": (
                    "id,name,size,lastModifiedDateTime,webUrl,file,folder,parentReference"
                ),
            },
        )
        raw_entries = payload.get("value")
        if not isinstance(raw_entries, list):
            raise MicrosoftGraphError("Microsoft Graph folder response is invalid.")

        entries: list[GraphDriveEntry] = []
        for raw in raw_entries[:bounded_limit]:
            if not isinstance(raw, dict):
                continue
            item_id = raw.get("id")
            name = raw.get("name")
            parent = raw.get("parentReference") or {}
            if (
                not isinstance(item_id, str)
                or not item_id
                or not isinstance(name, str)
                or not name
                or not isinstance(parent, dict)
                or parent.get("driveId") != drive_id
            ):
                raise MicrosoftGraphError(
                    "Microsoft Graph returned mismatched folder identity.",
                    category="identity_mismatch",
                    retryable=False,
                )
            is_folder = isinstance(raw.get("folder"), dict)
            is_file = isinstance(raw.get("file"), dict)
            if not is_folder and not (is_file and name.lower().endswith(".docx")):
                continue
            modified_at: datetime | None = None
            if raw.get("lastModifiedDateTime") is not None:
                try:
                    modified_at = datetime.fromisoformat(
                        str(raw["lastModifiedDateTime"]).replace("Z", "+00:00")
                    )
                except ValueError as exc:
                    raise MicrosoftGraphError(
                        "Microsoft Graph folder metadata is incomplete."
                    ) from exc
            size_bytes: int | None = None
            if is_file:
                try:
                    size_bytes = int(raw["size"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise MicrosoftGraphError(
                        "Microsoft Graph file metadata is incomplete."
                    ) from exc
                if size_bytes < 0:
                    raise MicrosoftGraphError(
                        "Microsoft Graph file metadata is incomplete."
                    )
            web_url = _validated_web_url(raw.get("webUrl")) if is_file else None
            entries.append(
                GraphDriveEntry(
                    drive_item_id=item_id,
                    kind="folder" if is_folder else "docx",
                    name=name,
                    size_bytes=size_bytes,
                    last_modified_at=modified_at,
                    web_url=web_url,
                )
            )
        return GraphDriveChildren(
            entries=tuple(entries),
            truncated=(
                isinstance(payload.get("@odata.nextLink"), str)
                or len(raw_entries) > bounded_limit
            ),
        )

    def get_drive_item_content(
        self, *, access_token: str, drive_id: str, drive_item_id: str
    ) -> bytes:
        """Download one bounded stream without persisting its preauthenticated URL."""
        safe_drive_id = quote(drive_id, safe="")
        safe_item_id = quote(drive_item_id, safe="")
        url = f"{GRAPH_BASE_URL}/drives/{safe_drive_id}/items/{safe_item_id}/content"
        headers: dict[str, str] = {"Authorization": f"Bearer {access_token}"}

        for redirect_count in range(MAX_DOWNLOAD_REDIRECTS + 1):
            try:
                with httpx.stream(
                    "GET",
                    url,
                    headers=headers,
                    timeout=self._timeout_seconds,
                    follow_redirects=False,
                ) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        if redirect_count == MAX_DOWNLOAD_REDIRECTS:
                            raise MicrosoftGraphError(
                                "Microsoft Graph download redirected too many times.",
                                category="download_failed",
                            )
                        location = response.headers.get("location")
                        if not location:
                            raise MicrosoftGraphError(
                                "Microsoft Graph download redirect is invalid.",
                                category="download_failed",
                            )
                        next_url = urljoin(url, location)
                        parsed = urlparse(next_url)
                        if parsed.scheme != "https" or not parsed.hostname:
                            raise MicrosoftGraphError(
                                "Microsoft Graph download redirect is unsafe.",
                                category="download_failed",
                                retryable=False,
                            )
                        url = next_url
                        headers = {}
                        continue
                    if response.status_code == 404:
                        raise MicrosoftGraphError(
                            "Microsoft Graph item was not found.",
                            category="not_found",
                            retryable=False,
                        )
                    if response.status_code in {401, 403}:
                        raise MicrosoftGraphError(
                            "Microsoft Graph access was denied.",
                            category="access_denied",
                            retryable=False,
                        )
                    if response.status_code >= 400:
                        raise MicrosoftGraphError(
                            "Microsoft Graph download failed.",
                            category="download_failed",
                            retryable=response.status_code in {408, 409, 429}
                            or response.status_code >= 500,
                        )
                    declared_length = response.headers.get("content-length")
                    expected_length: int | None = None
                    if declared_length is not None:
                        try:
                            expected_length = int(declared_length)
                            if expected_length < 0:
                                raise ValueError
                            if expected_length > MAX_DOWNLOAD_BYTES:
                                raise MicrosoftGraphError(
                                    "Microsoft Graph file exceeds the download limit.",
                                    category="content_too_large",
                                    retryable=False,
                                )
                        except ValueError as exc:
                            raise MicrosoftGraphError(
                                "Microsoft Graph download metadata is invalid.",
                                category="download_failed",
                            ) from exc
                    chunks: list[bytes] = []
                    total = 0
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > MAX_DOWNLOAD_BYTES:
                            raise MicrosoftGraphError(
                                "Microsoft Graph file exceeds the download limit.",
                                category="content_too_large",
                                retryable=False,
                            )
                        chunks.append(chunk)
                    if expected_length is not None and total != expected_length:
                        raise MicrosoftGraphError(
                            "Microsoft Graph download was incomplete.",
                            category="download_failed",
                        )
                    return b"".join(chunks)
            except MicrosoftGraphError:
                raise
            except httpx.HTTPError as exc:
                raise MicrosoftGraphError(
                    "Microsoft Graph download is unavailable.",
                    category="download_failed",
                ) from exc
        raise MicrosoftGraphError(
            "Microsoft Graph download failed.",
            category="download_failed",
        )
