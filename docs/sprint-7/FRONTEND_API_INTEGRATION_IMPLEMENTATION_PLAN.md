# Sprint 7 Frontend API Integration Implementation Plan

**Task ID:** S7-PR-001  
**Sprint:** Sprint 7 — Frontend API Integration + Live Workbench Session  
**Status:** Implementation Plan (Aligned with S4 Endpoints)  

---

## 1. Goal Description

Connect the React-based Workbench UI created in Sprint 6 to the actual live backend APIs built in Sprints 1–5. This plan outlines environment configuration, API client abstraction, session state management, error handling, and testing strategies.

---

## 2. Technical Design Areas

### 2.1 API Client Boundary & Environment Configuration
- Create a central client (e.g. `src/api/client.ts`) utilizing fetch.
- Define a base API URL mapping: `VITE_API_BASE_URL` in `.env.development` defaulting to `http://localhost:8000`.

### 2.2 Workbench Session Management & Heartbeats
- On route initialization (`/workbench/projects/:projectId`), dispatch a `POST /api/v1/workbench/sessions` call.
- Start a `setInterval` timer (every 30 seconds) calling `POST /api/v1/workbench/sessions/{session_id}/heartbeat` enforcing optimistic locking row versions to maintain session locks.

### 2.3 Session-Scoped Layout, Selection, Grid-view & Panel State
- Integrate state persistence with the live backend:
  - Save workspace user layout coordinates to `/sessions/{session_id}/layout`.
  - Fetch and save current grid sorting/filters config to `/sessions/{session_id}/grid-view`.
  - Cache grid row selections to `/sessions/{session_id}/selection`.
  - Retain drawer dimensions to `/sessions/{session_id}/panel-state`.
  - Fetch session notifications from `/sessions/{session_id}/notifications`.

### 2.4 Inline Edits, Checkpoints & Undo/Redo Integration
- Post draft cell updates to `POST /api/v1/workbench/sessions/{session_id}/inline-edit`.
- Sync list of active drafts from `GET /api/v1/workbench/sessions/{session_id}/inline-edits`.
- Trigger autosave checkpoints to `POST /api/v1/workbench/sessions/{session_id}/checkpoint`.
- Dispatch undo and redo events to `/sessions/{session_id}/undo` and `/sessions/{session_id}/redo` respectively.

### 2.5 Conflict and Access Violation UI States
- **Optimistic Lock Conflict**: If a `409 Conflict` status is returned from the heartbeat or edit API, pause grid editing and display a merge conflict modal.
- **RBAC Lock**: Render custom `RoleGateNotice` panels and lock related buttons if a `403 Forbidden` response is returned.

---

## 3. Integration Gaps & Deferred Endpoints

The following features do not have matching backend API endpoints and are deferred for Sprint 7:
1. **Live Grid Asset Loading**: Renders via local virtualized mock rows grid with session metadata synchronization.
2. **Sub-panel Details Context Fetching**: Context panels (Knowledge suggestions, price evidence quotes, lineage timesteps) populate from high-fidelity local mock data.
3. **Commit Draft Edits**: Marked as deferred and forbidden. Official mutations to `ProjectAssetLine` or valuation data are blocked.

---

## 4. Concurrency and Security Hardening Guardrails
- **RBAC Strictness**: The frontend must never bypass backend permissions (Viewer permissions block mutations, triggering HTTP `403 Forbidden` from the server).
- **Stale Check Verification**: Heartbeat and edit operations enforce optimistic locking checks. Mismatches return HTTP `409 Conflict`.
- **Workflow & Audit Requirements**: Mutations log user activities to `UserActionLog` on the backend. Workflow transitions remain blocked by unresolved validation issues; session-scoped layout, grid-view, selection, and panel-state saves must still respect backend RBAC and row_version checks.

---

## 5. Verification Plan

### Automated Tests
- Mock network request responses using MSW (Mock Service Worker) to test loading, error, conflict, and auth exception states in isolation.

### Manual Verification
- Launch local backend and frontend development servers.
- Inspect network logs in the developer browser console to confirm correct endpoint routes, heartbeats, and parameter payloads.

