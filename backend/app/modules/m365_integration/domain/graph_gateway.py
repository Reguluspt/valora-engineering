"""Microsoft Graph and delegated OAuth ports for OneDrive Personal."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Protocol


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


class M365OAuthClient(Protocol):
    def begin(self) -> OAuthAuthorizationStart: ...

    def complete(
        self, *, flow_material: bytes, auth_response: Mapping[str, str]
    ) -> OAuthAuthorizationResult: ...

    def acquire_access_token(self, *, token_cache: bytes) -> OAuthAccessToken: ...


class M365GraphGateway(Protocol):
    def get_default_drive(self, *, access_token: str) -> GraphDrive: ...

    def get_drive_item(
        self, *, access_token: str, drive_id: str, drive_item_id: str
    ) -> GraphDriveItem: ...

    def get_drive_item_content(
        self, *, access_token: str, drive_id: str, drive_item_id: str
    ) -> bytes: ...
