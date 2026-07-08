# S4-PR-001: Sprint 4 Workflow + Workbench Design Intake Report

This report documents the design intake and initial architecture alignment for Sprint 4 (Workflow + Workbench) of Project Valora.

## Current Working Branch and Status
- **Branch:** `s3-pr-011-sprint-3-final-acceptance` (ready for merging / branch creation)
- **Status:** Complete Sprint 3 baseline verified. All tests passing.

## Sprint 4 Scope Summary
- **Workflow Context:** Models and APIs tracking project states, tasks, gates, rules, decisions, and change logs.
- **Workbench Context:** Layout specifications, grids, panel states, selection states, inline edit drafts, checkpoints, and undo/redo stacks.
- **Change Request Context:** Reopening projects, reversing review decisions, and editing locked datasets.

## Models to Implement

### Workflow Context
1. `WorkflowDefinition` (`workflow_definitions`)
2. `WorkflowInstance` (`workflow_instances`)
3. `WorkflowTransition` (`workflow_transitions`)
4. `WorkflowTask` (`workflow_tasks`)
5. `ReviewDecision` (`review_decisions`)
6. `ApprovalGate` (`approval_gates`)
7. `ValidationRule` (`validation_rules`)
8. `ValidationIssue` (`validation_issues`)
9. `UserActionLog` (`user_action_logs`)

### Workbench Context
1. `WorkbenchSession` (`workbench_sessions`)
2. `WorkbenchLayout` (`workbench_layouts`)
3. `AssetGridView` (`asset_grid_views`)
4. `WorkbenchSelection` (`workbench_selections`)
5. `InlineEditDraft` (`inline_edit_drafts`)
6. `AutosaveCheckpoint` (`autosave_checkpoints`)
7. `UndoRedoStackEntry` (`undo_redo_stack_entries`)
8. `PanelState` (`panel_states`)
9. `ReviewQueueView` (`review_queue_views`)
10. `WorkbenchNotification` (`workbench_notifications`)

### Change Request Context
1. `ChangeRequest` (`change_requests`)
2. `ReviewDecisionReversal` (`review_decision_reversals`)

## API Endpoints Expected

### Workflow API
- `POST /api/v1/workflow/instances`
- `GET /api/v1/workflow/instances/{id}`
- `POST /api/v1/workflow/instances/{id}/transition`
- `GET /api/v1/workflow/tasks`
- `PATCH /api/v1/workflow/tasks/{id}`
- `POST /api/v1/workflow/decisions`
- `GET /api/v1/workflow/decisions/{id}`
- `GET /api/v1/workflow/validation-rules`
- `GET /api/v1/workflow/validation-issues`
- `POST /api/v1/workflow/change-requests`
- `POST /api/v1/workflow/change-requests/{id}/approve`
- `POST /api/v1/workflow/change-requests/{id}/execute`

### Workbench API
- `POST /api/v1/workbench/sessions`
- `GET /api/v1/workbench/sessions/{id}`
- `POST /api/v1/workbench/sessions/{id}/heartbeat`
- `POST /api/v1/workbench/sessions/{id}/layout`
- `GET /api/v1/workbench/sessions/{id}/grid-view`
- `POST /api/v1/workbench/sessions/{id}/selection`
- `POST /api/v1/workbench/sessions/{id}/inline-edit`
- `POST /api/v1/workbench/sessions/{id}/checkpoint`
- `POST /api/v1/workbench/sessions/{id}/undo`
- `POST /api/v1/workbench/sessions/{id}/redo`

## RBAC Permissions
- `workflow:definition:manage`
- `workflow:instance:manage`
- `workflow:task:assign`
- `workflow:task:complete`
- `workflow:decision:create`
- `workflow:change_request:create`
- `workflow:change_request:approve`
- `workflow:change_request:execute`
- `workbench:session:create`
- `workbench:session:modify`

## Audit Events
- `WORKFLOW_INSTANCE_CREATE`
- `WORKFLOW_TRANSITION`
- `WORKFLOW_TASK_COMPLETE`
- `REVIEW_DECISION_RECORD`
- `CHANGE_REQUEST_CREATE`
- `CHANGE_REQUEST_EXECUTE`
- `WORKBENCH_SESSION_START`
- `WORKBENCH_INLINE_EDIT`

## Concurrency and Row Versioning
- Row versioning checks enforced on:
  - `WorkflowInstance`
  - `WorkflowTask`
  - `WorkbenchSession`
  - `InlineEditDraft`
  - `ChangeRequest`

## Reversal and Undo/Redo Rules
- **Undo/Redo:** Modifies session-scoped draft state (`InlineEditDraft` or `AutosaveCheckpoint`). Never reverses finalized database changes or official specs.
- **Reversal:** ChangeRequest execution triggers `ReviewDecisionReversal` linking, keeping original `ReviewDecision` records intact (append-only audit trail).

## Risks and Ambiguities
- **SQLite vs PostgreSQL:** JSONB column properties (`WorkflowTransition.guard_expression`, `WorkbenchSelection.selected_target_ids`) must use standard SQLAlchemy JSON columns to remain testable in SQLite in-memory databases.

## Final Result
- **Result:** PASS
