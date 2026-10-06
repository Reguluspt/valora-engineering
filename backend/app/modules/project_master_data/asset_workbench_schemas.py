"""Strict set-wide human commands and bounded historical receipt responses."""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator


class ExpectedAssetLineVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    line_id: uuid.UUID
    row_version: int = Field(gt=0, strict=True)


class WorkbenchCommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_id: uuid.UUID
    confirm: StrictBool
    expected_project_row_version: int = Field(gt=0, strict=True)
    expected_case_version: str = Field(pattern=r"^[0-9a-f]{64}$", strict=True)
    expected_seal_id: uuid.UUID
    expected_authoritative_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$", strict=True)
    expected_membership_version: int = Field(gt=0, strict=True)
    expected_line_versions: list[ExpectedAssetLineVersion] = Field(min_length=1, strict=True)
    reason_note: str | None = Field(strict=True)

    @field_validator("confirm")
    @classmethod
    def confirmed(cls, value):
        if value is not True:
            raise ValueError("Explicit human confirmation required")
        return value

    @field_validator("reason_note")
    @classmethod
    def trim_reason(cls, value):
        if value is not None:
            value = value.strip()
            if not value or len(value) > 2000:
                raise ValueError("Reason must contain 1 to 2000 trimmed Unicode characters")
        return value

    @field_validator("expected_line_versions")
    @classmethod
    def unique_members(cls, value):
        if len({item.line_id for item in value}) != len(value):
            raise ValueError("Duplicate member")
        return value


class ConfirmProjectAssetWorkbenchRequest(WorkbenchCommandRequest):
    contract_version: Literal["asset-workbench-confirmation-v1"]
    supersedes_confirmation_id: uuid.UUID | None

    @model_validator(mode="after")
    def reason_for_supersession(self):
        if (self.supersedes_confirmation_id is None) != (self.reason_note is None):
            raise ValueError("First confirmation has no reason; supersession requires a reason")
        return self


class WithdrawProjectAssetWorkbenchConfirmationRequest(WorkbenchCommandRequest):
    contract_version: Literal["asset-workbench-withdrawal-v1"]
    expected_confirmation_id: uuid.UUID

    @model_validator(mode="after")
    def reason_required(self):
        if self.reason_note is None:
            raise ValueError("Withdrawal requires a reason")
        return self


class WorkbenchCommandResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_id: uuid.UUID
    receipt_id: uuid.UUID
    project_id: uuid.UUID
    contract_version: Literal["asset-workbench-confirmation-v1", "asset-workbench-withdrawal-v1"]
    confirmation_id: uuid.UUID
    reversal_id: uuid.UUID | None
    project_row_version: int = Field(gt=0, strict=True)
    created_at: datetime


class WorkbenchCommandResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result: WorkbenchCommandResult
    replayed: bool
    historical: bool
    current_case_version: str


class WorkbenchPreparationSnapshot(BaseModel):
    """Invocation metadata only; Case State remains the completion read model."""
    model_config = ConfigDict(extra="forbid")
    project_id: uuid.UUID
    case_version: str
    project_row_version: int
    seal_id: uuid.UUID | None
    authoritative_set_sha256: str | None
    membership_version: int | None
    line_versions: list[ExpectedAssetLineVersion]
    prior_confirmation_id: uuid.UUID | None
    withdrawn: bool
    can_confirm: bool
    can_withdraw: bool
    can_edit_description: bool
