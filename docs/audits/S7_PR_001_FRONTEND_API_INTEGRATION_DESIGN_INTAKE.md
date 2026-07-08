# S7-PR-001: Sprint 7 Frontend API Integration Design Intake Report

This report documents the design intake and initial architecture alignment for Sprint 7 (**Frontend API Integration + Live Workbench Session**) of Project Valora.

## 1. Scope Verification
- **Allowed Scope**: Plan how the React frontend created in Sprint 6 will interact with the FastAPI backend created in Sprints 1–5. Cover session setup, heartbeats, and session-scoped layout/selection/grid-view/panel-state configurations.
- **Forbidden Scope**: Zero lines of frontend or backend implementation code modified. Zero backend schema adjustments, API clients, or database migrations created.

## 2. API Endpoint Verification Matrix

The following table maps the frontend UI components to the **actual** FastAPI backend endpoints verified in backend modules:

| Frontend UI Context | Action / Trigger | Backend Target API Endpoint | RBAC Permission Required |
| :--- | :--- | :--- | :--- |
| **App Shell Init** | Create session on load | `POST /api/v1/workbench/sessions` | `workbench:open` |
| **App Shell Init** | Session Heartbeat timer | `POST /api/v1/workbench/sessions/{session_id}/heartbeat` | `workbench:edit` |
| **Layout State** | Save layout preferences | `POST /api/v1/workbench/sessions/{session_id}/layout` | `workbench:edit` |
| **Grid Settings** | List saved views | `GET /api/v1/workbench/sessions/{session_id}/grid-view` | `workbench:read` |
| **Grid Settings** | Save custom grid columns/filters | `POST /api/v1/workbench/sessions/{session_id}/grid-view` | `workbench:edit` |
| **Active Row** | Save current active row selection | `POST /api/v1/workbench/sessions/{session_id}/selection` | `workbench:edit` |
| **Active Row** | Get current active selections | `GET /api/v1/workbench/sessions/{session_id}/selection` | `workbench:read` |
| **Inline Editing** | Write draft cell change | `POST /api/v1/workbench/sessions/{session_id}/inline-edit` | `workbench:edit` |
| **Inline Editing** | List draft edits | `GET /api/v1/workbench/sessions/{session_id}/inline-edits` | `workbench:read` |
| **Draft Session** | Trigger autosave checkpoint | `POST /api/v1/workbench/sessions/{session_id}/checkpoint` | `workbench:edit` |
| **Undo Stack** | Revert last draft change | `POST /api/v1/workbench/sessions/{session_id}/undo` | `workbench:undo_redo` |
| **Redo Stack** | Reapply undone draft change | `POST /api/v1/workbench/sessions/{session_id}/redo` | `workbench:undo_redo` |
| **Drawer Settings** | Save right panel configuration | `POST /api/v1/workbench/sessions/{session_id}/panel-state` | `workbench:edit` |
| **Drawer Settings** | Get right panel configuration | `GET /api/v1/workbench/sessions/{session_id}/panel-state` | `workbench:read` |
| **Notification** | List session notifications | `GET /api/v1/workbench/sessions/{session_id}/notifications` | `workbench:read` |

---

## 3. Integration Gaps & Deferred Endpoints

The following endpoints specified in the original design book are **absent** from the actual backend implementation (`backend/app/api/workbench.py`) and are classified as **non-blocking integration gaps (deferred for Sprint 7)**:

1. **`GET /api/v1/workbench/projects/{project_id}/asset-lines`** (Live grid rows retrieval):
   - **Resolution**: Live asset data loading is deferred. The frontend will continue using the high-performance local virtualized mock rows grid with session metadata synchronization.
2. **`GET /api/v1/workbench/asset-lines/{line_id}/context`** (Live drawer context panels fetch):
   - **Resolution**: Deferred. Sub-panel details (Knowledge, Price Evidence, Lineage, Validation) will render from high-fidelity local mock context data keyed to selected rows.
3. **`POST /api/v1/workbench/inline-edits/{draft_id}/commit`** (Draft commit to master records):
   - **Resolution**: Deferred. Saving cells creates local `InlineEditDraft` records on the backend. Official data mutations to `ProjectAssetLine` or valuation data are blocked.

---

## 4. Concurrency and Security Hardening Guardrails
- **RBAC Strictness**: The frontend must never bypass backend permissions (e.g. Viewer permissions block mutations, triggering HTTP `403 Forbidden` from the server).
- **Stale Check Verification**: HEARTBEAT and edit operations enforce optimistic locking checks. Mismatches return HTTP `409 Conflict`.
- **Workflow & Audit Requirements**: Mutations log user activities to `UserActionLog` on the backend. Workflow transitions remain blocked by unresolved validation issues; session-scoped layout, grid-view, selection, and panel-state saves must still respect backend RBAC and row_version checks.

---

## 5. Final Result
- **Result:** PASS WITH FIXES
- **Recommendation:** Proceed to implementation planning under the corrected endpoint routes.

