# F2-PR-005 — Workbench / Current Asset Context IA Remediation

**Status:** READY FOR DEV
**Depends on:** F2-PR-003
**Risk:** HIGH — behavior-preserving presentation/IA migration

## File manifest
**MODIFY:** `WorkbenchLayout.tsx`, `AssetGrid.tsx`, `AssetGridToolbar.tsx`, `InlineDraftCell.tsx`, `UndoRedoControls.tsx`, `WorkbenchRightPanelShell.tsx`, Knowledge/Price/Lineage/Validation panel presentation, Workbench session/chrome as needed, focused tests.
**DO NOT MODIFY unless required by a failing behavior test:** API modules, draft/session hooks, persistence/concurrency contracts.

## Target IA
North-star authority says `Workbench tài sản [Asset Context Drawer theo ngữ cảnh]`. Therefore the current permanently visible four-tab right rail is not retained as a global fixed axis.

Implement an **Asset Context Drawer** opened from the active asset/row context. Contextual sections may expose asset information/knowledge, price evidence, lineage and validation information, but they are contextual content, not four permanent product navigation tabs. Do not create a global Review/Validation workflow.

## Grid
Preserve virtualization calculations, row selection, sorting/filtering, inline draft values, commit callback/version token and existing API behavior. Replace inline presentation styles with semantic table/grid classes. Active/selected rows use Fluent selected-state semantics, not cyan glow. Maintain dense table readability and keyboard-visible focus.

## Draft/edit
Preserve Enter/Escape/blur behavior unless a current test proves otherwise. Translate user-facing draft tooltips/labels to Vietnamese. Dirty state must not be conveyed by color alone. Do not convert local draft into persisted state.

## Toolbar/chrome
Use shared command/field primitives. Search/filter states follow Cross-product State Contract. Remove deprecated QC/approval/assignment affordances. Undo/redo/checkpoint remain only where current draft semantics support them.

## Behavioral lock
Must keep green:
- AssetGrid commit confirmation/callback/version-token tests;
- status-label tests;
- draft/session lifecycle tests;
- RBAC/conflict guards;
- asset-line loading/pagination/selection behavior.

## Acceptance
No fixed legacy four-tab right-panel IA; contextual drawer preserves useful information; no API/domain/CAS changes; visual screenshot for grid + drawer + conflict/draft state; full focused Workbench suite green.
