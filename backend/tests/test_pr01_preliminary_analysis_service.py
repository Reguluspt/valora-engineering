"""Focused proof for the PR-01 PreliminaryAnalysisSnapshot command foundation."""
from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
import app.modules.excel_import.models  # noqa: F401
import app.modules.project_master_data.application.preliminary_analysis_service as service
from app.modules.project_master_data.application.preliminary_analysis_service import (
    finalize_preliminary_analysis,
)
from app.modules.project_master_data.schemas import (
    PreliminaryAnalysisFinalizeRequest,
    PreliminaryAnalysisLineItem,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    Customer,
    CustomerStatus,
    ImportBatchStatus,
    OrganizationProfile,
    OrganizationStatus,
    PreliminaryAnalysisSnapshot,
    Project,
    ProjectAssetImportBatch,
    ProjectWorkflowStatus,
    Role,
    User,
    UserRole,
    UserStatus,
)
from app.modules.excel_import.models import (
    ColumnMappingDecision,
    ColumnMappingDecisionKind,
    ColumnMappingDecisionOutcome,
    ColumnMappingMemoryScope,
    ColumnMappingProfileUsage,
    ColumnMappingProposalSourceKind,
    ImportSourceArtifact,
    ImportSourceArtifactState,
    WorkbookStructureDisposition,
    WorkbookStructureSnapshot,
)


PRELIMINARY_ANALYSIS_PERMISSION = "project:preliminary_analysis:finalize"


@pytest.fixture
def analysis_db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def _line(
    *,
    identity: str = "Máy bơm nước 10HP",
    accepted_price_basis: str = "internet_survey",
    confirmed_reference_price: float = 1_000_000.0,
    transport_percentage: float = 5.0,
    proposed_unit_price: float = 1_050_000.0,
    human_line_confirmed: bool = True,
    has_unresolved_blocking_line: bool = False,
    source_row_number: int = 10,
    quantity: float = 2.0,
) -> dict:
    return {
        "identity": identity,
        "accepted_price_basis": accepted_price_basis,
        "confirmed_reference_price": confirmed_reference_price,
        "transport_percentage": transport_percentage,
        "proposed_unit_price": proposed_unit_price,
        "human_line_confirmed": human_line_confirmed,
        "has_unresolved_blocking_line": has_unresolved_blocking_line,
        "source_row_number": source_row_number,
        "quantity": quantity,
    }


