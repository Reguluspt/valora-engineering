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
    GraphExchangeItem,
    GraphMutationResult,
    GraphMutationStatus,
)


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
MAX_DOWNLOAD_REDIRECTS = 3
MAX_EXACT_CHILD_PAGES = 20


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

    def _get_url(
        self,
        *,
        access_token: str,
        url: str,
        params: dict | None = None,
    ) -> dict:
        parsed = urlparse(url)
        try:
            port = parsed.port
        except ValueError as exc:
            raise MicrosoftGraphError(
                "Microsoft Graph returned an unsafe pagination URL.",
                category="invalid_provider_url",
                retryable=False,
            ) from exc
        if (
            parsed.scheme != "https"
            or parsed.hostname != "graph.microsoft.com"
            or port not in {None, 443}
            or parsed.username is not None
            or parsed.password is not None
            or not parsed.path.startswith("/v1.0/")
        ):
            raise MicrosoftGraphError(
                "Microsoft Graph returned an unsafe pagination URL.",
                category="invalid_provider_url",
                retryable=False,
            )
        try:
            response = httpx.get(
                url,
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

    def _get(self, *, access_token: str, path: str, params: dict | None = None) -> dict:
        return self._get_url(
            access_token=access_token,
            url=f"{GRAPH_BASE_URL}{path}",
            params=params,
        )

    @staticmethod
    def _exchange_item(payload: dict, *, expected_drive_id: str) -> GraphExchangeItem:
        parent = payload.get("parentReference") or {}
        drive_item_id = payload.get("id")
        name = payload.get("name")
        e_tag = payload.get("eTag")
        parent_item_id = parent.get("id")
        drive_id = parent.get("driveId") or expected_drive_id
        is_folder = isinstance(payload.get("folder"), dict)
        is_file = isinstance(payload.get("file"), dict)
        try:
            size_bytes = int(payload.get("size", 0))
        except (TypeError, ValueError) as exc:
            raise MicrosoftGraphError("Microsoft Graph item metadata is invalid.") from exc
        if (
            drive_id != expected_drive_id
            or not isinstance(drive_item_id, str)
            or not drive_item_id
            or not isinstance(name, str)
            or not name
            or not isinstance(e_tag, str)
            or not e_tag
            or size_bytes < 0
            or is_folder == is_file
        ):
            raise MicrosoftGraphError(
                "Microsoft Graph returned mismatched item identity.",
                category="identity_mismatch",
                retryable=False,
            )
        return GraphExchangeItem(
            drive_id=drive_id,
            drive_item_id=drive_item_id,
            parent_item_id=parent_item_id if isinstance(parent_item_id, str) else None,
            kind="folder" if is_folder else "file",
            name=name,
            size_bytes=size_bytes,
            e_tag=e_tag,
            c_tag=payload.get("cTag") if isinstance(payload.get("cTag"), str) else None,
        )

    @staticmethod
    def _mutation_failure(response: httpx.Response) -> GraphMutationResult | None:
        request_id = response.headers.get("request-id")
        if response.status_code == 409:
            return GraphMutationResult(GraphMutationStatus.COLLISION, provider_request_id=request_id)
        if response.status_code == 412:
            return GraphMutationResult(
                GraphMutationStatus.STALE_PRECONDITION, provider_request_id=request_id
            )
        if response.status_code == 429:
            retry_after = response.headers.get("retry-after")
            return GraphMutationResult(
                GraphMutationStatus.UNAVAILABLE,
                provider_request_id=request_id,
                retry_after_seconds=(int(retry_after) if retry_after and retry_after.isdigit() else None),
            )
        if response.status_code >= 500 or response.status_code in {408}:
            return GraphMutationResult(
                GraphMutationStatus.OUTCOME_UNKNOWN, provider_request_id=request_id
            )
        if response.status_code >= 400:
            return GraphMutationResult(GraphMutationStatus.REJECTED, provider_request_id=request_id)
        return None

    def get_app_root(self, *, access_token: str) -> GraphExchangeItem:
        payload = self._get(
            access_token=access_token,
            path="/me/drive/special/approot",
            params={"$select": "id,name,size,eTag,cTag,folder,parentReference"},
        )
        parent = payload.get("parentReference") or {}
        drive_id = parent.get("driveId")
        if not isinstance(drive_id, str) or not drive_id:
            raise MicrosoftGraphError("Microsoft Graph app root identity is incomplete.")
        return self._exchange_item(payload, expected_drive_id=drive_id)

    def get_exchange_item_by_id(
        self, *, access_token: str, drive_id: str, drive_item_id: str
    ) -> GraphExchangeItem:
        payload = self._get(
            access_token=access_token,
            path=(
                f"/drives/{quote(drive_id, safe='')}/items/"
                f"{quote(drive_item_id, safe='')}"
            ),
            params={"$select": "id,name,size,eTag,cTag,file,folder,parentReference"},
        )
        item = self._exchange_item(payload, expected_drive_id=drive_id)
        if item.drive_item_id != drive_item_id:
            raise MicrosoftGraphError(
                "Microsoft Graph returned mismatched item identity.",
                category="identity_mismatch",
                retryable=False,
            )
        return item

    def resolve_child_by_exact_name(
        self,
        *,
        access_token: str,
        drive_id: str,
        parent_item_id: str,
        exact_name: str,
    ) -> tuple[GraphExchangeItem, ...]:
        if not exact_name or "/" in exact_name or "\\" in exact_name:
            raise MicrosoftGraphError(
                "Microsoft Graph child name is invalid.",
                category="invalid_target",
                retryable=False,
            )
        payload = self._get(
            access_token=access_token,
            path=(
                f"/drives/{quote(drive_id, safe='')}/items/"
                f"{quote(parent_item_id, safe='')}/children"
            ),
            params={
                "$top": "100",
                "$select": "id,name,size,eTag,cTag,file,folder,parentReference",
            },
        )
        matches: list[GraphExchangeItem] = []
        for page_index in range(MAX_EXACT_CHILD_PAGES):
            values = payload.get("value")
            if not isinstance(values, list):
                raise MicrosoftGraphError("Microsoft Graph folder response is invalid.")
            matches.extend(
                self._exchange_item(value, expected_drive_id=drive_id)
                for value in values
                if isinstance(value, dict) and value.get("name") == exact_name
            )
            next_link = payload.get("@odata.nextLink")
            if next_link is None:
                return tuple(matches)
            if not isinstance(next_link, str) or not next_link:
                raise MicrosoftGraphError("Microsoft Graph pagination response is invalid.")
            if page_index + 1 >= MAX_EXACT_CHILD_PAGES:
                raise MicrosoftGraphError(
                    "Microsoft Graph exact-child lookup exceeded its bounded page limit.",
                    category="provider_listing_truncated",
                    retryable=False,
                )
            payload = self._get_url(
                access_token=access_token,
                url=next_link,
            )
        raise MicrosoftGraphError(
            "Microsoft Graph exact-child lookup exceeded its bounded page limit.",
            category="provider_listing_truncated",
            retryable=False,
        )

    def ensure_child_folder(
        self,
        *,
        access_token: str,
        drive_id: str,
        parent_item_id: str,
        exact_name: str,
    ) -> GraphMutationResult:
        matches = self.resolve_child_by_exact_name(
            access_token=access_token,
            drive_id=drive_id,
            parent_item_id=parent_item_id,
            exact_name=exact_name,
        )
        if len(matches) == 1 and matches[0].kind == "folder":
            return GraphMutationResult(GraphMutationStatus.CREATED, item=matches[0])
        if matches:
            return GraphMutationResult(GraphMutationStatus.COLLISION)
        url = (
            f"{GRAPH_BASE_URL}/drives/{quote(drive_id, safe='')}/items/"
            f"{quote(parent_item_id, safe='')}/children"
        )
        try:
            response = httpx.post(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "name": exact_name,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "fail",
                },
                timeout=self._timeout_seconds,
            )
        except httpx.HTTPError:
            return GraphMutationResult(GraphMutationStatus.OUTCOME_UNKNOWN)
        failure = self._mutation_failure(response)
        if failure is not None:
            return failure
        try:
            payload = response.json()
        except ValueError:
            return GraphMutationResult(GraphMutationStatus.OUTCOME_UNKNOWN)
        return GraphMutationResult(
            GraphMutationStatus.CREATED,
            item=self._exchange_item(payload, expected_drive_id=drive_id),
            provider_request_id=response.headers.get("request-id"),
        )

    def create_file(
        self,
        *,
        access_token: str,
        drive_id: str,
        parent_item_id: str,
        exact_name: str,
        content: bytes,
    ) -> GraphMutationResult:
        if (
            not exact_name
            or "/" in exact_name
            or "\\" in exact_name
            or len(content) > MAX_DOWNLOAD_BYTES
        ):
            return GraphMutationResult(GraphMutationStatus.REJECTED)
        matches = self.resolve_child_by_exact_name(
            access_token=access_token,
            drive_id=drive_id,
            parent_item_id=parent_item_id,
            exact_name=exact_name,
        )
        if matches:
            return GraphMutationResult(GraphMutationStatus.COLLISION)
        url = (
            f"{GRAPH_BASE_URL}/drives/{quote(drive_id, safe='')}/items/"
            f"{quote(parent_item_id, safe='')}:/"
            f"{quote(exact_name, safe='')}:/content"
        )
        try:
            response = httpx.put(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/octet-stream",
                    "If-None-Match": "*",
                },
                content=content,
                timeout=self._timeout_seconds,
            )
        except httpx.HTTPError:
            return GraphMutationResult(GraphMutationStatus.OUTCOME_UNKNOWN)
        failure = self._mutation_failure(response)
        if failure is not None:
            return failure
        try:
            payload = response.json()
        except ValueError:
            return GraphMutationResult(GraphMutationStatus.OUTCOME_UNKNOWN)
        return GraphMutationResult(
            GraphMutationStatus.CREATED,
            item=self._exchange_item(payload, expected_drive_id=drive_id),
            provider_request_id=response.headers.get("request-id"),
        )

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
