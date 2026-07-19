"""S13-PR-003 application service for immutable workbook structure snapshots."""
from __future__ import annotations

import hashlib
import os
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Iterator

from fastapi import HTTPException
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.modules.excel_import.application.adapters import detect_format_and_adapter
from app.modules.excel_import.domain.source_artifact import (
    DEFAULT_SOURCE_LIMITS,
    SourceArtifactState,
)
from app.modules.excel_import.domain.workbook_adapter import AdapterError
from app.modules.excel_import.domain.workbook_structure import (
    STRUCTURE_RULE_VERSION,
    StructureDisposition,
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
_SUPPORTED_STRUCTURE_RULE_VERSIONS = frozenset(
    {"s13-pr-003-v1", "s13-pr-003-v2", "s13-pr-003-v3"}
)
_SNAPSHOT_PAGE_LIMIT_DEFAULT = 20
_SNAPSHOT_PAGE_LIMIT_MAX = 50
_FINALIZATION_EVENT_NAME = "WorkbookStructureAnalyzed"
_FINALIZATION_ENTITY_TYPE = "WorkbookStructureSnapshot"
_FINALIZATION_COMMAND_NAME = "AnalyzeWorkbookStructure"
_FINALIZATION_PAYLOAD_KEYS = frozenset(
    {
        "import_batch_id",
        "source_artifact_id",
        "source_generation",
        "snapshot_version",
        "rule_version",
        "disposition",
        "candidate_count",
        "analysis_digest_sha256",
    }
)


@dataclass(frozen=True)
class ArtifactFingerprint:
    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    import_batch_id: uuid.UUID
    generation: int
    state: str
    checksum_sha256: str
    file_size_bytes: int
    detected_format: str
    storage_object_key: str
    original_filename: str

    @classmethod
    def freeze(cls, artifact: ImportSourceArtifact) -> ArtifactFingerprint:
        return cls(
            id=artifact.id,
            organization_id=artifact.organization_id,
            project_id=artifact.project_id,
            import_batch_id=artifact.import_batch_id,
            generation=artifact.generation,
            state=artifact.state,
            checksum_sha256=artifact.checksum_sha256,
            file_size_bytes=artifact.file_size_bytes,
            detected_format=artifact.detected_format,
            storage_object_key=artifact.storage_object_key,
            original_filename=artifact.original_filename,
        )


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


def _validate_snapshot_page(limit: int, cursor: int | None) -> None:
    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= _SNAPSHOT_PAGE_LIMIT_MAX
    ):
        raise _error(
            422,
            "invalid_snapshot_page_limit",
            "Giới hạn trang snapshot phải từ 1 đến 50.",
        )
    if cursor is not None and (
        isinstance(cursor, bool) or not isinstance(cursor, int) or cursor < 0
    ):
        raise _error(
            422,
            "invalid_snapshot_page_cursor",
            "Con trỏ snapshot phải là số nguyên không âm.",
        )


def _query_artifact(
    db: Session,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    artifact_id: uuid.UUID,
    for_update: bool = False,
    populate_existing: bool = False,
) -> ImportSourceArtifact:
    query = db.query(ImportSourceArtifact).filter(
        ImportSourceArtifact.organization_id == org_id,
        ImportSourceArtifact.project_id == project_id,
        ImportSourceArtifact.import_batch_id == batch_id,
        ImportSourceArtifact.id == artifact_id,
    )
    if populate_existing:
        query = query.populate_existing()
    if for_update:
        query = query.with_for_update()
    artifact = query.first()
    if artifact is None:
        raise HTTPException(status_code=404, detail="Source artifact not found")
    return artifact


def _translate_source_error(exc: Exception) -> Exception:
    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, ObjectNotFound):
        return _error(409, "source_object_missing", "Không tìm thấy tệp nguồn đã lưu.")
    if isinstance(exc, ObjectStorageError):
        return _error(503, "source_object_unavailable", "Không thể đọc tệp nguồn vào lúc này.")
    return _error(503, "source_object_unavailable", "Không thể đọc tệp nguồn vào lúc này.")


