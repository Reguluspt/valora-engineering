"""PostgreSQL proof for unbound mapping and explicit current-batch authority."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker

from app.modules.excel_import.application.column_mapping_service import (
    confirm_column_mapping,
    materialize_confirmed_mapping_to_staging,
)
from app.modules.excel_import.infrastructure.object_storage import FakeObjectStorage
from app.modules.excel_import.models import ColumnMappingDecision, ColumnMappingProfile, ColumnMappingProfileUsage
from app.modules.project_master_data.models import AuditEvent, ProjectAssetImportBatch
from tests.test_s13_pr_004_column_mapping import _propose, _seed
from tests.test_s13_pr_004_column_mapping_postgresql import _cleanup, _postgres_engine_or_skip


def test_postgresql_unbound_mapping_has_null_historical_customer_and_no_memory():
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db = SessionLocal()
    storage = FakeObjectStorage()
    org_id = None
    try:
        seeded = _seed(db, storage=storage)
        org_id = seeded["org"].id
        seeded["project"].customer_id = None
        db.commit()
        proposal = _propose(db, seeded)
        assert proposal.exact_profile_id is None
        assert proposal.similar_profile_ids == ()
        assert proposal.decision.customer_id is None
        with pytest.raises(HTTPException) as exc:
            confirm_column_mapping(
                db, actor=seeded["user"], org_id=org_id,
                project_id=seeded["project"].id, batch_id=seeded["batch"].id,
                proposal_decision_id=proposal.decision.id,
                mapping_snapshot=proposal.decision.mapping_snapshot,
                memory_scope="customer", command_id=uuid.uuid4(),
            )
        assert exc.value.status_code == 409
        assert exc.value.detail["error_code"] == "mapping_customer_required"
        assert db.query(ColumnMappingProfile).filter_by(organization_id=org_id).count() == 0
        assert db.query(AuditEvent).filter_by(
            organization_id=org_id, event_name="ColumnMappingConfirmed"
        ).count() == 0

        confirmation = confirm_column_mapping(
            db, actor=seeded["user"], org_id=org_id,
            project_id=seeded["project"].id, batch_id=seeded["batch"].id,
            proposal_decision_id=proposal.decision.id,
            mapping_snapshot=proposal.decision.mapping_snapshot,
            memory_scope="none", command_id=uuid.uuid4(),
        )
        usage = materialize_confirmed_mapping_to_staging(
            db, actor=seeded["user"], org_id=org_id,
            project_id=seeded["project"].id, batch_id=seeded["batch"].id,
            confirmation_decision_id=confirmation.id, command_id=uuid.uuid4(),
            storage=storage,
        )
        assert confirmation.customer_id is None
        assert confirmation.profile_id is None
        assert usage.customer_id is None
        assert usage.materialized_asset_row_count == 3
        assert db.query(ColumnMappingDecision).filter_by(organization_id=org_id).count() == 2
        assert db.query(ColumnMappingProfile).filter_by(organization_id=org_id).count() == 0
        assert db.query(ColumnMappingProfileUsage).filter_by(organization_id=org_id).count() == 1
    finally:
        db.close()
        if org_id is not None:
            _cleanup(SessionLocal, org_id)
        engine.dispose()


def test_postgresql_historical_batch_and_null_pointer_reject_new_commands():
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db = SessionLocal()
    org_id = None
    try:
        seeded = _seed(db)
        org_id = seeded["org"].id
        proposal = _propose(db, seeded).decision
        confirmation = confirm_column_mapping(
            db, actor=seeded["user"], org_id=org_id,
            project_id=seeded["project"].id, batch_id=seeded["batch"].id,
            proposal_decision_id=proposal.id, mapping_snapshot=proposal.mapping_snapshot,
            memory_scope="none", command_id=uuid.uuid4(),
        )
        alternate = ProjectAssetImportBatch(
            organization_id=org_id, project_id=seeded["project"].id,
            source_filename="alternate.xlsx", status="created",
            created_by_user_id=seeded["user"].id,
        )
        db.add(alternate)
        db.flush()
        seeded["project"].current_preliminary_import_batch_id = alternate.id
        db.commit()
        with pytest.raises(HTTPException) as exc:
            _propose(db, seeded)
        assert exc.value.detail["error_code"] == "mapping_batch_not_current"
        with pytest.raises(HTTPException) as exc:
            confirm_column_mapping(
                db, actor=seeded["user"], org_id=org_id,
                project_id=seeded["project"].id, batch_id=seeded["batch"].id,
                proposal_decision_id=proposal.id, mapping_snapshot=proposal.mapping_snapshot,
                memory_scope="none", command_id=uuid.uuid4(),
            )
        assert exc.value.detail["error_code"] == "mapping_batch_not_current"
        with pytest.raises(HTTPException) as exc:
            materialize_confirmed_mapping_to_staging(
                db, actor=seeded["user"], org_id=org_id,
                project_id=seeded["project"].id, batch_id=seeded["batch"].id,
                confirmation_decision_id=confirmation.id, command_id=uuid.uuid4(),
            )
        assert exc.value.detail["error_code"] == "mapping_batch_not_current"
        seeded["project"].current_preliminary_import_batch_id = None
        db.commit()
        with pytest.raises(HTTPException) as exc:
            _propose(db, seeded)
        assert exc.value.detail["error_code"] == "mapping_batch_not_current"
    finally:
        db.close()
        if org_id is not None:
            _cleanup(SessionLocal, org_id)
        engine.dispose()


def test_postgresql_null_customer_confirmation_materializes_after_binding():
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db = SessionLocal()
    storage = FakeObjectStorage()
    org_id = None
    try:
        seeded = _seed(db, storage=storage)
        org_id = seeded["org"].id
        seeded["project"].customer_id = None
        db.commit()
        proposal = _propose(db, seeded).decision
        confirmation = confirm_column_mapping(
            db, actor=seeded["user"], org_id=org_id,
            project_id=seeded["project"].id, batch_id=seeded["batch"].id,
            proposal_decision_id=proposal.id, mapping_snapshot=proposal.mapping_snapshot,
            memory_scope="none", command_id=uuid.uuid4(),
        )
        db.commit()
        seeded["project"].customer_id = seeded["customer"].id
        db.commit()
        command_id = uuid.uuid4()
        usage = materialize_confirmed_mapping_to_staging(
            db, actor=seeded["user"], org_id=org_id,
            project_id=seeded["project"].id, batch_id=seeded["batch"].id,
            confirmation_decision_id=confirmation.id, command_id=command_id,
            storage=storage,
        )
        replay = materialize_confirmed_mapping_to_staging(
            db, actor=seeded["user"], org_id=org_id,
            project_id=seeded["project"].id, batch_id=seeded["batch"].id,
            confirmation_decision_id=confirmation.id, command_id=command_id,
            storage=storage,
        )
        assert replay.id == usage.id
        assert proposal.customer_id is None
        assert confirmation.customer_id is None
        assert usage.customer_id == seeded["customer"].id
    finally:
        db.close()
        if org_id is not None:
            _cleanup(SessionLocal, org_id)
        engine.dispose()