def _seed(
    analysis_db: Session,
    *,
    suffix: str = "a",
    grant_permission: bool = True,
    artifact_state: ImportSourceArtifactState = ImportSourceArtifactState.AVAILABLE,
) -> dict:
    org = OrganizationProfile(
        legal_name=f"Preliminary Analysis Org {suffix}",
        organization_slug=f"preliminary-analysis-{suffix}-{uuid.uuid4().hex[:8]}",
        status=OrganizationStatus.ACTIVE,
    )
    analysis_db.add(org)
    analysis_db.flush()
    actor = User(
        organization_id=org.id,
        email=f"preliminary-analysis-{suffix}-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Preliminary Analysis Human",
        status=UserStatus.ACTIVE,
    )
    analysis_db.add(actor)
    analysis_db.flush()
    role = Role(
        code=f"preliminary-analysis-{suffix}-{uuid.uuid4().hex[:8]}",
        display_name="Preliminary Analysis Fixture",
        permissions=[PRELIMINARY_ANALYSIS_PERMISSION],
    )
    analysis_db.add(role)
    analysis_db.flush()
    analysis_db.add(UserRole(user_id=actor.id, role_id=role.id, is_active=True))

    customer = Customer(
        organization_id=org.id,
        legal_name=f"Preliminary Analysis Customer {suffix}",
        status=CustomerStatus.ACTIVE,
        created_by=actor.id,
    )
    analysis_db.add(customer)
    analysis_db.flush()
    project = Project(
        organization_id=org.id,
        customer_id=customer.id,
        code=f"PR-{suffix}-{uuid.uuid4().hex[:6]}",
        name=f"Preliminary Analysis Project {suffix}",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=actor.id,
    )
    analysis_db.add(project)
    analysis_db.flush()
    batch = ProjectAssetImportBatch(
        organization_id=org.id,
        project_id=project.id,
        source_filename="danh-muc-v1.xlsx",
        status=ImportBatchStatus.PARSED.value,
        total_rows=1,
        valid_rows=1,
        created_by_user_id=actor.id,
    )
    analysis_db.add(batch)
    analysis_db.flush()
    artifact = ImportSourceArtifact(
        organization_id=org.id,
        project_id=project.id,
        import_batch_id=batch.id,
        generation=1,
        original_filename="danh-muc-v1.xlsx",
        detected_format="xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size_bytes=1024,
        checksum_sha256="a" * 64,
        storage_object_key=f"import-sources/{project.id}/v1.xlsx",
        state=artifact_state.value,
        created_by_user_id=actor.id,
    )
    analysis_db.add(artifact)
    analysis_db.flush()
    batch.current_source_artifact_id = artifact.id
    analysis_db.flush()
    structure = WorkbookStructureSnapshot(
        organization_id=org.id,
        project_id=project.id,
        import_batch_id=batch.id,
        source_artifact_id=artifact.id,
        snapshot_version=1,
        source_checksum_sha256="a" * 64,
        rule_version="s13-pr-003-v3",
        adapter_name="excel",
        adapter_version="1.0",
        disposition=WorkbookStructureDisposition.PROPOSED.value,
        candidate_count=1,
        structure_payload={"sheet": "Assets"},
        analysis_digest_sha256="b" * 64,
        created_by_user_id=actor.id,
    )
    analysis_db.add(structure)
    analysis_db.flush()
    proposal_decision = ColumnMappingDecision(
        organization_id=org.id,
        customer_id=customer.id,
        project_id=project.id,
        import_batch_id=batch.id,
        source_artifact_id=artifact.id,
        structure_snapshot_id=structure.id,
        decision_kind=ColumnMappingDecisionKind.PROPOSAL.value,
        outcome=ColumnMappingDecisionOutcome.PROPOSED.value,
        memory_scope=ColumnMappingMemoryScope.NONE.value,
        actor_user_id=actor.id,
        command_id=uuid.uuid4(),
        proposal_source_kind=ColumnMappingProposalSourceKind.HUMAN.value,
        proposal_source_version="1.0",
        mapping_contract_version="v1",
        template_fingerprint_sha256="c" * 64,
        mapping_snapshot={"roles": []},
        mapping_digest_sha256="d" * 64,
        before_summary={},
        after_summary={},
    )
    analysis_db.add(proposal_decision)
    analysis_db.flush()
    mapping_snapshot = {
        "contract_version": "s13-pr-004-v1",
        "source": {
            "source_artifact_id": str(artifact.id),
            "generation": artifact.generation,
            "checksum_sha256": artifact.checksum_sha256,
        },
        "structure": {
            "structure_snapshot_id": str(structure.id),
            "snapshot_version": 1,
            "rule_version": "s13-pr-003-v3",
            "analysis_digest_sha256": "b" * 64,
        },
        "template_fingerprint_sha256": "c" * 64,
        "candidate": {
            "candidate_index": 0,
            "sheet_name": "Assets",
            "header_start_row": 1,
            "header_end_row": 2,
            "data_start_row": 3,
        },
        "fields": [
            {
                "source_column_index": 1,
                "source_column_letter": "A",
                "original_header": "Tên tài sản",
                "semantic_role": "raw_asset_name",
            },
            {
                "source_column_index": 2,
                "source_column_letter": "B",
                "original_header": "Số lượng",
                "semantic_role": "quantity",
            },
            {
                "source_column_index": 3,
                "source_column_letter": "C",
                "original_header": "Ghi chú",
                "semantic_role": "ignore",
            },
        ],
    }
    decision = ColumnMappingDecision(
        organization_id=org.id,
        customer_id=customer.id,
        project_id=project.id,
        import_batch_id=batch.id,
        source_artifact_id=artifact.id,
        structure_snapshot_id=structure.id,
        decision_kind=ColumnMappingDecisionKind.CONFIRMATION.value,
        outcome=ColumnMappingDecisionOutcome.ACCEPTED.value,
        memory_scope=ColumnMappingMemoryScope.NONE.value,
        proposal_decision_id=proposal_decision.id,
        actor_user_id=actor.id,
        command_id=uuid.uuid4(),
        proposal_source_kind=ColumnMappingProposalSourceKind.HUMAN.value,
        proposal_source_version="1.0",
        mapping_contract_version="v1",
        template_fingerprint_sha256="c" * 64,
        mapping_snapshot=mapping_snapshot,
        mapping_digest_sha256="d" * 64,
        before_summary={},
        after_summary={},
    )
    analysis_db.add(decision)
    analysis_db.flush()
    usage = ColumnMappingProfileUsage(
        organization_id=org.id,
        customer_id=customer.id,
        project_id=project.id,
        import_batch_id=batch.id,
        source_artifact_id=artifact.id,
        structure_snapshot_id=structure.id,
        confirmation_decision_id=decision.id,
        command_id=uuid.uuid4(),
        materialization_contract_version="v1",
        mapping_contract_version="v1",
        template_fingerprint_sha256="c" * 64,
        mapping_snapshot=decision.mapping_snapshot,
        mapping_digest_sha256="d" * 64,
        source_checksum_sha256="a" * 64,
        structure_digest_sha256="b" * 64,
        materialized_asset_row_count=1,
        created_by_user_id=actor.id,
    )
    analysis_db.add(usage)
    analysis_db.commit()

    return {
        "org": org,
        "actor": actor,
        "role": role,
        "customer": customer,
        "project": project,
        "batch": batch,
        "artifact": artifact,
        "structure": structure,
        "decision": decision,
        "usage": usage,
    }


