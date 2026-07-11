import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.core.rbac import require_permission
from app.core.audit import log_audit_event
from app.modules.project_master_data.models import (
    User,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowInstanceStatus,
    WorkflowTransition,
    WorkflowTask,
    WorkflowTaskStatus,
    ReviewDecision,
    ValidationRule,
    ValidationIssue,
    ValidationIssueStatus,
    ValidationIssueSeverity,
    ApprovalGate,
    UserActionLog,
    ChangeRequest,
    ChangeRequestStatus,
    ChangeRequestType,
    ReviewDecisionChoice,
    ReviewDecisionReversal,
)
from app.modules.project_master_data.workflow_schemas import (
    WorkflowInstanceCreate,
    WorkflowInstanceSchema,
    WorkflowTransitionRequest,
    WorkflowTaskUpdate,
    WorkflowTaskSchema,
    ReviewDecisionCreate,
    ReviewDecisionSchema,
    ApprovalGateSchema,
    ValidationRuleSchema,
    ValidationIssueUpdate,
    ValidationIssueResolveRequest,
    ValidationIssueSchema,
    UserActionLogSchema,
    ChangeRequestCreate,
    ChangeRequestReviewRequest,
    ChangeRequestSchema,
)

router = APIRouter(prefix="/api/v1/workflow", tags=["Workflow"])


# Helper to log user action
def log_action(
    db: Session,
    user_id: uuid.UUID,
    action_type: str,
    target_type: str,
    target_id: uuid.UUID,
    payload: dict,
):
    serialized_payload = {}
    for k, v in payload.items():
        if isinstance(v, uuid.UUID):
            serialized_payload[k] = str(v)
        else:
            serialized_payload[k] = v

    log = UserActionLog(
        user_id=user_id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        action_payload=serialized_payload,
    )
    db.add(log)


ALLOWED_COMMANDS = {
    "StartImport",
    "CompleteImport",
    "CompleteParsing",
    "CompleteIdentityReview",
    "CompleteKnowledgeReview",
    "CompleteValuationReview",
    "CompletePriceReview",
    "SubmitForClientReview",
    "CompleteClientReview",
    "SubmitProjectForQC",
    "ApproveProject",
    "RejectProject",
    "ReopenProjectReview",
    "CancelProject",
}


@router.post("/instances", response_model=WorkflowInstanceSchema, status_code=201)
def create_instance(
    data: WorkflowInstanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workflow:instance:manage")),
):
    # Check definition exists
    wf_def = (
        db.query(WorkflowDefinition)
        .filter(WorkflowDefinition.id == data.workflow_definition_id)
        .first()
    )
    if not wf_def:
        raise HTTPException(status_code=404, detail="Workflow definition not found")

    instance = WorkflowInstance(
        workflow_definition_id=data.workflow_definition_id,
        target_type=data.target_type,
        target_id=data.target_id,
        current_state=data.current_state,
        status=WorkflowInstanceStatus.ACTIVE,
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)

    log_audit_event(
        db=db,
        event_name="WORKFLOW_INSTANCE_CREATE",
        entity_type="workflow_instance",
        entity_id=instance.id,
        actor_user_id=current_user.id,
    )
    log_action(
        db, current_user.id, "workflow_instance_creation", "workflow_instance", instance.id, {}
    )
    db.commit()

    return instance


@router.get("/instances/{instance_id}", response_model=WorkflowInstanceSchema)
def get_instance(
    instance_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workflow:read")),
):
    instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
    return instance


