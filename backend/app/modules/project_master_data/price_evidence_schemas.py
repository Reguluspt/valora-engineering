"""A10 bounded human source registration and exact sealed-line command contracts."""
import ipaddress
import re
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from app.modules.project_master_data.asset_workbench_schemas import WorkbenchCommandRequest


def plain_text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Nonblank plain text required")
    if any(c in value for c in ("<", ">", "{{", "}}", "${", "{%", "%}", "\x00")):
        raise ValueError("Executable markup is not source text")
    if any(ord(c) < 32 and c not in "\n\r\t" for c in value):
        raise ValueError("Control characters are not source text")
    return value.strip()


Text = Annotated[str, BeforeValidator(plain_text), Field(max_length=2000, strict=True)]
Material = Annotated[str, BeforeValidator(plain_text), Field(min_length=20, max_length=20000, strict=True)]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$", strict=True)]


def decimal_value(value):
    if not isinstance(value, (str, Decimal)) or isinstance(value, float):
        raise ValueError("Exact decimal string required")
    if not re.fullmatch(r"(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,8})?", str(value)):
        raise ValueError("Bounded nonnegative decimal required")
    return Decimal(value)


Amount = Annotated[Decimal, BeforeValidator(decimal_value)]


def utc_datetime(value):
    if not isinstance(value, (str, datetime)):
        raise ValueError("UTC timestamp required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("UTC timestamp required")
    return parsed.astimezone(timezone.utc)


UTC = Annotated[datetime, BeforeValidator(utc_datetime)]


def exact_date(value):
    if type(value) is date:
        return value
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("ISO calendar date required")
    return date.fromisoformat(value)


Date = Annotated[date, BeforeValidator(exact_date)]


def safe_reference(value):
    if not isinstance(value, str) or len(value) > 2048 or any(c.isspace() for c in value):
        raise ValueError("Bounded public HTTPS reference required")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment
            or "?" in value or "#" in value or "\\" in value or "%" in parsed.netloc
            or parsed.port not in (None, 443)):
        raise ValueError("Public HTTPS reference without credentials or query required")
    host = parsed.hostname.lower()
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if (not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", host) or "." not in host
                or host.endswith((".localhost", ".local", ".internal", ".lan", ".home", ".test"))
                or not re.search(r"\.[a-z]{2,63}$", host)
                or any(not label or len(label) > 63 or label.startswith("-") or label.endswith("-")
                       for label in host.split("."))):
            raise ValueError("Public DNS reference required")
    else:
        if not address.is_global:
            raise ValueError("Private or local reference denied")
    return value


Reference = Annotated[str, BeforeValidator(safe_reference)]


class StrictObject(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)


class ObservedValue(StrictObject):
    amount: Amount
    range_upper: Amount | None
    currency: str = Field(pattern=r"^[A-Z]{3}$", strict=True)
    unit_basis: Text
    quantity_basis: Amount
    tax: Text
    delivery: Text
    condition: Text
    locator: Text

    @model_validator(mode="after")
    def valid_range(self):
        if self.quantity_basis <= 0 or (self.range_upper is not None and self.range_upper < self.amount):
            raise ValueError("Invalid quantity or range")
        return self


class ExplanationInput(StrictObject):
    evidence_revision_id: uuid.UUID
    coefficient: Amount


class UnitPriceExplanation(StrictObject):
    method: Literal["sum_of_scaled_source_values"]
    inputs: list[ExplanationInput] = Field(min_length=1, max_length=50, strict=True)
    assumptions: Text
    calculations: Text
    units: Text
    currency: str = Field(pattern=r"^[A-Z]{3}$", strict=True)
    proposed_basis_value: Amount

    @model_validator(mode="after")
    def distinct_inputs(self):
        if len({item.evidence_revision_id for item in self.inputs}) != len(self.inputs):
            raise ValueError("Duplicate explanation input")
        return self


class HistoricalAppraisalSource(StrictObject):
    project_id: uuid.UUID
    line_id: uuid.UUID
    appraisal_date: Date
    result_excerpt: Material
    result_locator: Text
    result_value: ObservedValue