def _finalize(
    db: Session,
    seeded: dict,
    *,
    line_manifest: list[dict] | None = None,
    idempotency_key: str = "analysis-key-1",
    confirmed: bool = True,
    expected_project_version: int = 1,
    import_batch_id: uuid.UUID | None = None,
) -> PreliminaryAnalysisSnapshot:
    return finalize_preliminary_analysis(
        db,
        actor=seeded["actor"],
        org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        expected_project_version=expected_project_version,
        import_batch_id=import_batch_id if import_batch_id is not None else seeded["batch"].id,
        source_artifact_id=seeded["artifact"].id,
        structure_snapshot_id=seeded["structure"].id,
        mapping_decision_id=seeded["decision"].id,
        mapping_profile_usage_id=seeded["usage"].id,
        mapping_decision_digest_sha256=seeded["decision"].mapping_digest_sha256,
        profile_usage_mapping_digest_sha256=seeded["usage"].mapping_digest_sha256,
        line_manifest=line_manifest if line_manifest is not None else [_line()],
        idempotency_key=idempotency_key,
        confirmed=confirmed,
        correlation_id="correlation-1",
    )


def _assert_error(
    exc: pytest.ExceptionInfo,
    expected_status: int,
    expected_code: str,
) -> None:
    assert exc.value.status_code == expected_status
    assert exc.value.detail["error_code"] == expected_code


# ---------------------------------------------------------------------------
# Baseline success and project/snapshot integrity.
# ---------------------------------------------------------------------------


def test_finalize_creates_snapshot_and_emits_audit(analysis_db: Session) -> None:
    seeded = _seed(analysis_db)
    snapshot = _finalize(analysis_db, seeded)

    assert snapshot.project_id == seeded["project"].id
    assert snapshot.version == 1
    assert snapshot.idempotency_key == "analysis-key-1"
    assert snapshot.line_manifest[0]["source_row_number"] == 10
    assert snapshot.line_manifest[0]["quantity"] == 2.0
    assert snapshot.request_digest_sha256 is not None
    assert len(snapshot.request_digest_sha256) == 64

    audit = (
        analysis_db.query(AuditEvent)
        .filter_by(organization_id=seeded["org"].id, event_name="PreliminaryAnalysisSnapshotFinalized")
        .first()
    )
    assert audit is not None
    assert audit.payload["project_id"] == str(seeded["project"].id)
    assert audit.payload["source_artifact_id"] == str(seeded["artifact"].id)


def test_finalize_checks_project_row_version(analysis_db: Session) -> None:
    seeded = _seed(analysis_db)
    before = seeded["project"].row_version
    _finalize(analysis_db, seeded)
    analysis_db.refresh(seeded["project"])
    assert seeded["project"].row_version == before


def test_finalize_requires_permission(analysis_db: Session) -> None:
    seeded = _seed(analysis_db, grant_permission=False)
    seeded["actor"].roles.clear()
    analysis_db.commit()

    with pytest.raises(HTTPException) as exc:
        _finalize(analysis_db, seeded)

    _assert_error(exc, 403, "preliminary_analysis_forbidden")


def test_finalize_rejects_missing_project(analysis_db: Session) -> None:
    seeded = _seed(analysis_db)
    with pytest.raises(HTTPException) as exc:
        finalize_preliminary_analysis(
            analysis_db,
            actor=seeded["actor"],
            org_id=seeded["org"].id,
            project_id=uuid.uuid4(),
            expected_project_version=1,
            import_batch_id=seeded["batch"].id,
            source_artifact_id=seeded["artifact"].id,
            structure_snapshot_id=seeded["structure"].id,
            mapping_decision_id=seeded["decision"].id,
            mapping_profile_usage_id=seeded["usage"].id,
            mapping_decision_digest_sha256=seeded["decision"].mapping_digest_sha256,
            profile_usage_mapping_digest_sha256=seeded["usage"].mapping_digest_sha256,
            line_manifest=[_line()],
            idempotency_key="analysis-key-1",
            confirmed=True,
            correlation_id="correlation-1",
        )
    _assert_error(exc, 404, "project_not_found")


