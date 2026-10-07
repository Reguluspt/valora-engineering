"""Immutable supplier quotation journal and exact Numeric line facts."""
import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Integer, Numeric, String, UniqueConstraint, Uuid, event
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.db.mixins import UUIDMixin
from app.modules.project_master_data.asset_workbench_models import WorkbenchScope, scope_constraints
from app.modules.project_master_data.price_evidence_models import JSON_TYPE


class SupplierQuoteReceipt(Base, UUIDMixin, WorkbenchScope):
    __tablename__ = "supplier_quote_receipts"
    command_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    request_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    response_metadata: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    __table_args__ = (*scope_constraints("sq_receipt"),
        UniqueConstraint("command_id", name="uq_sq_command"),
        UniqueConstraint("organization_id", "project_id", "actor_user_id", "session_id", "id", name="uq_sq_receipt_scope"))


def scoped_fk(field, table, name):
    return ForeignKeyConstraint(["organization_id", "project_id", field],
        [f"{table}.{f}" for f in ("organization_id", "project_id", "id")], name=name, ondelete="RESTRICT")


class SupplierQuoteFact(Base, UUIDMixin, WorkbenchScope):
    __tablename__ = "supplier_quote_facts"
    quote_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    supplier_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    revision_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    predecessor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    source_revision_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    receipt_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    audit_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    seal_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    pre_row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    post_row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content_binding: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    invocation_binding: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    __table_args__ = (*scope_constraints("sq_fact"),
        UniqueConstraint("organization_id", "project_id", "id", name="uq_sq_fact_scope"),
        UniqueConstraint("organization_id", "project_id", "quote_id", "post_row_version", name="uq_sq_fact_order"),
        UniqueConstraint("organization_id", "project_id", "quote_id", "revision_number", name="uq_sq_revision"),
        UniqueConstraint("predecessor_id", name="uq_sq_successor"),
        UniqueConstraint("receipt_id", name="uq_sq_fact_receipt"),
        UniqueConstraint("audit_id", name="uq_sq_fact_audit"),
        ForeignKeyConstraint(["organization_id", "supplier_id"], ["suppliers.organization_id", "suppliers.id"], name="fk_sq_supplier", ondelete="RESTRICT"),
        ForeignKeyConstraint(["organization_id", "project_id", "quote_id", "source_revision_id"],
            [f"document_revisions.{f}" for f in ("organization_id", "project_id", "document_id", "id")], name="fk_sq_source_revision", ondelete="RESTRICT"),
        ForeignKeyConstraint(["organization_id", "source_revision_id"],
            ["storage_object_bindings.organization_id", "storage_object_bindings.document_revision_id"], name="fk_sq_retained_source", ondelete="RESTRICT"),
        scoped_fk("revision_id", __tablename__, "fk_sq_revision"),
        scoped_fk("predecessor_id", __tablename__, "fk_sq_predecessor"),
        scoped_fk("seal_id", "project_asset_review_seals", "fk_sq_seal"),
        ForeignKeyConstraint(["audit_id"], ["audit_events.id"], name="fk_sq_audit", ondelete="RESTRICT"),
        ForeignKeyConstraint(["organization_id", "project_id", "actor_user_id", "session_id", "receipt_id"],
            [f"supplier_quote_receipts.{f}" for f in ("organization_id", "project_id", "actor_user_id", "session_id", "id")], name="fk_sq_receipt", ondelete="RESTRICT"),
        CheckConstraint("pre_row_version > 0 AND post_row_version = pre_row_version + 1", name="chk_sq_versions"),
        CheckConstraint("(kind IN ('registration', 'revision') AND revision_id IS NULL AND revision_number > 0) OR "
            "(kind IN ('line-registration', 'confirmation', 'withdrawal', 'rejection') AND revision_id IS NOT NULL AND revision_number IS NULL AND predecessor_id IS NULL)", name="chk_sq_kind"))


class SupplierQuoteItem(Base, UUIDMixin):
    __tablename__ = "supplier_quote_items"
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    fact_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    line_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(26, 8), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(26, 8), nullable=False)
    unit: Mapped[str] = mapped_column(String(2000), nullable=False)
    source_locator: Mapped[str] = mapped_column(String(120), nullable=False)
    __table_args__ = (scoped_fk("fact_id", "supplier_quote_facts", "fk_sq_item_fact"),
        ForeignKeyConstraint(["project_id", "line_id"], ["project_asset_lines.project_id", "project_asset_lines.id"], name="fk_sq_item_line", ondelete="RESTRICT"),
        UniqueConstraint("fact_id", "line_id", name="uq_sq_item_line"),
        CheckConstraint("quantity > 0 AND unit_price > 0", name="chk_sq_item_amounts"))


MODELS = (SupplierQuoteReceipt, SupplierQuoteFact, SupplierQuoteItem)


def immutable(mapper, connection, target):
    raise ValueError("SUPPLIER_QUOTES facts are append-only")


for model in MODELS:
    event.listen(model, "before_update", immutable)
    event.listen(model, "before_delete", immutable)
