# Sprint 6 Frontend Workbench UI Implementation Plan

**Task ID:** S6-PR-001  
**Sprint:** Sprint 6 — Frontend App Shell + Workbench UI Foundation  
**Status:** Implementation Plan  

---

## 1. Goal Description

Establish the architectural and component foundation for the Frontend Project Workbench and App Shell within the Valora monorepo. This plan specifies the structure of React components, routing, session governance, and integration points with the backend APIs without implementing operational frontend code.

---

## 2. Proposed Changes

### Frontend Architecture

#### [NEW] [index.css](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/index.css)
- Implement core CSS design system tokens (colors, fonts, layout grids) matching the premium aesthetics required (dark-mode default, vibrant accent colors, subtle gradients).

#### [NEW] [App.tsx](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/App.tsx)
- Define the primary React router structure covering:
  - `/workbench/projects/{project_id}`
  - `/workbench/queue`
  - `/workbench/validation`

#### [NEW] [WorkbenchLayout.tsx](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/layout/WorkbenchLayout.tsx)
- The app shell structure: Header with project status dashboard, Main asset grid pane, expandable right-hand drawer (for sub-panels), and footer action dashboard.

#### [NEW] [AssetGrid.tsx](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/workbench/AssetGrid.tsx)
- A virtualized data table rendering row data according to `AssetLineGridRow` schemas.
- Handles mouse selection, inline focus transitions, and status badge color styling.

#### [NEW] [SubPanels.tsx](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/workbench/SubPanels.tsx)
- Implements right-hand panel view switcher:
  - **Knowledge Panel**: Displays suggestion differences with Apply action.
  - **Price Evidence Panel**: Enforces the **Market Quote ≠ Appraised Price** visual distinction rule.
  - **Lineage Panel**: Visual representation of the reuse history.
  - **Validation Panel**: Lists warnings and blocking errors.

#### [NEW] [SessionContext.tsx](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/context/SessionContext.tsx)
- Manages state for draft updates, session tokens, heartbeats, and local undo/redo stacks (`UndoRedoStackEntry[]`).

---

## 3. Verification Plan

### Automated Tests
- Build verification tests using unit tests for component mounting.
- Storybook integration tests for visual layout sanity.

### Manual Verification
- Render layout mockups inside target web browser instances.
- Verify screen layout reflows dynamically when resizing the window.