@router.post("/instances/{instance_id}/transition", response_model=WorkflowInstanceSchema)
def execute_transition(
    instance_id: uuid.UUID,
    req: WorkflowTransitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workflow:read")),  # Base check
):
    # 1. Verify command whitelist
    if req.command_name not in ALLOWED_COMMANDS:
        raise HTTPException(status_code=422, detail="Unknown transition command name")

    instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow instance not found")

    # 2. Concurrency check
    if instance.row_version != req.expected_row_version:
        raise HTTPException(status_code=409, detail="Stale row version")

    # 3. Find transition definition
    trans = (
        db.query(WorkflowTransition)
        .filter(
            WorkflowTransition.workflow_definition_id == instance.workflow_definition_id,
            WorkflowTransition.from_state == instance.current_state,
            WorkflowTransition.command_name == req.command_name,
            WorkflowTransition.is_active == True,
        )
        .first()
    )

    if not trans:
        raise HTTPException(
            status_code=400, detail="Invalid from_state or transition path not configured"
        )

    # 4. RBAC check for the transition permission if specified
    if trans.required_permission:
        has_perm = False
        for user_role in current_user.roles:
            if user_role.is_active and trans.required_permission in user_role.role.permissions:
                has_perm = True
                break
        if not has_perm:
            raise HTTPException(
                status_code=403, detail=f"Missing required permission: {trans.required_permission}"
            )

    # 5. Check blocking validation issues
    blocking_issues = (
        db.query(ValidationIssue)
        .filter(
            ValidationIssue.target_type == instance.target_type,
            ValidationIssue.target_id == instance.target_id,
            ValidationIssue.status == ValidationIssueStatus.OPEN,
            ValidationIssue.severity == ValidationIssueSeverity.BLOCKING,
        )
        .all()
    )

    if blocking_issues:
        # Check override permission
        has_override = False
        for user_role in current_user.roles:
            if user_role.is_active and "workflow:override_gate" in user_role.role.permissions:
                has_override = True
                break
        if not has_override or not req.override_reason:
            raise HTTPException(
                status_code=400, detail="Transition is blocked by open validation issues"
            )

    # 6. Perform transition mutation
    old_state = instance.current_state
    instance.current_state = trans.to_state
    instance.row_version += 1
    db.commit()

    log_audit_event(
        db=db,
        event_name="WORKFLOW_TRANSITION",
        entity_type="workflow_instance",
        entity_id=instance.id,
        actor_user_id=current_user.id,
        command_name=req.command_name,
        payload={"from_state": old_state, "to_state": trans.to_state},
    )
    log_action(
        db,
        current_user.id,
        "transition_execution",
        "workflow_instance",
        instance.id,
        {"from_state": old_state, "to_state": trans.to_state, "command": req.command_name},
    )
    db.commit()

    return instance


@router.get("/tasks", response_model=List[WorkflowTaskSchema])
def list_tasks(
    db: Session = Depends(get_db), current_user: User = Depends(require_permission("workflow:read"))
):
    return db.query(WorkflowTask).all()