@contextmanager
def _materialize_verified_source(
    fingerprint: ArtifactFingerprint,
    storage: ObjectStoragePort,
) -> Iterator[str]:
    """Own the verified temporary source through all adapter work."""
    suffix = f".{fingerprint.detected_format}" if fingerprint.detected_format in {"xls", "xlsx"} else ".bin"
    fd, path = tempfile.mkstemp(prefix="valora-structure-", suffix=suffix)
    os.close(fd)
    stream = None
    primary_error: Exception | None = None
    try:
        digest = hashlib.sha256()
        total = 0
        try:
            stream = storage.open_stream(fingerprint.storage_object_key)
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
                    if total > fingerprint.file_size_bytes:
                        raise _error(
                            409,
                            "source_size_mismatch",
                            "Kích thước tệp nguồn không khớp bằng chứng đã lưu.",
                        )
                    digest.update(chunk)
                    output.write(chunk)
            if total != fingerprint.file_size_bytes:
                raise _error(
                    409,
                    "source_size_mismatch",
                    "Kích thước tệp nguồn không khớp bằng chứng đã lưu.",
                )
            if digest.hexdigest() != fingerprint.checksum_sha256:
                raise _error(
                    409,
                    "source_checksum_mismatch",
                    "Mã kiểm tra tệp nguồn không khớp bằng chứng đã lưu.",
                )
        except Exception as exc:
            primary_error = _translate_source_error(exc)

        close_error: Exception | None = None
        close = getattr(stream, "close", None)
        if callable(close):
            try:
                close()
            except Exception as exc:
                close_error = exc
        if primary_error is not None:
            raise primary_error
        if close_error is not None:
            raise _error(
                503,
                "source_stream_close_failed",
                "Không thể đóng luồng tệp nguồn một cách an toàn.",
            ) from close_error

        yield path
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _verify_drift_reference(payload: dict) -> dict | None:
    reference = payload.get("drift_reference")
    if reference is None:
        return None
    if not isinstance(reference, dict):
        raise _error(
            500,
            "structure_snapshot_integrity_failure",
            "Tham chiếu biến động cấu trúc không hợp lệ.",
        )
    required = {"source_artifact_id", "source_generation"}
    if (
        not required.issubset(reference)
        or not isinstance(reference["source_generation"], int)
        or isinstance(reference["source_generation"], bool)
        or reference["source_generation"] <= 0
    ):
        raise _error(
            500,
            "structure_snapshot_integrity_failure",
            "Tham chiếu nguồn tiền nhiệm không đầy đủ.",
        )
    try:
        uuid.UUID(reference["source_artifact_id"])
        if reference.get("snapshot_id") is not None:
            uuid.UUID(reference["snapshot_id"])
    except (TypeError, ValueError, AttributeError) as exc:
        raise _error(
            500,
            "structure_snapshot_integrity_failure",
            "Định danh tham chiếu tiền nhiệm không hợp lệ.",
        ) from exc
    snapshot_id = reference.get("snapshot_id")
    snapshot_fields = (
        reference.get("snapshot_version"),
        reference.get("rule_version"),
        reference.get("analysis_digest_sha256"),
    )
    if snapshot_id is None:
        if any(value is not None for value in snapshot_fields):
            raise _error(
                500,
                "structure_snapshot_integrity_failure",
                "Tham chiếu snapshot tiền nhiệm không nhất quán.",
            )
    elif (
        not isinstance(snapshot_fields[0], int)
        or isinstance(snapshot_fields[0], bool)
        or snapshot_fields[0] <= 0
        or not isinstance(snapshot_fields[1], str)
        or not isinstance(snapshot_fields[2], str)
        or len(snapshot_fields[2]) != 64
        or snapshot_fields[2] != snapshot_fields[2].lower()
        or any(character not in "0123456789abcdef" for character in snapshot_fields[2])
    ):
        raise _error(
            500,
            "structure_snapshot_integrity_failure",
            "Bằng chứng snapshot tiền nhiệm không đầy đủ.",
        )
    return reference


