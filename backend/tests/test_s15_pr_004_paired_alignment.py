"""S15-R-002 content alignment tests over real Excel and DOCX extraction."""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.document_engine_intelligence.application.paired_alignment_service import (
    generate_dossier_row_alignments,
)
from app.modules.excel_import.models import (
    DossierAlignmentRun,
    DossierExtractedRow,
    DossierRowAlignment,
)
from app.modules.project_master_data.models import AuditEvent
from app.modules.workflow_workbench.application.reliable_job_service import (
    claim_job_lease,
    complete_job,
    enqueue_durable_job,
)
from tests.test_s15_pr_003_docx_extraction import (
    SourceBackedSeed,
    _extract_and_complete,
    _seed_source_backed_dossier,
    db_session,
)

__all__ = ["db_session"]


def _claim_alignment_job(
    db: Session,
    seed: SourceBackedSeed,
    *,
    excel_snapshot_id: object,
    report_snapshot_id: object,
    key: str,
):
    job = enqueue_durable_job(
        db,
        actor=seed.actor,
        org_id=seed.actor.organization_id,
        job_type="dossier_alignment",
        idempotency_key=key,
        payload={
            "dossier_bundle_id": str(seed.bundle_id),
            "excel_snapshot_id": str(excel_snapshot_id),
            "report_snapshot_id": str(report_snapshot_id),
        },
    )
    db.commit()
    return claim_job_lease(
        db,
        worker_id="alignment-worker",
        job_id=job.id,
        org_id=seed.actor.organization_id,
        lease_duration_seconds=60,
    )


def _generate_and_complete(
    db: Session,
    seed: SourceBackedSeed,
    *,
    excel_snapshot_id: object,
    report_snapshot_id: object,
    key: str,
) -> DossierAlignmentRun:
    job, attempt = _claim_alignment_job(
        db,
        seed,
        excel_snapshot_id=excel_snapshot_id,
        report_snapshot_id=report_snapshot_id,
        key=key,
    )
    run = generate_dossier_row_alignments(
        db,
        org_id=seed.actor.organization_id,
        dossier_bundle_id=seed.bundle_id,
        excel_snapshot_id=excel_snapshot_id,
        report_snapshot_id=report_snapshot_id,
        job_id=job.id,
        generation_token=job.generation_token,
    )
    complete_job(
        db,
        worker_id="alignment-worker",
        job_id=job.id,
        org_id=seed.actor.organization_id,
        attempt_id=attempt.id,
        generation_token=job.generation_token,
        result_payload={"alignment_run_id": str(run.id)},
    )
    return run


def test_alignment_uses_content_not_row_order_and_never_auto_confirms(
    db_session: Session,
) -> None:
    seed = _seed_source_backed_dossier(db_session, "alignment-content")
    excel_snapshot = _extract_and_complete(
        db_session, seed, seed.excel_source, key="align-extract-excel"
    )
    report_snapshot = _extract_and_complete(
        db_session, seed, seed.report_source, key="align-extract-report"
    )
    run = _generate_and_complete(
        db_session,
        seed,
        excel_snapshot_id=excel_snapshot.id,
        report_snapshot_id=report_snapshot.id,
        key="align-content",
    )

    assert run.total_excel_rows == 2
    assert run.candidate_count == 1
    assert run.review_required_count == 1
    assert run.unresolved_count == 0
    alignments = db_session.query(DossierRowAlignment).filter_by(alignment_run_id=run.id).all()
    assert len(alignments) == 2
    assert {item.state for item in alignments} == {"candidate", "review_required"}
    assert all(item.state not in {"confirmed", "rejected"} for item in alignments)

    by_excel_name = {}
    for alignment in alignments:
        excel_row = db_session.get(DossierExtractedRow, alignment.excel_row_id)
        technical_row = db_session.get(DossierExtractedRow, alignment.technical_row_id)
        by_excel_name[excel_row.normalized_fields["name"]] = (alignment, technical_row)
    generator_alignment, generator_technical = by_excel_name["Máy phát điện Cummins C500"]
    assert generator_technical.normalized_fields["name"] == "Máy phát điện Cummins C500"
    assert generator_alignment.match_basis["technical"]["stt_exact"] is True
    assert generator_alignment.match_basis["technical"]["order_used_only_as_tiebreaker"] is True
    assert generator_alignment.state == "review_required"
    assert {item["code"] for item in generator_alignment.conflicts} >= {"unit_mismatch"}
    assert (
        db_session.query(AuditEvent)
        .filter_by(event_name="DossierRowAlignmentCandidatesGenerated", entity_id=run.id)
        .count()
        == 1
    )


def test_alignment_rerun_is_idempotent_for_exact_snapshot_pair(db_session: Session) -> None:
    seed = _seed_source_backed_dossier(db_session, "alignment-idempotent")
    excel_snapshot = _extract_and_complete(
        db_session, seed, seed.excel_source, key="idem-extract-excel"
    )
    report_snapshot = _extract_and_complete(
        db_session, seed, seed.report_source, key="idem-extract-report"
    )
    first = _generate_and_complete(
        db_session,
        seed,
        excel_snapshot_id=excel_snapshot.id,
        report_snapshot_id=report_snapshot.id,
        key="alignment-idempotent-1",
    )
    second = _generate_and_complete(
        db_session,
        seed,
        excel_snapshot_id=excel_snapshot.id,
        report_snapshot_id=report_snapshot.id,
        key="alignment-idempotent-2",
    )
    assert second.id == first.id
    assert db_session.query(DossierAlignmentRun).count() == 1
    assert db_session.query(DossierRowAlignment).count() == 2
    assert (
        db_session.query(AuditEvent)
        .filter_by(event_name="DossierRowAlignmentCandidatesGenerated")
        .count()
        == 1
    )


def test_alignment_job_rejects_snapshot_from_wrong_role(db_session: Session) -> None:
    seed = _seed_source_backed_dossier(db_session, "alignment-role")
    excel_snapshot = _extract_and_complete(
        db_session, seed, seed.excel_source, key="role-extract-excel"
    )
    report_snapshot = _extract_and_complete(
        db_session, seed, seed.report_source, key="role-extract-report"
    )
    with pytest.raises(HTTPException) as exc_info:
        enqueue_durable_job(
            db_session,
            actor=seed.actor,
            org_id=seed.actor.organization_id,
            job_type="dossier_alignment",
            idempotency_key="alignment-swapped-snapshots",
            payload={
                "dossier_bundle_id": str(seed.bundle_id),
                "excel_snapshot_id": str(report_snapshot.id),
                "report_snapshot_id": str(excel_snapshot.id),
            },
        )
    assert exc_info.value.status_code == 404
