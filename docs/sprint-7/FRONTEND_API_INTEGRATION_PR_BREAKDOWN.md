# Sprint 7 Frontend API Integration PR Breakdown

**Task ID:** S7-PR-001  
**Sprint:** Sprint 7 — Frontend API Integration + Live Workbench Session  
**Status:** PR Sequencing Plan (Aligned with S4 Endpoints)  

---

## 1. Sequencing Strategy
To ensure incrementally reviewable updates, the integration must be divided into logical PR units.

---

## 2. PR Matrix

### S7-PR-002: API Client + Environment + Health/OpenAPI Smoke
- **Scope**:
  - Central fetch API client.
  - Environment variable setups for `VITE_API_BASE_URL`.
  - Smoke checks for OpenAPI schema and health status.

### S7-PR-003: Workbench Session + Heartbeat
- **Scope**:
  - Session initialization on project load (`/sessions`).
  - Active session heartbeat updates (`/sessions/{session_id}/heartbeat`).
  - Stale row version conflict alerts.

### S7-PR-004: Session-scoped Layout / Grid View / Selection / Panel State Integration
- **Scope**:
  - Wire workspace layouts (`/layout`).
  - Save current column views and filters (`/grid-view`).
  - Cache grid selections (`/selection`).
  - Sync drawer configuration state (`/panel-state`).
  - Retrieve notifications (`/notifications`).

### S7-PR-005: Inline Draft / Checkpoint / Undo / Redo Metadata Sync
- **Scope**:
  - Persist local edits on change (`/inline-edit` and `/inline-edits`).
  - Autosave checkpoint creation (`/checkpoint`).
  - Stack undo and redo routing updates (`/undo` and `/redo`).

### S7-PR-006: RBAC / 409 Conflict UI Hardening
- **Scope**:
  - Error routing interceptors for 403 Forbidden statuses.
  - Role-gated visual lockouts.
  - Conflict warning banner on 409 responses.

### S7-PR-007: Sprint 7 Final Acceptance
- **Scope**:
  - Complete regression coverage.
  - Verify zero changes to database models or migrations.