class SourceMaterial(StrictObject):
    category: Literal["internet_survey", "unit_price_explanation", "prior_appraisal_result"]
    origin: Text
    reference: Reference | None
    locator: Text
    effective_date: Date | None
    unknown_date_reason: Text | None
    captured_at: UTC
    capture_method: Literal["manual_transcription", "authored_explanation"]
    retained_text: Material
    limitations: Text
    value: ObservedValue | None
    explanation: UnitPriceExplanation | None
    historical: HistoricalAppraisalSource | None
    expires_at: UTC | None

    @model_validator(mode="after")
    def source_contract(self):
        if re.fullmatch(r"https?://\S+|[\d\s.,]+", self.retained_text):
            raise ValueError("Bare reference or amount is not retained source material")
        if (self.effective_date is None) != (self.unknown_date_reason is not None):
            raise ValueError("Dated source or explicit unknown-date reason required")
        if self.category == "internet_survey":
            if not self.reference or self.capture_method != "manual_transcription" or self.explanation or self.historical:
                raise ValueError("Internet survey provenance required")
        elif self.category == "unit_price_explanation":
            if not self.explanation or self.historical or self.capture_method != "authored_explanation" or not self.value:
                raise ValueError("Structured explanation required")
            if (self.value.amount != self.explanation.proposed_basis_value or self.value.range_upper is not None
                    or self.value.currency != self.explanation.currency or self.value.unit_basis != self.explanation.units):
                raise ValueError("Explanation value and units must agree")
        elif (not self.historical or self.explanation or self.capture_method != "manual_transcription"
              or self.value != self.historical.result_value or self.effective_date != self.historical.appraisal_date):
            raise ValueError("Complete historical result lineage required")
        return self


class PriceEvidenceCommand(WorkbenchCommandRequest):
    reason_note: Text | None
    expected_workbench_confirmation_id: uuid.UUID


class RegisterProjectPriceEvidenceRequest(PriceEvidenceCommand):
    contract_version: Literal["price-evidence-registration-v1"]
    source_id: uuid.UUID
    predecessor_revision_id: uuid.UUID | None
    material: SourceMaterial

    @model_validator(mode="after")
    def correction_reason(self):
        if self.predecessor_revision_id is not None and self.reason_note is None:
            raise ValueError("Correction requires a reason")
        return self


class DecideProjectPriceEvidenceRelevanceRequest(PriceEvidenceCommand):
    contract_version: Literal["price-evidence-relevance-v1"]
    evidence_revision_id: uuid.UUID
    line_id: uuid.UUID
    predecessor_relationship_id: uuid.UUID | None
    prior_decision_id: uuid.UUID | None
    expected_line_proof_sha256: Digest
    source_portion: Text
    relevance_rationale: Text
    suitability_rationale: Text
    limitations: Text
    applicability_date: Date
    temporal_applicability: Text
    source_priority_rationale: Text
    higher_priorities_considered: list[Literal["internet_survey", "unit_price_explanation"]] = Field(max_length=2, strict=True)
    outcome: Literal["accepted", "rejected"]
    disposition: Literal["qualifying_basis", "excluded_alternative", "unresolved_concern"]
    review_due_at: UTC

    @model_validator(mode="after")
    def decision_contract(self):
        if len(set(self.higher_priorities_considered)) != len(self.higher_priorities_considered):
            raise ValueError("Duplicate priority category")
        if (self.outcome == "accepted") != (self.disposition == "qualifying_basis"):
            raise ValueError("Decision disposition mismatch")
        if (self.outcome == "rejected" or self.prior_decision_id or self.predecessor_relationship_id) and not self.reason_note:
            raise ValueError("Negative or successor decision requires reason")
        if (self.prior_decision_id is None) != (self.predecessor_relationship_id is None):
            raise ValueError("Exact prior relationship and decision required")
        return self


class WithdrawProjectPriceEvidenceRequest(PriceEvidenceCommand):
    contract_version: Literal["price-evidence-withdrawal-v1"]
    target_kind: Literal["source", "relationship", "decision"]
    target_id: uuid.UUID
    reason_note: Text


class ConfirmProjectPriceEvidenceRequest(PriceEvidenceCommand):
    contract_version: Literal["price-evidence-confirmation-v1"]
    supersedes_confirmation_id: uuid.UUID | None

    @model_validator(mode="after")
    def confirmation_reason(self):
        if self.supersedes_confirmation_id and not self.reason_note:
            raise ValueError("Successor confirmation requires reason")
        return self