def test_finalize_rejects_org_mismatch(analysis_db: Session) -> None:
    seeded = _seed(analysis_db)
    other_org = OrganizationProfile(
        legal_name="Other Org",
        organization_slug=f"other-{uuid.uuid4().hex[:8]}",
        status=OrganizationStatus.ACTIVE,
    )
    analysis_db.add(other_org)
    analysis_db.flush()
    with pytest.raises(HTTPException) as exc:
        finalize_preliminary_analysis(
            analysis_db,
            actor=seeded["actor"],
            org_id=other_org.id,
            project_id=seeded["project"].id,
            expected_project_version=1,
            import_batch_id=seeded["batch"].id,
            source_artifact_id=seeded["artifact"].id,
            structure_snapshot_id=seeded["structure"].id,
            mapping_decision_id=seeded["decision"].id,
            mapping_profile_usage_id=seeded["usage"].id,
            mapping_decision_digest_sha256=seeded["decision"].mapping_digest_sha256,
            profile_usage_mapping_digest_sha256=seeded["usage"].mapping_digest_sha256,
            line_manifest=[_line()],
            idempotency_key="analysis-key-1",
            confirmed=True,
            correlation_id="correlation-1",
        )
    _assert_error(exc, 403, "preliminary_analysis_forbidden")


def test_finalize_rejects_actor_from_another_org(analysis_db: Session) -> None:
    seeded = _seed(analysis_db)
    other_org = OrganizationProfile(
        legal_name="Other Org",
        organization_slug=f"other-{uuid.uuid4().hex[:8]}",
        status=OrganizationStatus.ACTIVE,
    )
    analysis_db.add(other_org)
    analysis_db.flush()
    other_actor = User(
        organization_id=other_org.id,
        email=f"other-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Other Human",
        status=UserStatus.ACTIVE,
    )
    analysis_db.add(other_actor)
    analysis_db.flush()
    role = Role(code="other-role", display_name="Other Role", permissions=[PRELIMINARY_ANALYSIS_PERMISSION])
    analysis_db.add(role)
    analysis_db.flush()
    analysis_db.add(UserRole(user_id=other_actor.id, role_id=role.id, is_active=True))
    analysis_db.commit()

    with pytest.raises(HTTPException) as exc:
        finalize_preliminary_analysis(
            analysis_db,
            actor=other_actor,
            org_id=seeded["org"].id,
            project_id=seeded["project"].id,
            expected_project_version=1,
            import_batch_id=seeded["batch"].id,
            source_artifact_id=seeded["artifact"].id,
            structure_snapshot_id=seeded["structure"].id,
            mapping_decision_id=seeded["decision"].id,
            mapping_profile_usage_id=seeded["usage"].id,
            mapping_decision_digest_sha256=seeded["decision"].mapping_digest_sha256,
            profile_usage_mapping_digest_sha256=seeded["usage"].mapping_digest_sha256,
            line_manifest=[_line()],
            idempotency_key="analysis-key-1",
            confirmed=True,
            correlation_id="correlation-1",
        )
    _assert_error(exc, 403, "preliminary_analysis_forbidden")


def test_finalize_rejects_unconfirmed_command(analysis_db: Session) -> None:
    seeded = _seed(analysis_db)
    with pytest.raises(HTTPException) as exc:
        _finalize(analysis_db, seeded, confirmed=False)
    _assert_error(exc, 400, "preliminary_analysis_confirmation_required")


@pytest.mark.parametrize(
    "confirmed",
    [1, "yes"],
)
def test_finalize_rejects_truthy_non_bool_confirmed(
    analysis_db: Session, confirmed: Any
) -> None:
    seeded = _seed(analysis_db)
    with pytest.raises(HTTPException) as exc:
        _finalize(analysis_db, seeded, confirmed=confirmed)
    _assert_error(exc, 400, "preliminary_analysis_confirmation_required")
    assert analysis_db.query(PreliminaryAnalysisSnapshot).count() == 0
    assert analysis_db.query(AuditEvent).count() == 0


def test_finalize_rejects_stale_project_version(analysis_db: Session) -> None:
    seeded = _seed(analysis_db)
    seeded["project"].row_version = 42
    analysis_db.commit()
    with pytest.raises(HTTPException) as exc:
        _finalize(analysis_db, seeded, expected_project_version=1)
    _assert_error(exc, 409, "project_version_conflict")


def test_finalize_rejects_blocked_line(analysis_db: Session) -> None:
    seeded = _seed(analysis_db)
    with pytest.raises(HTTPException) as exc:
        _finalize(
            analysis_db,
            seeded,
            line_manifest=[_line(has_unresolved_blocking_line=True)],
        )
    _assert_error(exc, 409, "preliminary_analysis_line_blocking")


def test_finalize_rejects_unconfirmed_line(analysis_db: Session) -> None:
    seeded = _seed(analysis_db)
    with pytest.raises(HTTPException) as exc:
        _finalize(
            analysis_db,
            seeded,
            line_manifest=[_line(human_line_confirmed=False)],
        )
    _assert_error(exc, 409, "preliminary_analysis_line_confirmation_missing")


