"""Narrow append-only PRICE_EVIDENCE aggregate; no legacy evidence promotion."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKeyConstraint, Integer, JSON, String, UniqueConstraint, Uuid, CheckConstraint, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.db.mixins import UUIDMixin
from app.modules.project_master_data.asset_workbench_models import WorkbenchScope, scope_constraints

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class PriceEvidenceReceipt(Base, UUIDMixin, WorkbenchScope):
    __tablename__ = "price_evidence_receipts"
    command_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    request_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    response_metadata: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    __table_args__ = (*scope_constraints("pe_receipt"),
        UniqueConstraint("command_id", name="uq_pe_command"),
        UniqueConstraint("organization_id", "project_id", "actor_user_id", "session_id", "id", name="uq_pe_receipt_scope"))


class PriceEvidenceFact(WorkbenchScope):
    receipt_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    audit_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    seal_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    pre_row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    post_row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    # Immutable complete attestations: loaded and verified as a unit, never queried by JSON fields.
    content_binding: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    invocation_binding: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)


def fact_constraints(prefix):
    return (*scope_constraints(prefix),
        ForeignKeyConstraint(["audit_id"], ["audit_events.id"], name=f"fk_{prefix}_audit", ondelete="RESTRICT"),
        UniqueConstraint("audit_id", name=f"uq_{prefix}_audit"),
        ForeignKeyConstraint(["organization_id", "project_id", "actor_user_id", "session_id", "receipt_id"],
            [f"price_evidence_receipts.{f}" for f in ("organization_id", "project_id", "actor_user_id", "session_id", "id")],
            name=f"fk_{prefix}_receipt", ondelete="RESTRICT"),
        ForeignKeyConstraint(["organization_id", "project_id", "seal_id"],
            [f"project_asset_review_seals.{f}" for f in ("organization_id", "project_id", "id")],
            name=f"fk_{prefix}_seal", ondelete="RESTRICT"),
        UniqueConstraint("organization_id", "project_id", "id", name=f"uq_{prefix}_scope"),
        UniqueConstraint("receipt_id", name=f"uq_{prefix}_receipt"),
        CheckConstraint("pre_row_version > 0 AND post_row_version = pre_row_version + 1", name=f"chk_{prefix}_version"))


def scoped_fk(field, table, prefix):
    return ForeignKeyConstraint(["organization_id", "project_id", field],
        [f"{table}.{f}" for f in ("organization_id", "project_id", "id")], name=prefix, ondelete="RESTRICT")


class ProjectPriceEvidenceSource(Base, UUIDMixin, PriceEvidenceFact):
    __tablename__ = "project_price_evidence_sources"
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    predecessor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (*fact_constraints("pe_source"),
        UniqueConstraint("organization_id", "project_id", "source_id", "revision", name="uq_pe_source_revision"),
        UniqueConstraint("predecessor_id", name="uq_pe_source_successor"),
        scoped_fk("predecessor_id", __tablename__, "fk_pe_source_prior"),
        CheckConstraint("revision > 0 AND ((revision = 1 AND predecessor_id IS NULL) OR "
                        "(revision > 1 AND predecessor_id IS NOT NULL AND predecessor_id != id))", name="chk_pe_source_prior"),
        CheckConstraint("category IN ('internet_survey', 'unit_price_explanation', 'prior_appraisal_result')", name="chk_pe_source_category"))


class ProjectPriceEvidenceDecision(Base, UUIDMixin, PriceEvidenceFact):
    """One immutable relationship revision and its exact human decision, atomically admitted."""
    __tablename__ = "project_price_evidence_decisions"
    relationship_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, unique=True)
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    evidence_revision_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    line_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    predecessor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    disposition: Mapped[str] = mapped_column(String(32), nullable=False)
    review_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (*fact_constraints("pe_decision"),
        scoped_fk("evidence_revision_id", "project_price_evidence_sources", "fk_pe_decision_source"),
        scoped_fk("predecessor_id", __tablename__, "fk_pe_decision_prior"),
        ForeignKeyConstraint(["project_id", "line_id"], ["project_asset_lines.project_id", "project_asset_lines.id"],
                             name="fk_pe_decision_line", ondelete="RESTRICT"),
        UniqueConstraint("predecessor_id", name="uq_pe_decision_successor"),
        UniqueConstraint("organization_id", "project_id", "line_id", "source_id", "post_row_version", name="uq_pe_decision_order"),
        CheckConstraint("review_due_at > created_at", name="chk_pe_decision_deadline"),
        CheckConstraint("(outcome = 'accepted' AND disposition = 'qualifying_basis') OR "
                        "(outcome = 'rejected' AND disposition IN ('excluded_alternative', 'unresolved_concern'))", name="chk_pe_decision_outcome"))


class ProjectPriceEvidenceConfirmation(Base, UUIDMixin, PriceEvidenceFact):
    __tablename__ = "project_price_evidence_confirmations"
    predecessor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    workbench_confirmation_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    __table_args__ = (*fact_constraints("pe_confirmation"),
        scoped_fk("predecessor_id", __tablename__, "fk_pe_confirmation_prior"),
        scoped_fk("workbench_confirmation_id", "project_asset_workbench_confirmations", "fk_pe_confirmation_upstream"),
        UniqueConstraint("predecessor_id", name="uq_pe_confirmation_successor"))


class ProjectPriceEvidenceWithdrawal(Base, UUIDMixin, PriceEvidenceFact):
    __tablename__ = "project_price_evidence_withdrawals"
    target_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    __table_args__ = (*fact_constraints("pe_withdrawal"),
        UniqueConstraint("target_kind", "target_id", name="uq_pe_withdrawal_target"),
        CheckConstraint("target_kind IN ('source', 'relationship', 'decision', 'confirmation')", name="chk_pe_withdrawal_target"))


FACT_MODELS = (ProjectPriceEvidenceSource, ProjectPriceEvidenceDecision, ProjectPriceEvidenceConfirmation, ProjectPriceEvidenceWithdrawal)


def immutable(mapper, connection, target):
    raise ValueError("PRICE_EVIDENCE facts are append-only")


for model in (PriceEvidenceReceipt, *FACT_MODELS):
    event.listen(model, "before_update", immutable)
    event.listen(model, "before_delete", immutable)
