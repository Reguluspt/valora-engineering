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
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session, sessionmaker

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
    "set_reconcile_work_session_factory",
    "set_source_limits_override",
    "set_pointer_probe_hook",
]

_HEX64 = re.compile(r"^[0-9a-f]{64}$")

# Test/injection seams (None = production defaults)
_work_session_factory: Callable[[Any], Session] | None = None
_source_limits_override: SourceArtifactLimits | None = None
_pointer_probe_hook: Callable[[], None] | None = None


def set_reconcile_work_session_factory(
    factory: Callable[[Any], Session] | None,
) -> None:
    """Inject dedicated work-session factory for reconciler failpoint tests."""
    global _work_session_factory
    _work_session_factory = factory


def set_source_limits_override(limits: SourceArtifactLimits | None) -> None:
    """Inject SourceArtifactLimits for HTTP/service boundary tests."""
    global _source_limits_override
    _source_limits_override = limits


def set_pointer_probe_hook(hook: Callable[[], None] | None) -> None:
    """Inject pre-probe barrier for concurrent finalize race tests."""
    global _pointer_probe_hook
    _pointer_probe_hook = hook


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_uuid(value: Any) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _engine_from_bind(bind: Any) -> Any:
    """Return an Engine (never a live Connection) for short-lived probe sessions."""
    return getattr(bind, "engine", bind)


def _read_committed_batch_pointer(bind: Any, batch_id: uuid.UUID) -> uuid.UUID | None:
    """
    Read durable current_source_artifact_id outside the work Session identity map.

    Uses an AUTOCOMMIT connection from the Engine so:
    - UUID binds are typed (no raw text())
    - concurrent committed pointer updates are visible on file/PG dialects
    - returning the connection cannot roll back the caller's open transaction
      (a second Session/connection checkout on SQLite StaticPool/singleton
      pools previously rolled back the finalize transaction mid-flight)
    """
    engine = _engine_from_bind(bind)
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        raw = conn.execute(
            select(ProjectAssetImportBatch.current_source_artifact_id).where(
                ProjectAssetImportBatch.id == batch_id
            )
        ).scalar()
        return _as_uuid(raw)


def _atomic_claim_current_pointer(
    session: Session,
    *,
    batch_id: uuid.UUID,
    art_id: uuid.UUID,
    art_generation: int,
) -> bool:
    """
    Atomically claim batch.current_source_artifact_id for ``art_id`` if no
    higher-generation current pointer is already durable.

    The winner decision is a single conditional UPDATE evaluated against DB
    state at write time (not an earlier non-atomic read). A later ORM flush
    must not issue an unconditional pointer overwrite: callers must not assign
    ``batch.current_source_artifact_id`` except after a successful claim, and
    must expire the attribute so SQLAlchemy does not emit a stale UPDATE.

    Race harness: optional probe hook fires after the pre-claim observation of
    the durable pointer and before the CAS UPDATE, so a concurrent finalize can
    commit between observe and write.
    """
    # Observe durable pointer first (typed, cross-dialect), then optional barrier.
    observed = _read_committed_batch_pointer(session.get_bind(), batch_id)
    if _pointer_probe_hook is not None:
        _pointer_probe_hook()

    # Correlated generation of the currently pointed artifact (NULL if none).
    current_gen = (
        select(ImportSourceArtifact.generation)
        .where(ImportSourceArtifact.id == ProjectAssetImportBatch.current_source_artifact_id)
        .correlate(ProjectAssetImportBatch)
        .scalar_subquery()
    )
    stmt = (
        update(ProjectAssetImportBatch)
        .where(
            ProjectAssetImportBatch.id == batch_id,
            or_(
                ProjectAssetImportBatch.current_source_artifact_id.is_(None),
                ProjectAssetImportBatch.current_source_artifact_id == art_id,
                current_gen.is_(None),
                current_gen < art_generation,
            ),
        )
        .values(current_source_artifact_id=art_id)
        # Never synchronize/expire ORM identity map here — a false expire+reload of
        # ImportSourceArtifact mid-finalize drops the pending→available dirty state.
        .execution_options(synchronize_session=False)
    )
    # Flush pending ORM state (including art.state=available) before the CAS so the
    # pointer FK target and generation rows are visible within this transaction.
    session.flush()
    with session.no_autoflush:
        result = session.execute(stmt)
    won = bool(result.rowcount and result.rowcount > 0)
    batch = session.get(ProjectAssetImportBatch, batch_id)
    if batch is not None:
        # Reload pointer from this transaction; do not dirty-assign (avoids a second
        # unconditional ORM UPDATE of current_source_artifact_id on commit).
        session.expire(batch, ["current_source_artifact_id"])
    _ = observed
    return won


