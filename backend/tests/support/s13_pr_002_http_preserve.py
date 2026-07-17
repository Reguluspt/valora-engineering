"""Shared exact HTTP rejection preservation contract for S13-PR-002.

Used by every retained endpoint N+1 rejection node so weaker “count-only /
no-Reserved-audit / key-set-only” helpers cannot silently reappear.
"""
from __future__ import annotations

import copy
import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.modules.excel_import.models import ImportSourceArtifact
from app.modules.project_master_data.models import (
    AuditEvent,
    ProjectAssetImportBatch,
    ProjectAssetImportStagingRow,
    ProjectAssetLine,
)

# Stable field lists — exact equality required on reject.
ARTIFACT_FIELDS = (
    "id",
    "organization_id",
    "project_id",
    "import_batch_id",
    "generation",
    "original_filename",
    "detected_format",
    "content_type",
    "file_size_bytes",
    "checksum_sha256",
    "storage_object_key",
    "storage_etag",
    "state",
    "adapter_name",
    "adapter_version",
    "adapter_metadata",
    "created_by_user_id",
    "available_at",
    "failed_at",
    "orphaned_at",
    "failure_code",
    "created_at",
    "updated_at",
)

BATCH_FIELDS = (
    "id",
    "organization_id",
    "project_id",
    "source_filename",
    "status",
    "total_rows",
    "valid_rows",
    "invalid_rows",
    "warning_rows",
    "created_by_user_id",
    "current_source_artifact_id",
    "created_at",
    "updated_at",
)

STAGING_FIELDS = (
    "id",
    "organization_id",
    "project_id",
    "import_batch_id",
    "source_row_number",
    "raw_values",
    "mapped_values",
    "normalized_preview",
    "validation_status",
    "validation_errors",
    "validation_warnings",
    "proposed_asset_name",
    "proposed_description",
    "proposed_quantity",
    "proposed_unit",
)

LINE_FIELDS = (
    "id",
    "project_id",
    "asset_name",
    "description",
    "quantity",
    "review_status",
    "validation_status",
)

AUDIT_FIELDS = (
    "id",
    "organization_id",
    "actor_user_id",
    "command_name",
    "event_name",
    "entity_type",
    "entity_id",
    "created_at",
    "correlation_id",
    "payload",
)


def _json_safe(value: Any) -> Any:
    """Deep-copy JSON-compatible values without retaining mutable aliases."""
    if value is None:
        return None
    return json.loads(json.dumps(value, default=str, sort_keys=True))


def _dt(value: Any) -> Any:
    if value is None:
        return None
    # Normalize timezone-aware/naive to ISO for stable equality across reloads.
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _uuid(value: Any) -> Any:
    if value is None:
        return None
    return str(value)


def _row_artifact(a: ImportSourceArtifact) -> dict[str, Any]:
    return {
        "id": _uuid(a.id),
        "organization_id": _uuid(a.organization_id),
        "project_id": _uuid(a.project_id),
        "import_batch_id": _uuid(a.import_batch_id),
        "generation": a.generation,
        "original_filename": a.original_filename,
        "detected_format": a.detected_format,
        "content_type": a.content_type,
        "file_size_bytes": a.file_size_bytes,
        "checksum_sha256": a.checksum_sha256,
        "storage_object_key": a.storage_object_key,
        "storage_etag": a.storage_etag,
        "state": a.state,
        "adapter_name": a.adapter_name,
        "adapter_version": a.adapter_version,
        "adapter_metadata": _json_safe(a.adapter_metadata or {}),
        "created_by_user_id": _uuid(a.created_by_user_id),
        "available_at": _dt(a.available_at),
        "failed_at": _dt(a.failed_at),
        "orphaned_at": _dt(a.orphaned_at),
        "failure_code": a.failure_code,
        "created_at": _dt(a.created_at),
        "updated_at": _dt(a.updated_at),
    }


def _row_batch(b: ProjectAssetImportBatch) -> dict[str, Any]:
    return {
        "id": _uuid(b.id),
        "organization_id": _uuid(b.organization_id),
        "project_id": _uuid(b.project_id),
        "source_filename": b.source_filename,
        "status": b.status,
        "total_rows": b.total_rows,
        "valid_rows": b.valid_rows,
        "invalid_rows": b.invalid_rows,
        "warning_rows": b.warning_rows,
        "created_by_user_id": _uuid(b.created_by_user_id),
        "current_source_artifact_id": _uuid(b.current_source_artifact_id),
        "created_at": _dt(b.created_at),
        "updated_at": _dt(b.updated_at),
    }


def _row_staging(s: ProjectAssetImportStagingRow) -> dict[str, Any]:
    return {
        "id": _uuid(s.id),
        "organization_id": _uuid(s.organization_id),
        "project_id": _uuid(s.project_id),
        "import_batch_id": _uuid(s.import_batch_id),
        "source_row_number": s.source_row_number,
        "raw_values": _json_safe(s.raw_values),
        "mapped_values": _json_safe(s.mapped_values),
        "normalized_preview": _json_safe(s.normalized_preview),
        "validation_status": s.validation_status,
        "validation_errors": _json_safe(s.validation_errors),
        "validation_warnings": _json_safe(s.validation_warnings),
        "proposed_asset_name": s.proposed_asset_name,
        "proposed_description": s.proposed_description,
        "proposed_quantity": s.proposed_quantity,
        "proposed_unit": s.proposed_unit,
    }