class WithdrawProjectPriceEvidenceConfirmationRequest(PriceEvidenceCommand):
    contract_version: Literal["price-evidence-confirmation-withdrawal-v1"]
    expected_confirmation_id: uuid.UUID
    reason_note: Text


COMMAND_SCHEMAS = {schema.model_fields["contract_version"].annotation.__args__[0]: schema for schema in (
    RegisterProjectPriceEvidenceRequest, DecideProjectPriceEvidenceRelevanceRequest,
    WithdrawProjectPriceEvidenceRequest, ConfirmProjectPriceEvidenceRequest,
    WithdrawProjectPriceEvidenceConfirmationRequest)}


class PriceEvidenceResult(StrictObject):
    command_id: uuid.UUID
    receipt_id: uuid.UUID
    project_id: uuid.UUID
    contract_version: str
    record_id: uuid.UUID
    relationship_id: uuid.UUID | None
    project_row_version: int
    created_at: datetime


class PriceEvidenceResponse(StrictObject):
    result: PriceEvidenceResult
    replayed: bool
    historical: Literal[True]
    current_case_version: str


class EvidenceLinePrecondition(StrictObject):
    line_id: uuid.UUID
    row_version: int
    proof_sha256: Digest


class EvidenceSourcePrecondition(StrictObject):
    source_id: uuid.UUID
    evidence_revision_id: uuid.UUID
    withdrawn: bool


class EvidenceDecisionPrecondition(StrictObject):
    line_id: uuid.UUID
    source_id: uuid.UUID
    evidence_revision_id: uuid.UUID
    relationship_id: uuid.UUID
    decision_id: uuid.UUID
    withdrawn: bool


class PriceEvidencePreparation(StrictObject):
    project_id: uuid.UUID
    case_version: Digest
    project_row_version: int
    seal_id: uuid.UUID | None
    authoritative_set_sha256: Digest | None
    membership_version: int | None
    workbench_confirmation_id: uuid.UUID | None
    prior_confirmation_id: uuid.UUID | None
    lines: list[EvidenceLinePrecondition]
    sources: list[EvidenceSourcePrecondition]
    decisions: list[EvidenceDecisionPrecondition]
    can_register: bool
    can_decide: bool
    can_confirm: bool
    can_withdraw: bool


class PriceEvidenceSourceRead(StrictObject):
    project_id: uuid.UUID
    source_id: uuid.UUID
    evidence_revision_id: uuid.UUID
    predecessor_revision_id: uuid.UUID | None
    revision: int
    registrar_id: uuid.UUID
    registered_at: datetime
    material: SourceMaterial


class PriceEvidenceDecisionView(StrictObject):
    decision_id: uuid.UUID
    relationship_id: uuid.UUID
    evidence_revision_id: uuid.UUID
    line_id: uuid.UUID
    outcome: Literal["accepted", "rejected"]
    disposition: Literal["qualifying_basis", "excluded_alternative", "unresolved_concern"]
    qualifying: bool
    withdrawn: bool
    review_due_at: datetime
    review_expired: bool
    unresolved_concern: bool
    can_withdraw: bool


class PriceEvidenceSourceView(StrictObject):
    source_id: uuid.UUID
    evidence_revision_id: uuid.UUID
    revision: int
    predecessor_revision_id: uuid.UUID | None
    category: Literal["internet_survey", "unit_price_explanation", "prior_appraisal_result"]
    origin: str
    effective_date: date | None
    date_unknown: bool
    captured_at: datetime
    expires_at: datetime | None
    expired: bool
    current: bool
    withdrawn: bool
    eligible: bool
    can_correct: bool
    can_withdraw: bool
    can_accept: bool
    can_reject: bool
    explanation_input_eligible: bool
    decision: PriceEvidenceDecisionView | None


class PriceEvidenceWorkspace(StrictObject):
    project_id: uuid.UUID
    case_version: Digest
    line_id: uuid.UUID | None
    covered_count: int | None
    sealed_count: int
    confirmation_id: uuid.UUID | None
    confirmation_withdrawn: bool
    confirmation_current: bool
    can_withdraw_confirmation: bool
    line_covered: bool | None
    line_hold: bool
    reason_codes: list[str]
    sources: list[PriceEvidenceSourceView]
    offset: int
    total: int
    next_offset: int | None