def _verify_snapshot_core(
    snapshot: WorkbookStructureSnapshot,
    source_artifact: ImportSourceArtifact | None = None,
) -> dict | None:
    """Verify one snapshot without issuing SQL or following lineage links."""
    if snapshot.rule_version not in _SUPPORTED_STRUCTURE_RULE_VERSIONS:
        raise _error(
            500,
            "structure_snapshot_integrity_failure",
            "Phiên bản quy tắc phân tích cấu trúc không được hỗ trợ.",
        )
    payload = snapshot.structure_payload
    if not isinstance(payload, dict):
        raise _error(
            500,
            "structure_snapshot_integrity_failure",
            "Bằng chứng phân tích cấu trúc không còn toàn vẹn.",
        )
    if not payload_digest_matches(payload, snapshot.analysis_digest_sha256):
        raise _error(
            500,
            "structure_snapshot_integrity_failure",
            "Bằng chứng phân tích cấu trúc không còn toàn vẹn.",
        )
    if (
        payload.get("rule_version") != snapshot.rule_version
        or payload.get("disposition") != snapshot.disposition
        or payload.get("candidate_count") != snapshot.candidate_count
    ):
        raise _error(
            500,
            "structure_snapshot_integrity_failure",
            "Thuộc tính snapshot không khớp bằng chứng đã lưu.",
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
    if snapshot.rule_version == "s13-pr-003-v1":
        if "drift_reference" not in payload:
            return None
    elif "drift_reference" not in payload:
        raise _error(
            500,
            "structure_snapshot_integrity_failure",
            "Snapshot thiếu tham chiếu biến động cấu trúc theo phiên bản quy tắc.",
        )
    reference = _verify_drift_reference(payload)
    if reference is not None and source_artifact is not None and (
        reference["source_artifact_id"] == str(source_artifact.id)
        or reference["source_generation"] >= source_artifact.generation
    ):
        raise _error(
            500,
            "structure_snapshot_integrity_failure",
            "Tham chiếu tiền nhiệm không đi lùi theo thế hệ nguồn.",
        )
    return reference


def _verify_finalization_seals(
    db: Session,
    snapshots: list[WorkbookStructureSnapshot],
    source_artifact: ImportSourceArtifact,
) -> None:
    """Require one exact, atomic finalization seal for every page target."""
    if not snapshots:
        return
    snapshot_ids = {snapshot.id for snapshot in snapshots}
    events = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.organization_id == source_artifact.organization_id,
            AuditEvent.event_name == _FINALIZATION_EVENT_NAME,
            AuditEvent.entity_type == _FINALIZATION_ENTITY_TYPE,
            AuditEvent.entity_id.in_(snapshot_ids),
            AuditEvent.command_name == _FINALIZATION_COMMAND_NAME,
        )
        .order_by(
            AuditEvent.entity_id.asc(),
            AuditEvent.created_at.asc(),
            AuditEvent.id.asc(),
        )
        .populate_existing()
        .limit(len(snapshots) + 1)
        .all()
    )
    events_by_snapshot: dict[uuid.UUID, list[AuditEvent]] = {}
    for audit_event in events:
        if audit_event.entity_id is not None:
            events_by_snapshot.setdefault(audit_event.entity_id, []).append(audit_event)

    for snapshot in snapshots:
        matching = events_by_snapshot.get(snapshot.id, [])
        if len(matching) != 1:
            raise _error(
                500,
                "structure_snapshot_integrity_failure",
                "Dấu niêm phong hoàn tất snapshot không hợp lệ.",
            )
        audit_event = matching[0]
        expected_payload = {
            "import_batch_id": str(snapshot.import_batch_id),
            "source_artifact_id": str(snapshot.source_artifact_id),
            "source_generation": source_artifact.generation,
            "snapshot_version": snapshot.snapshot_version,
            "rule_version": snapshot.rule_version,
            "disposition": snapshot.disposition,
            "candidate_count": snapshot.candidate_count,
            "analysis_digest_sha256": snapshot.analysis_digest_sha256,
        }
        payload = audit_event.payload
        if (
            audit_event.organization_id != snapshot.organization_id
            or audit_event.actor_user_id != snapshot.created_by_user_id
            or audit_event.event_name != _FINALIZATION_EVENT_NAME
            or audit_event.entity_type != _FINALIZATION_ENTITY_TYPE
            or audit_event.entity_id != snapshot.id
            or audit_event.command_name != _FINALIZATION_COMMAND_NAME
            or audit_event.created_at is None
            or not isinstance(payload, dict)
            or frozenset(payload) != _FINALIZATION_PAYLOAD_KEYS
            or any(
                type(payload[key]) is not type(expected) or payload[key] != expected
                for key, expected in expected_payload.items()
            )
        ):
            raise _error(
                500,
                "structure_snapshot_integrity_failure",
                "Dấu niêm phong hoàn tất snapshot không khớp bằng chứng đã lưu.",
            )


