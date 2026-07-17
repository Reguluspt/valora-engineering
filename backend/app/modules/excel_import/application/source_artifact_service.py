"""S13-PR-002: reserve/upload/finalize ImportSourceArtifact without staging mutation."""
from __future__ import annotations

import hashlib
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

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
    ObjectNotFound,
    ObjectStorageError,
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

__all__ = [
    "upload_source_artifact",
    "list_source_artifacts",
    "get_source_artifact",
    "reconcile_source_artifacts",
    "count_staging_rows",
    "is_source_artifact_referenced",
]

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _content_type_for(fmt: str) -> str:
    if fmt == "xls":
        return "application/vnd.ms-excel"
    return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _build_object_key(
    org_id: uuid.UUID, project_id: uuid.UUID, batch_id: uuid.UUID, artifact_id: uuid.UUID
) -> str:
    return f"org/{org_id}/project/{project_id}/import-batch/{batch_id}/source/{artifact_id}"


def _normalize_checksum(hex_digest: str) -> str:
    out = hex_digest.lower()
    if not _HEX64.match(out):
        raise RuntimeError("invalid_checksum")
    return out


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
    command_name: str = "UploadImportSourceArtifact",
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
            command_name=command_name,
        )
    )


def is_source_artifact_referenced(
    db: Session,
    artifact: ImportSourceArtifact,
) -> bool:
    """
    Extension point: future audit/review references may block object delete.

    Protected when:
    - successful available history (content identity must not be deleted)
    - current pointer on any batch
    """
    if artifact.state == SourceArtifactState.AVAILABLE.value:
        return True
    pointed = (
        db.query(ProjectAssetImportBatch.id)
        .filter(ProjectAssetImportBatch.current_source_artifact_id == artifact.id)
        .first()
    )
    return pointed is not None


def _sha256_object(storage: ObjectStoragePort, key: str, *, chunk_size: int) -> str:
    """
    Stream object and return lowercase hex digest.

    Raises:
      ObjectNotFound — exact missing key
      ObjectStorageError — infrastructure/read failure (never content mismatch)
    """
    try:
        h = hashlib.sha256()
        with storage.open_stream(key) as rs:
            while True:
                chunk = rs.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return _normalize_checksum(h.hexdigest())
    except ObjectNotFound:
        raise
    except ObjectStorageError:
        raise
    except Exception as exc:
        # Do not relabel infra/I/O as checksum corruption
        raise ObjectStorageError("hash_stream_failed", type(exc).__name__) from exc


def _spool_and_hash(
    file: UploadFile,
    limits: SourceArtifactLimits,
    *,
    suffix: str = ".bin",
) -> tuple[str, int, str]:
    h = hashlib.sha256()
    total = 0
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
        return path, total, _normalize_checksum(h.hexdigest())
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise


