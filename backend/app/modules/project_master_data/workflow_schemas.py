import uuid
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict
from app.modules.project_master_data.models import (
    WorkflowDefinitionStatus, WorkflowInstanceStatus, WorkflowTaskStatus,
    WorkflowTaskPriority, ReviewDecisionChoice, ApprovalGateStatus,
    ValidationRuleCategory, ValidationIssueSeverity, ValidationIssueStatus
)

# Shared Config
class SchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# WorkflowDefinition
class WorkflowDefinitionSchema(SchemaBase):
    id: uuid.UUID
    code: str
    name: str
    version: int
    status: WorkflowDefinitionStatus
    created_at: datetime
    updated_at: datetime


# WorkflowTransition
class WorkflowTransitionSchema(SchemaBase):
    id: uuid.UUID
    workflow_definition_id: uuid.UUID
    from_state: str
    to_state: str
    command_name: str
    required_permission: Optional[str] = None
    guard_expression: Optional[Dict[str, Any]] = None
    is_active: bool


# WorkflowInstance
class WorkflowInstanceCreate(BaseModel):
    workflow_definition_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    current_state: str


class WorkflowInstanceSchema(SchemaBase):
    id: uuid.UUID
    workflow_definition_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    current_state: str
    status: WorkflowInstanceStatus
    row_version: int
    created_at: datetime
    updated_at: datetime


# Transition Command Request
class WorkflowTransitionRequest(BaseModel):
    command_name: str
    expected_row_version: int
    payload: Optional[Dict[str, Any]] = None
    override_reason: Optional[str] = None


# WorkflowTask
class WorkflowTaskUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[WorkflowTaskStatus] = None
    priority: Optional[WorkflowTaskPriority] = None
    assigned_to: Optional[uuid.UUID] = None
    due_at: Optional[datetime] = None
    expected_row_version: int


class WorkflowTaskSchema(SchemaBase):
    id: uuid.UUID
    workflow_instance_id: uuid.UUID
    task_type: str
    title: str
    status: WorkflowTaskStatus
    priority: WorkflowTaskPriority
    assigned_to: Optional[uuid.UUID]
    due_at: Optional[datetime]
    row_version: int
    created_at: datetime
    updated_at: datetime


# ReviewDecision
class ReviewDecisionCreate(BaseModel):
    target_type: str
    target_id: uuid.UUID
    decision: ReviewDecisionChoice
    reason: Optional[str] = None
    evidence_ids: Optional[Dict[str, Any]] = None
    previous_state: Optional[str] = None
    new_state: Optional[str] = None


class ReviewDecisionSchema(SchemaBase):
    id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    decision: ReviewDecisionChoice
    reason: Optional[str]
    decided_by: uuid.UUID
    decided_at: datetime
    evidence_ids: Optional[Dict[str, Any]]
    previous_state: Optional[str]
    new_state: Optional[str]


# ApprovalGate
class ApprovalGateSchema(SchemaBase):
    id: uuid.UUID
    gate_code: str
    target_type: str
    target_id: uuid.UUID
    gate_status: ApprovalGateStatus
    blocking_issue_count: int
    evaluated_at: datetime


# ValidationRule
class ValidationRuleSchema(SchemaBase):
    id: uuid.UUID
    rule_code: str
    category: ValidationRuleCategory
    name: str
    description: Optional[str]
    is_blocking: bool
    is_active: bool


# ValidationIssue
class ValidationIssueUpdate(BaseModel):
    severity: Optional[ValidationIssueSeverity] = None
    status: Optional[ValidationIssueStatus] = None
    issue_message: Optional[str] = None
    expected_row_version: int


class ValidationIssueResolveRequest(BaseModel):
    resolution_notes: str
    expected_row_version: int


class ValidationIssueSchema(SchemaBase):
    id: uuid.UUID
    validation_rule_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    severity: ValidationIssueSeverity
    status: ValidationIssueStatus
    issue_message: str
    detected_at: datetime
    resolved_by: Optional[uuid.UUID]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    row_version: int


# UserActionLog
class UserActionLogSchema(SchemaBase):
    id: uuid.UUID
    session_id: Optional[uuid.UUID]
    user_id: uuid.UUID
    action_type: str
    target_type: str
    target_id: uuid.UUID
    action_payload: Optional[Dict[str, Any]]
    created_at: datetime
