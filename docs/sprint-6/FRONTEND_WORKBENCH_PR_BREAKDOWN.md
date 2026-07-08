# Sprint 6 Frontend Workbench PR Breakdown

**Task ID:** S6-PR-001  
**Sprint:** Sprint 6 — Frontend App Shell + Workbench UI Foundation  
**Status:** PR Sequencing Plan  

---

## 1. Sequencing Strategy
To align with Project Valora's PR rules, the frontend implementation must be split into small, independently reviewable PRs. Each PR must include mock-data rendering tests and verify security compliance.

---

## 2. PR Matrix

### PR 1: App Shell, Design System Tokens & Base Layout
- **Scope**:
  - CSS tokens in `index.css` (color palette, spacing, typography).
  - Main app shell scaffolding: Sidebar, layout headers, drawer boundaries.
- **Reference**: `06_WORKBENCH/01_WORKBENCH_OVERVIEW.md`
- **Verification**: Basic render tests verifying container structures.

### PR 2: Virtualized Asset Grid Core Component
- **Scope**:
  - Virtualized table list implementation rendering rows for `AssetLineGridRow`.
  - Column styling, sorting triggers, and selection handlers.
- **Reference**: `06_WORKBENCH/02_ASSET_GRID.md`
- **Verification**: Virtualization benchmark tests under high row count counts (e.g. 500+ mock rows).

### PR 3: Asset Details Context Side Drawer & Panels
- **Scope**:
  - Knowledge panel differences compare UI.
  - Price Evidence panel rendering quotes separate from appraised values.
  - Lineage path viewer.
  - Validation warning components.
- **Reference**: `06_WORKBENCH/03_KNOWLEDGE_PANEL.md`, `06_WORKBENCH/04_PRICE_EVIDENCE_PANEL.md`, `06_WORKBENCH/05_LINEAGE_VIEWER.md`
- **Verification**: Tests checking that click events on rows trigger detail updates.

### PR 4: Inline Edit Drafts, Checkpoints & Undo/Redo Engine
- **Scope**:
  - Context reducer for `UndoRedoStackEntry`.
  - Global hotkeys listener integration (Ctrl+S, Ctrl+Z, Ctrl+Y, Arrow navigation).
- **Reference**: `06_WORKBENCH/08_AUTOSAVE_UNDO_REDO.md`, `06_WORKBENCH/11_KEYBOARD_SHORTCUTS.md`
- **Verification**: Session unit tests ensuring undo and redo actions restore the correct history values.

### PR 5: Review Queue Dashboard
- **Scope**:
  - Review queue listing filter dashboard.
  - Role-based interaction restrictions (e.g. read-only views for Viewers).
- **Reference**: `06_WORKBENCH/06_REVIEW_QUEUE.md`, `13_SECURITY/06_WORKFLOW_WORKBENCH_SECURITY.md`
- **Verification**: Permission mock tests validating button lockouts based on user scopes.


