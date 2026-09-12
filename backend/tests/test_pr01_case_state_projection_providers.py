"""Focused unit tests for Global Case State raw providers (VALORA-PR01-IMPL-003)."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
import app.modules.excel_import.models  # noqa: F401
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
from app.modules.project_master_data.application.case_state_projection import (
    ProjectionIntegrityError,
    ProviderResult,
    evaluate_official_intake_provider,
    evaluate_preliminary_analysis_provider,
    evaluate_preliminary_ready_provider,
    evaluate_preliminary_request_provider,
)
from app.modules.project_master_data.application.official_intake_service import (
    get_official_intake_open_blockers,
    get_official_intake_open_warnings,
)
from app.modules.project_master_data.application.preliminary_result_service import (
    _build_lineage_manifest,
    snapshot_canonical_digest,
    validate_stored_v2_manifest,
)
from app.modules.project_master_data.models import (
    Customer,
    CustomerStatus,
    OrganizationProfile,
    OrganizationStatus,
    PreliminaryAnalysisSnapshot,
    PreliminaryResultArtifact,
    Project,
    ProjectAssetImportBatch,
    ProjectAssetLine,
    ProjectOfficialIntakeCommit,
    Role,
    User,
    UserRole,
    UserStatus,
    ValidationIssue,
    ValidationIssueSeverity,
    ValidationIssueStatus,
    ValidationRule,
    ValidationRuleCategory,
)


@pytest.fixture
def test_db() -> Session:
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


def _seed_basic(test_db: Session) -> dict[str, Any]:
    org = OrganizationProfile(
        legal_name="Provider Test Org",
        organization_slug=f"provider-test-{uuid.uuid4().hex[:8]}",
        status=OrganizationStatus.ACTIVE,
    )
    test_db.add(org)
    test_db.flush()

    actor = User(
        organization_id=org.id,
        email=f"provider-user-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Provider Human",
        status=UserStatus.ACTIVE,
    )
    test_db.add(actor)
    test_db.flush()

    role = Role(
        code=f"role-{uuid.uuid4().hex[:8]}",
        display_name="Provider Role",
        permissions=["project:read"],
    )
    test_db.add(role)
    test_db.flush()

    user_role = UserRole(user_id=actor.id, role_id=role.id, is_active=True)
    test_db.add(user_role)

    customer = Customer(
        organization_id=org.id,
        legal_name="Provider Customer",
        status=CustomerStatus.ACTIVE,
        created_by=actor.id,
    )
    test_db.add(customer)
    test_db.flush()

    project = Project(
        organization_id=org.id,
        customer_id=customer.id,
        code=f"PRJ-{uuid.uuid4().hex[:6]}",
        name="Provider Project",
        created_by=actor.id,
    )
    test_db.add(project)
    test_db.flush()

    return {
        "org": org,
        "actor": actor,
        "customer": customer,
        "project": project,
    }


def _valid_v2_line(row_num: int = 1) -> dict[str, Any]:
    return {
        "identity": f"Equip {row_num}",
        "accepted_price_basis": "Supplier Quote",
        "confirmed_reference_price": 1000.0,
        "transport_percentage": 5.0,
        "proposed_unit_price": 1050.0,
        "human_line_confirmed": True,
        "has_unresolved_blocking_line": False,
        "source_row_number": row_num,
        "quantity": 10.0,
    }


def test_preliminary_request_zero_batches(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    res = evaluate_preliminary_request_provider(
        test_db, org_id=seeded["org"].id, project_id=seeded["project"].id
    )
    assert res.result == "INCOMPLETE"
    assert res.fact_token == "preliminary_request_v1:null:absent-v1:absent"
    assert res.provider_key == "preliminary_request_v1"


def test_preliminary_request_batch_with_null_artifact(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    batch = ProjectAssetImportBatch(
        organization_id=seeded["org"].id,
        project_id=seeded["project"].id,
        source_filename="test.xlsx",
        source_sheet_name="Sheet1",
        created_by_user_id=seeded["actor"].id,
    )
    test_db.add(batch)
    test_db.flush()

    res = evaluate_preliminary_request_provider(
        test_db, org_id=seeded["org"].id, project_id=seeded["project"].id
    )
    assert res.result == "INCOMPLETE"
    assert res.fact_token == "preliminary_request_v1:null:absent-v1:absent"


def test_preliminary_request_single_batch_available(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    batch = ProjectAssetImportBatch(
        organization_id=seeded["org"].id,
        project_id=seeded["project"].id,
        source_filename="test.xlsx",
        source_sheet_name="Sheet1",
        created_by_user_id=seeded["actor"].id,
    )
    test_db.add(batch)
    test_db.flush()

    now = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)
    artifact = ImportSourceArtifact(
        organization_id=seeded["org"].id,
        project_id=seeded["project"].id,
        import_batch_id=batch.id,
        generation=1,
        original_filename="test.xlsx",
        detected_format="xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size_bytes=1024,
        checksum_sha256="a" * 64,
        storage_object_key="key-1",
        state=ImportSourceArtifactState.AVAILABLE.value,
        available_at=now,
        created_by_user_id=seeded["actor"].id,
    )
    test_db.add(artifact)
    test_db.flush()
    batch.current_source_artifact_id = artifact.id
    test_db.flush()

    res = evaluate_preliminary_request_provider(
        test_db, org_id=seeded["org"].id, project_id=seeded["project"].id
    )
    assert res.result == "COMPLETE"
    assert res.fact_token.startswith(f"preliminary_request_v1:{str(artifact.id).lower()}:av1-")
    assert res.fact_token.endswith(":complete")


def test_preliminary_request_single_batch_pending_or_failed(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    batch = ProjectAssetImportBatch(
        organization_id=seeded["org"].id,
        project_id=seeded["project"].id,
        source_filename="test.xlsx",
        source_sheet_name="Sheet1",
        created_by_user_id=seeded["actor"].id,
    )
    test_db.add(batch)
    test_db.flush()

    artifact = ImportSourceArtifact(
        organization_id=seeded["org"].id,
        project_id=seeded["project"].id,
        import_batch_id=batch.id,
        generation=1,
        original_filename="test.xlsx",
        detected_format="xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size_bytes=1024,
        checksum_sha256="b" * 64,
        storage_object_key="key-2",
        state=ImportSourceArtifactState.PENDING.value,
        created_by_user_id=seeded["actor"].id,
    )
    test_db.add(artifact)
    test_db.flush()
    batch.current_source_artifact_id = artifact.id
    test_db.flush()

    res = evaluate_preliminary_request_provider(
        test_db, org_id=seeded["org"].id, project_id=seeded["project"].id
    )
    assert res.result == "INCOMPLETE"
    assert res.fact_token.startswith(f"preliminary_request_v1:{str(artifact.id).lower()}:av1-")
    assert res.fact_token.endswith(":incomplete")


def test_preliminary_request_dangling_pointer_integrity_error(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    batch = ProjectAssetImportBatch(
        organization_id=seeded["org"].id,
        project_id=seeded["project"].id,
        source_filename="test.xlsx",
        source_sheet_name="Sheet1",
        created_by_user_id=seeded["actor"].id,
    )
    test_db.add(batch)
    test_db.flush()
    batch.current_source_artifact_id = uuid.uuid4()
    test_db.flush()

    with pytest.raises(ProjectionIntegrityError):
        evaluate_preliminary_request_provider(
            test_db, org_id=seeded["org"].id, project_id=seeded["project"].id
        )


def test_preliminary_request_multiple_batches_ambiguity(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    b1 = ProjectAssetImportBatch(
        organization_id=seeded["org"].id,
        project_id=seeded["project"].id,
        source_filename="test1.xlsx",
        source_sheet_name="Sheet1",
        created_by_user_id=seeded["actor"].id,
    )
    b2 = ProjectAssetImportBatch(
        organization_id=seeded["org"].id,
        project_id=seeded["project"].id,
        source_filename="test2.xlsx",
        source_sheet_name="Sheet1",
        created_by_user_id=seeded["actor"].id,
    )
    test_db.add_all([b1, b2])
    test_db.flush()

    res = evaluate_preliminary_request_provider(
        test_db, org_id=seeded["org"].id, project_id=seeded["project"].id
    )
    assert res.result == "NOT_AVAILABLE"
    assert res.fact_token.startswith("preliminary_request_v1:null:amb1-")
    assert res.fact_token.endswith(":not_available")


def test_preliminary_analysis_zero_snapshots(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    res = evaluate_preliminary_analysis_provider(
        test_db, org_id=seeded["org"].id, project_id=seeded["project"].id
    )
    assert res.result == "INCOMPLETE"
    assert res.fact_token == "preliminary_analysis_v1:null:absent-v1:absent"


def test_preliminary_analysis_single_snapshot_complete(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    batch = ProjectAssetImportBatch(
        organization_id=seeded["org"].id,
        project_id=seeded["project"].id,
        source_filename="test.xlsx",
        source_sheet_name="Sheet1",
        created_by_user_id=seeded["actor"].id,
    )
    test_db.add(batch)
    test_db.flush()

    artifact = ImportSourceArtifact(
        organization_id=seeded["org"].id,
        project_id=seeded["project"].id,
        import_batch_id=batch.id,
        generation=1,
        original_filename="test.xlsx",
        detected_format="xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size_bytes=1024,
        checksum_sha256="c" * 64,
        storage_object_key="key-3",
        state=ImportSourceArtifactState.AVAILABLE.value,
        created_by_user_id=seeded["actor"].id,
    )
    test_db.add(artifact)
    test_db.flush()
    batch.current_source_artifact_id = artifact.id
    test_db.flush()

    structure = WorkbookStructureSnapshot(
        organization_id=seeded["org"].id,
        project_id=seeded["project"].id,
        import_batch_id=batch.id,
        source_artifact_id=artifact.id,
        snapshot_version=1,
        source_checksum_sha256="c" * 64,
        rule_version="v1",
        adapter_name="test",
        adapter_version="1.0",
        disposition=WorkbookStructureDisposition.PROPOSED.value,
        candidate_count=1,
        structure_payload={"candidates": []},
        analysis_digest_sha256="d" * 64,
        created_by_user_id=seeded["actor"].id,
    )
    test_db.add(structure)
    test_db.flush()

    proposal = ColumnMappingDecision(
        organization_id=seeded["org"].id,
        customer_id=seeded["customer"].id,
        project_id=seeded["project"].id,
        import_batch_id=batch.id,
        source_artifact_id=artifact.id,
        structure_snapshot_id=structure.id,
        decision_kind=ColumnMappingDecisionKind.PROPOSAL.value,
        outcome=ColumnMappingDecisionOutcome.PROPOSED.value,
        memory_scope=ColumnMappingMemoryScope.NONE.value,
        actor_user_id=seeded["actor"].id,
        command_id=uuid.uuid4(),
        proposal_source_kind=ColumnMappingProposalSourceKind.HUMAN.value,
        proposal_source_version="1.0",
        mapping_contract_version="v1",
        template_fingerprint_sha256="f" * 64,
        mapping_snapshot={"candidate": {}, "fields": []},
        mapping_digest_sha256="e" * 64,
        before_summary={},
        after_summary={},
    )
    test_db.add(proposal)
    test_db.flush()

    decision = ColumnMappingDecision(
        organization_id=seeded["org"].id,
        customer_id=seeded["customer"].id,
        project_id=seeded["project"].id,
        import_batch_id=batch.id,
        source_artifact_id=artifact.id,
        structure_snapshot_id=structure.id,
        decision_kind=ColumnMappingDecisionKind.CONFIRMATION.value,
        outcome=ColumnMappingDecisionOutcome.ACCEPTED.value,
        memory_scope=ColumnMappingMemoryScope.NONE.value,
        proposal_decision_id=proposal.id,
        actor_user_id=seeded["actor"].id,
        command_id=uuid.uuid4(),
        proposal_source_kind=ColumnMappingProposalSourceKind.HUMAN.value,
        proposal_source_version="1.0",
        mapping_contract_version="v1",
        template_fingerprint_sha256="f" * 64,
        mapping_snapshot={"candidate": {}, "fields": []},
        mapping_digest_sha256="e" * 64,
        before_summary={},
        after_summary={},
    )
    test_db.add(decision)
    test_db.flush()

    usage = ColumnMappingProfileUsage(
        organization_id=seeded["org"].id,
        customer_id=seeded["customer"].id,
        project_id=seeded["project"].id,
        import_batch_id=batch.id,
        source_artifact_id=artifact.id,
        structure_snapshot_id=structure.id,
        confirmation_decision_id=decision.id,
        command_id=uuid.uuid4(),
        materialization_contract_version="v1",
        mapping_contract_version="v1",
        template_fingerprint_sha256="f" * 64,
        mapping_snapshot={"candidate": {}, "fields": []},
        mapping_digest_sha256="e" * 64,
        source_checksum_sha256="c" * 64,
        structure_digest_sha256="d" * 64,
        materialized_asset_row_count=1,
        created_by_user_id=seeded["actor"].id,
    )
    test_db.add(usage)
    test_db.flush()

    line_manifest = [_valid_v2_line(1)]
    line_manifest_digest = hashlib.sha256(
        json.dumps(line_manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest().lower()

    snapshot = PreliminaryAnalysisSnapshot(
        organization_id=seeded["org"].id,
        customer_id=seeded["customer"].id,
        project_id=seeded["project"].id,
        version=1,
        import_batch_id=batch.id,
        source_artifact_id=artifact.id,
        structure_snapshot_id=structure.id,
        mapping_decision_id=decision.id,
        mapping_profile_usage_id=usage.id,
        source_artifact_generation=1,
        mapping_decision_digest_sha256="e" * 64,
        profile_usage_mapping_digest_sha256="e" * 64,
        line_manifest=line_manifest,
        line_manifest_digest_sha256=line_manifest_digest,
        finalized_by_user_id=seeded["actor"].id,
        finalized_at=datetime(2026, 9, 4, 13, 0, 0, tzinfo=timezone.utc),
        idempotency_key="key-snap-1",
        request_digest_sha256="2" * 64,
    )
    test_db.add(snapshot)
    test_db.flush()

    res = evaluate_preliminary_analysis_provider(
        test_db, org_id=seeded["org"].id, project_id=seeded["project"].id
    )
    assert res.result == "COMPLETE"
    assert res.fact_token.startswith(f"preliminary_analysis_v1:{str(snapshot.id).lower()}:av1-")
    assert res.fact_token.endswith(":complete")


def test_preliminary_analysis_v1_manifest_incomplete(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    # Stored snapshot with v1-shaped line manifest (missing required v2 keys)
    v1_line = {"identity": "Old", "proposed_unit_price": 100.0}
    snapshot = PreliminaryAnalysisSnapshot(
        organization_id=seeded["org"].id,
        customer_id=seeded["customer"].id,
        project_id=seeded["project"].id,
        version=1,
        import_batch_id=uuid.uuid4(),
        source_artifact_id=uuid.uuid4(),
        structure_snapshot_id=uuid.uuid4(),
        mapping_decision_id=uuid.uuid4(),
        mapping_profile_usage_id=uuid.uuid4(),
        source_artifact_generation=1,
        mapping_decision_digest_sha256="e" * 64,
        profile_usage_mapping_digest_sha256="e" * 64,
        line_manifest=[v1_line],
        line_manifest_digest_sha256="1" * 64,
        finalized_by_user_id=seeded["actor"].id,
        finalized_at=datetime(2026, 9, 4, 13, 0, 0, tzinfo=timezone.utc),
        idempotency_key="key-snap-v1",
        request_digest_sha256="2" * 64,
    )
    test_db.add(snapshot)
    test_db.flush()

    res = evaluate_preliminary_analysis_provider(
        test_db, org_id=seeded["org"].id, project_id=seeded["project"].id
    )
    assert res.result == "INCOMPLETE"
    # Still contributes av1 token
    assert res.fact_token.startswith(f"preliminary_analysis_v1:{str(snapshot.id).lower()}:av1-")
    assert res.fact_token.endswith(":incomplete")


def test_preliminary_analysis_multiple_snapshots_ambiguity(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    s1 = PreliminaryAnalysisSnapshot(
        organization_id=seeded["org"].id,
        customer_id=seeded["customer"].id,
        project_id=seeded["project"].id,
        version=1,
        import_batch_id=uuid.uuid4(),
        source_artifact_id=uuid.uuid4(),
        structure_snapshot_id=uuid.uuid4(),
        mapping_decision_id=uuid.uuid4(),
        mapping_profile_usage_id=uuid.uuid4(),
        source_artifact_generation=1,
        mapping_decision_digest_sha256="e" * 64,
        profile_usage_mapping_digest_sha256="e" * 64,
        line_manifest=[_valid_v2_line(1)],
        line_manifest_digest_sha256="1" * 64,
        finalized_by_user_id=seeded["actor"].id,
        finalized_at=datetime(2026, 9, 4, 13, 0, 0, tzinfo=timezone.utc),
        idempotency_key="key-s1",
        request_digest_sha256="2" * 64,
    )
    s2 = PreliminaryAnalysisSnapshot(
        organization_id=seeded["org"].id,
        customer_id=seeded["customer"].id,
        project_id=seeded["project"].id,
        version=2,
        import_batch_id=uuid.uuid4(),
        source_artifact_id=uuid.uuid4(),
        structure_snapshot_id=uuid.uuid4(),
        mapping_decision_id=uuid.uuid4(),
        mapping_profile_usage_id=uuid.uuid4(),
        source_artifact_generation=1,
        mapping_decision_digest_sha256="e" * 64,
        profile_usage_mapping_digest_sha256="e" * 64,
        line_manifest=[_valid_v2_line(1)],
        line_manifest_digest_sha256="1" * 64,
        finalized_by_user_id=seeded["actor"].id,
        finalized_at=datetime(2026, 9, 4, 14, 0, 0, tzinfo=timezone.utc),
        idempotency_key="key-s2",
        request_digest_sha256="3" * 64,
    )
    test_db.add_all([s1, s2])
    test_db.flush()

    res = evaluate_preliminary_analysis_provider(
        test_db, org_id=seeded["org"].id, project_id=seeded["project"].id
    )
    assert res.result == "NOT_AVAILABLE"
    assert res.fact_token.startswith("preliminary_analysis_v1:null:amb1-")
    assert res.fact_token.endswith(":not_available")


def test_preliminary_ready_zero_artifacts(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    res = evaluate_preliminary_ready_provider(
        test_db, org_id=seeded["org"].id, project_id=seeded["project"].id
    )
    assert res.result == "INCOMPLETE"
    assert res.fact_token == "preliminary_ready_v1:null:absent-v1:absent"


def _seed_complete_preliminary_ready(test_db: Session, seeded: dict) -> dict[str, Any]:
    org_id = seeded["org"].id
    project_id = seeded["project"].id
    customer_id = seeded["customer"].id
    actor_id = seeded["actor"].id

    batch = ProjectAssetImportBatch(
        organization_id=org_id,
        project_id=project_id,
        source_filename="source.xlsx",
        source_sheet_name="Sheet1",
        created_by_user_id=actor_id,
    )
    test_db.add(batch)
    test_db.flush()

    source_artifact = ImportSourceArtifact(
        organization_id=org_id,
        project_id=project_id,
        import_batch_id=batch.id,
        generation=1,
        original_filename="source.xlsx",
        detected_format="xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size_bytes=1024,
        checksum_sha256="c" * 64,
        storage_object_key="key-src-1",
        state=ImportSourceArtifactState.AVAILABLE.value,
        created_by_user_id=actor_id,
    )
    test_db.add(source_artifact)
    test_db.flush()

    batch.current_source_artifact_id = source_artifact.id
    test_db.flush()

    structure = WorkbookStructureSnapshot(
        organization_id=org_id,
        project_id=project_id,
        import_batch_id=batch.id,
        source_artifact_id=source_artifact.id,
        snapshot_version=1,
        source_checksum_sha256="c" * 64,
        rule_version="rv1",
        adapter_name="openpyxl",
        adapter_version="1.0",
        disposition=WorkbookStructureDisposition.PROPOSED.value,
        candidate_count=1,
        structure_payload={},
        analysis_digest_sha256="d" * 64,
        created_by_user_id=actor_id,
    )
    test_db.add(structure)
    test_db.flush()

    candidate = {
        "sheet_name": "Sheet1",
        "header_start_row": 1,
        "header_end_row": 1,
        "data_start_row": 2,
        "min_row": 1,
        "max_row": 10,
        "min_column": 1,
        "max_column": 5,
    }
    quantity_field = {
        "semantic_role": "quantity",
        "source_column_index": 2,
        "source_column_letter": "B",
    }
    mapping_snapshot = {
        "candidate": candidate,
        "fields": [quantity_field],
        "template_fingerprint_sha256": "f" * 64,
    }

    proposal = ColumnMappingDecision(
        organization_id=org_id,
        customer_id=customer_id,
        project_id=project_id,
        import_batch_id=batch.id,
        source_artifact_id=source_artifact.id,
        structure_snapshot_id=structure.id,
        decision_kind=ColumnMappingDecisionKind.PROPOSAL.value,
        outcome=ColumnMappingDecisionOutcome.PROPOSED.value,
        memory_scope=ColumnMappingMemoryScope.NONE.value,
        actor_user_id=actor_id,
        command_id=uuid.uuid4(),
        proposal_source_kind=ColumnMappingProposalSourceKind.HUMAN.value,
        proposal_source_version="1.0",
        mapping_contract_version="v2",
        template_fingerprint_sha256="f" * 64,
        mapping_snapshot=mapping_snapshot,
        mapping_digest_sha256="e" * 64,
        before_summary={},
        after_summary={},
    )
    test_db.add(proposal)
    test_db.flush()

    decision = ColumnMappingDecision(
        organization_id=org_id,
        customer_id=customer_id,
        project_id=project_id,
        import_batch_id=batch.id,
        source_artifact_id=source_artifact.id,
        structure_snapshot_id=structure.id,
        decision_kind=ColumnMappingDecisionKind.CONFIRMATION.value,
        outcome=ColumnMappingDecisionOutcome.ACCEPTED.value,
        memory_scope=ColumnMappingMemoryScope.NONE.value,
        proposal_decision_id=proposal.id,
        actor_user_id=actor_id,
        command_id=uuid.uuid4(),
        proposal_source_kind=ColumnMappingProposalSourceKind.HUMAN.value,
        proposal_source_version="1.0",
        mapping_contract_version="v2",
        template_fingerprint_sha256="f" * 64,
        mapping_snapshot=mapping_snapshot,
        mapping_digest_sha256="e" * 64,
        before_summary={},
        after_summary={},
    )
    test_db.add(decision)
    test_db.flush()

    usage = ColumnMappingProfileUsage(
        organization_id=org_id,
        customer_id=customer_id,
        project_id=project_id,
        import_batch_id=batch.id,
        source_artifact_id=source_artifact.id,
        structure_snapshot_id=structure.id,
        confirmation_decision_id=decision.id,
        command_id=uuid.uuid4(),
        materialization_contract_version="v1",
        mapping_contract_version="v2",
        template_fingerprint_sha256="f" * 64,
        mapping_snapshot=mapping_snapshot,
        mapping_digest_sha256="e" * 64,
        source_checksum_sha256="c" * 64,
        structure_digest_sha256="d" * 64,
        materialized_asset_row_count=1,
        created_by_user_id=actor_id,
    )
    test_db.add(usage)
    test_db.flush()

    line_manifest = [_valid_v2_line(1)]
    line_manifest_digest = hashlib.sha256(
        json.dumps(line_manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest().lower()

    snapshot = PreliminaryAnalysisSnapshot(
        organization_id=org_id,
        customer_id=customer_id,
        project_id=project_id,
        version=1,
        import_batch_id=batch.id,
        source_artifact_id=source_artifact.id,
        structure_snapshot_id=structure.id,
        mapping_decision_id=decision.id,
        mapping_profile_usage_id=usage.id,
        source_artifact_generation=1,
        mapping_decision_digest_sha256="e" * 64,
        profile_usage_mapping_digest_sha256="e" * 64,
        line_manifest=line_manifest,
        line_manifest_digest_sha256=line_manifest_digest,
        finalized_by_user_id=actor_id,
        finalized_at=datetime(2026, 9, 4, 13, 0, 0, tzinfo=timezone.utc),
        idempotency_key="key-snap-ready-1",
        request_digest_sha256="2" * 64,
    )
    test_db.add(snapshot)
    test_db.flush()

    expected_digest = snapshot_canonical_digest(snapshot)

    full_lineage = _build_lineage_manifest(
        org_id=org_id,
        project_id=project_id,
        customer_id=customer_id,
        snapshot=snapshot,
        artifact=source_artifact,
        structure=structure,
        decision=decision,
        usage=usage,
        candidate=candidate,
        quantity_field=quantity_field,
        price_col=6,
        amount_col=7,
        snapshot_digest=expected_digest,
        line_manifest=line_manifest,
    )

    artifact = PreliminaryResultArtifact(
        organization_id=org_id,
        customer_id=customer_id,
        project_id=project_id,
        version=1,
        original_filename="result.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size_bytes=2048,
        content_checksum_sha256="9" * 64,
        storage_object_key="key-res-1",
        source_snapshot_sha256=expected_digest,
        lineage_manifest=full_lineage,
        created_by_user_id=actor_id,
    )
    test_db.add(artifact)
    test_db.flush()

    return {
        "batch": batch,
        "source_artifact": source_artifact,
        "structure": structure,
        "decision": decision,
        "usage": usage,
        "snapshot": snapshot,
        "artifact": artifact,
        "expected_digest": expected_digest,
        "full_lineage": full_lineage,
    }


def test_preliminary_ready_single_artifact_complete(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    ready = _seed_complete_preliminary_ready(test_db, seeded)
    artifact = ready["artifact"]
    snapshot = ready["snapshot"]

    analysis_res = ProviderResult(
        stage="PRELIMINARY_ANALYSIS",
        result="COMPLETE",
        fact_token="preliminary_analysis_v1:test:complete",
        provider_key="preliminary_analysis_v1",
        authoritative_entity=snapshot,
    )

    res = evaluate_preliminary_ready_provider(
        test_db,
        org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        analysis_provider_result=analysis_res,
    )
    assert res.result == "COMPLETE"
    assert res.fact_token.startswith(f"preliminary_ready_v1:{str(artifact.id).lower()}:av1-")
    assert res.fact_token.endswith(":complete")


def test_preliminary_ready_missing_lineage_group(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    ready = _seed_complete_preliminary_ready(test_db, seeded)
    artifact = ready["artifact"]
    full_lineage = ready["full_lineage"]
    snapshot = ready["snapshot"]
    analysis_res = ProviderResult(
        stage="PRELIMINARY_ANALYSIS",
        result="COMPLETE",
        fact_token="preliminary_analysis_v1:test:complete",
        provider_key="preliminary_analysis_v1",
        authoritative_entity=snapshot,
    )
    for group_key in [
        "source_workbook",
        "structure_snapshot",
        "mapping",
        "analysis_snapshot",
        "mapped_region",
        "quantity_column",
        "output_layout",
    ]:
        mutated_lineage = dict(full_lineage)
        del mutated_lineage[group_key]
        artifact.lineage_manifest = mutated_lineage
        test_db.flush()

        res = evaluate_preliminary_ready_provider(
            test_db,
            org_id=seeded["org"].id,
            project_id=seeded["project"].id,
            analysis_provider_result=analysis_res,
        )
        assert res.result == "INCOMPLETE"
        assert res.fact_token.endswith(":incomplete")


def test_preliminary_ready_mutated_source_checksum_or_format(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    ready = _seed_complete_preliminary_ready(test_db, seeded)
    artifact = ready["artifact"]
    full_lineage = ready["full_lineage"]
    snapshot = ready["snapshot"]
    analysis_res = ProviderResult(
        stage="PRELIMINARY_ANALYSIS",
        result="COMPLETE",
        fact_token="preliminary_analysis_v1:test:complete",
        provider_key="preliminary_analysis_v1",
        authoritative_entity=snapshot,
    )
    # Mutate checksum
    mutated = json.loads(json.dumps(full_lineage))
    mutated["source_workbook"]["checksum_sha256"] = "x" * 64
    artifact.lineage_manifest = mutated
    test_db.flush()
    res = evaluate_preliminary_ready_provider(
        test_db,
        org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        analysis_provider_result=analysis_res,
    )
    assert res.result == "INCOMPLETE"
    assert res.fact_token.endswith(":incomplete")

    # Mutate detected format
    mutated = json.loads(json.dumps(full_lineage))
    mutated["source_workbook"]["detected_format"] = "xls"
    artifact.lineage_manifest = mutated
    test_db.flush()
    res = evaluate_preliminary_ready_provider(
        test_db,
        org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        analysis_provider_result=analysis_res,
    )
    assert res.result == "INCOMPLETE"
    assert res.fact_token.endswith(":incomplete")


def test_preliminary_ready_mutated_structure_version_rule_digest(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    ready = _seed_complete_preliminary_ready(test_db, seeded)
    artifact = ready["artifact"]
    full_lineage = ready["full_lineage"]
    snapshot = ready["snapshot"]
    analysis_res = ProviderResult(
        stage="PRELIMINARY_ANALYSIS",
        result="COMPLETE",
        fact_token="preliminary_analysis_v1:test:complete",
        provider_key="preliminary_analysis_v1",
        authoritative_entity=snapshot,
    )
    for field, val in [("snapshot_version", 99), ("rule_version", "rv99"), ("analysis_digest_sha256", "x" * 64)]:
        mutated = json.loads(json.dumps(full_lineage))
        mutated["structure_snapshot"][field] = val
        artifact.lineage_manifest = mutated
        test_db.flush()
        res = evaluate_preliminary_ready_provider(
            test_db,
            org_id=seeded["org"].id,
            project_id=seeded["project"].id,
            analysis_provider_result=analysis_res,
        )
        assert res.result == "INCOMPLETE"
        assert res.fact_token.endswith(":incomplete")


def test_preliminary_ready_mutated_mapping_fingerprint_contract_digests(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    ready = _seed_complete_preliminary_ready(test_db, seeded)
    artifact = ready["artifact"]
    full_lineage = ready["full_lineage"]
    snapshot = ready["snapshot"]
    analysis_res = ProviderResult(
        stage="PRELIMINARY_ANALYSIS",
        result="COMPLETE",
        fact_token="preliminary_analysis_v1:test:complete",
        provider_key="preliminary_analysis_v1",
        authoritative_entity=snapshot,
    )
    for field, val in [
        ("template_fingerprint_sha256", "x" * 64),
        ("mapping_contract_version", "v99"),
        ("decision_digest_sha256", "x" * 64),
        ("usage_mapping_digest_sha256", "x" * 64),
    ]:
        mutated = json.loads(json.dumps(full_lineage))
        mutated["mapping"][field] = val
        artifact.lineage_manifest = mutated
        test_db.flush()
        res = evaluate_preliminary_ready_provider(
            test_db,
            org_id=seeded["org"].id,
            project_id=seeded["project"].id,
            analysis_provider_result=analysis_res,
        )
        assert res.result == "INCOMPLETE"
        assert res.fact_token.endswith(":incomplete")


def test_preliminary_ready_mutated_analysis_version_line_manifest_finalizer_finalized_at(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    ready = _seed_complete_preliminary_ready(test_db, seeded)
    artifact = ready["artifact"]
    full_lineage = ready["full_lineage"]
    snapshot = ready["snapshot"]
    analysis_res = ProviderResult(
        stage="PRELIMINARY_ANALYSIS",
        result="COMPLETE",
        fact_token="preliminary_analysis_v1:test:complete",
        provider_key="preliminary_analysis_v1",
        authoritative_entity=snapshot,
    )
    for field, val in [
        ("version", 99),
        ("line_manifest_digest_sha256", "x" * 64),
        ("finalized_by_user_id", str(uuid.uuid4())),
        ("finalized_at", "2099-01-01T00:00:00+00:00"),
    ]:
        mutated = json.loads(json.dumps(full_lineage))
        mutated["analysis_snapshot"][field] = val
        artifact.lineage_manifest = mutated
        test_db.flush()
        res = evaluate_preliminary_ready_provider(
            test_db,
            org_id=seeded["org"].id,
            project_id=seeded["project"].id,
            analysis_provider_result=analysis_res,
        )
        assert res.result == "INCOMPLETE"
        assert res.fact_token.endswith(":incomplete")


def test_preliminary_ready_mutated_remaining_manifest_sections(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    ready = _seed_complete_preliminary_ready(test_db, seeded)
    artifact = ready["artifact"]
    full_lineage = ready["full_lineage"]
    snapshot = ready["snapshot"]
    analysis_res = ProviderResult(
        stage="PRELIMINARY_ANALYSIS",
        result="COMPLETE",
        fact_token="preliminary_analysis_v1:test:complete",
        provider_key="preliminary_analysis_v1",
        authoritative_entity=snapshot,
    )
    mutations = [
        ("mapped_region", "max_column", 99),
        ("quantity_column", "source_column_index", 99),
        ("output_layout", "price_column_index", 99),
    ]
    for section, field, val in mutations:
        mutated = json.loads(json.dumps(full_lineage))
        mutated[section][field] = val
        artifact.lineage_manifest = mutated
        test_db.flush()
        res = evaluate_preliminary_ready_provider(
            test_db,
            org_id=seeded["org"].id,
            project_id=seeded["project"].id,
            analysis_provider_result=analysis_res,
        )
        assert res.result == "INCOMPLETE"
        assert res.fact_token.endswith(":incomplete")

    # line_locator_count mutation
    mutated = json.loads(json.dumps(full_lineage))
    mutated["line_locator_count"] = 99
    artifact.lineage_manifest = mutated
    test_db.flush()
    res = evaluate_preliminary_ready_provider(
        test_db,
        org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        analysis_provider_result=analysis_res,
    )
    assert res.result == "INCOMPLETE"
    assert res.fact_token.endswith(":incomplete")

    # generation_contract mutation
    mutated = json.loads(json.dumps(full_lineage))
    mutated["generation_contract"] = "invalid-contract"
    artifact.lineage_manifest = mutated
    test_db.flush()
    res = evaluate_preliminary_ready_provider(
        test_db,
        org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        analysis_provider_result=analysis_res,
    )
    assert res.result == "INCOMPLETE"
    assert res.fact_token.endswith(":incomplete")

    # customer_id mutation
    mutated = json.loads(json.dumps(full_lineage))
    mutated["customer_id"] = str(uuid.uuid4())
    artifact.lineage_manifest = mutated
    test_db.flush()
    res = evaluate_preliminary_ready_provider(
        test_db,
        org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        analysis_provider_result=analysis_res,
    )
    assert res.result == "INCOMPLETE"
    assert res.fact_token.endswith(":incomplete")


def test_preliminary_ready_lineage_manifest_type_sensitive_rejections(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    ready = _seed_complete_preliminary_ready(test_db, seeded)
    artifact = ready["artifact"]
    full_lineage = ready["full_lineage"]
    snapshot = ready["snapshot"]
    analysis_res = ProviderResult(
        stage="PRELIMINARY_ANALYSIS",
        result="COMPLETE",
        fact_token="preliminary_analysis_v1:test:complete",
        provider_key="preliminary_analysis_v1",
        authoritative_entity=snapshot,
    )

    # 1. Integer-versus-boolean mutations (including coordinator reproduction cases)
    int_to_bool_cases = [
        ("source_workbook", "generation", True),
        ("structure_snapshot", "snapshot_version", True),
        ("analysis_snapshot", "version", True),
        ("mapped_region", "header_start_row", True),
        ("mapped_region", "max_column", True),
        ("quantity_column", "source_column_index", True),
        ("output_layout", "price_column_index", True),
        ("output_layout", "amount_column_index", True),
    ]
    for section, field, mutated_val in int_to_bool_cases:
        mutated = json.loads(json.dumps(full_lineage))
        mutated[section][field] = mutated_val
        artifact.lineage_manifest = mutated
        test_db.flush()
        res = evaluate_preliminary_ready_provider(
            test_db,
            org_id=seeded["org"].id,
            project_id=seeded["project"].id,
            analysis_provider_result=analysis_res,
        )
        assert res.result == "INCOMPLETE"
        assert res.fact_token.endswith(":incomplete")

    # line_locator_count (top-level) int -> bool (coordinator reproduction)
    mutated = json.loads(json.dumps(full_lineage))
    mutated["line_locator_count"] = True
    artifact.lineage_manifest = mutated
    test_db.flush()
    res = evaluate_preliminary_ready_provider(
        test_db,
        org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        analysis_provider_result=analysis_res,
    )
    assert res.result == "INCOMPLETE"
    assert res.fact_token.endswith(":incomplete")

    # 2. Boolean-versus-integer mutation (output_layout.header_merge True -> 1; coordinator reproduction)
    mutated = json.loads(json.dumps(full_lineage))
    mutated["output_layout"]["header_merge"] = 1
    artifact.lineage_manifest = mutated
    test_db.flush()
    res = evaluate_preliminary_ready_provider(
        test_db,
        org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        analysis_provider_result=analysis_res,
    )
    assert res.result == "INCOMPLETE"
    assert res.fact_token.endswith(":incomplete")

    # 3. Numeric-versus-string mutations
    num_to_str_cases = [
        ("source_workbook", "generation", "1"),
        ("structure_snapshot", "snapshot_version", "1"),
        ("analysis_snapshot", "version", "1"),
        ("mapped_region", "max_column", "5"),
        ("quantity_column", "source_column_index", "2"),
        ("output_layout", "price_column_index", "6"),
    ]
    for section, field, mutated_val in num_to_str_cases:
        mutated = json.loads(json.dumps(full_lineage))
        mutated[section][field] = mutated_val
        artifact.lineage_manifest = mutated
        test_db.flush()
        res = evaluate_preliminary_ready_provider(
            test_db,
            org_id=seeded["org"].id,
            project_id=seeded["project"].id,
            analysis_provider_result=analysis_res,
        )
        assert res.result == "INCOMPLETE"
        assert res.fact_token.endswith(":incomplete")

    # line_locator_count (top-level) num -> str
    mutated = json.loads(json.dumps(full_lineage))
    mutated["line_locator_count"] = "1"
    artifact.lineage_manifest = mutated
    test_db.flush()
    res = evaluate_preliminary_ready_provider(
        test_db,
        org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        analysis_provider_result=analysis_res,
    )
    assert res.result == "INCOMPLETE"
    assert res.fact_token.endswith(":incomplete")

    # 4. Integer-versus-float mutations
    int_to_float_cases = [
        ("source_workbook", "generation", 1.0),
        ("structure_snapshot", "snapshot_version", 1.0),
        ("analysis_snapshot", "version", 1.0),
        ("mapped_region", "max_column", 5.0),
        ("quantity_column", "source_column_index", 2.0),
        ("output_layout", "price_column_index", 6.0),
    ]
    for section, field, mutated_val in int_to_float_cases:
        mutated = json.loads(json.dumps(full_lineage))
        mutated[section][field] = mutated_val
        artifact.lineage_manifest = mutated
        test_db.flush()
        res = evaluate_preliminary_ready_provider(
            test_db,
            org_id=seeded["org"].id,
            project_id=seeded["project"].id,
            analysis_provider_result=analysis_res,
        )
        assert res.result == "INCOMPLETE"
        assert res.fact_token.endswith(":incomplete")

    # line_locator_count (top-level) int -> float
    mutated = json.loads(json.dumps(full_lineage))
    mutated["line_locator_count"] = 1.0
    artifact.lineage_manifest = mutated
    test_db.flush()
    res = evaluate_preliminary_ready_provider(
        test_db,
        org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        analysis_provider_result=analysis_res,
    )
    assert res.result == "INCOMPLETE"
    assert res.fact_token.endswith(":incomplete")


def test_preliminary_ready_single_artifact_incomplete_contributes_identity_and_av1(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    artifact = PreliminaryResultArtifact(
        organization_id=seeded["org"].id,
        customer_id=seeded["customer"].id,
        project_id=seeded["project"].id,
        version=1,
        original_filename="result.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size_bytes=2048,
        content_checksum_sha256="9" * 64,
        storage_object_key="key-res-incomplete",
        source_snapshot_sha256="c" * 64,
        lineage_manifest={},
        created_by_user_id=seeded["actor"].id,
    )
    test_db.add(artifact)
    test_db.flush()

    res = evaluate_preliminary_ready_provider(
        test_db,
        org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        analysis_provider_result=None,
    )
    assert res.result == "INCOMPLETE"
    assert res.authoritative_entity == artifact
    assert res.fact_token.startswith(f"preliminary_ready_v1:{str(artifact.id).lower()}:av1-")
    assert res.fact_token.endswith(":incomplete")


def test_preliminary_ready_multiple_artifacts_ambiguity(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    a1 = PreliminaryResultArtifact(
        organization_id=seeded["org"].id,
        customer_id=seeded["customer"].id,
        project_id=seeded["project"].id,
        version=1,
        original_filename="res1.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size_bytes=2048,
        content_checksum_sha256="9" * 64,
        storage_object_key="key-res-1",
        source_snapshot_sha256="c" * 64,
        lineage_manifest={},
        created_by_user_id=seeded["actor"].id,
    )
    a2 = PreliminaryResultArtifact(
        organization_id=seeded["org"].id,
        customer_id=seeded["customer"].id,
        project_id=seeded["project"].id,
        version=2,
        original_filename="res2.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size_bytes=2048,
        content_checksum_sha256="8" * 64,
        storage_object_key="key-res-2",
        source_snapshot_sha256="c" * 64,
        lineage_manifest={},
        created_by_user_id=seeded["actor"].id,
    )
    test_db.add_all([a1, a2])
    test_db.flush()

    res = evaluate_preliminary_ready_provider(
        test_db, org_id=seeded["org"].id, project_id=seeded["project"].id
    )
    assert res.result == "NOT_AVAILABLE"
    assert res.fact_token.startswith("preliminary_ready_v1:null:amb1-")
    assert res.fact_token.endswith(":not_available")


def test_official_intake_zero_commits(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    res = evaluate_official_intake_provider(
        test_db, org_id=seeded["org"].id, project_id=seeded["project"].id
    )
    assert res.result == "INCOMPLETE"
    assert res.fact_token == "official_intake_commit_v1:null:absent-v1:absent"


def test_official_intake_single_commit(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    commit = ProjectOfficialIntakeCommit(
        organization_id=seeded["org"].id,
        customer_id=seeded["customer"].id,
        project_id=seeded["project"].id,
        preliminary_result_artifact_id=uuid.uuid4(),
        preliminary_result_version=1,
        preliminary_result_sha256="4" * 64,
        source_snapshot_sha256="5" * 64,
        project_version_before=1,
        idempotency_key="idemp-1",
        request_digest_sha256="6" * 64,
        committed_by_user_id=seeded["actor"].id,
        committed_at=datetime(2026, 9, 4, 15, 30, 0, tzinfo=timezone.utc),
    )
    test_db.add(commit)
    test_db.flush()

    res = evaluate_official_intake_provider(
        test_db, org_id=seeded["org"].id, project_id=seeded["project"].id
    )
    assert res.result == "COMPLETE"
    assert res.fact_token.startswith(f"official_intake_commit_v1:{str(commit.id).lower()}:av1-")
    assert res.fact_token.endswith(":complete")


def test_official_intake_multiple_commits_integrity_error(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    c1 = MagicMock(spec=ProjectOfficialIntakeCommit)
    c2 = MagicMock(spec=ProjectOfficialIntakeCommit)
    with patch.object(test_db, "query") as mock_query:
        mock_query.return_value.filter.return_value.all.return_value = [c1, c2]
        with pytest.raises(ProjectionIntegrityError):
            evaluate_official_intake_provider(
                test_db, org_id=seeded["org"].id, project_id=seeded["project"].id
            )


def test_blocker_and_warning_helpers_filtering_and_ordering(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    org_id = seeded["org"].id
    project_id = seeded["project"].id

    line = ProjectAssetLine(
        project_id=project_id,
        asset_name="Line 1",
        quantity=1.0,
    )
    test_db.add(line)
    test_db.flush()

    rule_blocking = ValidationRule(
        rule_code=f"RULE-B-{uuid.uuid4().hex[:6]}",
        category=ValidationRuleCategory.EVIDENCE,
        name="Blocking Rule",
        is_blocking=True,
        is_active=True,
    )
    rule_warning = ValidationRule(
        rule_code=f"RULE-W-{uuid.uuid4().hex[:6]}",
        category=ValidationRuleCategory.EVIDENCE,
        name="Warning Rule",
        is_blocking=False,
        is_active=True,
    )
    test_db.add_all([rule_blocking, rule_warning])
    test_db.flush()

    # Blockers (project and line targets)
    b2 = ValidationIssue(
        id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        validation_rule_id=rule_blocking.id,
        severity=ValidationIssueSeverity.BLOCKING,
        status=ValidationIssueStatus.OPEN,
        target_type="project_asset_line",
        target_id=line.id,
        issue_message="Blocker line issue",
    )
    b1 = ValidationIssue(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        validation_rule_id=rule_blocking.id,
        severity=ValidationIssueSeverity.BLOCKING,
        status=ValidationIssueStatus.OPEN,
        target_type="project",
        target_id=project_id,
        issue_message="Blocker project issue",
    )
    # Resolved blocker should be excluded
    b_resolved = ValidationIssue(
        id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
        validation_rule_id=rule_blocking.id,
        severity=ValidationIssueSeverity.BLOCKING,
        status=ValidationIssueStatus.RESOLVED,
        target_type="project",
        target_id=project_id,
        issue_message="Resolved issue",
    )
    # Warnings
    w1 = ValidationIssue(
        id=uuid.UUID("00000000-0000-0000-0000-000000000010"),
        validation_rule_id=rule_warning.id,
        severity=ValidationIssueSeverity.WARNING,
        status=ValidationIssueStatus.OPEN,
        target_type="Project",
        target_id=project_id,
        issue_message="Warning issue",
    )
    # Foreign project issue should be excluded
    foreign_b = ValidationIssue(
        id=uuid.UUID("00000000-0000-0000-0000-000000000099"),
        validation_rule_id=rule_blocking.id,
        severity=ValidationIssueSeverity.BLOCKING,
        status=ValidationIssueStatus.OPEN,
        target_type="project",
        target_id=uuid.uuid4(),
        issue_message="Foreign issue",
    )

    test_db.add_all([b2, b1, b_resolved, w1, foreign_b])
    test_db.flush()

    blockers = get_official_intake_open_blockers(test_db, org_id=org_id, project_id=project_id)
    assert len(blockers) == 2
    assert blockers[0].id == uuid.UUID("00000000-0000-0000-0000-000000000001")
    assert blockers[1].id == uuid.UUID("00000000-0000-0000-0000-000000000002")

    warnings = get_official_intake_open_warnings(test_db, org_id=org_id, project_id=project_id)
    assert len(warnings) == 1
    assert warnings[0].id == uuid.UUID("00000000-0000-0000-0000-000000000010")


def test_blocker_and_warning_helpers_cross_tenant_target_exclusion(test_db: Session) -> None:
    seeded = _seed_basic(test_db)
    project_id = seeded["project"].id

    foreign_org = OrganizationProfile(
        legal_name="Foreign Org",
        organization_slug=f"foreign-org-{uuid.uuid4().hex[:8]}",
        status=OrganizationStatus.ACTIVE,
    )
    test_db.add(foreign_org)
    test_db.flush()

    line = ProjectAssetLine(
        project_id=project_id,
        asset_name="Line 1",
        quantity=1.0,
    )
    test_db.add(line)
    test_db.flush()

    rule_b = ValidationRule(
        rule_code=f"RULE-CB-{uuid.uuid4().hex[:6]}",
        category=ValidationRuleCategory.EVIDENCE,
        name="Rule B",
        is_blocking=True,
        is_active=True,
    )
    rule_w = ValidationRule(
        rule_code=f"RULE-CW-{uuid.uuid4().hex[:6]}",
        category=ValidationRuleCategory.EVIDENCE,
        name="Rule W",
        is_blocking=False,
        is_active=True,
    )
    test_db.add_all([rule_b, rule_w])
    test_db.flush()

    b = ValidationIssue(
        validation_rule_id=rule_b.id,
        severity=ValidationIssueSeverity.BLOCKING,
        status=ValidationIssueStatus.OPEN,
        target_type="project",
        target_id=project_id,
        issue_message="Issue 1",
    )
    w = ValidationIssue(
        validation_rule_id=rule_w.id,
        severity=ValidationIssueSeverity.WARNING,
        status=ValidationIssueStatus.OPEN,
        target_type="project",
        target_id=project_id,
        issue_message="Issue 2",
    )
    test_db.add_all([b, w])
    test_db.flush()

    # Query with foreign org_id must return empty list
    assert get_official_intake_open_blockers(test_db, org_id=foreign_org.id, project_id=project_id) == []
    assert get_official_intake_open_warnings(test_db, org_id=foreign_org.id, project_id=project_id) == []


def test_public_validator_wrappers() -> None:
    valid_manifest = [_valid_v2_line(1)]
    assert validate_stored_v2_manifest(valid_manifest) is True

    # Empty list
    assert validate_stored_v2_manifest([]) is False

    # Missing human confirmation
    unconfirmed = [_valid_v2_line(1)]
    unconfirmed[0]["human_line_confirmed"] = False
    assert validate_stored_v2_manifest(unconfirmed) is False

    # Blocking line
    blocked = [_valid_v2_line(1)]
    blocked[0]["has_unresolved_blocking_line"] = True
    assert validate_stored_v2_manifest(blocked) is False

    # Negative price
    bad_price = [_valid_v2_line(1)]
    bad_price[0]["proposed_unit_price"] = -5.0
    assert validate_stored_v2_manifest(bad_price) is False

    # v1 manifest missing keys
    v1_line = [{"identity": "Old", "proposed_unit_price": 100.0}]
    assert validate_stored_v2_manifest(v1_line) is False
