"""Microsoft Graph and delegated OAuth ports for OneDrive Personal."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal, Mapping, Protocol


@dataclass(frozen=True)
class OAuthAuthorizationStart:
    authorization_url: str
    state: str
    flow_material: bytes


@dataclass(frozen=True)
class OAuthAuthorizationResult:
    consumer_issuer: str
    microsoft_account_subject: str
    access_token: str
    token_cache: bytes
    granted_scopes: frozenset[str]


@dataclass(frozen=True)
class OAuthAccessToken:
    access_token: str
    token_cache: bytes


@dataclass(frozen=True)
class GraphDrive:
    drive_id: str
    drive_type: str


@dataclass(frozen=True)
class GraphDriveItem:
    drive_id: str
    drive_item_id: str
    graph_version_id: str | None
    e_tag: str
    c_tag: str | None
    last_modified_at: datetime
    size_bytes: int
    name: str
    path: str | None
    web_url: str


@dataclass(frozen=True)
class GraphDriveEntry:
    drive_item_id: str
    kind: str
    name: str
    size_bytes: int | None
    last_modified_at: datetime | None
    web_url: str | None


@dataclass(frozen=True)
class GraphDriveChildren:
    entries: tuple[GraphDriveEntry, ...]
    truncated: bool


class GraphMutationStatus(StrEnum):
    CREATED = "CREATED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    COLLISION = "COLLISION"
    STALE_PRECONDITION = "STALE_PRECONDITION"
    UNAVAILABLE = "UNAVAILABLE"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class GraphExchangeItem:
    drive_id: str
    drive_item_id: str
    parent_item_id: str | None
    kind: Literal["folder", "file"]
    name: str
    size_bytes: int
    e_tag: str
    c_tag: str | None = None
    graph_version_id: str | None = None


@dataclass(frozen=True)
class GraphMutationResult:
    status: GraphMutationStatus
    item: GraphExchangeItem | None = None
    provider_request_id: str | None = None
    retry_after_seconds: int | None = None


class M365OAuthClient(Protocol):
    def begin(
        self, *, scope_profile: Literal["read_only", "exchange_write"] = "read_only"
    ) -> OAuthAuthorizationStart: ...

    def complete(
        self, *, flow_material: bytes, auth_response: Mapping[str, str]
    ) -> OAuthAuthorizationResult: ...

    def acquire_access_token(
        self,
        *,
        token_cache: bytes,
        scope_profile: Literal["read_only", "exchange_write"] = "read_only",
    ) -> OAuthAccessToken: ...


class M365GraphGateway(Protocol):
    def get_default_drive(self, *, access_token: str) -> GraphDrive: ...

    def get_drive_item(
        self, *, access_token: str, drive_id: str, drive_item_id: str
    ) -> GraphDriveItem: ...

    def get_drive_item_content(
        self, *, access_token: str, drive_id: str, drive_item_id: str
    ) -> bytes: ...

    def list_drive_children(
        self,
        *,
        access_token: str,
        drive_id: str,
        parent_item_id: str | None,
        limit: int,
    ) -> GraphDriveChildren: ...

    def get_app_root(self, *, access_token: str) -> GraphExchangeItem: ...

    def ensure_child_folder(
        self,
        *,
        access_token: str,
        drive_id: str,
        parent_item_id: str,
        exact_name: str,
    ) -> GraphMutationResult: ...

    def create_file(
        self,
        *,
        access_token: str,
        drive_id: str,
        parent_item_id: str,
        exact_name: str,
        content: bytes,
    ) -> GraphMutationResult: ...

    def get_exchange_item_by_id(
        self, *, access_token: str, drive_id: str, drive_item_id: str
    ) -> GraphExchangeItem: ...

    def resolve_child_by_exact_name(
        self,
        *,
        access_token: str,
        drive_id: str,
        parent_item_id: str,
        exact_name: str,
    ) -> tuple[GraphExchangeItem, ...]: ...