def _mark_failed(
    db: Session,
    *,
    artifact_id: uuid.UUID,
    org_id: uuid.UUID,
    actor_id: uuid.UUID,
    batch_id: uuid.UUID,
    generation: int,
    failure_code: str,
    correlation_id: str | None,
) -> None:
    art = (
        db.query(ImportSourceArtifact)
        .filter(ImportSourceArtifact.id == artifact_id)
        .with_for_update()
        .first()
    )
    if not art or art.state != SourceArtifactState.PENDING.value:
        return
    _assert_transition(art.state, SourceArtifactState.FAILED)
    art.state = SourceArtifactState.FAILED.value
    art.failed_at = _utcnow()
    art.failure_code = failure_code[:64]
    _audit(
        db,
        org_id=org_id,
        actor_id=actor_id,
        event_name="ImportSourceArtifactFailed",
        entity_id=artifact_id,
        payload={
            "import_batch_id": str(batch_id),
            "generation": generation,
            "failure_code": art.failure_code,
        },
        correlation_id=correlation_id,
    )
    db.commit()


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

    Full adapter safety inspection runs before DB reservation and object write.
    Does NOT create/modify staging rows or ProjectAssetLine.
    """
    limits = limits or DEFAULT_SOURCE_LIMITS
    storage = storage or get_object_storage()

    size_hdr = get_request_size(request)
    if size_hdr is not None and size_hdr < 0:
        raise HTTPException(status_code=400, detail="Kích thước yêu cầu HTTP không hợp lệ.")
    if size_hdr is not None and size_hdr > limits.max_request_bytes:
        raise HTTPException(
            status_code=413,
            detail="Kích thước yêu cầu HTTP vượt quá giới hạn cho phép.",
        )

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
    artifact_id: uuid.UUID | None = None
    next_gen = 0
    try:
        path, size, checksum = _spool_and_hash(file, limits, suffix=ext or ".bin")

        # Full bounded safety inspection BEFORE reservation/object write
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

        failure_code = "object_write_failed"
        try:
            storage.ensure_bucket()
            with open(path, "rb") as stream:
                st = storage.put_stream(
                    object_key,
                    stream,
                    content_type=artifact.content_type,
                    expected_size=size,
                )
            with storage.open_stream(object_key) as rs:
                rh = hashlib.sha256()
                while True:
                    chunk = rs.read(limits.read_chunk_size)
                    if not chunk:
                        break
                    rh.update(chunk)
                got = _normalize_checksum(rh.hexdigest())
                if got != checksum:
                    failure_code = "checksum_mismatch"
                    raise RuntimeError("checksum_mismatch")
            etag = st.etag
        except Exception as exc:
            if isinstance(exc, ObjectStorageError):
                failure_code = exc.code[:64]
            elif "checksum" in str(exc).lower():
                failure_code = "checksum_mismatch"
            elif isinstance(exc, ObjectNotFound):
                failure_code = "object_missing"
            else:
                failure_code = type(exc).__name__[:64]
            # Residual object may remain on checksum mismatch after put — leave for reconciler
            _mark_failed(
                db,
                artifact_id=artifact_id,
                org_id=org_id,
                actor_id=current_user.id,
                batch_id=batch_id,
                generation=next_gen,
                failure_code=failure_code,
                correlation_id=correlation_id,
            )
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

        # Stale finish: newer available current already wins — this pending → failed/orphan path
        if batch.current_source_artifact_id:
            current = (
                db.query(ImportSourceArtifact)
                .filter(ImportSourceArtifact.id == batch.current_source_artifact_id)
                .first()
            )
            if (
                current
                and current.generation > art.generation
                and current.state == SourceArtifactState.AVAILABLE.value
            ):
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
        # Current pointer only to same-batch artifact
        if art.import_batch_id != batch.id:
            raise HTTPException(status_code=500, detail="Không thể lưu tệp nguồn an toàn. Vui lòng thử lại.")
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
    reference_check: Callable[[Session, ImportSourceArtifact], bool] | None = None,
) -> dict[str, int]:
    """
    Bounded reconciler for pending/failed/orphaned artifacts.

    Per-item commit: one item failure cannot roll back earlier durable outcomes.
    Counters update only after successful item commit.
    """
    if org_id is None:
        raise HTTPException(status_code=400, detail="Phạm vi tổ chức là bắt buộc cho đối soát.")
    if actor_id is None:
        raise HTTPException(status_code=400, detail="Tác nhân hệ thống là bắt buộc cho đối soát.")

    limits = DEFAULT_SOURCE_LIMITS
    storage = storage or get_object_storage()
    max_items = max_items if max_items is not None else limits.reconcilers_max_items
    if max_items < 1:
        raise HTTPException(status_code=400, detail="max_items phải >= 1.")
    ref_check = reference_check or is_source_artifact_referenced
    now_ts = _utcnow().timestamp()
    cutoff = now_ts - limits.orphan_retention_seconds

    # Snapshot ids first so later commits do not affect cursor; oldest first
    id_rows = (
        db.query(ImportSourceArtifact.id)
        .filter(
            ImportSourceArtifact.organization_id == org_id,
            ImportSourceArtifact.state.in_(
                [
                    SourceArtifactState.PENDING.value,
                    SourceArtifactState.FAILED.value,
                    SourceArtifactState.ORPHANED.value,
                ]
            ),
        )
        .order_by(ImportSourceArtifact.created_at.asc(), ImportSourceArtifact.id.asc())
        .limit(max_items)
        .all()
    )
    artifact_ids = [r[0] for r in id_rows]

    scanned = 0
    marked_orphan = 0
    marked_failed = 0
    deleted = 0
    errors = 0

    for art_id in artifact_ids:
        scanned += 1
        try:
            # Ensure clean session per item
            try:
                db.rollback()
            except Exception:
                pass

            art = (
                db.query(ImportSourceArtifact)
                .filter(
                    ImportSourceArtifact.id == art_id,
                    ImportSourceArtifact.organization_id == org_id,
                )
                .with_for_update()
                .first()
            )
            if not art:
                continue
            batch = (
                db.query(ProjectAssetImportBatch)
                .filter(
                    ProjectAssetImportBatch.id == art.import_batch_id,
                    ProjectAssetImportBatch.organization_id == org_id,
                )
                .with_for_update()
                .first()
            )
            if not batch:
                continue
            if batch.current_source_artifact_id == art.id:
                continue
            if ref_check(db, art):
                continue

            created_ts = art.created_at.timestamp() if art.created_at else now_ts
            past_retention = created_ts < cutoff
            item_failed = 0
            item_orphan = 0
            item_deleted = 0

            if art.state == SourceArtifactState.PENDING.value:
                try:
                    st = storage.head(art.storage_object_key)
                except ObjectStorageError:
                    errors += 1
                    db.rollback()
                    continue
                if st is None:
                    if past_retention and not ref_check(db, art):
                        _assert_transition(art.state, SourceArtifactState.FAILED)
                        art.state = SourceArtifactState.FAILED.value
                        art.failed_at = _utcnow()
                        art.failure_code = "pending_object_missing"
                        _audit(
                            db,
                            org_id=org_id,
                            actor_id=actor_id,
                            event_name="ImportSourceArtifactFailed",
                            entity_id=art.id,
                            payload={
                                "import_batch_id": str(art.import_batch_id),
                                "generation": art.generation,
                                "failure_code": art.failure_code,
                            },
                            correlation_id=None,
                            command_name="ReconcileImportSourceArtifact",
                        )
                        item_failed = 1
                else:
                    failure_code = None
                    if st.size != art.file_size_bytes:
                        failure_code = "size_mismatch"
                    else:
                        try:
                            digest = _sha256_object(
                                storage,
                                art.storage_object_key,
                                chunk_size=limits.read_chunk_size,
                            )
                            if digest != art.checksum_sha256:
                                failure_code = "checksum_mismatch"
                        except ObjectNotFound:
                            failure_code = "pending_object_missing"
                        except ObjectStorageError:
                            # Infrastructure — do not mutate content truth
                            errors += 1
                            db.rollback()
                            continue
                    if failure_code and not ref_check(db, art):
                        _assert_transition(art.state, SourceArtifactState.FAILED)
                        art.state = SourceArtifactState.FAILED.value
                        art.failed_at = _utcnow()
                        art.failure_code = failure_code
                        _audit(
                            db,
                            org_id=org_id,
                            actor_id=actor_id,
                            event_name="ImportSourceArtifactFailed",
                            entity_id=art.id,
                            payload={
                                "import_batch_id": str(art.import_batch_id),
                                "generation": art.generation,
                                "failure_code": art.failure_code,
                            },
                            correlation_id=None,
                            command_name="ReconcileImportSourceArtifact",
                        )
                        item_failed = 1
                    elif (
                        not failure_code
                        and past_retention
                        and batch.current_source_artifact_id != art.id
                        and not ref_check(db, art)
                    ):
                        _assert_transition(art.state, SourceArtifactState.ORPHANED)
                        art.state = SourceArtifactState.ORPHANED.value
                        art.orphaned_at = _utcnow()
                        _audit(
                            db,
                            org_id=org_id,
                            actor_id=actor_id,
                            event_name="ImportSourceArtifactOrphaned",
                            entity_id=art.id,
                            payload={
                                "import_batch_id": str(art.import_batch_id),
                                "generation": art.generation,
                                "reason": "pending_retention",
                            },
                            correlation_id=None,
                            command_name="ReconcileImportSourceArtifact",
                        )
                        item_orphan = 1

            elif art.state == SourceArtifactState.FAILED.value:
                try:
                    st = storage.head(art.storage_object_key)
                except ObjectStorageError:
                    errors += 1
                    db.rollback()
                    continue
                if st is not None and past_retention and not ref_check(db, art):
                    _assert_transition(art.state, SourceArtifactState.ORPHANED)
                    art.state = SourceArtifactState.ORPHANED.value
                    art.orphaned_at = _utcnow()
                    _audit(
                        db,
                        org_id=org_id,
                        actor_id=actor_id,
                        event_name="ImportSourceArtifactOrphaned",
                        entity_id=art.id,
                        payload={
                            "import_batch_id": str(art.import_batch_id),
                            "generation": art.generation,
                            "reason": "failed_residual_object",
                        },
                        correlation_id=None,
                        command_name="ReconcileImportSourceArtifact",
                    )
                    item_orphan = 1

            elif art.state == SourceArtifactState.ORPHANED.value:
                orphan_ts = art.orphaned_at.timestamp() if art.orphaned_at else created_ts
                if orphan_ts < cutoff:
                    if batch.current_source_artifact_id == art.id:
                        db.rollback()
                        continue
                    # Late re-check under lock immediately before delete
                    if ref_check(db, art):
                        db.rollback()
                        continue
                    key = art.storage_object_key
                    try:
                        storage.delete(key)
                    except ObjectStorageError:
                        errors += 1
                        db.rollback()
                        continue
                    try:
                        if storage.head(key) is not None:
                            errors += 1
                            db.rollback()
                            continue
                    except ObjectStorageError:
                        errors += 1
                        db.rollback()
                        continue
                    # Final ref re-check before durable audit (race protection)
                    if ref_check(db, art):
                        # Object may already be deleted; do not claim Object-deleted audit
                        db.rollback()
                        continue
                    _audit(
                        db,
                        org_id=org_id,
                        actor_id=actor_id,
                        event_name="ImportSourceArtifactObjectDeleted",
                        entity_id=art.id,
                        payload={
                            "import_batch_id": str(art.import_batch_id),
                            "generation": art.generation,
                        },
                        correlation_id=None,
                        command_name="ReconcileImportSourceArtifact",
                    )
                    item_deleted = 1

            db.commit()
            marked_failed += item_failed
            marked_orphan += item_orphan
            deleted += item_deleted
        except Exception:
            errors += 1
            try:
                db.rollback()
            except Exception:
                pass
            continue

    return {
        "scanned": scanned,
        "marked_orphan": marked_orphan,
        "marked_failed": marked_failed,
        "deleted_objects": deleted,
        "errors": errors,
    }


def count_staging_rows(db: Session, batch_id: uuid.UUID) -> int:
    return (
        db.query(ProjectAssetImportStagingRow)
        .filter(ProjectAssetImportStagingRow.import_batch_id == batch_id)
        .count()
    )
