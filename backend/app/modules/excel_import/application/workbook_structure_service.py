"""S13-PR-003 application service for immutable workbook structure snapshots."""
from __future__ import annotations

import hashlib
import os
import tempfile
import uuid

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.excel_import.application.adapters import detect_format_and_adapter
from app.modules.excel_import.domain.source_artifact import (
    DEFAULT_SOURCE_LIMITS,
    SourceArtifactState,
)
from app.modules.excel_import.domain.workbook_adapter import AdapterError
from app.modules.excel_import.domain.workbook_structure import (
    STRUCTURE_RULE_VERSION,
    analyze_workbook_structure,
    canonical_payload_digest,
    payload_digest_matches,
    require_review_for_drift,
)
from app.modules.excel_import.infrastructure.object_storage import (
    ObjectNotFound,
    ObjectStorageError,
    ObjectStoragePort,
    get_object_storage,
)
from app.modules.excel_import.models import (
    ImportSourceArtifact,
    WorkbookStructureSnapshot,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    ProjectAssetImportBatch,
)

_COPY_CHUNK_SIZE = 64 * 1024


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


def _query_artifact(
    db: Session,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    artifact_id: uuid.UUID,
    for_update: bool = False,
) -> ImportSourceArtifact:
    query = db.query(ImportSourceArtifact).filter(
        ImportSourceArtifact.organization_id == org_id,
        ImportSourceArtifact.project_id == project_id,
        ImportSourceArtifact.import_batch_id == batch_id,
        ImportSourceArtifact.id == artifact_id,
    )
    if for_update:
        query = query.with_for_update()
    artifact = query.first()
    if artifact is None:
        raise HTTPException(status_code=404, detail="Source artifact not found")
    return artifact


