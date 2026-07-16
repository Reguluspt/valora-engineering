"""S13-PR-002: reserve/upload/finalize ImportSourceArtifact without staging mutation."""
from __future__ import annotations

import hashlib
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.modules.excel_import.application.adapters import detect_format_and_adapter
from app.modules.excel_import.application.parse_workbook import (
    get_request_size,
    sanitize_filename,
)
from app.modules.excel_import.domain.source_artifact import (
    DEFAULT_SOURCE_LIMITS,
    SourceArtifactLimits,
    SourceArtifactState,
    VALID_TRANSITIONS,
)
from app.modules.excel_import.domain.workbook_adapter import AdapterError
from app.modules.excel_import.infrastructure.object_storage import (
    ObjectStoragePort,
    get_object_storage,
)
from app.modules.excel_import.models import ImportSourceArtifact
from app.modules.project_master_data.models import (
    AuditEvent,
    Project,
    ProjectAssetImportBatch,
    ProjectAssetImportStagingRow,
)

# re-export for clarity
__all__ = [
    "upload_source_artifact",
    "list_source_artifacts",
    "get_source_artifact",
    "reconcile_source_artifacts",
    "count_staging_rows",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _content_type_for(fmt: str) -> str:
    if fmt == "xls":
        return "application/vnd.ms-excel"
    return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _build_object_key(org_id: uuid.UUID, project_id: uuid.UUID, batch_id: uuid.UUID, artifact_id: uuid.UUID) -> str:
    # Server-owned path from trusted IDs only — never raw filename
    return f"org/{org_id}/project/{project_id}/import-batch/{batch_id}/source/{artifact_id}"


def _assert_transition(current: str, new: SourceArtifactState) -> None:
    cur = SourceArtifactState(current)
    allowed = VALID_TRANSITIONS.get(cur, frozenset())
    if new not in allowed:
        raise HTTPException(status_code=409, detail="Chuyển trạng thái nguồn không hợp lệ.")


def _audit(
    db: Session,
    *,
    org_id: uuid.UUID,
    actor_id: uuid.UUID,
    event_name: str,
    entity_id: uuid.UUID,
    payload: dict[str, Any],
    correlation_id: str | None,
) -> None:
    db.add(
        AuditEvent(
            organization_id=org_id,
            actor_user_id=actor_id,
            event_name=event_name,
            entity_type="ImportSourceArtifact",
            entity_id=entity_id,
            payload=payload,
            correlation_id=correlation_id,
            command_name="UploadImportSourceArtifact",
        )
    )


def _spool_and_hash(
    file: UploadFile,
    limits: SourceArtifactLimits,
    *,
    suffix: str = ".bin",
) -> tuple[str, int, str]:
    """Stream to spool path with size limit; return (path, size, sha256 hex)."""
    h = hashlib.sha256()
    total = 0
    # openpyxl validates extension; keep original suffix (.xlsx/.xls)
    safe_suffix = suffix if suffix.startswith(".") else f".{suffix}"
    fd, path = tempfile.mkstemp(prefix="valora-src-", suffix=safe_suffix)
    os.close(fd)
    try:
        with open(path, "wb") as out:
            while True:
                chunk = file.file.read(limits.read_chunk_size)
                if not chunk:
                    break
                total += len(chunk)
                if total > limits.max_upload_bytes:
                    raise AdapterError(
                        413,
                        "upload_too_large",
                        "Kích thước tệp tải lên vượt quá giới hạn cho phép.",
                        "file_size",
                    )
                h.update(chunk)
                out.write(chunk)
        return path, total, h.hexdigest()
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise


def upload_source_artifact(
    db: Session,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    file: UploadFile,
    request,
    current_user,
    correlation_id: str | None = None,
    storage: ObjectStoragePort | None = None,
    limits: SourceArtifactLimits | None = None,
) -> ImportSourceArtifact:
    """
    Adaptive Intake v2 source intake.

    Does NOT create/modify staging rows or ProjectAssetLine.
    """
    limits = limits or DEFAULT_SOURCE_LIMITS
    storage = storage or get_object_storage()

    # Request size limit (S12-compatible)
    size_hdr = get_request_size(request)
    if size_hdr is not None and size_hdr < 0:
        raise HTTPException(status_code=400, detail="Kích thước yêu cầu HTTP không hợp lệ.")
    if size_hdr is not None and size_hdr > limits.max_request_bytes:
        raise HTTPException(
            status_code=413,
            detail="Kích thước yêu cầu HTTP vượt quá giới hạn cho phép.",
        )

    # Lock Project → batch
    project = (
        db.query(Project)
        .filter(Project.organization_id == org_id, Project.id == project_id)
        .with_for_update()
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    batch = (
        db.query(ProjectAssetImportBatch)
        .filter(
            ProjectAssetImportBatch.organization_id == org_id,
            ProjectAssetImportBatch.project_id == project_id,
            ProjectAssetImportBatch.id == batch_id,
        )
        .with_for_update()
        .first()
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found")

    sanitized = sanitize_filename(file.filename or "source.xlsx")
    ext = ""
    if "." in sanitized:
        ext = sanitized[sanitized.rfind(".") :].lower()
    path = None
    artifact: ImportSourceArtifact | None = None
    try:
        path, size, checksum = _spool_and_hash(file, limits, suffix=ext or ".bin")

        # Format + safety inspection before reservation can become available
        try:
            fmt, adapter = detect_format_and_adapter(path, sanitized)
            inspection = adapter.inspect(path)
        except AdapterError as ae:
            raise HTTPException(status_code=ae.status, detail=ae.detail) from ae

        last_gen = (
            db.query(ImportSourceArtifact.generation)
            .filter(ImportSourceArtifact.import_batch_id == batch_id)
            .order_by(ImportSourceArtifact.generation.desc())
            .first()
        )
        next_gen = (last_gen[0] if last_gen else 0) + 1
        artifact_id = uuid.uuid4()
        object_key = _build_object_key(org_id, project_id, batch_id, artifact_id)

        artifact = ImportSourceArtifact(
            id=artifact_id,
            organization_id=org_id,
            project_id=project_id,
            import_batch_id=batch_id,
            generation=next_gen,
            original_filename=sanitized,
            detected_format=fmt.value if hasattr(fmt, "value") else str(fmt),
            content_type=_content_type_for(str(fmt.value if hasattr(fmt, "value") else fmt)),
            file_size_bytes=size,
            checksum_sha256=checksum,
            storage_object_key=object_key,
            state=SourceArtifactState.PENDING.value,
            adapter_name=inspection.adapter_name,
            adapter_version=inspection.adapter_version,
            adapter_metadata={
                "sheet_names": list(inspection.sheet_names),
                "sheet_count": len(inspection.sheet_names),
                **(inspection.safe_metadata or {}),
            },
            created_by_user_id=current_user.id,
        )
        db.add(artifact)
        _audit(
            db,
            org_id=org_id,
            actor_id=current_user.id,
            event_name="ImportSourceArtifactReserved",
            entity_id=artifact_id,
            payload={
                "import_batch_id": str(batch_id),
                "generation": next_gen,
                "detected_format": artifact.detected_format,
                "checksum_sha256": checksum,
                "file_size_bytes": size,
            },
            correlation_id=correlation_id,
        )
        db.commit()

        # Object write outside final pointer transaction
        try:
            storage.ensure_bucket()
            with open(path, "rb") as stream:
                st = storage.put_stream(
                    object_key,
                    stream,
                    content_type=artifact.content_type,
                    expected_size=size,
                )
            # Strong verify: re-hash object bytes
            with storage.open_stream(object_key) as rs:
                rh = hashlib.sha256()
                while True:
                    chunk = rs.read(limits.read_chunk_size)
                    if not chunk:
                        break
                    rh.update(chunk)
                if rh.hexdigest() != checksum:
                    try:
                        storage.delete(object_key)
                    except Exception:
                        pass
                    raise RuntimeError("checksum_mismatch")
            etag = st.etag
        except Exception as exc:
            # Mark failed; keep prior current
            art = (
                db.query(ImportSourceArtifact)
                .filter(ImportSourceArtifact.id == artifact_id)
                .with_for_update()
                .first()
            )
            if art and art.state == SourceArtifactState.PENDING.value:
                _assert_transition(art.state, SourceArtifactState.FAILED)
                art.state = SourceArtifactState.FAILED.value
                art.failed_at = _utcnow()
                art.failure_code = type(exc).__name__[:64]
                _audit(
                    db,
                    org_id=org_id,
                    actor_id=current_user.id,
                    event_name="ImportSourceArtifactFailed",
                    entity_id=artifact_id,
                    payload={
                        "import_batch_id": str(batch_id),
                        "generation": next_gen,
                        "failure_code": art.failure_code,
                    },
                    correlation_id=correlation_id,
                )
                db.commit()
            raise HTTPException(
                status_code=500,
                detail="Không thể lưu tệp nguồn an toàn. Vui lòng thử lại.",
            ) from exc

        # Finalize available + current pointer
        project = (
            db.query(Project)
            .filter(Project.organization_id == org_id, Project.id == project_id)
            .with_for_update()
            .first()
        )
        batch = (
            db.query(ProjectAssetImportBatch)
            .filter(
                ProjectAssetImportBatch.organization_id == org_id,
                ProjectAssetImportBatch.project_id == project_id,
                ProjectAssetImportBatch.id == batch_id,
            )
            .with_for_update()
            .first()
        )
        art = (
            db.query(ImportSourceArtifact)
            .filter(
                ImportSourceArtifact.id == artifact_id,
                ImportSourceArtifact.organization_id == org_id,
            )
            .with_for_update()
            .first()
        )
        if not project or not batch or not art:
            raise HTTPException(status_code=404, detail="Import batch not found")

        # Stale finish: if a higher successful generation already current, do not win
        if batch.current_source_artifact_id:
            current = (
                db.query(ImportSourceArtifact)
                .filter(ImportSourceArtifact.id == batch.current_source_artifact_id)
                .first()
            )
            if current and current.generation > art.generation and current.state == "available":
                _assert_transition(art.state, SourceArtifactState.ORPHANED)
                art.state = SourceArtifactState.ORPHANED.value
                art.orphaned_at = _utcnow()
                art.failure_code = "stale_generation"
                _audit(
                    db,
                    org_id=org_id,
                    actor_id=current_user.id,
                    event_name="ImportSourceArtifactOrphaned",
                    entity_id=artifact_id,
                    payload={
                        "import_batch_id": str(batch_id),
                        "generation": art.generation,
                        "reason": "stale_generation",
                    },
                    correlation_id=correlation_id,
                )
                db.commit()
                return art

        _assert_transition(art.state, SourceArtifactState.AVAILABLE)
        art.state = SourceArtifactState.AVAILABLE.value
        art.available_at = _utcnow()
        art.storage_etag = etag
        batch.current_source_artifact_id = art.id
        _audit(
            db,
            org_id=org_id,
            actor_id=current_user.id,
            event_name="ImportSourceArtifactAvailable",
            entity_id=artifact_id,
            payload={
                "import_batch_id": str(batch_id),
                "generation": art.generation,
                "checksum_sha256": art.checksum_sha256,
                "file_size_bytes": art.file_size_bytes,
                "detected_format": art.detected_format,
            },
            correlation_id=correlation_id,
        )
        db.commit()
        db.refresh(art)
        return art

    except HTTPException:
        raise
    except AdapterError as ae:
        raise HTTPException(status_code=ae.status, detail=ae.detail) from ae
    finally:
        if path and os.path.exists(path):
            try:
                os.unlink(path)
            except OSError:
                pass


def list_source_artifacts(
    db: Session,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
) -> list[ImportSourceArtifact]:
    batch = (
        db.query(ProjectAssetImportBatch)
        .filter(
            ProjectAssetImportBatch.organization_id == org_id,
            ProjectAssetImportBatch.project_id == project_id,
            ProjectAssetImportBatch.id == batch_id,
        )
        .first()
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found")
    return (
        db.query(ImportSourceArtifact)
        .filter(
            ImportSourceArtifact.organization_id == org_id,
            ImportSourceArtifact.project_id == project_id,
            ImportSourceArtifact.import_batch_id == batch_id,
        )
        .order_by(ImportSourceArtifact.generation.asc())
        .all()
    )


def get_source_artifact(
    db: Session,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    artifact_id: uuid.UUID,
) -> ImportSourceArtifact:
    art = (
        db.query(ImportSourceArtifact)
        .filter(
            ImportSourceArtifact.organization_id == org_id,
            ImportSourceArtifact.project_id == project_id,
            ImportSourceArtifact.import_batch_id == batch_id,
            ImportSourceArtifact.id == artifact_id,
        )
        .first()
    )
    if not art:
        raise HTTPException(status_code=404, detail="Source artifact not found")
    return art


def reconcile_source_artifacts(
    db: Session,
    *,
    storage: ObjectStoragePort | None = None,
    max_items: int | None = None,
    actor_id: uuid.UUID | None = None,
    org_id: uuid.UUID | None = None,
) -> dict[str, int]:
    """
    Bounded reconciler for pending/failed/orphaned artifacts.

    - Does not delete available successful generations or current pointers.
    - Deletes objects only for orphaned rows past retention when unreferenced.
    """
    limits = DEFAULT_SOURCE_LIMITS
    storage = storage or get_object_storage()
    max_items = max_items if max_items is not None else limits.reconcilers_max_items
    cutoff = _utcnow().timestamp() - limits.orphan_retention_seconds

    q = db.query(ImportSourceArtifact).filter(
        ImportSourceArtifact.state.in_(
            [
                SourceArtifactState.PENDING.value,
                SourceArtifactState.FAILED.value,
                SourceArtifactState.ORPHANED.value,
            ]
        )
    )
    if org_id is not None:
        q = q.filter(ImportSourceArtifact.organization_id == org_id)
    rows = q.order_by(ImportSourceArtifact.created_at.asc()).limit(max_items).all()

    scanned = 0
    marked_orphan = 0
    deleted = 0
    for art in rows:
        scanned += 1
        batch = (
            db.query(ProjectAssetImportBatch)
            .filter(ProjectAssetImportBatch.id == art.import_batch_id)
            .with_for_update()
            .first()
        )
        if not batch:
            continue
        # Never touch current
        if batch.current_source_artifact_id == art.id:
            continue
        # Never delete available history
        if art.state == SourceArtifactState.AVAILABLE.value:
            continue

        # Pending with object present long enough → orphan for later cleanup
        if art.state == SourceArtifactState.PENDING.value:
            st = storage.head(art.storage_object_key)
            if st is not None and art.created_at and art.created_at.timestamp() < cutoff:
                art2 = (
                    db.query(ImportSourceArtifact)
                    .filter(ImportSourceArtifact.id == art.id)
                    .with_for_update()
                    .first()
                )
                if art2 and art2.state == SourceArtifactState.PENDING.value:
                    if batch.current_source_artifact_id != art2.id:
                        _assert_transition(art2.state, SourceArtifactState.ORPHANED)
                        art2.state = SourceArtifactState.ORPHANED.value
                        art2.orphaned_at = _utcnow()
                        marked_orphan += 1
            continue

        if art.state == SourceArtifactState.ORPHANED.value:
            if art.orphaned_at and art.orphaned_at.timestamp() < cutoff:
                # Re-check under lock
                art2 = (
                    db.query(ImportSourceArtifact)
                    .filter(ImportSourceArtifact.id == art.id)
                    .with_for_update()
                    .first()
                )
                batch2 = (
                    db.query(ProjectAssetImportBatch)
                    .filter(ProjectAssetImportBatch.id == art.import_batch_id)
                    .with_for_update()
                    .first()
                )
                if not art2 or not batch2:
                    continue
                if batch2.current_source_artifact_id == art2.id:
                    continue
                if art2.state != SourceArtifactState.ORPHANED.value:
                    continue
                key = art2.storage_object_key
                storage.delete(key)
                if actor_id:
                    _audit(
                        db,
                        org_id=art2.organization_id,
                        actor_id=actor_id,
                        event_name="ImportSourceArtifactObjectDeleted",
                        entity_id=art2.id,
                        payload={
                            "import_batch_id": str(art2.import_batch_id),
                            "generation": art2.generation,
                        },
                        correlation_id=None,
                    )
                deleted += 1
    db.commit()
    return {"scanned": scanned, "marked_orphan": marked_orphan, "deleted_objects": deleted}


def count_staging_rows(db: Session, batch_id: uuid.UUID) -> int:
    return (
        db.query(ProjectAssetImportStagingRow)
        .filter(ProjectAssetImportStagingRow.import_batch_id == batch_id)
        .count()
    )