def test_finalize_rejects_artifact_not_available(analysis_db: Session) -> None:
    seeded = _seed(analysis_db, artifact_state=ImportSourceArtifactState.FAILED)
    with pytest.raises(HTTPException) as exc:
        _finalize(analysis_db, seeded)
    _assert_error(exc, 409, "source_artifact_not_available")


def test_finalize_rejects_batch_mismatch(analysis_db: Session) -> None:
    seeded = _seed(analysis_db)
    other_batch = ProjectAssetImportBatch(
        organization_id=seeded["org"].id,
        project_id=uuid.uuid4(),
        source_filename="other.xlsx",
        status=ImportBatchStatus.PARSED.value,
        total_rows=1,
        valid_rows=1,
        created_by_user_id=seeded["actor"].id,
    )
    analysis_db.add(other_batch)
    analysis_db.flush()
    with pytest.raises(HTTPException) as exc:
        _finalize(analysis_db, seeded, import_batch_id=other_batch.id)
    _assert_error(exc, 404, "import_batch_not_found")


# ---------------------------------------------------------------------------
# Idempotency behavior.
# ---------------------------------------------------------------------------


def test_finalize_same_request_is_idempotent(analysis_db: Session) -> None:
    seeded = _seed(analysis_db)
    first = _finalize(analysis_db, seeded)
    second = _finalize(analysis_db, seeded)
    assert first.id == second.id
    assert analysis_db.query(PreliminaryAnalysisSnapshot).count() == 1
    assert (
        analysis_db.query(AuditEvent)
        .filter_by(event_name="PreliminaryAnalysisSnapshotFinalized")
        .count()
        == 1
    )


def test_finalize_same_key_different_content_is_reused(analysis_db: Session) -> None:
    seeded = _seed(analysis_db)
    _finalize(analysis_db, seeded)
    with pytest.raises(HTTPException) as exc:
        _finalize(analysis_db, seeded, line_manifest=[_line(quantity=5.0)])
    _assert_error(exc, 409, "preliminary_analysis_idempotency_key_reused")
    assert analysis_db.query(PreliminaryAnalysisSnapshot).count() == 1


def test_finalize_different_key_after_success_is_already_finalized(
    analysis_db: Session,
) -> None:
    seeded = _seed(analysis_db)
    _finalize(analysis_db, seeded)
    with pytest.raises(HTTPException) as exc:
        _finalize(analysis_db, seeded, idempotency_key="different-key")
    _assert_error(exc, 409, "preliminary_analysis_already_finalized")


def test_finalize_replay_with_empty_key_is_invalid_after_success(
    analysis_db: Session,
) -> None:
    seeded = _seed(analysis_db)
    _finalize(analysis_db, seeded)
    with pytest.raises(HTTPException) as exc:
        _finalize(analysis_db, seeded, idempotency_key="")
    _assert_error(exc, 422, "invalid_idempotency_key")


def test_finalize_with_empty_key_is_invalid(analysis_db: Session) -> None:
    seeded = _seed(analysis_db)
    with pytest.raises(HTTPException) as exc:
        _finalize(analysis_db, seeded, idempotency_key="")
    _assert_error(exc, 422, "invalid_idempotency_key")


# ---------------------------------------------------------------------------
# Row-version / line manifest digest / audit integrity.
# ---------------------------------------------------------------------------


def test_finalize_line_manifest_digest_changes_with_content(analysis_db: Session) -> None:
    seeded = _seed(analysis_db)
    first = _finalize(analysis_db, seeded, idempotency_key="digest-key-a")
    analysis_db.refresh(first)
    first_digest = first.line_manifest_digest_sha256

    seeded2 = _seed(analysis_db, suffix="b")
    second = _finalize(analysis_db, seeded2, idempotency_key="digest-key-b")
    assert second.line_manifest_digest_sha256 == first_digest

    seeded3 = _seed(analysis_db, suffix="c")
    third = _finalize(
        analysis_db,
        seeded3,
        idempotency_key="digest-key-c",
        line_manifest=[_line(quantity=5.0)],
    )
    assert third.line_manifest_digest_sha256 != first_digest


def test_empty_line_manifest_is_rejected(analysis_db: Session) -> None:
    seeded = _seed(analysis_db)
    with pytest.raises(HTTPException) as exc:
        _finalize(analysis_db, seeded, line_manifest=[])
    _assert_error(exc, 409, "preliminary_analysis_line_manifest_empty")


def test_line_condition_failures(
    analysis_db: Session,
) -> None:
    seeded = _seed(analysis_db)
    manifest = [_line(), _line(identity="Máy bơm 20HP", source_row_number=11)]
    manifest[1]["human_line_confirmed"] = False
    manifest[1]["has_unresolved_blocking_line"] = True

    with pytest.raises(HTTPException) as exc:
        _finalize(analysis_db, seeded, line_manifest=manifest)

    assert exc.value.status_code == 409
    assert "Dòng 1" in exc.value.detail["detail"]
    assert analysis_db.query(PreliminaryAnalysisSnapshot).count() == 0


