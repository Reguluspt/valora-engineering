"""Historical mapping tests read the new explicit authority CAS before commands."""

from __future__ import annotations

from app.modules.excel_import.application.column_mapping_service import (
    confirm_column_mapping as _confirm,
    materialize_confirmed_mapping_to_staging as _materialize,
)
from app.modules.excel_import.application.mapping_authority import authority_slot
from app.modules.excel_import.models import ColumnMappingDecision, ColumnMappingProfileUsage


def _revision(db, org_id, project_id):
    slot = authority_slot(db, org_id=org_id, project_id=project_id)
    return slot.selection_revision if slot is not None else 0


def confirm_column_mapping(db, **kwargs):
    if "expected_selection_revision" not in kwargs:
        existing = db.query(ColumnMappingDecision).filter_by(
            organization_id=kwargs["org_id"], command_id=kwargs["command_id"],
        ).first()
        kwargs["expected_selection_revision"] = (
            (existing.before_summary or {}).get("expected_selection_revision", 0)
            if existing is not None else _revision(db, kwargs["org_id"], kwargs["project_id"])
        )
    return _confirm(db, **kwargs)


def materialize_confirmed_mapping_to_staging(db, **kwargs):
    if "expected_selection_revision" not in kwargs:
        existing = db.query(ColumnMappingProfileUsage).filter_by(
            organization_id=kwargs["org_id"], command_id=kwargs["command_id"],
        ).first()
        kwargs["expected_selection_revision"] = (
            existing.expected_selection_revision
            if existing is not None else _revision(db, kwargs["org_id"], kwargs["project_id"])
        )
    return _materialize(db, **kwargs)
