"""Focused unit tests for Global Case State projection aggregator and orchestrator (VALORA-PR01-IMPL-003)."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import HTTPException
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
    ProjectionError,
    compute_case_version,
    get_case_state_projection,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    Customer,
    CustomerStatus,
    OrganizationProfile,
    OrganizationStatus,
    PreliminaryAnalysisSnapshot,
    PreliminaryResultArtifact,
    Project,
    ProjectAssetImportBatch,
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


def _add_test_issue(
    test_db: Session,
    *,
    target_type: str,
    target_id: uuid.UUID,
    severity: ValidationIssueSeverity,
    status: ValidationIssueStatus = ValidationIssueStatus.OPEN,
) -> ValidationIssue:
    rule = ValidationRule(
        rule_code=f"AG-RULE-{severity.value}-{uuid.uuid4().hex[:6]}",
        category=ValidationRuleCategory.EVIDENCE,
        name=f"Rule {severity.value}",
        is_blocking=(severity == ValidationIssueSeverity.BLOCKING),
        is_active=True,
    )
    test_db.add(rule)
    test_db.flush()
    issue = ValidationIssue(
        validation_rule_id=rule.id,
        target_type=target_type,
        target_id=target_id,
        severity=severity,
        status=status,
        issue_message=f"Test {severity.value} issue",
    )
    test_db.add(issue)
    test_db.flush()
    return issue


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


def _seed(
    test_db: Session,
    *,
    grant_read: bool = True,
    actor_active: bool = True,
    org_active: bool = True,
) -> dict[str, Any]:
    org = OrganizationProfile(
        legal_name="Aggregator Org",
        organization_slug=f"agg-org-{uuid.uuid4().hex[:8]}",
        status=OrganizationStatus.ACTIVE if org_active else OrganizationStatus.SUSPENDED,
    )
    test_db.add(org)
    test_db.flush()

    actor = User(
        organization_id=org.id,
        email=f"agg-user-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Aggregator Human",
        status=UserStatus.ACTIVE if actor_active else UserStatus.INACTIVE,
    )
    test_db.add(actor)
    test_db.flush()

    role = Role(
        code=f"role-{uuid.uuid4().hex[:8]}",
        display_name="Aggregator Role",
        permissions=["project:read"] if grant_read else [],
    )
    test_db.add(role)
    test_db.flush()

    user_role = UserRole(user_id=actor.id, role_id=role.id, is_active=True)
    test_db.add(user_role)

    customer = Customer(
        organization_id=org.id,
        legal_name="Aggregator Customer",
        status=CustomerStatus.ACTIVE,
        created_by=actor.id,
    )
    test_db.add(customer)
    test_db.flush()

    project = Project(
        organization_id=org.id,
        customer_id=customer.id,
        code=f"PRJ-{uuid.uuid4().hex[:6]}",
        name="Aggregator Project",
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
        "identity": f"Equipment {row_num}",
        "accepted_price_basis": "Supplier Quote",
        "confirmed_reference_price": 1000.0,
        "transport_percentage": 5.0,
        "proposed_unit_price": 1050.0,
        "human_line_confirmed": True,
        "has_unresolved_blocking_line": False,
        "source_row_number": row_num,
        "quantity": 10.0,
    }


def test_internal_auth_missing_read_permission_gives_403(test_db: Session) -> None:
    seeded = _seed(test_db, grant_read=False)
    with pytest.raises(HTTPException) as exc_info:
        get_case_state_projection(
            test_db,
            actor=seeded["actor"],
            org_id=seeded["org"].id,
            project_id=seeded["project"].id,
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error_code"] == "case_state_forbidden"


def test_internal_auth_inactive_actor_gives_403(test_db: Session) -> None:
    seeded = _seed(test_db, actor_active=False)
    with pytest.raises(HTTPException) as exc_info:
        get_case_state_projection(
            test_db,
            actor=seeded["actor"],
            org_id=seeded["org"].id,
            project_id=seeded["project"].id,
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error_code"] == "case_state_forbidden"


def test_internal_auth_safe_404_cross_tenant_or_missing(test_db: Session) -> None:
    seeded = _seed(test_db)
    random_project_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc_info:
        get_case_state_projection(
            test_db,
            actor=seeded["actor"],
            org_id=seeded["org"].id,
            project_id=random_project_id,
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error_code"] == "project_not_found"


def test_read_path_no_audit_and_no_writes(test_db: Session) -> None:
    seeded = _seed(test_db)
    init_audits = test_db.query(AuditEvent).count()

    proj = get_case_state_projection(
        test_db,
        actor=seeded["actor"],
        org_id=seeded["org"].id,
        project_id=seeded["project"].id,
    )
    assert proj is not None
    assert not test_db.dirty
    assert not test_db.new
    assert not test_db.deleted
    assert test_db.query(AuditEvent).count() == init_audits


def test_case_version_determinism_and_sensitivity(test_db: Session) -> None:
    seeded = _seed(test_db)
    org_id = seeded["org"].id
    project_id = seeded["project"].id
    actor = seeded["actor"]

    # Initial state: 0 batches -> empty prefix
    p1 = get_case_state_projection(test_db, actor=actor, org_id=org_id, project_id=project_id)
    p2 = get_case_state_projection(test_db, actor=actor, org_id=org_id, project_id=project_id)
    assert p1.case_version == p2.case_version
    assert len(p1.case_version) == 64

    # Add a batch and artifact -> case_version must change
    batch = ProjectAssetImportBatch(
        organization_id=org_id,
        project_id=project_id,
        source_filename="test.xlsx",
        source_sheet_name="Sheet1",
        created_by_user_id=actor.id,
    )
    test_db.add(batch)
    test_db.flush()

    artifact = ImportSourceArtifact(
        organization_id=org_id,
        project_id=project_id,
        import_batch_id=batch.id,
        generation=1,
        original_filename="test.xlsx",
        detected_format="xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size_bytes=1024,
        checksum_sha256="a" * 64,
        storage_object_key="key-1",
        state=ImportSourceArtifactState.AVAILABLE.value,
        created_by_user_id=actor.id,
    )
    test_db.add(artifact)
    test_db.flush()
    batch.current_source_artifact_id = artifact.id
    test_db.flush()

    p3 = get_case_state_projection(test_db, actor=actor, org_id=org_id, project_id=project_id)
    assert p3.case_version != p1.case_version

    # Add an open blocker -> case_version must change
    blocker = _add_test_issue(
        test_db,
        target_type="project",
        target_id=project_id,
        severity=ValidationIssueSeverity.BLOCKING,
        status=ValidationIssueStatus.OPEN,
    )

    p4 = get_case_state_projection(test_db, actor=actor, org_id=org_id, project_id=project_id)
    assert p4.case_version != p3.case_version

    # Increment blocker row_version -> case_version must change
    blocker.row_version += 1
    test_db.flush()
    p5 = get_case_state_projection(test_db, actor=actor, org_id=org_id, project_id=project_id)
    assert p5.case_version != p4.case_version

    # Resolve blocker -> case_version must change
    blocker.status = ValidationIssueStatus.RESOLVED
    test_db.flush()
    p6 = get_case_state_projection(test_db, actor=actor, org_id=org_id, project_id=project_id)
    assert p6.case_version != p5.case_version
    # Resolved blocker is excluded, so p6 matches p3!
    assert p6.case_version == p3.case_version

    # Add a warning -> case_version must change
    _add_test_issue(
        test_db,
        target_type="project",
        target_id=project_id,
        severity=ValidationIssueSeverity.WARNING,
        status=ValidationIssueStatus.OPEN,
    )
    p7 = get_case_state_projection(test_db, actor=actor, org_id=org_id, project_id=project_id)
    assert p7.case_version != p6.case_version


def test_warning_never_blocks_and_surfaced_separately(test_db: Session) -> None:
    seeded = _seed(test_db)
    org_id = seeded["org"].id
    project_id = seeded["project"].id
    actor = seeded["actor"]

    _add_test_issue(
        test_db,
        target_type="project",
        target_id=project_id,
        severity=ValidationIssueSeverity.WARNING,
        status=ValidationIssueStatus.OPEN,
    )

    proj = get_case_state_projection(test_db, actor=actor, org_id=org_id, project_id=project_id)
    assert len(proj.warnings) == 1
    assert len(proj.blockers) == 0
    # Warning does not make any stage BLOCKED
    for stg in proj.stages:
        assert stg.result != "BLOCKED"
    assert proj.next_action.kind != "BLOCKER"


def test_blocker_precedence_outranks_preliminary_pending(test_db: Session) -> None:
    seeded = _seed(test_db)
    org_id = seeded["org"].id
    project_id = seeded["project"].id
    actor = seeded["actor"]

    blocker = _add_test_issue(
        test_db,
        target_type="project",
        target_id=project_id,
        severity=ValidationIssueSeverity.BLOCKING,
        status=ValidationIssueStatus.OPEN,
    )

    proj = get_case_state_projection(test_db, actor=actor, org_id=org_id, project_id=project_id)
    # Preliminary stages have no registered blockers and must never become BLOCKED
    assert proj.stages[0].stage == "PRELIMINARY_REQUEST"
    assert proj.stages[0].result == "INCOMPLETE"
    assert proj.stages[1].stage == "PRELIMINARY_ANALYSIS"
    assert proj.stages[1].result == "INCOMPLETE"
    assert proj.stages[2].stage == "PRELIMINARY_READY"
    assert proj.stages[2].result == "INCOMPLETE"
    # OFFICIAL_INTAKE becomes BLOCKED because commit is absent and blocker is present
    assert proj.stages[3].stage == "OFFICIAL_INTAKE"
    assert proj.stages[3].result == "BLOCKED"

    # Next action: Blocker takes precedence over preliminary_request_pending
    assert proj.next_action.kind == "BLOCKER"
    assert proj.next_action.stage == "OFFICIAL_INTAKE"
    assert proj.next_action.validation_issue_id == str(blocker.id)
    assert proj.next_action.semantic_route_key is None


def test_blocker_when_commit_exists_keeps_official_intake_complete(test_db: Session) -> None:
    seeded = _seed(test_db)
    org_id = seeded["org"].id
    project_id = seeded["project"].id
    actor = seeded["actor"]

    commit = ProjectOfficialIntakeCommit(
        organization_id=org_id,
        customer_id=seeded["customer"].id,
        project_id=project_id,
        preliminary_result_artifact_id=uuid.uuid4(),
        preliminary_result_version=1,
        preliminary_result_sha256="4" * 64,
        source_snapshot_sha256="5" * 64,
        project_version_before=1,
        idempotency_key="idemp-1",
        request_digest_sha256="6" * 64,
        committed_by_user_id=actor.id,
    )
    test_db.add(commit)

    blocker = _add_test_issue(
        test_db,
        target_type="project",
        target_id=project_id,
        severity=ValidationIssueSeverity.BLOCKING,
        status=ValidationIssueStatus.OPEN,
    )

    proj = get_case_state_projection(test_db, actor=actor, org_id=org_id, project_id=project_id)
    # OFFICIAL_INTAKE remains COMPLETE when commit exists
    assert proj.stages[3].stage == "OFFICIAL_INTAKE"
    assert proj.stages[3].result == "COMPLETE"
    # Blocker still takes next action precedence
    assert proj.next_action.kind == "BLOCKER"
    assert proj.next_action.stage == "OFFICIAL_INTAKE"
    assert proj.next_action.validation_issue_id == str(blocker.id)


def test_current_stage_never_jumps_past_incomplete(test_db: Session) -> None:
    seeded = _seed(test_db)
    org_id = seeded["org"].id
    project_id = seeded["project"].id
    actor = seeded["actor"]

    # Only commit row is added; preliminary stages are incomplete
    commit = ProjectOfficialIntakeCommit(
        organization_id=org_id,
        customer_id=seeded["customer"].id,
        project_id=project_id,
        preliminary_result_artifact_id=uuid.uuid4(),
        preliminary_result_version=1,
        preliminary_result_sha256="4" * 64,
        source_snapshot_sha256="5" * 64,
        project_version_before=1,
        idempotency_key="idemp-1",
        request_digest_sha256="6" * 64,
        committed_by_user_id=actor.id,
    )
    test_db.add(commit)
    test_db.flush()

    proj = get_case_state_projection(test_db, actor=actor, org_id=org_id, project_id=project_id)
    # Even though OFFICIAL_INTAKE is COMPLETE, current_stage MUST remain PRELIMINARY_REQUEST
    assert proj.current_stage == "PRELIMINARY_REQUEST"
    assert proj.next_action.kind == "PENDING"
    assert proj.next_action.stage == "PRELIMINARY_REQUEST"
    assert proj.next_action.semantic_route_key == "preliminary_request_pending"


def test_all_four_complete_semantics(test_db: Session) -> None:
    seeded = _seed(test_db)
    org_id = seeded["org"].id
    project_id = seeded["project"].id
    customer_id = seeded["customer"].id
    actor = seeded["actor"]

    # 1. PRELIMINARY_REQUEST complete
    batch = ProjectAssetImportBatch(
        organization_id=org_id,
        project_id=project_id,
        source_filename="test.xlsx",
        source_sheet_name="Sheet1",
        created_by_user_id=actor.id,
    )
    test_db.add(batch)
    test_db.flush()

    source_artifact = ImportSourceArtifact(
        organization_id=org_id,
        project_id=project_id,
        import_batch_id=batch.id,
        generation=1,
        original_filename="test.xlsx",
        detected_format="xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size_bytes=1024,
        checksum_sha256="c" * 64,
        storage_object_key="key-src-1",
        state=ImportSourceArtifactState.AVAILABLE.value,
        created_by_user_id=actor.id,
    )
    test_db.add(source_artifact)
    test_db.flush()
    batch.current_source_artifact_id = source_artifact.id
    test_db.flush()

    # 2. PRELIMINARY_ANALYSIS complete
    structure = WorkbookStructureSnapshot(
        organization_id=org_id,
        project_id=project_id,
        import_batch_id=batch.id,
        source_artifact_id=source_artifact.id,
        snapshot_version=1,
        source_checksum_sha256="c" * 64,
        rule_version="v1",
        adapter_name="test",
        adapter_version="1.0",
        disposition=WorkbookStructureDisposition.PROPOSED.value,
        candidate_count=1,
        structure_payload={"candidates": []},
        analysis_digest_sha256="d" * 64,
        created_by_user_id=actor.id,
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
        actor_user_id=actor.id,
        command_id=uuid.uuid4(),
        proposal_source_kind=ColumnMappingProposalSourceKind.HUMAN.value,
        proposal_source_version="1.0",
        mapping_contract_version="v1",
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
        actor_user_id=actor.id,
        command_id=uuid.uuid4(),
        proposal_source_kind=ColumnMappingProposalSourceKind.HUMAN.value,
        proposal_source_version="1.0",
        mapping_contract_version="v1",
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
        mapping_contract_version="v1",
        template_fingerprint_sha256="f" * 64,
        mapping_snapshot=mapping_snapshot,
        mapping_digest_sha256="e" * 64,
        source_checksum_sha256="c" * 64,
        structure_digest_sha256="d" * 64,
        materialized_asset_row_count=1,
        created_by_user_id=actor.id,
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
        finalized_by_user_id=actor.id,
        finalized_at=datetime(2026, 9, 4, 13, 0, 0, tzinfo=timezone.utc),
        idempotency_key="key-s1",
        request_digest_sha256="2" * 64,
    )
    test_db.add(snapshot)
    test_db.flush()

    # 3. PRELIMINARY_READY complete
    from app.modules.project_master_data.application.preliminary_result_service import (
        _build_lineage_manifest,
        snapshot_canonical_digest,
    )
    snap_digest = snapshot_canonical_digest(snapshot)

    lineage_manifest = _build_lineage_manifest(
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
        snapshot_digest=snap_digest,
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
        source_snapshot_sha256=snap_digest,
        lineage_manifest=lineage_manifest,
        created_by_user_id=actor.id,
    )
    test_db.add(artifact)
    test_db.flush()

    # 4. OFFICIAL_INTAKE complete
    commit = ProjectOfficialIntakeCommit(
        organization_id=org_id,
        customer_id=customer_id,
        project_id=project_id,
        preliminary_result_artifact_id=artifact.id,
        preliminary_result_version=1,
        preliminary_result_sha256=artifact.content_checksum_sha256,
        source_snapshot_sha256=snap_digest,
        project_version_before=1,
        idempotency_key="idemp-1",
        request_digest_sha256="6" * 64,
        committed_by_user_id=actor.id,
    )
    test_db.add(commit)
    test_db.flush()

    proj = get_case_state_projection(test_db, actor=actor, org_id=org_id, project_id=project_id)
    # All 4 prefix stages COMPLETE
    assert proj.stages[0].result == "COMPLETE"
    assert proj.stages[1].result == "COMPLETE"
    assert proj.stages[2].result == "COMPLETE"
    assert proj.stages[3].result == "COMPLETE"

    # current_stage is OFFICIAL_INTAKE
    assert proj.current_stage == "OFFICIAL_INTAKE"

    # next_action is NO_AUTHORIZED_DOWNSTREAM_ACTION
    assert proj.next_action.kind == "NO_AUTHORIZED_DOWNSTREAM_ACTION"
    assert proj.next_action.stage is None
    assert proj.next_action.semantic_route_key is None
    assert proj.next_action.validation_issue_id is None

    # All 12 downstream stages remain explicitly unavailable in PR-01.
    assert len(proj.stages) == 16
    for downstream in proj.stages[4:]:
        assert downstream.result == "NOT_AVAILABLE"
        assert downstream.provider_key is None


def test_unexpected_provider_failure_raises_typed_projection_error(test_db: Session) -> None:
    seeded = _seed(test_db)
    with patch(
        "app.modules.project_master_data.application.case_state_projection.evaluate_preliminary_request_provider",
        side_effect=RuntimeError("Simulated provider explosion"),
    ):
        with pytest.raises(ProjectionError) as exc_info:
            get_case_state_projection(
                test_db,
                actor=seeded["actor"],
                org_id=seeded["org"].id,
                project_id=seeded["project"].id,
            )
        assert "Unexpected provider failure" in str(exc_info.value)


def test_compute_case_version_golden_vector() -> None:
    org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    project_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    facts = [
        "official_intake_commit_v1:null:absent-v1:absent",
        "preliminary_analysis_v1:null:absent-v1:absent",
        "preliminary_ready_v1:null:absent-v1:absent",
        "preliminary_request_v1:null:absent-v1:absent",
    ]
    token, sorted_facts = compute_case_version(org_id=org_id, project_id=project_id, facts=facts)
    assert sorted_facts == sorted(facts)
    expected_envelope = {
        "contract": "global-case-state-v1",
        "facts": sorted(facts),
        "organization_id": "11111111-1111-1111-1111-111111111111",
        "project_id": "22222222-2222-2222-2222-222222222222",
    }
    expected_bytes = json.dumps(expected_envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected_sha = hashlib.sha256(expected_bytes).hexdigest()
    assert token == expected_sha


def test_aggregator_present_but_incomplete_snapshot_and_ready_artifact(test_db: Session) -> None:
    seeded = _seed(test_db)
    org_id = seeded["org"].id
    project_id = seeded["project"].id
    actor = seeded["actor"]

    # Snapshot present but incomplete (missing valid lineage/batch)
    v1_line = {"identity": "Old", "proposed_unit_price": 100.0}
    snapshot = PreliminaryAnalysisSnapshot(
        organization_id=org_id,
        customer_id=seeded["customer"].id,
        project_id=project_id,
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
        finalized_by_user_id=actor.id,
        finalized_at=datetime(2026, 9, 4, 13, 0, 0, tzinfo=timezone.utc),
        idempotency_key="key-s-inc",
        request_digest_sha256="2" * 64,
    )
    test_db.add(snapshot)

    # Artifact present but incomplete
    artifact = PreliminaryResultArtifact(
        organization_id=org_id,
        customer_id=seeded["customer"].id,
        project_id=project_id,
        version=1,
        original_filename="result.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size_bytes=2048,
        content_checksum_sha256="9" * 64,
        storage_object_key="key-res-inc",
        source_snapshot_sha256="c" * 64,
        lineage_manifest={},
        created_by_user_id=actor.id,
    )
    test_db.add(artifact)
    test_db.flush()

    proj = get_case_state_projection(test_db, actor=actor, org_id=org_id, project_id=project_id)
    # Both stages are INCOMPLETE
    assert proj.stages[1].stage == "PRELIMINARY_ANALYSIS"
    assert proj.stages[1].result == "INCOMPLETE"
    assert proj.stages[2].stage == "PRELIMINARY_READY"
    assert proj.stages[2].result == "INCOMPLETE"

    # But their fact tokens contain their IDs and av1 tokens
    assert f"preliminary_analysis_v1:{str(snapshot.id).lower()}:av1-" in proj.stages[1].fact_token
    assert proj.stages[1].fact_token.endswith(":incomplete")
    assert f"preliminary_ready_v1:{str(artifact.id).lower()}:av1-" in proj.stages[2].fact_token
    assert proj.stages[2].fact_token.endswith(":incomplete")

    # And those fact tokens are contributed into facts and case_version
    assert proj.stages[1].fact_token in proj.facts
    assert proj.stages[2].fact_token in proj.facts