# ---------------------------------------------------------------------------
# Branch A — v1 contract superseded regression matrix.
# ---------------------------------------------------------------------------


def _v1_line(**overrides) -> dict:
    line = _line(**overrides)
    return {k: v for k, v in line.items() if k in service._LINE_V2_KEYS - {"source_row_number", "quantity"}}


def test_v1_shaped_finalize_is_superseded_before_db_lookup(analysis_db: Session) -> None:
    seeded = _seed(analysis_db)

    with pytest.raises(HTTPException) as exc:
        _finalize(analysis_db, seeded, line_manifest=[_v1_line()])

    _assert_error(exc, 409, "preliminary_analysis_contract_superseded")
    assert analysis_db.query(PreliminaryAnalysisSnapshot).count() == 0
    assert analysis_db.query(AuditEvent).count() == 0


def test_v1_shaped_same_key_replay_is_superseded_without_writes(analysis_db: Session) -> None:
    seeded = _seed(analysis_db)
    key = "v1-replay-key"

    with pytest.raises(HTTPException) as exc:
        _finalize(analysis_db, seeded, idempotency_key=key, line_manifest=[_v1_line()])
    _assert_error(exc, 409, "preliminary_analysis_contract_superseded")

    with pytest.raises(HTTPException) as exc:
        _finalize(analysis_db, seeded, idempotency_key=key, line_manifest=[_v1_line()])
    _assert_error(exc, 409, "preliminary_analysis_contract_superseded")

    assert analysis_db.query(PreliminaryAnalysisSnapshot).count() == 0
    assert analysis_db.query(AuditEvent).count() == 0


def test_v2_request_using_old_v1_key_after_v2_snapshot_is_reused(analysis_db: Session) -> None:
    seeded = _seed(analysis_db)
    key = "old-v1-key"

    # First, a v1-shaped attempt with this key is superseded.
    with pytest.raises(HTTPException) as exc:
        _finalize(analysis_db, seeded, idempotency_key=key, line_manifest=[_v1_line()])
    _assert_error(exc, 409, "preliminary_analysis_contract_superseded")

    # Then a valid v2 snapshot is created with the same key.
    v2 = _finalize(analysis_db, seeded, idempotency_key=key)
    assert v2.idempotency_key == key

    # A later v2 request reusing the old v1 key with different content is rejected.
    with pytest.raises(HTTPException) as exc:
        _finalize(
            analysis_db,
            seeded,
            idempotency_key=key,
            line_manifest=[_line(quantity=5.0)],
        )
    _assert_error(exc, 409, "preliminary_analysis_idempotency_key_reused")


def test_different_key_v2_against_existing_v1_snapshot_is_already_finalized(
    analysis_db: Session,
) -> None:
    seeded = _seed(analysis_db)
    # Simulate a legacy v1 snapshot already persisted.
    legacy = PreliminaryAnalysisSnapshot(
        organization_id=seeded["org"].id,
        customer_id=seeded["customer"].id,
        project_id=seeded["project"].id,
        version=1,
        import_batch_id=seeded["batch"].id,
        source_artifact_id=seeded["artifact"].id,
        structure_snapshot_id=seeded["structure"].id,
        mapping_decision_id=seeded["decision"].id,
        mapping_profile_usage_id=seeded["usage"].id,
        source_artifact_generation=seeded["artifact"].generation,
        mapping_decision_digest_sha256=seeded["decision"].mapping_digest_sha256,
        profile_usage_mapping_digest_sha256=seeded["usage"].mapping_digest_sha256,
        line_manifest=[_v1_line()],
        line_manifest_digest_sha256="0" * 64,
        finalized_by_user_id=seeded["actor"].id,
        idempotency_key="legacy-v1-key",
        request_digest_sha256="1" * 64,
    )
    analysis_db.add(legacy)
    analysis_db.commit()

    with pytest.raises(HTTPException) as exc:
        _finalize(analysis_db, seeded, idempotency_key="v2-key")

    _assert_error(exc, 409, "preliminary_analysis_already_finalized")