def _verify_snapshot_page(
    db: Session,
    snapshots: list[WorkbookStructureSnapshot],
    source_artifact: ImportSourceArtifact,
) -> None:
    """Bulk-load bounded lineage context, then verify all links in memory."""
    if not snapshots:
        return
    references = [
        _verify_snapshot_core(snapshot, source_artifact) for snapshot in snapshots
    ]
    _verify_finalization_seals(db, snapshots, source_artifact)
    lineage_required = any(
        snapshot.rule_version in {"s13-pr-003-v2", "s13-pr-003-v3"}
        for snapshot in snapshots
    )
    durable_predecessor = None
    if lineage_required:
        durable_predecessor = (
            db.query(ImportSourceArtifact)
            .filter(
                ImportSourceArtifact.organization_id == source_artifact.organization_id,
                ImportSourceArtifact.project_id == source_artifact.project_id,
                ImportSourceArtifact.import_batch_id == source_artifact.import_batch_id,
                ImportSourceArtifact.state == SourceArtifactState.AVAILABLE.value,
                ImportSourceArtifact.generation < source_artifact.generation,
            )
            .order_by(ImportSourceArtifact.generation.desc())
            .populate_existing()
            .first()
        )
    for snapshot, reference in zip(snapshots, references, strict=True):
        if snapshot.rule_version == "s13-pr-003-v1":
            continue
        if (durable_predecessor is None) != (reference is None) or (
            durable_predecessor is not None
            and reference is not None
            and (
                reference["source_artifact_id"] != str(durable_predecessor.id)
                or reference["source_generation"] != durable_predecessor.generation
            )
        ):
            raise _error(
                500,
                "structure_snapshot_integrity_failure",
                "Tham chiếu không khớp nguồn tiền nhiệm trực tiếp.",
            )

    artifact_ids = {
        uuid.UUID(reference["source_artifact_id"])
        for reference in references
        if reference is not None
    }
    snapshot_ids = {
        uuid.UUID(reference["snapshot_id"])
        for reference in references
        if reference is not None and reference.get("snapshot_id") is not None
    }
    referenced_context = (
        db.query(ImportSourceArtifact, WorkbookStructureSnapshot)
        .outerjoin(
            WorkbookStructureSnapshot,
            and_(
                WorkbookStructureSnapshot.id.in_(snapshot_ids),
                WorkbookStructureSnapshot.organization_id
                == source_artifact.organization_id,
                WorkbookStructureSnapshot.project_id == source_artifact.project_id,
                WorkbookStructureSnapshot.import_batch_id
                == source_artifact.import_batch_id,
                WorkbookStructureSnapshot.source_artifact_id == ImportSourceArtifact.id,
            ),
        )
        .filter(
            ImportSourceArtifact.id.in_(artifact_ids),
            ImportSourceArtifact.organization_id == source_artifact.organization_id,
            ImportSourceArtifact.project_id == source_artifact.project_id,
            ImportSourceArtifact.import_batch_id == source_artifact.import_batch_id,
        )
        .order_by(ImportSourceArtifact.id.asc(), WorkbookStructureSnapshot.id.asc())
        .populate_existing()
        .all()
        if artifact_ids
        else []
    )
    artifacts_by_id = {artifact.id: artifact for artifact, _snapshot in referenced_context}
    snapshots_by_id = {
        snapshot.id: snapshot
        for _artifact, snapshot in referenced_context
        if snapshot is not None
    }
    for reference in references:
        if reference is None:
            continue
        artifact_id = uuid.UUID(reference["source_artifact_id"])
        referenced_artifact = artifacts_by_id.get(artifact_id)
        if referenced_artifact is None or (
            referenced_artifact.generation != reference["source_generation"]
            or referenced_artifact.state != SourceArtifactState.AVAILABLE.value
        ):
            raise _error(
                500,
                "structure_snapshot_integrity_failure",
                "Không tìm thấy nguồn của snapshot tiền nhiệm.",
            )
        if reference.get("snapshot_id") is None:
            continue
        referenced = snapshots_by_id.get(uuid.UUID(reference["snapshot_id"]))
        if referenced is None or (
            referenced.source_artifact_id != referenced_artifact.id
            or referenced.snapshot_version != reference["snapshot_version"]
            or referenced.rule_version != reference["rule_version"]
            or referenced.analysis_digest_sha256 != reference["analysis_digest_sha256"]
        ):
            raise _error(
                500,
                "structure_snapshot_integrity_failure",
                "Tham chiếu snapshot tiền nhiệm không khớp dữ liệu bền vững.",
            )
        # Direct verification only: never walk the referenced generation's links.
        _verify_snapshot_core(referenced, referenced_artifact)