def _as_utc_timestamp(dt: datetime | None, *, fallback: float) -> float:
    """
    Convert a DB datetime to a UTC epoch timestamp.

    SQLite (and some drivers) return naive datetimes for UTC wall-clock values.
    Python's datetime.timestamp() treats naive values as *local* time, which
    shifts retention cutoffs on non-UTC hosts. Treat naive as UTC.
    """
    if dt is None:
        return fallback
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


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


def _sha256_object(
    storage: ObjectStoragePort,
    key: str,
    *,
    chunk_size: int,
    expected_size: int,
) -> str:
    """
    Stream object, count bytes, return lowercase hex digest.

    Only a complete stream of exactly expected_size may return a digest for
    content comparison. Clean EOF short-read / oversize are infrastructure.

    Raises:
      ObjectNotFound — exact missing key
      ObjectStorageError — infrastructure/read failure (never content mismatch)
    """
    if expected_size < 0:
        raise ObjectStorageError("invalid_expected_size")
    try:
        h = hashlib.sha256()
        total = 0
        with storage.open_stream(key) as rs:
            while True:
                chunk = rs.read(chunk_size)
                if not chunk:
                    break
                total += len(chunk)
                if total > expected_size:
                    raise ObjectStorageError("object_too_large")
                h.update(chunk)
        if total < expected_size:
            # Clean EOF before expected size — not content corruption
            raise ObjectStorageError("short_read")
        if total != expected_size:
            raise ObjectStorageError("size_mismatch")
        return _normalize_checksum(h.hexdigest())
    except ObjectNotFound:
        raise
    except ObjectStorageError:
        raise
    except Exception as exc:
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
    limits = limits or _source_limits_override or DEFAULT_SOURCE_LIMITS
    storage = storage or get_object_storage()

    size_hdr = get_request_size(request)
    if size_hdr is not None and size_hdr < 0:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "request_too_large", "detail": "Kích thước yêu cầu HTTP không hợp lệ."},
        )
    if size_hdr is not None and size_hdr > limits.max_request_bytes:
        raise HTTPException(
            status_code=413,
            detail={
                "error_code": "request_too_large",
                "detail": "Kích thước yêu cầu HTTP vượt quá giới hạn cho phép.",
            },
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
            fmt, adapter = detect_format_and_adapter(path, sanitized, limits=limits)
            inspection = adapter.inspect(path)
        except AdapterError as ae:
            raise HTTPException(
                status_code=ae.status,
                detail={"error_code": ae.error_code, "detail": ae.detail},
            ) from ae

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
            # Same size-aware verifier as reconciler — never treat short-read as corruption
            try:
                got = _sha256_object(
                    storage,
                    object_key,
                    chunk_size=limits.read_chunk_size,
                    expected_size=size,
                )
            except ObjectStorageError:
                raise
            except ObjectNotFound:
                raise
            if got != checksum:
                failure_code = "checksum_mismatch"
                raise RuntimeError("checksum_mismatch")
            etag = st.etag
        except Exception as exc:
            if isinstance(exc, ObjectStorageError):
                # short_read / object_too_large / timeout / put_failed — infrastructure only
                failure_code = exc.code[:64]
            elif isinstance(exc, ObjectNotFound):
                failure_code = "object_missing"
            elif "checksum" in str(exc).lower() or failure_code == "checksum_mismatch":
                failure_code = "checksum_mismatch"
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

        # Finalize available + current pointer (fresh lock; concurrent reconciler may have won)
        project = (
            db.query(Project)
            .filter(Project.organization_id == org_id, Project.id == project_id)
            .populate_existing()
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
            .populate_existing()
            .with_for_update()
            .first()
        )
        art = (
            db.query(ImportSourceArtifact)
            .filter(
                ImportSourceArtifact.id == artifact_id,
                ImportSourceArtifact.organization_id == org_id,
            )
            .populate_existing()
            .with_for_update()
            .first()
        )
        if not project or not batch or not art:
            raise HTTPException(status_code=404, detail="Import batch not found")

        # Reconciler (or prior durable finalize) already owns the transition — no second audit.
        # Roll back first so a stale batch pointer in this Session cannot clobber the winner.
        if art.state == SourceArtifactState.AVAILABLE.value:
            try:
                db.rollback()
            except Exception:
                pass
            art = (
                db.query(ImportSourceArtifact)
                .filter(
                    ImportSourceArtifact.id == artifact_id,
                    ImportSourceArtifact.organization_id == org_id,
                )
                .populate_existing()
                .first()
            )
            if art is None:
                raise HTTPException(status_code=404, detail="Source artifact not found")
            if art.storage_etag is None and etag is not None:
                art.storage_etag = etag
                try:
                    db.commit()
                    db.refresh(art)
                except Exception:
                    try:
                        db.rollback()
                    except Exception:
                        pass
                    art = (
                        db.query(ImportSourceArtifact)
                        .filter(ImportSourceArtifact.id == artifact_id)
                        .populate_existing()
                        .first()
                    )
            return art

        if art.state != SourceArtifactState.PENDING.value:
            # Concurrent actor moved us to failed/orphaned — surface residual without inventing available.
            try:
                db.rollback()
            except Exception:
                pass
            art = (
                db.query(ImportSourceArtifact)
                .filter(
                    ImportSourceArtifact.id == artifact_id,
                    ImportSourceArtifact.organization_id == org_id,
                )
                .populate_existing()
                .first()
            )
            if art is None:
                raise HTTPException(status_code=404, detail="Source artifact not found")
            return art

        # Stale finish: newer available current already wins — this pending → orphan path
        if batch.current_source_artifact_id:
            current = (
                db.query(ImportSourceArtifact)
                .filter(ImportSourceArtifact.id == batch.current_source_artifact_id)
                .populate_existing()
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
        # Atomic CAS first; only emit Available audit after a winning claim so a
        # concurrent higher generation cannot leave a durable Available trail.
        claimed = _atomic_claim_current_pointer(
            db,
            batch_id=batch.id,
            art_id=art.id,
            art_generation=art.generation,
        )
        if not claimed:
            art.state = SourceArtifactState.ORPHANED.value
            art.available_at = None
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
        try:
            db.commit()
        except Exception as commit_exc:
            try:
                db.rollback()
            except Exception:
                pass
            # Ambiguity: commit may already be durable (disconnect after success).
            try:
                recovered = (
                    db.query(ImportSourceArtifact)
                    .filter(
                        ImportSourceArtifact.id == artifact_id,
                        ImportSourceArtifact.organization_id == org_id,
                    )
                    .populate_existing()
                    .first()
                )
                batch_r = (
                    db.query(ProjectAssetImportBatch)
                    .filter(
                        ProjectAssetImportBatch.id == batch_id,
                        ProjectAssetImportBatch.organization_id == org_id,
                    )
                    .populate_existing()
                    .first()
                )
                if (
                    recovered is not None
                    and recovered.state == SourceArtifactState.AVAILABLE.value
                    and batch_r is not None
                    and batch_r.current_source_artifact_id == recovered.id
                ):
                    # Durable success — never compensate into failed.
                    return recovered
            except Exception:
                pass
            try:
                _mark_failed(
                    db,
                    artifact_id=artifact_id,
                    org_id=org_id,
                    actor_id=current_user.id,
                    batch_id=batch_id,
                    generation=next_gen,
                    failure_code="finalize_commit_failed",
                    correlation_id=correlation_id,
                )
            except Exception:
                pass
            raise HTTPException(
                status_code=500,
                detail="Không thể lưu tệp nguồn an toàn. Vui lòng thử lại.",
            ) from commit_exc
        db.refresh(art)
        return art

    except HTTPException:
        raise
    except AdapterError as ae:
        raise HTTPException(
            status_code=ae.status,
            detail={"error_code": ae.error_code, "detail": ae.detail},
        ) from ae
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
    now: datetime | None = None,
) -> dict[str, int]:
    """
    Bounded reconciler for pending/failed/orphaned artifacts.

    Transaction ownership: opens a dedicated Session on the same bind as ``db``.
    Never commits or rolls back the caller session (unflushed and flushed UOW preserved).
    ``now`` injects the retention clock for deterministic tests.
    """
    if org_id is None:
        raise HTTPException(status_code=400, detail="Phạm vi tổ chức là bắt buộc cho đối soát.")
    if actor_id is None:
        raise HTTPException(status_code=400, detail="Tác nhân hệ thống là bắt buộc cho đối soát.")

    limits = _source_limits_override or DEFAULT_SOURCE_LIMITS
    storage = storage or get_object_storage()
    max_items = max_items if max_items is not None else limits.reconcilers_max_items
    if max_items < 1:
        raise HTTPException(status_code=400, detail="max_items phải >= 1.")
    ref_check = reference_check or is_source_artifact_referenced
    now_dt = now if now is not None else _utcnow()
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    now_ts = now_dt.timestamp()
    cutoff = now_ts - limits.orphan_retention_seconds

    with db.no_autoflush:
        bind = db.bind if db.bind is not None else db.get_bind()
    if _work_session_factory is not None:
        work: Session = _work_session_factory(bind)
    else:
        WorkSession = sessionmaker(bind=bind, autoflush=False, autocommit=False)
        work = WorkSession()

    scanned = 0
    marked_orphan = 0
    marked_failed = 0
    deleted = 0
    errors = 0
    artifact_ids: list[uuid.UUID] = []

    try:
        try:
            id_rows = (
                work.query(ImportSourceArtifact.id)
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
        finally:
            if work.in_transaction():
                try:
                    work.rollback()
                except Exception:
                    pass

        for art_id in artifact_ids:
            scanned += 1
            committed = False
            try:
                art = (
                    work.query(ImportSourceArtifact)
                    .filter(
                        ImportSourceArtifact.id == art_id,
                        ImportSourceArtifact.organization_id == org_id,
                    )
                    .populate_existing()
                    .with_for_update()
                    .first()
                )
                if not art:
                    if work.in_transaction():
                        work.rollback()
                    continue
                # Concurrent uploader may have finalized between id-scan and lock.
                if art.state == SourceArtifactState.AVAILABLE.value:
                    if work.in_transaction():
                        work.rollback()
                    continue
                batch = (
                    work.query(ProjectAssetImportBatch)
                    .filter(
                        ProjectAssetImportBatch.id == art.import_batch_id,
                        ProjectAssetImportBatch.organization_id == org_id,
                    )
                    .populate_existing()
                    .with_for_update()
                    .first()
                )
                if not batch:
                    if work.in_transaction():
                        work.rollback()
                    continue
                if batch.current_source_artifact_id == art.id:
                    if work.in_transaction():
                        work.rollback()
                    continue
                if ref_check(work, art):
                    if work.in_transaction():
                        work.rollback()
                    continue

                created_ts = _as_utc_timestamp(art.created_at, fallback=now_ts)
                past_retention = created_ts < cutoff
                item_failed = 0
                item_orphan = 0
                item_deleted = 0

                if art.state == SourceArtifactState.PENDING.value:
                    try:
                        st = storage.head(art.storage_object_key)
                    except ObjectStorageError:
                        errors += 1
                        if work.in_transaction():
                            work.rollback()
                        continue
                    if st is None:
                        if past_retention and not ref_check(work, art):
                            _assert_transition(art.state, SourceArtifactState.FAILED)
                            art.state = SourceArtifactState.FAILED.value
                            art.failed_at = _utcnow()
                            art.failure_code = "pending_object_missing"
                            _audit(
                                work,
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
                        try:
                            digest = _sha256_object(
                                storage,
                                art.storage_object_key,
                                chunk_size=limits.read_chunk_size,
                                expected_size=art.file_size_bytes,
                            )
                            if digest != art.checksum_sha256:
                                failure_code = "checksum_mismatch"
                        except ObjectNotFound:
                            failure_code = "pending_object_missing"
                        except ObjectStorageError:
                            errors += 1
                            if work.in_transaction():
                                work.rollback()
                            continue
                        if failure_code and not ref_check(work, art):
                            _assert_transition(art.state, SourceArtifactState.FAILED)
                            art.state = SourceArtifactState.FAILED.value
                            art.failed_at = _utcnow()
                            art.failure_code = failure_code
                            _audit(
                                work,
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
                            and not ref_check(work, art)
                        ):
                            _assert_transition(art.state, SourceArtifactState.ORPHANED)
                            art.state = SourceArtifactState.ORPHANED.value
                            art.orphaned_at = _utcnow()
                            _audit(
                                work,
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
                        elif not failure_code and not ref_check(work, art):
                            newer_wins = False
                            if batch.current_source_artifact_id:
                                cur = (
                                    work.query(ImportSourceArtifact)
                                    .filter(
                                        ImportSourceArtifact.id
                                        == batch.current_source_artifact_id
                                    )
                                    .first()
                                )
                                if (
                                    cur
                                    and cur.generation > art.generation
                                    and cur.state == SourceArtifactState.AVAILABLE.value
                                ):
                                    newer_wins = True
                            if newer_wins:
                                _assert_transition(art.state, SourceArtifactState.ORPHANED)
                                art.state = SourceArtifactState.ORPHANED.value
                                art.orphaned_at = _utcnow()
                                art.failure_code = "stale_generation"
                                _audit(
                                    work,
                                    org_id=org_id,
                                    actor_id=actor_id,
                                    event_name="ImportSourceArtifactOrphaned",
                                    entity_id=art.id,
                                    payload={
                                        "import_batch_id": str(art.import_batch_id),
                                        "generation": art.generation,
                                        "reason": "stale_recovery",
                                    },
                                    correlation_id=None,
                                    command_name="ReconcileImportSourceArtifact",
                                )
                                item_orphan = 1
                            else:
                                _assert_transition(art.state, SourceArtifactState.AVAILABLE)
                                art.state = SourceArtifactState.AVAILABLE.value
                                art.available_at = _utcnow()
                                art.failure_code = None
                                # Atomic CAS first; Available audit only after win.
                                claimed = _atomic_claim_current_pointer(
                                    work,
                                    batch_id=batch.id,
                                    art_id=art.id,
                                    art_generation=art.generation,
                                )
                                if not claimed:
                                    art.state = SourceArtifactState.ORPHANED.value
                                    art.available_at = None
                                    art.orphaned_at = _utcnow()
                                    art.failure_code = "stale_generation"
                                    _audit(
                                        work,
                                        org_id=org_id,
                                        actor_id=actor_id,
                                        event_name="ImportSourceArtifactOrphaned",
                                        entity_id=art.id,
                                        payload={
                                            "import_batch_id": str(art.import_batch_id),
                                            "generation": art.generation,
                                            "reason": "stale_recovery_cas",
                                        },
                                        correlation_id=None,
                                        command_name="ReconcileImportSourceArtifact",
                                    )
                                    item_orphan = 1
                                else:
                                    _audit(
                                        work,
                                        org_id=org_id,
                                        actor_id=actor_id,
                                        event_name="ImportSourceArtifactAvailable",
                                        entity_id=art.id,
                                        payload={
                                            "import_batch_id": str(art.import_batch_id),
                                            "generation": art.generation,
                                            "reason": "reconcile_promote_verified_pending",
                                        },
                                        correlation_id=None,
                                        command_name="ReconcileImportSourceArtifact",
                                    )

                elif art.state == SourceArtifactState.FAILED.value:
                    try:
                        st = storage.head(art.storage_object_key)
                    except ObjectStorageError:
                        errors += 1
                        if work.in_transaction():
                            work.rollback()
                        continue
                    if st is not None and past_retention and not ref_check(work, art):
                        _assert_transition(art.state, SourceArtifactState.ORPHANED)
                        art.state = SourceArtifactState.ORPHANED.value
                        art.orphaned_at = _utcnow()
                        _audit(
                            work,
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
                    orphan_ts = _as_utc_timestamp(art.orphaned_at, fallback=created_ts)
                    if orphan_ts < cutoff:
                        if batch.current_source_artifact_id == art.id:
                            if work.in_transaction():
                                work.rollback()
                            continue
                        if ref_check(work, art):
                            if work.in_transaction():
                                work.rollback()
                            continue
                        key = art.storage_object_key
                        try:
                            storage.delete(key)
                        except ObjectStorageError:
                            errors += 1
                            if work.in_transaction():
                                work.rollback()
                            continue
                        try:
                            if storage.head(key) is not None:
                                errors += 1
                                if work.in_transaction():
                                    work.rollback()
                                continue
                        except ObjectStorageError:
                            errors += 1
                            if work.in_transaction():
                                work.rollback()
                            continue
                        if ref_check(work, art):
                            if work.in_transaction():
                                work.rollback()
                            continue
                        _audit(
                            work,
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

                # Pointer claim is atomic at UPDATE time (_atomic_claim_current_pointer).
                # Do not re-assign batch.current_source_artifact_id here — that would
                # re-introduce an unconditional ORM overwrite on flush/commit.
                work.commit()
                committed = True
                marked_failed += item_failed
                marked_orphan += item_orphan
                deleted += item_deleted
            except Exception:
                errors += 1
            finally:
                if not committed and work.in_transaction():
                    try:
                        work.rollback()
                    except Exception:
                        pass

        if work.in_transaction():
            try:
                work.rollback()
            except Exception:
                pass
    finally:
        work.close()

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