def test_v1_snapshot_cannot_generate_artifacts_is_invariant(analysis_db: Session) -> None:
    """Legacy v1 facts remain readable but are not accepted for artifact generation."""
    seeded = _seed(analysis_db)
    legacy = PreliminaryAnalysisSnapshot(
        organization_id=seeded["org"].id,
        customer_id=seeded["customer"].id,
        project_id=seeded["project"].id,
        version=1,
        import_batch_id=seeded["batch"].id,
        source_artifact_id=seeded["artifact"].id,
        structure_snapshot_id=seeded["structure"].id,
        mapping_decision_id=seeded["decision"].id,
        mapping_profile_usage_id=seeded["usage"].id,
        source_artifact_generation=seeded["artifact"].generation,
        mapping_decision_digest_sha256=seeded["decision"].mapping_digest_sha256,
        profile_usage_mapping_digest_sha256=seeded["usage"].mapping_digest_sha256,
        line_manifest=[_v1_line()],
        line_manifest_digest_sha256="0" * 64,
        finalized_by_user_id=seeded["actor"].id,
        idempotency_key="legacy-v1-key",
        request_digest_sha256="1" * 64,
    )
    analysis_db.add(legacy)
    analysis_db.commit()

    # The legacy row remains readable.
    persisted = analysis_db.get(PreliminaryAnalysisSnapshot, legacy.id)
    assert persisted is not None
    assert "source_row_number" not in persisted.line_manifest[0]


# ---------------------------------------------------------------------------
# RED-before/green-after regression tests for strict boolean/numeric handling.
# These must fail before the schema and service defense corrections are applied.
# ---------------------------------------------------------------------------
_VALID_LINE_DICT = {
    "identity": "Máy bơm nước 10HP",
    "accepted_price_basis": "internet_survey",
    "confirmed_reference_price": 1_000_000.0,
    "transport_percentage": 5.0,
    "proposed_unit_price": 1_050_000.0,
    "human_line_confirmed": True,
    "has_unresolved_blocking_line": False,
    "source_row_number": 10,
    "quantity": 2.0,
}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("human_line_confirmed", None),
        ("human_line_confirmed", "true"),
        ("human_line_confirmed", "True"),
        ("human_line_confirmed", 1),
        ("human_line_confirmed", 0),
        ("human_line_confirmed", 1.0),
        ("has_unresolved_blocking_line", None),
        ("has_unresolved_blocking_line", "true"),
        ("has_unresolved_blocking_line", 1),
        ("has_unresolved_blocking_line", 0),
    ],
)
def test_schema_line_rejects_non_bool_for_boolean_flags(field: str, value) -> None:
    line = dict(_VALID_LINE_DICT)
    line[field] = value
    with pytest.raises(ValidationError):
        PreliminaryAnalysisLineItem(**line)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("confirmed_reference_price", "1000000"),
        ("confirmed_reference_price", True),
        ("confirmed_reference_price", False),
        ("confirmed_reference_price", float("nan")),
        ("confirmed_reference_price", float("inf")),
        ("confirmed_reference_price", float("-inf")),
        ("transport_percentage", "5"),
        ("transport_percentage", True),
        ("transport_percentage", float("nan")),
        ("transport_percentage", float("inf")),
        ("proposed_unit_price", "1050000"),
        ("proposed_unit_price", False),
        ("proposed_unit_price", float("-inf")),
        ("source_row_number", "10"),
        ("source_row_number", 10.0),
        ("source_row_number", None),
        ("quantity", "2"),
        ("quantity", None),
        ("quantity", float("nan")),
        ("quantity", float("inf")),
    ],
)
def test_schema_line_rejects_non_finite_non_number_for_numeric_fields(field: str, value) -> None:
    line = dict(_VALID_LINE_DICT)
    line[field] = value
    with pytest.raises(ValidationError):
        PreliminaryAnalysisLineItem(**line)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("confirmed", None),
        ("confirmed", "true"),
        ("confirmed", 1),
        ("confirmed", 0),
    ],
)
def test_schema_finalize_request_rejects_non_bool_confirmed(field: str, value) -> None:
    request = {
        "project_id": uuid.uuid4(),
        "expected_project_version": 1,
        "import_batch_id": uuid.uuid4(),
        "source_artifact_id": uuid.uuid4(),
        "structure_snapshot_id": uuid.uuid4(),
        "mapping_decision_id": uuid.uuid4(),
        "mapping_profile_usage_id": uuid.uuid4(),
        "line_manifest": [_VALID_LINE_DICT],
        "idempotency_key": "key-1",
        field: value,
    }
    with pytest.raises(ValidationError):
        PreliminaryAnalysisFinalizeRequest(**request)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("human_line_confirmed", "true"),
        ("human_line_confirmed", 1),
        ("human_line_confirmed", None),
        ("has_unresolved_blocking_line", "true"),
        ("has_unresolved_blocking_line", 1),
        ("has_unresolved_blocking_line", None),
        ("has_unresolved_blocking_line", True),
    ],
)
def test_service_direct_validator_rejects_non_bool_for_boolean_flags(field: str, value) -> None:
    line = dict(_VALID_LINE_DICT)
    line[field] = value
    with pytest.raises(HTTPException) as exc:
        service._validate_line_conditions([line])
    assert exc.value.status_code == 409


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("confirmed_reference_price", True),
        ("confirmed_reference_price", float("nan")),
        ("confirmed_reference_price", float("inf")),
        ("transport_percentage", True),
        ("transport_percentage", float("-inf")),
        ("proposed_unit_price", False),
        ("proposed_unit_price", float("nan")),
        ("source_row_number", "10"),
        ("source_row_number", 10.5),
        ("source_row_number", None),
        ("quantity", "2"),
        ("quantity", None),
        ("quantity", float("nan")),
        ("quantity", float("inf")),
    ],
)
def test_service_direct_validator_rejects_non_finite_numbers(field: str, value) -> None:
    line = dict(_VALID_LINE_DICT)
    line[field] = value
    with pytest.raises(HTTPException) as exc:
        service._validate_line_conditions([line])
    assert exc.value.status_code == 409


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("human_line_confirmed", "true"),
        ("has_unresolved_blocking_line", 1),
        ("confirmed_reference_price", float("inf")),
        ("transport_percentage", True),
        ("proposed_unit_price", float("nan")),
        ("source_row_number", 10.5),
        ("quantity", "2"),
    ],
)
def test_finalize_rejects_invalid_line_values_without_persistence(
    analysis_db: Session, field: str, value
) -> None:
    seeded = _seed(analysis_db)
    line = dict(_VALID_LINE_DICT)
    line[field] = value

    with pytest.raises(HTTPException) as exc:
        _finalize(analysis_db, seeded, line_manifest=[line])

    assert exc.value.status_code == 409
    assert analysis_db.query(PreliminaryAnalysisSnapshot).count() == 0
    assert analysis_db.query(AuditEvent).count() == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("confirmed_reference_price", 1_000_000),
        ("transport_percentage", 0),
        ("proposed_unit_price", 1_050_000),
        ("source_row_number", 1),
        ("source_row_number", 2),
        ("quantity", 0.0),
        ("quantity", 1),
    ],
)
def test_schema_and_service_accept_valid_integer_and_zero_values(field: str, value) -> None:
    line = dict(_VALID_LINE_DICT)
    line[field] = value
    parsed = PreliminaryAnalysisLineItem(**line)
    assert getattr(parsed, field) == value
    service._validate_line_conditions([line])