def _force_review(payload: dict, reason: str) -> dict:
    out = dict(payload)
    out["disposition"] = StructureDisposition.REVIEW_REQUIRED.value
    reasons = list(out.get("disposition_reasons") or [])
    if reason not in reasons:
        reasons.append(reason)
    out["disposition_reasons"] = reasons
    return out


def _fingerprint_matches(artifact: ImportSourceArtifact, fingerprint: ArtifactFingerprint) -> bool:
    current = ArtifactFingerprint.freeze(artifact)
    return asdict(current) == asdict(fingerprint)


def _resolve_predecessor(
    db: Session,
    *,
    fingerprint: ArtifactFingerprint,
) -> tuple[dict | None, WorkbookStructureSnapshot | None]:
    predecessor = (
        db.query(ImportSourceArtifact)
        .filter(
            ImportSourceArtifact.organization_id == fingerprint.organization_id,
            ImportSourceArtifact.project_id == fingerprint.project_id,
            ImportSourceArtifact.import_batch_id == fingerprint.import_batch_id,
            ImportSourceArtifact.state == SourceArtifactState.AVAILABLE.value,
            ImportSourceArtifact.generation < fingerprint.generation,
        )
        .order_by(ImportSourceArtifact.generation.desc())
        .populate_existing()
        .first()
    )
    if predecessor is None:
        return None, None
    snapshot = (
        db.query(WorkbookStructureSnapshot)
        .filter(
            WorkbookStructureSnapshot.organization_id == fingerprint.organization_id,
            WorkbookStructureSnapshot.project_id == fingerprint.project_id,
            WorkbookStructureSnapshot.import_batch_id == fingerprint.import_batch_id,
            WorkbookStructureSnapshot.source_artifact_id == predecessor.id,
        )
        .order_by(WorkbookStructureSnapshot.snapshot_version.desc())
        .populate_existing()
        .first()
    )
    reference = {
        "source_artifact_id": str(predecessor.id),
        "source_generation": predecessor.generation,
        "snapshot_id": str(snapshot.id) if snapshot is not None else None,
        "snapshot_version": snapshot.snapshot_version if snapshot is not None else None,
        "rule_version": snapshot.rule_version if snapshot is not None else None,
        "analysis_digest_sha256": snapshot.analysis_digest_sha256 if snapshot is not None else None,
    }
    if snapshot is not None:
        _verify_snapshot_page(db, [snapshot], predecessor)
    return reference, snapshot


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
        populate_existing=True,
    )
    fingerprint = ArtifactFingerprint.freeze(artifact)
    if fingerprint.state != SourceArtifactState.AVAILABLE.value:
        raise _error(
            409,
            "source_artifact_not_available",
            "Tệp nguồn chưa sẵn sàng để phân tích cấu trúc.",
        )

    storage = storage or get_object_storage()
    adapter = None
    try:
        with _materialize_verified_source(fingerprint, storage) as path:
            try:
                detected_format, adapter = detect_format_and_adapter(
                    path,
                    fingerprint.original_filename,
                    limits=DEFAULT_SOURCE_LIMITS,
                )
                if detected_format.value != fingerprint.detected_format:
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
            finally:
                if adapter is not None:
                    adapter.close()
    except AdapterError as exc:
        raise _error(exc.status, exc.error_code, exc.detail) from exc

    payload["source"] = {
        "source_artifact_id": str(fingerprint.id),
        "source_generation": fingerprint.generation,
        "source_checksum_sha256": fingerprint.checksum_sha256,
        "detected_format": fingerprint.detected_format,
        "adapter_name": inspection.adapter_name,
        "adapter_version": inspection.adapter_version,
    }

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
    if batch is None:
        raise HTTPException(status_code=404, detail="Import batch not found")
    locked_artifact = _query_artifact(
        db,
        org_id=org_id,
        project_id=project_id,
        batch_id=batch_id,
        artifact_id=artifact_id,
        for_update=True,
        populate_existing=True,
    )
    if not _fingerprint_matches(locked_artifact, fingerprint):
        raise _error(
            409,
            "source_artifact_changed",
            "Bằng chứng tệp nguồn đã thay đổi trong khi phân tích.",
        )

    drift_reference, previous = _resolve_predecessor(db, fingerprint=fingerprint)
    payload["drift_reference"] = drift_reference
    if drift_reference is not None and previous is None:
        payload = _force_review(payload, "prior_generation_snapshot_missing")
    elif previous is not None:
        if previous.rule_version != STRUCTURE_RULE_VERSION:
            payload = _force_review(payload, "structure_rule_version_changed")
        payload = require_review_for_drift(payload, previous.structure_payload)
    digest = canonical_payload_digest(payload)

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
        source_checksum_sha256=fingerprint.checksum_sha256,
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
                "source_generation": fingerprint.generation,
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
    limit: int = _SNAPSHOT_PAGE_LIMIT_DEFAULT,
    cursor: int | None = None,
) -> tuple[list[WorkbookStructureSnapshot], int | None]:
    _validate_snapshot_page(limit, cursor)
    artifact = _query_artifact(
        db,
        org_id=org_id,
        project_id=project_id,
        batch_id=batch_id,
        artifact_id=artifact_id,
        populate_existing=True,
    )
    query = db.query(WorkbookStructureSnapshot).filter(
            WorkbookStructureSnapshot.organization_id == org_id,
            WorkbookStructureSnapshot.project_id == project_id,
            WorkbookStructureSnapshot.import_batch_id == batch_id,
            WorkbookStructureSnapshot.source_artifact_id == artifact_id,
        )
    if cursor is not None:
        query = query.filter(WorkbookStructureSnapshot.snapshot_version > cursor)
    snapshots = (
        query
        .order_by(WorkbookStructureSnapshot.snapshot_version.asc())
        .populate_existing()
        .limit(limit + 1)
        .all()
    )
    has_more = len(snapshots) > limit
    page = snapshots[:limit]
    _verify_snapshot_page(db, page, artifact)
    next_cursor = page[-1].snapshot_version if has_more and page else None
    return page, next_cursor


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
        populate_existing=True,
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
        .populate_existing()
        .first()
    )
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Structure snapshot not found")
    _verify_snapshot_page(db, [snapshot], artifact)
    return snapshot
