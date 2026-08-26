"""Source-backed business handlers registered by the durable worker."""
from __future__ import annotations

from collections.abc import Callable
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.modules.document_engine_intelligence.application.dossier_extraction_service import (
    DossierExtractionError,
    extract_dossier_source,
)
from app.modules.document_engine_intelligence.application.paired_alignment_service import (
    DossierAlignmentError,
    generate_dossier_row_alignments,
)
from app.modules.excel_import.infrastructure.object_storage import (
    ObjectStoragePort,
    get_object_storage,
)
from worker.runtime import JobExecutionContext, JobHandler, JobHandlerFailure

SessionFactory = Callable[[], Session]


def _payload_uuid(context: JobExecutionContext, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(context.payload[field_name]))
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise JobHandlerFailure(
            "invalid_job_payload", f"Job payload field {field_name} is invalid."
        ) from exc


def _http_failure(exc: HTTPException) -> JobHandlerFailure:
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("error_code") or "job_contract_error")
        message = str(detail.get("detail") or "Job contract validation failed.")
    else:
        code = "job_contract_error"
        message = str(detail)
    return JobHandlerFailure(code, message)


def handle_document_extraction(
    context: JobExecutionContext,
    *,
    session_factory: SessionFactory = SessionLocal,
    storage: ObjectStoragePort | None = None,
) -> dict[str, object]:
    bundle_id = _payload_uuid(context, "dossier_bundle_id")
    source_file_id = _payload_uuid(context, "source_file_id")
    db = session_factory()
    try:
        snapshot = extract_dossier_source(
            db,
            org_id=context.organization_id,
            dossier_bundle_id=bundle_id,
            source_file_id=source_file_id,
            job_id=context.job_id,
            generation_token=context.generation_token,
            storage=storage if storage is not None else get_object_storage(),
        )
        return {
            "extraction_snapshot_id": str(snapshot.id),
            "source_file_id": str(snapshot.source_file_id),
            "source_kind": snapshot.source_kind,
            "source_checksum_sha256": snapshot.source_checksum_sha256,
            "extraction_digest_sha256": snapshot.extraction_digest_sha256,
            "table_count": snapshot.table_count,
            "row_count": snapshot.row_count,
        }
    except DossierExtractionError as exc:
        db.rollback()
        raise JobHandlerFailure(exc.code, exc.detail, retryable=exc.retryable) from exc
    except HTTPException as exc:
        db.rollback()
        raise _http_failure(exc) from exc
    finally:
        db.close()


def handle_dossier_alignment(
    context: JobExecutionContext,
    *,
    session_factory: SessionFactory = SessionLocal,
) -> dict[str, object]:
    bundle_id = _payload_uuid(context, "dossier_bundle_id")
    excel_snapshot_id = _payload_uuid(context, "excel_snapshot_id")
    report_snapshot_id = _payload_uuid(context, "report_snapshot_id")
    db = session_factory()
    try:
        run = generate_dossier_row_alignments(
            db,
            org_id=context.organization_id,
            dossier_bundle_id=bundle_id,
            excel_snapshot_id=excel_snapshot_id,
            report_snapshot_id=report_snapshot_id,
            job_id=context.job_id,
            generation_token=context.generation_token,
        )
        return {
            "alignment_run_id": str(run.id),
            "excel_snapshot_id": str(run.excel_snapshot_id),
            "report_snapshot_id": str(run.report_snapshot_id),
            "source_pair_digest_sha256": run.source_pair_digest_sha256,
            "algorithm_version": run.algorithm_version,
            "status": run.status,
            "total_excel_rows": run.total_excel_rows,
            "candidate_count": run.candidate_count,
            "review_required_count": run.review_required_count,
            "unresolved_count": run.unresolved_count,
        }
    except DossierAlignmentError as exc:
        db.rollback()
        raise JobHandlerFailure(exc.code, exc.detail, retryable=exc.retryable) from exc
    except HTTPException as exc:
        db.rollback()
        raise _http_failure(exc) from exc
    finally:
        db.close()


def build_handler_registry(
    *,
    session_factory: SessionFactory = SessionLocal,
    storage: ObjectStoragePort | None = None,
) -> dict[str, JobHandler]:
    def document_extraction(context: JobExecutionContext) -> dict[str, object]:
        return handle_document_extraction(
            context,
            session_factory=session_factory,
            storage=storage,
        )

    def dossier_alignment(context: JobExecutionContext) -> dict[str, object]:
        return handle_dossier_alignment(context, session_factory=session_factory)

    return {
        "document_extraction": document_extraction,
        "dossier_alignment": dossier_alignment,
    }