def _materialize_verified_source(
    artifact: ImportSourceArtifact,
    storage: ObjectStoragePort,
) -> str:
    suffix = f".{artifact.detected_format}" if artifact.detected_format in {"xls", "xlsx"} else ".bin"
    fd, path = tempfile.mkstemp(prefix="valora-structure-", suffix=suffix)
    os.close(fd)
    stream = None
    digest = hashlib.sha256()
    total = 0
    verified = False
    try:
        stream = storage.open_stream(artifact.storage_object_key)
        with open(path, "wb") as output:
            while True:
                chunk = stream.read(_COPY_CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > DEFAULT_SOURCE_LIMITS.max_upload_bytes:
                    raise _error(
                        413,
                        "source_object_too_large",
                        "Kích thước tệp nguồn vượt quá giới hạn phân tích.",
                    )
                if total > artifact.file_size_bytes:
                    raise _error(
                        409,
                        "source_size_mismatch",
                        "Kích thước tệp nguồn không khớp bằng chứng đã lưu.",
                    )
                digest.update(chunk)
                output.write(chunk)
        if total != artifact.file_size_bytes:
            raise _error(
                409,
                "source_size_mismatch",
                "Kích thước tệp nguồn không khớp bằng chứng đã lưu.",
            )
        if digest.hexdigest() != artifact.checksum_sha256:
            raise _error(
                409,
                "source_checksum_mismatch",
                "Mã kiểm tra tệp nguồn không khớp bằng chứng đã lưu.",
            )
        verified = True
        return path
    except ObjectNotFound as exc:
        raise _error(
            409,
            "source_object_missing",
            "Không tìm thấy tệp nguồn đã lưu.",
        ) from exc
    except ObjectStorageError as exc:
        raise _error(
            503,
            "source_object_unavailable",
            "Không thể đọc tệp nguồn vào lúc này.",
        ) from exc
    finally:
        close = getattr(stream, "close", None)
        try:
            if callable(close):
                close()
        finally:
            if not verified:
                try:
                    os.unlink(path)
                except OSError:
                    pass


def _verify_snapshot(
    snapshot: WorkbookStructureSnapshot,
    source_artifact: ImportSourceArtifact | None = None,
) -> None:
    if not payload_digest_matches(snapshot.structure_payload, snapshot.analysis_digest_sha256):
        raise _error(
            500,
            "structure_snapshot_integrity_failure",
            "Bằng chứng phân tích cấu trúc không còn toàn vẹn.",
        )
    payload = snapshot.structure_payload
    if payload.get("rule_version") != snapshot.rule_version:
        raise _error(
            500,
            "structure_snapshot_integrity_failure",
            "Phiên bản quy tắc phân tích không khớp bằng chứng đã lưu.",
        )
    if payload.get("disposition") != snapshot.disposition:
        raise _error(
            500,
            "structure_snapshot_integrity_failure",
            "Trạng thái phân tích không khớp bằng chứng đã lưu.",
        )
    if payload.get("candidate_count") != snapshot.candidate_count:
        raise _error(
            500,
            "structure_snapshot_integrity_failure",
            "Số lượng ứng viên không khớp bằng chứng đã lưu.",
        )
    source = payload.get("source")
    if not isinstance(source, dict) or (
        source.get("source_artifact_id") != str(snapshot.source_artifact_id)
        or source.get("source_checksum_sha256") != snapshot.source_checksum_sha256
        or source.get("adapter_name") != snapshot.adapter_name
        or source.get("adapter_version") != snapshot.adapter_version
    ):
        raise _error(
            500,
            "structure_snapshot_integrity_failure",
            "Nguồn và bộ chuyển đổi không khớp bằng chứng đã lưu.",
        )
    if source_artifact is not None and (
        snapshot.source_artifact_id != source_artifact.id
        or snapshot.source_checksum_sha256 != source_artifact.checksum_sha256
        or source.get("source_generation") != source_artifact.generation
        or source.get("detected_format") != source_artifact.detected_format
    ):
        raise _error(
            500,
            "structure_snapshot_integrity_failure",
            "Danh tính tệp nguồn không khớp bằng chứng phân tích đã lưu.",
        )


def _latest_previous_snapshot(
    db: Session,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    artifact_id: uuid.UUID,
    generation: int,
) -> WorkbookStructureSnapshot | None:
    previous = (
        db.query(WorkbookStructureSnapshot)
        .join(
            ImportSourceArtifact,
            ImportSourceArtifact.id == WorkbookStructureSnapshot.source_artifact_id,
        )
        .filter(
            WorkbookStructureSnapshot.organization_id == org_id,
            WorkbookStructureSnapshot.project_id == project_id,
            WorkbookStructureSnapshot.import_batch_id == batch_id,
            WorkbookStructureSnapshot.source_artifact_id != artifact_id,
            ImportSourceArtifact.generation < generation,
        )
        .order_by(
            ImportSourceArtifact.generation.desc(),
            WorkbookStructureSnapshot.snapshot_version.desc(),
        )
        .first()
    )
    if previous is not None:
        _verify_snapshot(previous)
    return previous


def analyze_source_artifact_structure(
    db: Session,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    artifact_id: uuid.UUID,
    current_user,
    correlation_id: str | None = None,
    storage: ObjectStoragePort | None = None,
) -> WorkbookStructureSnapshot:
    """Analyze verified source bytes and append one immutable snapshot."""
    artifact = _query_artifact(
        db,
        org_id=org_id,
        project_id=project_id,
        batch_id=batch_id,
        artifact_id=artifact_id,
    )
    if artifact.state != SourceArtifactState.AVAILABLE.value:
        raise _error(
            409,
            "source_artifact_not_available",
            "Tệp nguồn chưa sẵn sàng để phân tích cấu trúc.",
        )

    storage = storage or get_object_storage()
    path = _materialize_verified_source(artifact, storage)
    adapter = None
    try:
        detected_format, adapter = detect_format_and_adapter(
            path,
            artifact.original_filename,
            limits=DEFAULT_SOURCE_LIMITS,
        )
        if detected_format.value != artifact.detected_format:
            raise _error(
                409,
                "source_format_mismatch",
                "Định dạng tệp nguồn không khớp bằng chứng đã lưu.",
            )
        inspection = adapter.inspect(path)
        payload = analyze_workbook_structure(
            inspection,
            lambda sheet_name: adapter.iter_rows(path, sheet_name),
        )
    except AdapterError as exc:
        raise _error(exc.status, exc.error_code, exc.detail) from exc
    finally:
        try:
            if adapter is not None:
                adapter.close()
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    payload["source"] = {
        "source_artifact_id": str(artifact.id),
        "source_generation": artifact.generation,
        "source_checksum_sha256": artifact.checksum_sha256,
        "detected_format": artifact.detected_format,
        "adapter_name": inspection.adapter_name,
        "adapter_version": inspection.adapter_version,
    }
    previous = _latest_previous_snapshot(
        db,
        org_id=org_id,
        project_id=project_id,
        batch_id=batch_id,
        artifact_id=artifact_id,
        generation=artifact.generation,
    )
    payload = require_review_for_drift(
        payload,
        previous.structure_payload if previous is not None else None,
    )
    digest = canonical_payload_digest(payload)

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
    if batch is None:
        raise HTTPException(status_code=404, detail="Import batch not found")
    locked_artifact = _query_artifact(
        db,
        org_id=org_id,
        project_id=project_id,
        batch_id=batch_id,
        artifact_id=artifact_id,
        for_update=True,
    )
    if (
        locked_artifact.state != SourceArtifactState.AVAILABLE.value
        or locked_artifact.checksum_sha256 != artifact.checksum_sha256
        or locked_artifact.file_size_bytes != artifact.file_size_bytes
    ):
        raise _error(
            409,
            "source_artifact_changed",
            "Bằng chứng tệp nguồn đã thay đổi trong khi phân tích.",
        )

    last_version = (
        db.query(func.max(WorkbookStructureSnapshot.snapshot_version))
        .filter(WorkbookStructureSnapshot.source_artifact_id == artifact_id)
        .scalar()
    )
    snapshot = WorkbookStructureSnapshot(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=project_id,
        import_batch_id=batch_id,
        source_artifact_id=artifact_id,
        snapshot_version=int(last_version or 0) + 1,
        source_checksum_sha256=artifact.checksum_sha256,
        rule_version=STRUCTURE_RULE_VERSION,
        adapter_name=inspection.adapter_name,
        adapter_version=inspection.adapter_version,
        disposition=payload["disposition"],
        candidate_count=payload["candidate_count"],
        structure_payload=payload,
        analysis_digest_sha256=digest,
        created_by_user_id=current_user.id,
    )
    db.add(snapshot)
    db.add(
        AuditEvent(
            organization_id=org_id,
            actor_user_id=current_user.id,
            event_name="WorkbookStructureAnalyzed",
            entity_type="WorkbookStructureSnapshot",
            entity_id=snapshot.id,
            payload={
                "import_batch_id": str(batch_id),
                "source_artifact_id": str(artifact_id),
                "source_generation": artifact.generation,
                "snapshot_version": snapshot.snapshot_version,
                "rule_version": snapshot.rule_version,
                "disposition": snapshot.disposition,
                "candidate_count": snapshot.candidate_count,
                "analysis_digest_sha256": digest,
            },
            correlation_id=correlation_id,
            command_name="AnalyzeWorkbookStructure",
        )
    )
    db.commit()
    db.refresh(snapshot)
    return snapshot


def list_structure_snapshots(
    db: Session,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    artifact_id: uuid.UUID,
) -> list[WorkbookStructureSnapshot]:
    artifact = _query_artifact(
        db,
        org_id=org_id,
        project_id=project_id,
        batch_id=batch_id,
        artifact_id=artifact_id,
    )
    snapshots = (
        db.query(WorkbookStructureSnapshot)
        .filter(
            WorkbookStructureSnapshot.organization_id == org_id,
            WorkbookStructureSnapshot.project_id == project_id,
            WorkbookStructureSnapshot.import_batch_id == batch_id,
            WorkbookStructureSnapshot.source_artifact_id == artifact_id,
        )
        .order_by(WorkbookStructureSnapshot.snapshot_version.asc())
        .all()
    )
    for snapshot in snapshots:
        _verify_snapshot(snapshot, artifact)
    return snapshots


def get_structure_snapshot(
    db: Session,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    artifact_id: uuid.UUID,
    snapshot_id: uuid.UUID,
) -> WorkbookStructureSnapshot:
    artifact = _query_artifact(
        db,
        org_id=org_id,
        project_id=project_id,
        batch_id=batch_id,
        artifact_id=artifact_id,
    )
    snapshot = (
        db.query(WorkbookStructureSnapshot)
        .filter(
            WorkbookStructureSnapshot.organization_id == org_id,
            WorkbookStructureSnapshot.project_id == project_id,
            WorkbookStructureSnapshot.import_batch_id == batch_id,
            WorkbookStructureSnapshot.source_artifact_id == artifact_id,
            WorkbookStructureSnapshot.id == snapshot_id,
        )
        .first()
    )
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Structure snapshot not found")
    _verify_snapshot(snapshot, artifact)
    return snapshot
