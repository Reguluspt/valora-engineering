import uuid
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict
from app.modules.project_master_data.models import (
    WorkbenchSessionStatus,
    InlineEditDraftStatus,
    UndoRedoActionType,
    WorkbenchPanelType,
    WorkbenchNotificationType,
)


class SchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# WorkbenchSession
class WorkbenchSessionCreate(BaseModel):
    project_id: uuid.UUID


class WorkbenchSessionSchema(SchemaBase):
    id: uuid.UUID
    user_id: uuid.UUID
    project_id: uuid.UUID
    status: WorkbenchSessionStatus
    current_selection: Optional[Dict[str, Any]]
    started_at: datetime
    last_active_at: datetime
    row_version: int


class WorkbenchSessionHeartbeatRequest(BaseModel):
    expected_row_version: int


# WorkbenchLayout
class WorkbenchLayoutSave(BaseModel):
    layout_name: str
    layout_payload: Dict[str, Any]
    is_default: bool = False


class WorkbenchLayoutSchema(SchemaBase):
    id: uuid.UUID
    user_id: uuid.UUID
    layout_name: str
    layout_payload: Dict[str, Any]
    is_default: bool
    created_at: datetime
    updated_at: datetime


# AssetGridView
class AssetGridViewSave(BaseModel):
    view_name: str
    columns: Dict[str, Any]
    filters: Optional[Dict[str, Any]] = None
    sort: Optional[Dict[str, Any]] = None
    is_default: bool = False


class AssetGridViewSchema(SchemaBase):
    id: uuid.UUID
    user_id: uuid.UUID
    project_id: Optional[uuid.UUID]
    view_name: str
    columns: Dict[str, Any]
    filters: Optional[Dict[str, Any]]
    sort: Optional[Dict[str, Any]]
    is_default: bool
    created_at: datetime
    updated_at: datetime


# WorkbenchSelection
class WorkbenchSelectionSave(BaseModel):
    selected_target_type: str
    selected_target_ids: List[str]


class WorkbenchSelectionSchema(SchemaBase):
    id: uuid.UUID
    session_id: uuid.UUID
    selected_target_type: str
    selected_target_ids: List[str]
    updated_at: datetime


# InlineEditDraft
class InlineEditDraftCreate(BaseModel):
    target_type: str
    target_id: uuid.UUID
    field_key: str
    draft_value: Dict[str, Any]
    base_value: Optional[Dict[str, Any]] = None
    base_row_version: Optional[int] = None


class InlineEditDraftSchema(SchemaBase):
    id: uuid.UUID
    session_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    field_key: str
    draft_value: Dict[str, Any]
    base_value: Optional[Dict[str, Any]]
    base_row_version: Optional[int]
    status: InlineEditDraftStatus
    updated_at: datetime


# AutosaveCheckpoint
class AutosaveCheckpointCreate(BaseModel):
    checkpoint_payload: Dict[str, Any]


class AutosaveCheckpointSchema(SchemaBase):
    id: uuid.UUID
    session_id: uuid.UUID
    checkpoint_payload: Dict[str, Any]
    created_at: datetime
    expires_at: Optional[datetime]


# UndoRedoStackEntry
class UndoRedoStackEntrySchema(SchemaBase):
    id: uuid.UUID
    session_id: uuid.UUID
    sequence_no: int
    target_type: str
    target_id: uuid.UUID
    field_key: Optional[str]
    before_value: Optional[Dict[str, Any]]
    after_value: Optional[Dict[str, Any]]
    action_type: UndoRedoActionType
    is_undone: bool
    created_at: datetime


# PanelState
class PanelStateSave(BaseModel):
    panel_type: WorkbenchPanelType
    is_expanded: bool
    width: Optional[int] = None


class PanelStateSchema(SchemaBase):
    id: uuid.UUID
    session_id: uuid.UUID
    panel_type: WorkbenchPanelType
    is_expanded: bool
    width: Optional[int]
    updated_at: datetime


