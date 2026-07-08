# Sprint 4 Implementation Plan: Workflow + Workbench

This plan lays out the development strategy for implementing Project Workflow, Workbench UX logic, and Change Requests.

## Architectural Objectives
1. **State Isolation:** Ensure draft workbench states remain isolated from the official master database.
2. **Deterministic Rules:** Validate all project line and pricing rules before triggering approval gateways.
3. **Optimistic Locking:** Utilize `row_version` properties to prevent overwriting updates.
4. **Append-Only History:** Decisions and reversals remain append-only, preserving the data lineage.

## Proposed Component Changes

### Component 1: Workflow Engine
- **Models:**
  - `WorkflowDefinition`, `WorkflowInstance`, `WorkflowTransition`, `WorkflowTask`
  - `ReviewDecision`, `ApprovalGate`, `ValidationRule`, `ValidationIssue`
- **APIs:**
  - Standard transition execution, review logging, and gate queries.
- **RBAC:**
  - Restricts transition actions to users holding specific workflow roles.

### Component 2: Workbench Manager
- **Models:**
  - `WorkbenchSession`, `WorkbenchLayout`, `AssetGridView`
  - `WorkbenchSelection`, `InlineEditDraft`, `AutosaveCheckpoint`, `UndoRedoStackEntry`
- **APIs:**
  - Autocomplete filters, session states, layouts, and draft check-pointing.
- **Rules:**
  - Undo and redo entry manipulations are locked to draft tables.

### Component 3: Change Control
- **Models:**
  - `ChangeRequest`, `ReviewDecisionReversal`
- **APIs:**
  - Create change requests, review approvals, and execute reversal payload transitions.
- **Rules:**
  - Project reopens require a valid ChangeRequest justification.

## Verification Strategy
- **Integration Tests:** Test transitions, validation rule failures, and 409 conflict checks.
- **RBAC Validation:** Assert unauthorized users are blocked from transition endpoints.
