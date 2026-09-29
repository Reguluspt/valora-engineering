"""Explicit Project mapping authority shared by mapping and pointer writers.

Callers lock Project, then the current batch, before taking the slot lock.
This module never commits; authority and the caller's audit share one transaction.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.audit import log_audit_event
from app.modules.excel_import.models import (
    ColumnMappingDecision,
    ColumnMappingProfileUsage,
    ProjectColumnMappingAuthority,
)
from app.modules.project_master_data.models import Project


def authority_slot(
    db: Session, *, org_id: uuid.UUID, project_id: uuid.UUID, create: bool = False,
    lock: bool = False,
) -> ProjectColumnMappingAuthority | None:
    query = db.query(ProjectColumnMappingAuthority).filter(
        ProjectColumnMappingAuthority.organization_id == org_id,
        ProjectColumnMappingAuthority.project_id == project_id,
    ).populate_existing()
    if lock:
        query = query.with_for_update()
    slot = query.first()
    if slot is None and create:
        slot = ProjectColumnMappingAuthority(
            organization_id=org_id, project_id=project_id, selection_revision=0,
        )
        db.add(slot)
        db.flush()
    return slot


def require_revision(slot: ProjectColumnMappingAuthority | None, expected: int) -> None:
    if expected != (slot.selection_revision if slot is not None else 0):
        raise HTTPException(status_code=409, detail={
            "error_code": "mapping_selection_revision_conflict",
            "detail": "Quyền chọn ánh xạ đã thay đổi. Vui lòng tải lại trạng thái.",
        })


def terminal_outcomes(
    db: Session, *, org_id: uuid.UUID, project_id: uuid.UUID,
    proposal_id: uuid.UUID,
) -> list[ColumnMappingDecision]:
    return db.query(ColumnMappingDecision).filter(
        ColumnMappingDecision.organization_id == org_id,
        ColumnMappingDecision.project_id == project_id,
        ColumnMappingDecision.proposal_decision_id == proposal_id,
        ColumnMappingDecision.decision_kind.in_(("confirmation", "rejection")),
    ).all()


def lineage_has_usage(
    db: Session, *, org_id: uuid.UUID, project_id: uuid.UUID,
    batch_id: uuid.UUID, source_id: uuid.UUID, structure_id: uuid.UUID,
) -> bool:
    return db.query(ColumnMappingProfileUsage.id).filter(
        ColumnMappingProfileUsage.organization_id == org_id,
        ColumnMappingProfileUsage.project_id == project_id,
        ColumnMappingProfileUsage.import_batch_id == batch_id,
        ColumnMappingProfileUsage.source_artifact_id == source_id,
        ColumnMappingProfileUsage.structure_snapshot_id == structure_id,
    ).first() is not None


def invalidate_authority(
    db: Session, *, org_id: uuid.UUID, project_id: uuid.UUID,
    actor_id: uuid.UUID, reason: str, correlation_id: str | None = None,
    changed_batch_id: uuid.UUID | None = None,
) -> None:
    """Clear all current mapping claims after a committed pointer change.

    Caller holds Project then batch locks and commits this with the pointer.
    """
    if changed_batch_id is not None:
        current_batch_id = db.query(Project.current_preliminary_import_batch_id).filter(
            Project.organization_id == org_id, Project.id == project_id,
        ).scalar()
        if current_batch_id != changed_batch_id:
            return
    slot = authority_slot(db, org_id=org_id, project_id=project_id, create=True, lock=True)
    assert slot is not None
    previous = {
        "confirmation_decision_id": str(slot.confirmation_decision_id) if slot.confirmation_decision_id else None,
        "selected_usage_id": str(slot.selected_usage_id) if slot.selected_usage_id else None,
        "current_staging_usage_id": str(slot.current_staging_usage_id) if slot.current_staging_usage_id else None,
        "selection_revision": slot.selection_revision,
    }
    slot.import_batch_id = None
    slot.source_artifact_id = None
    slot.structure_snapshot_id = None
    slot.confirmation_decision_id = None
    slot.selected_usage_id = None
    slot.current_staging_usage_id = None
    slot.selection_revision += 1
    log_audit_event(
        db=db, event_name="ProjectColumnMappingAuthorityInvalidated",
        entity_type="ProjectColumnMappingAuthority", entity_id=slot.id,
        organization_id=org_id, actor_user_id=actor_id,
        command_name="InvalidateProjectColumnMappingAuthority",
        correlation_id=correlation_id,
        payload={"project_id": str(project_id), "reason": reason,
                 "previous": previous, "selection_revision": slot.selection_revision},
    )


def require_staging_replacement_open(
    db: Session, *, org_id: uuid.UUID, project_id: uuid.UUID, batch_id: uuid.UUID,
    current_source_id: uuid.UUID | None,
) -> None:
    """Close non-mapping replacement where ownership cannot be maintained."""
    slot = authority_slot(db, org_id=org_id, project_id=project_id, lock=True)
    if slot is not None and slot.import_batch_id == batch_id and (
        slot.confirmation_decision_id is not None or slot.current_staging_usage_id is not None
    ):
        raise HTTPException(status_code=409, detail={
            "error_code": "mapping_staging_owned",
            "detail": "Staging đang thuộc ánh xạ đã chọn; cần xử lý ánh xạ trước.",
        })
    if current_source_id is None:
        return
    legacy_usage = db.query(ColumnMappingProfileUsage.id).filter(
        ColumnMappingProfileUsage.organization_id == org_id,
        ColumnMappingProfileUsage.project_id == project_id,
        ColumnMappingProfileUsage.import_batch_id == batch_id,
        ColumnMappingProfileUsage.source_artifact_id == current_source_id,
    ).first()
    if legacy_usage is not None:
        raise HTTPException(status_code=409, detail={
            "error_code": "mapping_legacy_staging_unresolved",
            "detail": "Quyền sở hữu staging lịch sử chưa được xác minh.",
        })
