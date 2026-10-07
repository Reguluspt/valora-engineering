"""Exact human quotation commands; confirmation adds no professional checklist."""
import uuid
from typing import Literal

from pydantic import Field, model_validator

from app.modules.project_master_data.asset_workbench_schemas import WorkbenchCommandRequest
from app.modules.project_master_data.price_evidence_schemas import StrictObject, Amount, Text, UTC, Date


class QuoteTerms(StrictObject):
    quotation_number: Text | None
    quotation_number_not_issued_reason: Text | None = None
    quote_date: Date
    effective_at: UTC
    expires_at: UTC | None
    review_due_at: UTC
    currency: str = Field(pattern=r"^[A-Z]{3}$", strict=True)
    tax: Text
    delivery: Text
    condition: Text
    warranty: Text
    payment: Text
    acquisition_method: Literal["already_retained_document_reference"] = "already_retained_document_reference"
    limitations: Text
    source_locator: str = Field(pattern=r"^[A-Za-z0-9 .,:()_-]{1,120}$", strict=True)
    comparison_basis: Literal["unassessed", "same_working_unit_basis"] = "unassessed"

    @model_validator(mode="after")
    def dates(self):
        if self.expires_at and (self.effective_at >= self.expires_at or self.review_due_at > self.expires_at):
            raise ValueError("Invalid quotation validity")
        if (self.quotation_number is None) != (self.quotation_number_not_issued_reason is not None):
            raise ValueError("Number or explicit not-issued explanation required")
        return self


class QuoteItemInput(StrictObject):
    line_id: uuid.UUID
    quantity: Amount
    unit: Text
    unit_price: Amount
    source_locator: str = Field(pattern=r"^[A-Za-z0-9 .,:()_-]{1,120}$", strict=True)

    @model_validator(mode="after")
    def positive_quantity(self):
        if self.quantity <= 0 or self.unit_price <= 0:
            raise ValueError("Positive exact quantity and price required")
        return self


class QuoteCommand(WorkbenchCommandRequest):
    expected_session_id: uuid.UUID
    expected_price_evidence_confirmation_id: uuid.UUID
    supplier_id: uuid.UUID
    expected_supplier_row_version: int = Field(gt=0, strict=True)
    quote_id: uuid.UUID
    expected_revision_id: uuid.UUID | None
    expected_quote_head_version: int = Field(ge=0, strict=True)
    expected_source_generation: int = Field(gt=0, strict=True)


class QuoteSourceCommand(QuoteCommand):
    source_revision_id: uuid.UUID
    terms: QuoteTerms


class RegisterSupplierQuoteRequest(QuoteSourceCommand):
    contract_version: Literal["supplier-quote-registration-v1"]


class RegisterSupplierQuoteLineRequest(QuoteCommand):
    contract_version: Literal["supplier-quote-line-registration-v1"]
    item: QuoteItemInput


class ReviseSupplierQuoteRequest(QuoteSourceCommand):
    contract_version: Literal["supplier-quote-revision-v1"]
    items: list[QuoteItemInput] = Field(min_length=1, max_length=1000, strict=True)
    revision_reason: Literal["correction", "replacement", "negotiation"]
    resolves_concern_ids: list[uuid.UUID] = Field(default_factory=list, max_length=1000)
    resolution_evidence: Text | None = None

    @model_validator(mode="after")
    def distinct_lines(self):
        if self.reason_note is None:
            raise ValueError("Reasoned successor required")
        if len({item.line_id for item in self.items}) != len(self.items):
            raise ValueError("Duplicate exact line mapping")
        if len({item.source_locator for item in self.items}) != len(self.items):
            raise ValueError("Repeated source item allocation")
        if len(set(self.resolves_concern_ids)) != len(self.resolves_concern_ids) or bool(self.resolves_concern_ids) != bool(self.resolution_evidence):
            raise ValueError("Concern resolution must identify the exact retained concerns and evidence")
        return self


class ConfirmSupplierQuoteRequest(QuoteCommand):
    contract_version: Literal["supplier-quote-confirmation-v1"]


class WithdrawSupplierQuoteRequest(QuoteCommand):
    contract_version: Literal["supplier-quote-withdrawal-v1"]
    target_revision_id: uuid.UUID
    concern_code: Literal["identity_concern", "authenticity_concern", "integrity_concern"] | None = None

    @model_validator(mode="after")
    def reason_required(self):
        if self.reason_note is None:
            raise ValueError("Reasoned withdrawal required")
        return self


class RejectSupplierQuoteRequest(QuoteCommand):
    contract_version: Literal["supplier-quote-rejection-v1"]
    concern_code: Literal["identity_concern", "authenticity_concern", "integrity_concern"] | None = None

    @model_validator(mode="after")
    def reason_required(self):
        if self.reason_note is None:
            raise ValueError("Reasoned rejection required")
        return self


COMMAND_SCHEMAS = {schema.model_fields["contract_version"].annotation.__args__[0]: schema for schema in (
    RegisterSupplierQuoteRequest, RegisterSupplierQuoteLineRequest, ReviseSupplierQuoteRequest,
    ConfirmSupplierQuoteRequest, WithdrawSupplierQuoteRequest, RejectSupplierQuoteRequest)}
