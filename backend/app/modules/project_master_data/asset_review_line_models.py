"""Dedicated append-only line proof, decision and receipt storage (ADR 0049)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (Boolean, CheckConstraint, DateTime, ForeignKeyConstraint, Integer,
                        JSON, String, Text, UniqueConstraint, Uuid, event, func)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.db.mixins import UUIDMixin, utc_now


class ScopeMixin:
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    line_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False)


def scope_constraints(prefix):
    return (
        ForeignKeyConstraint(["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"], name=f"fk_{prefix}_project", ondelete="RESTRICT"),
        ForeignKeyConstraint(["project_id", "line_id"],
            ["project_asset_lines.project_id", "project_asset_lines.id"],
            name=f"fk_{prefix}_line", ondelete="RESTRICT"),
        ForeignKeyConstraint(["organization_id", "actor_user_id"],
            ["users.organization_id", "users.id"], name=f"fk_{prefix}_actor", ondelete="RESTRICT"),
        ForeignKeyConstraint(["project_id", "actor_user_id", "session_id"],
            ["workbench_sessions.project_id", "workbench_sessions.user_id", "workbench_sessions.id"],
            name=f"fk_{prefix}_session", ondelete="RESTRICT"),
    )


class AssetReviewCommandReceipt(Base, UUIDMixin, ScopeMixin):
    __tablename__ = "asset_review_command_receipts"
    command_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    request_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    response_metadata: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False)
    __table_args__ = (
        *scope_constraints("ar_receipt"),
        UniqueConstraint("organization_id", "command_id", name="uq_ar_receipt_command"),
        UniqueConstraint("organization_id", "project_id", "line_id", "actor_user_id", "session_id", "id",
                         name="uq_ar_receipt_proof_scope"),
        CheckConstraint("contract_version IN ('asset-line-validation-v1', 'asset-line-human-review-v1')",
                        name="chk_ar_receipt_contract"),
    )


class ProofMixin(ScopeMixin):
    receipt_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    seal_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    membership_version: Mapped[int] = mapped_column(Integer, nullable=False)
    official_input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    reference_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    pre_row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    post_row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False)


def proof_constraints(prefix):
    return (
        *scope_constraints(prefix),
        ForeignKeyConstraint(["organization_id", "project_id", "line_id", "actor_user_id", "session_id", "receipt_id"],
            [f"asset_review_command_receipts.{f}" for f in
             ("organization_id", "project_id", "line_id", "actor_user_id", "session_id", "id")],
            name=f"fk_{prefix}_receipt", ondelete="RESTRICT"),
        ForeignKeyConstraint(["organization_id", "project_id", "seal_id"],
            ["project_asset_review_seals.organization_id", "project_asset_review_seals.project_id",
             "project_asset_review_seals.id"], name=f"fk_{prefix}_seal", ondelete="RESTRICT"),
        UniqueConstraint("organization_id", "project_id", "line_id", "id", name=f"uq_{prefix}_scope"),
        UniqueConstraint("receipt_id", name=f"uq_{prefix}_receipt"),
        CheckConstraint("membership_version = 1 AND confirmed AND pre_row_version > 0 "
                        "AND post_row_version = pre_row_version + 1", name=f"chk_{prefix}_versions"),
    )


class AssetLineValidationGeneration(Base, UUIDMixin, ProofMixin):
    __tablename__ = "asset_line_validation_generations"
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_contract: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    findings: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    __table_args__ = (
        *proof_constraints("ar_validation"),
        UniqueConstraint("organization_id", "project_id", "line_id", "generation", name="uq_ar_validation_generation"),
        CheckConstraint("generation > 0 AND outcome IN ('valid', 'invalid', 'warning') "
                        "AND rule_contract = 'official-asset-line-validation-v1'", name="chk_ar_validation_outcome"),
    )


class AssetLineHumanDecision(Base, UUIDMixin, ProofMixin):
    __tablename__ = "asset_line_human_decisions"
    decision_version: Mapped[int] = mapped_column(Integer, nullable=False)
    target_review_status: Mapped[str] = mapped_column(String(16), nullable=False)
    reason_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_generation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    __table_args__ = (
        *proof_constraints("ar_decision"),
        UniqueConstraint("organization_id", "project_id", "line_id", "decision_version", name="uq_ar_decision_version"),
        ForeignKeyConstraint(["organization_id", "project_id", "line_id", "validation_generation_id"],
            [f"asset_line_validation_generations.{f}" for f in ("organization_id", "project_id", "line_id", "id")],
            name="fk_ar_decision_validation", ondelete="RESTRICT"),
        CheckConstraint("decision_version > 0 AND target_review_status IN ('accepted', 'flagged', 'rejected')",
                        name="chk_ar_decision_target"),
        CheckConstraint("target_review_status != 'accepted' OR validation_generation_id IS NOT NULL",
                        name="chk_ar_decision_positive_proof"),
        CheckConstraint("reason_note IS NULL OR (length(trim(reason_note)) > 0 AND length(reason_note) <= 2000)",
                        name="chk_ar_decision_reason"),
        CheckConstraint("target_review_status = 'accepted' OR reason_note IS NOT NULL", name="chk_ar_decision_negative_reason"),
    )


class AssetLineDecisionReversal(Base, UUIDMixin, ScopeMixin):
    __tablename__ = "asset_line_decision_reversals"
    prior_decision_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    successor_decision_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    __table_args__ = (
        *scope_constraints("ar_reversal"),
        *(ForeignKeyConstraint(["organization_id", "project_id", "line_id", f"{kind}_decision_id"],
            [f"asset_line_human_decisions.{f}" for f in ("organization_id", "project_id", "line_id", "id")],
            name=f"fk_ar_reversal_{kind}", ondelete="RESTRICT") for kind in ("prior", "successor")),
        UniqueConstraint("prior_decision_id", name="uq_ar_reversal_prior"),
        UniqueConstraint("successor_decision_id", name="uq_ar_reversal_successor"),
        CheckConstraint("prior_decision_id != successor_decision_id", name="chk_ar_reversal_distinct"),
    )


def _immutable(mapper, connection, target):
    raise ValueError("Asset Review evidence is append-only")


for _model in (AssetReviewCommandReceipt, AssetLineValidationGeneration,
               AssetLineHumanDecision, AssetLineDecisionReversal):
    event.listen(_model, "before_update", _immutable)
    event.listen(_model, "before_delete", _immutable)
