"""Strict confirmed commands and safe receipt metadata; no user-supplied verdicts."""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator


class LineCommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_id: uuid.UUID
    confirm: StrictBool
    expected_row_version: int = Field(gt=0, strict=True)
    expected_case_version: str = Field(pattern=r"^[0-9a-f]{64}$", strict=True)

    @field_validator("confirm")
    @classmethod
    def confirmed(cls, value):
        if value is not True:
            raise ValueError("Human confirmation required")
        return value


class ValidateProjectAssetLineRequest(LineCommandRequest):
    contract_version: Literal["asset-line-validation-v1"]


class DecideProjectAssetLineReviewRequest(LineCommandRequest):
    contract_version: Literal["asset-line-human-review-v1"]
    target_review_status: Literal["accepted", "flagged", "rejected"]
    reason_note: str | None = Field(default=None, strict=True)
    supersedes_decision_id: uuid.UUID | None = None

    @field_validator("reason_note")
    @classmethod
    def trim_reason(cls, value):
        if value is not None:
            value = value.strip()
            if not value or len(value) > 2000:
                raise ValueError("Reason must contain 1 to 2000 trimmed Unicode characters")
        return value


class LineFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    field: str
    severity: Literal["error", "advisory"]
    reference_id: uuid.UUID | None


class LineCommandResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_id: uuid.UUID
    receipt_id: uuid.UUID
    project_id: uuid.UUID
    line_id: uuid.UUID
    proof_id: uuid.UUID
    contract_version: Literal["asset-line-validation-v1", "asset-line-human-review-v1"]
    line_row_version: int
    created_at: datetime
    validation_outcome: Literal["valid", "invalid", "warning"] | None = None
    validation_generation: int | None = None
    target_review_status: Literal["accepted", "flagged", "rejected"] | None = None
    decision_version: int | None = None
    reversal_id: uuid.UUID | None = None
    findings: list[LineFinding] = Field(default_factory=list)


class LineCommandResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result: LineCommandResult
    replayed: bool
    historical: bool
    current_case_version: str