@router.get("/tasks/{task_id}", response_model=WorkflowTaskSchema)
def get_task(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workflow:read")),
):
    task = db.query(WorkflowTask).filter(WorkflowTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/tasks/{task_id}", response_model=WorkflowTaskSchema)
def update_task(
    task_id: uuid.UUID,
    update: WorkflowTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workflow:task:assign")),
):
    task = db.query(WorkflowTask).filter(WorkflowTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.row_version != update.expected_row_version:
        raise HTTPException(status_code=409, detail="Stale row version")

    if update.title is not None:
        task.title = update.title
    if update.status is not None:
        task.status = update.status
    if update.priority is not None:
        task.priority = update.priority
    if update.assigned_to is not None:
        task.assigned_to = update.assigned_to
    if update.due_at is not None:
        task.due_at = update.due_at

    task.row_version += 1
    db.commit()
    db.refresh(task)

    log_audit_event(
        db=db,
        event_name="WORKFLOW_TASK_UPDATE",
        entity_type="workflow_task",
        entity_id=task.id,
        actor_user_id=current_user.id,
    )
    db.commit()
    return task


@router.post("/tasks/{task_id}/complete", response_model=WorkflowTaskSchema)
def complete_task(
    task_id: uuid.UUID,
    expected_row_version: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workflow:task:complete")),
):
    task = db.query(WorkflowTask).filter(WorkflowTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.row_version != expected_row_version:
        raise HTTPException(status_code=409, detail="Stale row version")

    task.status = WorkflowTaskStatus.COMPLETED
    task.row_version += 1
    db.commit()
    db.refresh(task)

    log_audit_event(
        db=db,
        event_name="WORKFLOW_TASK_COMPLETE",
        entity_type="workflow_task",
        entity_id=task.id,
        actor_user_id=current_user.id,
    )
    log_action(db, current_user.id, "task_complete", "workflow_task", task.id, {})
    db.commit()

    return task


@router.post("/decisions", response_model=ReviewDecisionSchema, status_code=201)
def create_decision(
    data: ReviewDecisionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workflow:decision:create")),
):
    decision = ReviewDecision(
        target_type=data.target_type,
        target_id=data.target_id,
        decision=data.decision,
        reason=data.reason,
        decided_by=current_user.id,
        evidence_ids=data.evidence_ids,
        previous_state=data.previous_state,
        new_state=data.new_state,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)

    log_audit_event(
        db=db,
        event_name="REVIEW_DECISION_RECORD",
        entity_type="review_decision",
        entity_id=decision.id,
        actor_user_id=current_user.id,
    )
    log_action(db, current_user.id, "review_decision_creation", "review_decision", decision.id, {})
    db.commit()

    return decision


@router.get("/decisions/{decision_id}", response_model=ReviewDecisionSchema)
def get_decision(
    decision_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workflow:read")),
):
    decision = db.query(ReviewDecision).filter(ReviewDecision.id == decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


@router.get("/validation-rules", response_model=List[ValidationRuleSchema])
def list_validation_rules(
    db: Session = Depends(get_db), current_user: User = Depends(require_permission("workflow:read"))
):
    return db.query(ValidationRule).all()


@router.get("/validation-issues", response_model=List[ValidationIssueSchema])
def list_validation_issues(
    db: Session = Depends(get_db), current_user: User = Depends(require_permission("workflow:read"))
):
    return db.query(ValidationIssue).all()


@router.get("/validation-issues/{issue_id}", response_model=ValidationIssueSchema)
def get_validation_issue(
    issue_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workflow:read")),
):
    issue = db.query(ValidationIssue).filter(ValidationIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Validation issue not found")
    return issue


@router.patch("/validation-issues/{issue_id}", response_model=ValidationIssueSchema)
def update_validation_issue(
    issue_id: uuid.UUID,
    update: ValidationIssueUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workflow:instance:manage")),
):
    issue = db.query(ValidationIssue).filter(ValidationIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Validation issue not found")

    if issue.row_version != update.expected_row_version:
        raise HTTPException(status_code=409, detail="Stale row version")

    if update.severity is not None:
        issue.severity = update.severity
    if update.status is not None:
        issue.status = update.status
    if update.issue_message is not None:
        issue.issue_message = update.issue_message

    issue.row_version += 1
    db.commit()
    db.refresh(issue)

    log_audit_event(
        db=db,
        event_name="VALIDATION_ISSUE_UPDATE",
        entity_type="validation_issue",
        entity_id=issue.id,
        actor_user_id=current_user.id,
    )
    db.commit()
    return issue


@router.post("/validation-issues/{issue_id}/resolve", response_model=ValidationIssueSchema)
def resolve_validation_issue(
    issue_id: uuid.UUID,
    req: ValidationIssueResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workflow:instance:manage")),
):
    issue = db.query(ValidationIssue).filter(ValidationIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Validation issue not found")

    if issue.row_version != req.expected_row_version:
        raise HTTPException(status_code=409, detail="Stale row version")

    issue.status = ValidationIssueStatus.RESOLVED
    issue.resolved_by = current_user.id
    issue.resolved_at = datetime.now(timezone.utc)
    issue.resolution_notes = req.resolution_notes
    issue.row_version += 1
    db.commit()
    db.refresh(issue)

    log_audit_event(
        db=db,
        event_name="VALIDATION_ISSUE_RESOLVE",
        entity_type="validation_issue",
        entity_id=issue.id,
        actor_user_id=current_user.id,
    )
    log_action(db, current_user.id, "validation_issue_resolution", "validation_issue", issue.id, {})
    db.commit()

    return issue


@router.get("/approval-gates", response_model=List[ApprovalGateSchema])
def list_approval_gates(
    db: Session = Depends(get_db), current_user: User = Depends(require_permission("workflow:read"))
):
    return db.query(ApprovalGate).all()


@router.get("/action-logs", response_model=List[UserActionLogSchema])
def list_action_logs(
    db: Session = Depends(get_db), current_user: User = Depends(require_permission("workflow:read"))
):
    return db.query(UserActionLog).all()


@router.post("/change-requests", response_model=ChangeRequestSchema, status_code=201)
def create_change_request(
    data: ChangeRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workflow:change_request:create")),
):
    code = f"CR-{uuid.uuid4().hex[:8].upper()}"
    cr = ChangeRequest(
        request_code=code,
        target_type=data.target_type,
        target_id=data.target_id,
        change_type=data.change_type,
        requested_payload=data.requested_payload,
        reason=data.reason,
        status=ChangeRequestStatus.PENDING_REVIEW,
        priority=data.priority,
        requested_by=current_user.id,
    )
    db.add(cr)
    db.commit()
    db.refresh(cr)

    log_audit_event(
        db=db,
        event_name="CHANGE_REQUEST_CREATE",
        entity_type="change_request",
        entity_id=cr.id,
        actor_user_id=current_user.id,
    )
    log_action(db, current_user.id, "change_request_creation", "change_request", cr.id, {})
    db.commit()

    return cr


@router.get("/change-requests", response_model=List[ChangeRequestSchema])
def list_change_requests(
    db: Session = Depends(get_db), current_user: User = Depends(require_permission("workflow:read"))
):
    return db.query(ChangeRequest).all()


@router.get("/change-requests/{change_request_id}", response_model=ChangeRequestSchema)
def get_change_request(
    change_request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workflow:read")),
):
    cr = db.query(ChangeRequest).filter(ChangeRequest.id == change_request_id).first()
    if not cr:
        raise HTTPException(status_code=404, detail="Change request not found")
    return cr


@router.post("/change-requests/{change_request_id}/approve", response_model=ChangeRequestSchema)
def approve_change_request(
    change_request_id: uuid.UUID,
    req: ChangeRequestReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workflow:change_request:review")),
):
    cr = db.query(ChangeRequest).filter(ChangeRequest.id == change_request_id).first()
    if not cr:
        raise HTTPException(status_code=404, detail="Change request not found")

    if cr.row_version != req.expected_row_version:
        raise HTTPException(status_code=409, detail="Stale row version")

    cr.status = ChangeRequestStatus.APPROVED
    cr.reviewed_by = current_user.id
    cr.reviewed_at = datetime.now(timezone.utc)
    cr.review_note = req.review_note
    cr.row_version += 1
    db.commit()
    db.refresh(cr)

    log_audit_event(
        db=db,
        event_name="CHANGE_REQUEST_APPROVE",
        entity_type="change_request",
        entity_id=cr.id,
        actor_user_id=current_user.id,
    )
    log_action(db, current_user.id, "change_request_approval", "change_request", cr.id, {})
    db.commit()

    return cr


@router.post("/change-requests/{change_request_id}/reject", response_model=ChangeRequestSchema)
def reject_change_request(
    change_request_id: uuid.UUID,
    req: ChangeRequestReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workflow:change_request:review")),
):
    cr = db.query(ChangeRequest).filter(ChangeRequest.id == change_request_id).first()
    if not cr:
        raise HTTPException(status_code=404, detail="Change request not found")

    if cr.row_version != req.expected_row_version:
        raise HTTPException(status_code=409, detail="Stale row version")

    if not req.review_note:
        raise HTTPException(status_code=400, detail="Rejection reason is required")

    cr.status = ChangeRequestStatus.REJECTED
    cr.reviewed_by = current_user.id
    cr.reviewed_at = datetime.now(timezone.utc)
    cr.review_note = req.review_note
    cr.row_version += 1
    db.commit()
    db.refresh(cr)

    log_audit_event(
        db=db,
        event_name="CHANGE_REQUEST_REJECT",
        entity_type="change_request",
        entity_id=cr.id,
        actor_user_id=current_user.id,
    )
    log_action(db, current_user.id, "change_request_rejection", "change_request", cr.id, {})
    db.commit()

    return cr


@router.post("/change-requests/{change_request_id}/execute", response_model=ChangeRequestSchema)
def execute_change_request(
    change_request_id: uuid.UUID,
    expected_row_version: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workflow:change_request:execute")),
):
    cr = db.query(ChangeRequest).filter(ChangeRequest.id == change_request_id).first()
    if not cr:
        raise HTTPException(status_code=404, detail="Change request not found")

    if cr.row_version != expected_row_version:
        raise HTTPException(status_code=409, detail="Stale row version")

    if cr.status != ChangeRequestStatus.APPROVED:
        raise HTTPException(
            status_code=400, detail="Change request must be approved before execution"
        )

    # Execution logic
    if cr.change_type == ChangeRequestType.REVERSE_REVIEW_DECISION:
        # Locate original review decision
        orig_dec_id = cr.requested_payload.get("original_decision_id")
        if not orig_dec_id:
            raise HTTPException(
                status_code=400, detail="Missing original_decision_id in requested_payload"
            )

        orig_dec = (
            db.query(ReviewDecision).filter(ReviewDecision.id == uuid.UUID(orig_dec_id)).first()
        )
        if not orig_dec:
            raise HTTPException(status_code=404, detail="Original review decision not found")

        # Determine target choice reversal
        reversal_choice = (
            ReviewDecisionChoice.REJECT
            if orig_dec.decision == ReviewDecisionChoice.APPROVE
            else ReviewDecisionChoice.APPROVE
        )

        # Append a new reversal ReviewDecision
        rev_dec = ReviewDecision(
            target_type=orig_dec.target_type,
            target_id=orig_dec.target_id,
            decision=reversal_choice,
            reason=f"Reversed via ChangeRequest {cr.request_code}: {cr.reason}",
            decided_by=current_user.id,
            previous_state=orig_dec.new_state,
            new_state=orig_dec.previous_state,
        )
        db.add(rev_dec)
        db.commit()
        db.refresh(rev_dec)

        # Create ReviewDecisionReversal link
        reversal_link = ReviewDecisionReversal(
            change_request_id=cr.id,
            original_review_decision_id=orig_dec.id,
            reversal_review_decision_id=rev_dec.id,
            reason=cr.reason,
            created_by=current_user.id,
        )
        db.add(reversal_link)

    else:
        # Reopening or other data modifications are unsupported/deferred to keep execution safe
        raise HTTPException(
            status_code=422,
            detail="Reversal execution is not supported for this change request type",
        )

    cr.status = ChangeRequestStatus.EXECUTED
    cr.executed_by = current_user.id
    cr.executed_at = datetime.now(timezone.utc)
    cr.row_version += 1
    db.commit()
    db.refresh(cr)

    log_audit_event(
        db=db,
        event_name="CHANGE_REQUEST_EXECUTE",
        entity_type="change_request",
        entity_id=cr.id,
        actor_user_id=current_user.id,
    )
    log_action(db, current_user.id, "change_request_execution", "change_request", cr.id, {})
    db.commit()

    return cr