# WorkbenchNotification
class WorkbenchNotificationSchema(SchemaBase):
    id: uuid.UUID
    user_id: uuid.UUID
    session_id: Optional[uuid.UUID]
    notification_type: WorkbenchNotificationType
    message: str
    is_read: bool
    created_at: datetime


class AssetLineDraftStateSchema(BaseModel):
    asset_line_id: uuid.UUID
    has_saved_draft: bool = False
    has_unsaved_changes: bool = False
    is_locked: bool = False
    is_stale: bool = False
    draft_status: str = "clean"
    changed_fields: List[str] = []
    last_saved_at: Optional[datetime] = None
    last_saved_by: Optional[uuid.UUID] = None


class ProjectDraftStateResponse(BaseModel):
    project_id: uuid.UUID
    items: List[AssetLineDraftStateSchema]
    total: int


class AssetLineDraftSaveRequest(BaseModel):
    field_key: str
    draft_value: Any
    base_value: Optional[Any] = None
    version_token: str


class AssetLineDraftSaveResponse(BaseModel):
    project_id: uuid.UUID
    asset_line_id: uuid.UUID
    draft_status: str
    field_key: str
    has_saved_draft: bool
    has_unsaved_changes: bool
    is_stale: bool
    changed_fields: List[str]
    saved_at: datetime


class AssetLineDraftCommitRequest(BaseModel):
    field_keys: List[str]
    confirm: bool
    version_token: str


class AssetLineDraftCommitResponse(BaseModel):
    project_id: uuid.UUID
    asset_line_id: uuid.UUID
    committed_fields: List[str]
    draft_status: str
    has_saved_draft: bool
    has_unsaved_changes: bool
    is_stale: bool
    committed_at: datetime


# ProjectAssetImportBatch
class ProjectAssetImportBatchCreate(BaseModel):
    source_filename: str
    source_sheet_name: Optional[str] = None


class ProjectAssetImportBatchResponse(SchemaBase):
    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    source_filename: str
    source_sheet_name: Optional[str]
    total_rows: int
    valid_rows: int
    invalid_rows: int
    warning_rows: int
    created_at: datetime
    updated_at: datetime


class ProjectAssetImportValidationMessage(BaseModel):
    field: Optional[str] = None
    message_key: str
    message: Optional[str] = None


class ProjectAssetImportStagingRowResponse(SchemaBase):
    id: uuid.UUID
    import_batch_id: uuid.UUID
    source_row_number: int
    validation_status: str
    validation_errors: List[ProjectAssetImportValidationMessage]
    validation_warnings: List[ProjectAssetImportValidationMessage]
    proposed_asset_name: Optional[str] = None
    proposed_description: Optional[str] = None
    proposed_quantity: Optional[str] = None
    proposed_unit: Optional[str] = None
    proposed_raw_price: Optional[str] = None
    proposed_currency: Optional[str] = None
    proposed_appraised_unit_price: Optional[str] = None
    proposed_review_status: Optional[str] = None
    proposed_validation_status: Optional[str] = None


class ProjectAssetImportStagingRowPaginationResponse(BaseModel):
    project_id: uuid.UUID
    import_batch_id: uuid.UUID
    items: List[ProjectAssetImportStagingRowResponse]
    total: int
    limit: int
    offset: int


class ProjectAssetImportBatchApplyRequest(BaseModel):
    confirm: Optional[bool] = None


class ProjectAssetImportBatchApplyCreatedLine(BaseModel):
    line_id: uuid.UUID
    staging_row_id: uuid.UUID
    source_row_number: int


class ProjectAssetImportBatchApplyResponse(BaseModel):
    project_id: uuid.UUID
    import_batch_id: uuid.UUID
    status: str
    created_count: int
    created_lines: List[ProjectAssetImportBatchApplyCreatedLine]
