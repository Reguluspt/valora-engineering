"""Deterministic non-live Graph fake for the bounded Exchange contract."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.modules.m365_integration.domain.graph_gateway import (
    GraphDrive,
    GraphDriveChildren,
    GraphDriveEntry,
    GraphDriveItem,
    GraphExchangeItem,
    GraphMutationResult,
    GraphMutationStatus,
)


class InMemoryM365GraphGateway:
    """One-drive fake with explicit lost-response and collision behavior."""

    def __init__(self, *, drive_id: str = "fake-personal-drive") -> None:
        self.drive_id = drive_id
        self.app_root_item_id = "approot"
        self.create_calls = 0
        self.ensure_calls = 0
        self._fault: str | None = None
        self._items: dict[str, GraphExchangeItem] = {
            self.app_root_item_id: GraphExchangeItem(
                drive_id=drive_id,
                drive_item_id=self.app_root_item_id,
                parent_item_id=None,
                kind="folder",
                name="approot",
                size_bytes=0,
                e_tag="approot-etag",
            )
        }
        self._content: dict[str, bytes] = {}

    def set_fault(self, fault: str | None) -> None:
        self._fault = fault

    def _new_item(
        self, *, parent_item_id: str, name: str, kind: str, content: bytes = b""
    ) -> GraphExchangeItem:
        item_id = uuid.uuid4().hex
        item = GraphExchangeItem(
            drive_id=self.drive_id,
            drive_item_id=item_id,
            parent_item_id=parent_item_id,
            kind="folder" if kind == "folder" else "file",
            name=name,
            size_bytes=len(content),
            e_tag=f"etag-{item_id}",
            c_tag=f"ctag-{item_id}",
        )
        self._items[item_id] = item
        if kind == "file":
            self._content[item_id] = content
        return item

    def seed_file(self, *, parent_item_id: str, name: str, content: bytes) -> GraphExchangeItem:
        return self._new_item(
            parent_item_id=parent_item_id, name=name, kind="file", content=content
        )

    def replace_file_content(self, *, drive_item_id: str, content: bytes) -> GraphExchangeItem:
        current = self._items[drive_item_id]
        replacement = GraphExchangeItem(
            drive_id=current.drive_id,
            drive_item_id=current.drive_item_id,
            parent_item_id=current.parent_item_id,
            kind="file",
            name=current.name,
            size_bytes=len(content),
            e_tag=f"etag-{uuid.uuid4().hex}",
            c_tag=f"ctag-{uuid.uuid4().hex}",
        )
        self._items[drive_item_id] = replacement
        self._content[drive_item_id] = content
        return replacement

    def rename_item(self, *, drive_item_id: str, name: str) -> None:
        current = self._items[drive_item_id]
        self._items[drive_item_id] = GraphExchangeItem(
            **{**current.__dict__, "name": name, "e_tag": f"etag-{uuid.uuid4().hex}"}
        )

    def move_item(self, *, drive_item_id: str, parent_item_id: str) -> None:
        current = self._items[drive_item_id]
        self._items[drive_item_id] = GraphExchangeItem(
            **{
                **current.__dict__,
                "parent_item_id": parent_item_id,
                "e_tag": f"etag-{uuid.uuid4().hex}",
            }
        )

    def delete_item(self, *, drive_item_id: str) -> None:
        self._items.pop(drive_item_id, None)
        self._content.pop(drive_item_id, None)

    def get_default_drive(self, *, access_token: str) -> GraphDrive:
        del access_token
        return GraphDrive(drive_id=self.drive_id, drive_type="personal")

    def get_app_root(self, *, access_token: str) -> GraphExchangeItem:
        del access_token
        return self._items[self.app_root_item_id]

    def resolve_child_by_exact_name(
        self,
        *,
        access_token: str,
        drive_id: str,
        parent_item_id: str,
        exact_name: str,
    ) -> tuple[GraphExchangeItem, ...]:
        del access_token
        if drive_id != self.drive_id:
            return ()
        return tuple(
            item
            for item in self._items.values()
            if item.parent_item_id == parent_item_id and item.name == exact_name
        )

    def ensure_child_folder(
        self,
        *,
        access_token: str,
        drive_id: str,
        parent_item_id: str,
        exact_name: str,
    ) -> GraphMutationResult:
        self.ensure_calls += 1
        matches = self.resolve_child_by_exact_name(
            access_token=access_token,
            drive_id=drive_id,
            parent_item_id=parent_item_id,
            exact_name=exact_name,
        )
        if len(matches) > 1 or (matches and matches[0].kind != "folder"):
            return GraphMutationResult(GraphMutationStatus.COLLISION)
        if matches:
            return GraphMutationResult(GraphMutationStatus.CREATED, item=matches[0])
        if parent_item_id not in self._items or self._items[parent_item_id].kind != "folder":
            return GraphMutationResult(GraphMutationStatus.REJECTED)
        return GraphMutationResult(
            GraphMutationStatus.CREATED,
            item=self._new_item(
                parent_item_id=parent_item_id, name=exact_name, kind="folder"
            ),
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
        self.create_calls += 1
        if self._fault == "before_send_unavailable":
            return GraphMutationResult(GraphMutationStatus.UNAVAILABLE)
        matches = self.resolve_child_by_exact_name(
            access_token=access_token,
            drive_id=drive_id,
            parent_item_id=parent_item_id,
            exact_name=exact_name,
        )
        if matches:
            return GraphMutationResult(GraphMutationStatus.COLLISION)
        if parent_item_id not in self._items or self._items[parent_item_id].kind != "folder":
            return GraphMutationResult(GraphMutationStatus.REJECTED)
        item = self._new_item(
            parent_item_id=parent_item_id,
            name=exact_name,
            kind="file",
            content=content,
        )
        if self._fault == "after_commit_unknown":
            return GraphMutationResult(GraphMutationStatus.OUTCOME_UNKNOWN)
        return GraphMutationResult(GraphMutationStatus.CREATED, item=item)

    def get_exchange_item_by_id(
        self, *, access_token: str, drive_id: str, drive_item_id: str
    ) -> GraphExchangeItem:
        del access_token
        if drive_id != self.drive_id or drive_item_id not in self._items:
            raise KeyError(drive_item_id)
        return self._items[drive_item_id]

    def get_drive_item(
        self, *, access_token: str, drive_id: str, drive_item_id: str
    ) -> GraphDriveItem:
        item = self.get_exchange_item_by_id(
            access_token=access_token, drive_id=drive_id, drive_item_id=drive_item_id
        )
        if item.kind != "file":
            raise KeyError(drive_item_id)
        return GraphDriveItem(
            drive_id=drive_id,
            drive_item_id=drive_item_id,
            graph_version_id=item.graph_version_id,
            e_tag=item.e_tag,
            c_tag=item.c_tag,
            last_modified_at=datetime.now(timezone.utc),
            size_bytes=item.size_bytes,
            name=item.name,
            path=None,
            web_url=f"https://example.invalid/{drive_item_id}",
        )

    def get_drive_item_content(
        self, *, access_token: str, drive_id: str, drive_item_id: str
    ) -> bytes:
        self.get_exchange_item_by_id(
            access_token=access_token, drive_id=drive_id, drive_item_id=drive_item_id
        )
        return self._content[drive_item_id]

    def list_drive_children(
        self,
        *,
        access_token: str,
        drive_id: str,
        parent_item_id: str | None,
        limit: int,
    ) -> GraphDriveChildren:
        del access_token
        parent = parent_item_id or self.app_root_item_id
        items = [
            item
            for item in self._items.values()
            if item.parent_item_id == parent and item.drive_id == drive_id
        ]
        return GraphDriveChildren(
            entries=tuple(
                GraphDriveEntry(
                    drive_item_id=item.drive_item_id,
                    kind="folder" if item.kind == "folder" else "docx",
                    name=item.name,
                    size_bytes=item.size_bytes if item.kind == "file" else None,
                    last_modified_at=datetime.now(timezone.utc),
                    web_url=None,
                )
                for item in items[:limit]
            ),
            truncated=len(items) > limit,
        )
