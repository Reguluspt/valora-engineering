"""Append-only whole-set preparation attestations, withdrawals and receipts."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (Boolean, CheckConstraint, DateTime, ForeignKeyConstraint, Integer,
                        JSON, String, Text, UniqueConstraint, Uuid, event, func)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.db.mixins import UUIDMixin, utc_now


class WorkbenchScope:
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False)


def scope_constraints(prefix):
    return (
        ForeignKeyConstraint(["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"], name=f"fk_{prefix}_project", ondelete="RESTRICT"),
        ForeignKeyConstraint(["organization_id", "actor_user_id"],
            ["users.organization_id", "users.id"], name=f"fk_{prefix}_actor", ondelete="RESTRICT"),
        ForeignKeyConstraint(["project_id", "actor_user_id", "session_id"],
            ["workbench_sessions.project_id", "workbench_sessions.user_id", "workbench_sessions.id"],
            name=f"fk_{prefix}_session", ondelete="RESTRICT"),
    )


class AssetWorkbenchCommandReceipt(Base, UUIDMixin, WorkbenchScope):
    __tablename__ = "asset_workbench_command_receipts"
    command_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    request_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    response_metadata: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    __table_args__ = (
        *scope_constraints("aw_receipt"),
        UniqueConstraint("organization_id", "command_id", name="uq_aw_receipt_command"),
        UniqueConstraint("organization_id", "project_id", "actor_user_id", "session_id", "id",
                         name="uq_aw_receipt_scope"),
        CheckConstraint("contract_version IN ('asset-workbench-confirmation-v1', 'asset-workbench-withdrawal-v1')",
                        name="chk_aw_receipt_contract"),
    )


class WorkbenchEvidence(WorkbenchScope):
    receipt_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    seal_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    authoritative_set_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    membership_version: Mapped[int] = mapped_column(Integer, nullable=False)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    # Immutable snapshot: never queried by internal fields; compared as one canonical binding.
    content_binding: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    invocation_binding: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    pre_row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    post_row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason_note: Mapped[str | None] = mapped_column(Text, nullable=True)


def evidence_constraints(prefix):
    return (
        *scope_constraints(prefix),
        ForeignKeyConstraint(["organization_id", "project_id", "actor_user_id", "session_id", "receipt_id"],
            [f"asset_workbench_command_receipts.{f}" for f in
             ("organization_id", "project_id", "actor_user_id", "session_id", "id")],
            name=f"fk_{prefix}_receipt", ondelete="RESTRICT"),
        ForeignKeyConstraint(["organization_id", "project_id", "seal_id"],
            [f"project_asset_review_seals.{f}" for f in ("organization_id", "project_id", "id")],
            name=f"fk_{prefix}_seal", ondelete="RESTRICT"),
        UniqueConstraint("organization_id", "project_id", "id", name=f"uq_{prefix}_scope"),
        UniqueConstraint("receipt_id", name=f"uq_{prefix}_receipt"),
        CheckConstraint("membership_version = 1 AND confirmed AND pre_row_version > 0 "
                        "AND post_row_version = pre_row_version + 1", name=f"chk_{prefix}_versions"),
        CheckConstraint("reason_note IS NULL OR (length(trim(reason_note)) > 0 AND length(reason_note) <= 2000)",
                        name=f"chk_{prefix}_reason"),
    )


class ProjectAssetWorkbenchConfirmation(Base, UUIDMixin, WorkbenchEvidence):
    __tablename__ = "project_asset_workbench_confirmations"
    confirmation_version: Mapped[int] = mapped_column(Integer, nullable=False)
    supersedes_confirmation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    prior_reversal_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    __table_args__ = (
        *evidence_constraints("aw_confirmation"),
        UniqueConstraint("organization_id", "project_id", "confirmation_version", name="uq_aw_confirmation_version"),
        UniqueConstraint("supersedes_confirmation_id", name="uq_aw_confirmation_successor"),
        ForeignKeyConstraint(["organization_id", "project_id", "supersedes_confirmation_id"],
            [f"project_asset_workbench_confirmations.{f}" for f in ("organization_id", "project_id", "id")],
            name="fk_aw_confirmation_prior", ondelete="RESTRICT"),
        ForeignKeyConstraint(["organization_id", "project_id", "prior_reversal_id"],
            [f"project_asset_workbench_withdrawals.{f}" for f in ("organization_id", "project_id", "id")],
            name="fk_aw_confirmation_reversal", ondelete="RESTRICT", use_alter=True),
        CheckConstraint("contract_version = 'asset-workbench-confirmation-v1' AND confirmation_version > 0",
                        name="chk_aw_confirmation_contract"),
        CheckConstraint("(supersedes_confirmation_id IS NULL AND reason_note IS NULL AND confirmation_version = 1 "
                        "AND prior_reversal_id IS NULL) OR (supersedes_confirmation_id IS NOT NULL "
                        "AND supersedes_confirmation_id != id AND reason_note IS NOT NULL AND confirmation_version > 1)",
                        name="chk_aw_confirmation_supersession"),
    )


class ProjectAssetWorkbenchWithdrawal(Base, UUIDMixin, WorkbenchEvidence):
    __tablename__ = "project_asset_workbench_withdrawals"
    confirmation_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    __table_args__ = (
        *evidence_constraints("aw_withdrawal"),
        ForeignKeyConstraint(["organization_id", "project_id", "confirmation_id"],
            [f"project_asset_workbench_confirmations.{f}" for f in ("organization_id", "project_id", "id")],
            name="fk_aw_withdrawal_confirmation", ondelete="RESTRICT"),
        UniqueConstraint("confirmation_id", name="uq_aw_withdrawal_confirmation"),
        CheckConstraint("contract_version = 'asset-workbench-withdrawal-v1' AND reason_note IS NOT NULL",
                        name="chk_aw_withdrawal_contract"),
    )


def _immutable(mapper, connection, target):
    raise ValueError("Asset Workbench evidence is append-only")


for _model in (AssetWorkbenchCommandReceipt, ProjectAssetWorkbenchConfirmation, ProjectAssetWorkbenchWithdrawal):
    event.listen(_model, "before_update", _immutable)
    event.listen(_model, "before_delete", _immutable)