def _row_line(line: ProjectAssetLine) -> dict[str, Any]:
    return {
        "id": _uuid(line.id),
        "project_id": _uuid(line.project_id),
        "asset_name": line.asset_name,
        "description": line.description,
        "quantity": float(line.quantity) if line.quantity is not None else None,
        "review_status": line.review_status,
        "validation_status": line.validation_status,
    }


def _row_audit(a: AuditEvent) -> dict[str, Any]:
    return {
        "id": _uuid(a.id),
        "organization_id": _uuid(a.organization_id),
        "actor_user_id": _uuid(a.actor_user_id),
        "command_name": a.command_name,
        "event_name": a.event_name,
        "entity_type": a.entity_type,
        "entity_id": _uuid(a.entity_id),
        "created_at": _dt(a.created_at),
        "correlation_id": a.correlation_id,
        "payload": _json_safe(a.payload),
    }


def _as_uuid(value: Any):
    """Accept UUID instances or string UUIDs for SQLAlchemy UUID bind params."""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def snapshot_source_intake_preserve(
    db: Session,
    fake_storage,
    *,
    project_id,
    batch_id,
) -> dict[str, Any]:
    """Immutable deep snapshot of all preserve-relevant state before an HTTP reject."""
    db.expire_all()
    pid = _as_uuid(project_id)
    bid = _as_uuid(batch_id)
    arts = (
        db.query(ImportSourceArtifact)
        .order_by(ImportSourceArtifact.generation.asc(), ImportSourceArtifact.id.asc())
        .all()
    )
    batches = (
        db.query(ProjectAssetImportBatch)
        .filter(ProjectAssetImportBatch.id == bid)
        .all()
    )
    staging = (
        db.query(ProjectAssetImportStagingRow)
        .filter(ProjectAssetImportStagingRow.import_batch_id == bid)
        .order_by(ProjectAssetImportStagingRow.source_row_number.asc(), ProjectAssetImportStagingRow.id.asc())
        .all()
    )
    lines = (
        db.query(ProjectAssetLine)
        .filter(ProjectAssetLine.project_id == pid)
        .order_by(ProjectAssetLine.id.asc())
        .all()
    )
    audits = db.query(AuditEvent).order_by(AuditEvent.id.asc()).all()
    return {
        "objects": {k: bytes(v) for k, v in fake_storage._objects.items()},
        "content_types": dict(fake_storage._content_types),
        "artifacts": [_row_artifact(a) for a in arts],
        "batches": [_row_batch(b) for b in batches],
        "staging": [_row_staging(s) for s in staging],
        "lines": [_row_line(ln) for ln in lines],
        "audits": [_row_audit(a) for a in audits],
        "project_id": _uuid(pid),
        "batch_id": _uuid(bid),
    }


def assert_source_intake_preserve(db: Session, fake_storage, snap: dict[str, Any]) -> None:
    """Exact equality of every snapshot component after an HTTP rejection."""
    db.expire_all()
    after = snapshot_source_intake_preserve(
        db,
        fake_storage,
        project_id=snap["project_id"],
        batch_id=snap["batch_id"],
    )
    assert after["objects"] == snap["objects"], "object-store bytes changed on reject"
    assert after["content_types"] == snap["content_types"], "content_types changed on reject"
    assert after["artifacts"] == snap["artifacts"], "artifact rows changed on reject"
    assert after["batches"] == snap["batches"], "batch fields changed on reject"
    assert after["staging"] == snap["staging"], "staging rows changed on reject"
    assert after["lines"] == snap["lines"], "official lines changed on reject"
    assert after["audits"] == snap["audits"], "audit snapshot changed on reject"


def assert_http_rejection_preserve(
    res,
    *,
    status: int,
    error_code: str,
    db: Session,
    fake_storage,
    snap: dict[str, Any],
) -> None:
    """Unconditional status/error_code + full preservation contract."""
    assert res.status_code == status, res.text
    body = res.json()
    detail = body.get("detail")
    assert isinstance(detail, dict), f"detail must be mapping, got {type(detail)!r}: {detail!r}"
    assert detail.get("error_code") == error_code, detail
    assert_source_intake_preserve(db, fake_storage, snap)


def assert_audit_snapshot_detects_mutations() -> None:
    """Self-test: snapshot comparison detects insert/delete/payload mutation."""
    base = [
        {
            "id": "1",
            "organization_id": "o",
            "actor_user_id": "u",
            "command_name": "C",
            "event_name": "E",
            "entity_type": "T",
            "entity_id": "e",
            "created_at": "t",
            "correlation_id": None,
            "payload": {"k": "v"},
        }
    ]
    inserted = copy.deepcopy(base) + [
        {
            "id": "2",
            "organization_id": "o",
            "actor_user_id": "u",
            "command_name": "C2",
            "event_name": "E2",
            "entity_type": "T",
            "entity_id": "e2",
            "created_at": "t2",
            "correlation_id": None,
            "payload": {},
        }
    ]
    deleted: list = []
    mutated = copy.deepcopy(base)
    mutated[0]["payload"] = {"k": "mutated"}
    assert base != inserted
    assert base != deleted
    assert base != mutated
    # Deep-copy isolation: mutating after snapshot must not alter the original
    src = {"payload": {"nested": [1, 2]}}
    copied = _json_safe(src)
    src["payload"]["nested"].append(3)
    assert copied == {"payload": {"nested": [1, 2]}}