def test_service_direct_validator_rejects_zero_source_row_number() -> None:
    line = dict(_VALID_LINE_DICT)
    line["source_row_number"] = 0
    with pytest.raises(HTTPException) as exc:
        service._validate_line_conditions([line])
    assert exc.value.status_code == 409
    assert exc.value.detail["error_code"] == "preliminary_analysis_line_source_row_number_invalid"


def test_schema_line_rejects_zero_source_row_number() -> None:
    line = dict(_VALID_LINE_DICT)
    line["source_row_number"] = 0
    with pytest.raises(ValidationError):
        PreliminaryAnalysisLineItem(**line)


# ---------------------------------------------------------------------------
# v2 line manifest strict field presence and range regression tests.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", ["source_row_number", "quantity"])
def test_schema_line_rejects_missing_v2_required_field(field: str) -> None:
    line = dict(_VALID_LINE_DICT)
    del line[field]
    with pytest.raises(ValidationError):
        PreliminaryAnalysisLineItem(**line)


def test_schema_line_rejects_negative_source_row_number() -> None:
    line = dict(_VALID_LINE_DICT)
    line["source_row_number"] = -1
    with pytest.raises(ValidationError):
        PreliminaryAnalysisLineItem(**line)


def test_schema_line_rejects_negative_quantity() -> None:
    line = dict(_VALID_LINE_DICT)
    line["quantity"] = -0.01
    with pytest.raises(ValidationError):
        PreliminaryAnalysisLineItem(**line)


def test_service_direct_validator_rejects_negative_source_row_number() -> None:
    line = dict(_VALID_LINE_DICT)
    line["source_row_number"] = -1
    with pytest.raises(HTTPException) as exc:
        service._validate_line_conditions([line])
    assert exc.value.status_code == 409


def test_service_direct_validator_rejects_negative_quantity() -> None:
    line = dict(_VALID_LINE_DICT)
    line["quantity"] = -1.0
    with pytest.raises(HTTPException) as exc:
        service._validate_line_conditions([line])
    assert exc.value.status_code == 409


def test_finalize_persists_v2_line_fields_with_source_reference(analysis_db: Session) -> None:
    seeded = _seed(analysis_db)
    snapshot = _finalize(
        analysis_db,
        seeded,
        line_manifest=[_line(source_row_number=42, quantity=7.5)],
    )
    assert snapshot.line_manifest[0]["source_row_number"] == 42
    assert snapshot.line_manifest[0]["quantity"] == 7.5
