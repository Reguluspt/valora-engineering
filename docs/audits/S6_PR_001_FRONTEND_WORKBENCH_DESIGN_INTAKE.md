# Sprint 6 Frontend Workbench UI Design Intake Audit

**Task ID:** S6-PR-001  
**Sprint:** Sprint 6 — Frontend App Shell + Workbench UI Foundation  
**Status:** Design Intake & Implementation Planning Only  
**Result:** PASS

---

## 1. Executive Summary

This audit assesses the design specifications, API contracts, security policies, and user interaction rules for Sprint 6 of Project Valora. The focus is exclusively on **design ingestion and implementation planning** for the Frontend App Shell and the Workbench UI Foundation, strictly complying with the forbidden scopes (no implementation code changed).

All primary sources from the Design Reference Package (including the completed `valora-design-book-v1.2-delta-workflow-workbench-completed.zip` package and the `06_v1.2-zeta-ai-governance-security-hardening-completed` package) have been reviewed.

---

## 2. Scope Verification

### 2.1 Allowed Scope for Sprint 6 Intake
- **Frontend Planning**: Architecture of the React-based Project Workbench layout, Asset Grid with virtualization/sorting/filtering/searching, Right-side contextual panels (Knowledge, Price Evidence, Lineage, Validation), Review Queue, and layout/panel state persistence.
- **Security Hardening Planning**: Design map for React sessions, token management, temporary permission overrides, and organization tenant isolation checks.
- **Audit Logging Planning**: Alignment of frontend user events (inline edit draft saves, commits, overrides, undo/redo) to downstream audit tables without implementing backend writers.

### 2.2 Forbidden Scope Enforced
- **Zero implementation changes**: No backend routers, models, migrations, or database tables created or modified.
- **Zero frontend code written**: React code, styling, or component implementations are deferred to execution PRs.
- **Zero mock/dummy domains**: No external API integrations, AI provider integrations, OCR triggers, or rendering libraries added.

---

## 3. Design Intake Traceability Matrix

The following table maps the requirements from the Design Book to the implementation plans:

| Design Section / Spec | Requirement Summary | Implementation Plan Focus |
| :--- | :--- | :--- |
| **06_WORKBENCH/01_WORKBENCH_OVERVIEW.md** | Workbench layout components: Header, status bar, Asset Grid, right panels, footer actions, bulk actions. | Page shell layout structure in React using Astryx Design System guidelines. |
| **06_WORKBENCH/02_ASSET_GRID.md** | Grid columns (`line_no`, `raw_name`, `appraised_price`, status enums) and row states (`raw` through `excluded`). Support sorting, pagination (limit 200), filtering, inline edits. | React Grid virtualized implementation using Astryx grid wrappers. Interactive cell states for drafts. |
| **06_WORKBENCH/03_KNOWLEDGE_PANEL.md** | Current spec versions, suggested specifications, confidence scores, and actions (Apply to Draft, Compare). | Knowledge panel container. Diff presentation logic for suggested vs. current specs. |
| **06_WORKBENCH/04_PRICE_EVIDENCE_PANEL.md** | Displays QuoteBatch, QuoteLines, AppraisedPriceDecision. **Market Quote ≠ Appraised Price** visual split rule. | Evidence comparison layout. Appraised price edit form with required rationale block. |
| **06_WORKBENCH/05_LINEAGE_VIEWER.md** | Lineage path `[original_source → direct_source → current_project]`. Read-only. | Lineage chain representation using a horizontal stepper or timeline component. |
| **06_WORKBENCH/06_REVIEW_QUEUE.md** | Review types, priorities, claim workflows. Concurrency locks (`row_version`). | Queue list filter/claim interface with custom validation headers. |
| **06_WORKBENCH/07_VALIDATION_AND_ISSUES.md** | Severity ranks (`info` through `blocking`). Category mapping. | Banner alert components and filtering tabs for Asset Grid based on issue severity. |
| **06_WORKBENCH/08_AUTOSAVE_UNDO_REDO.md** | Draft-only autosave, undo/redo session stacks, reload on conflict. | React Context session reducer to manage `UndoRedoStackEntry` states. |
| **06_WORKBENCH/11_KEYBOARD_SHORTCUTS.md** | Grid navigation (Arrows, Enter, Tab) and action triggers (`A`, `R`, `D`, `M`, `V`, `L`, `E`, `K`, `P`). | Event listener integration hooks for global and component-focused hotkeys. |

---

## 4. API Schema & Permission Compliance Checklist

### 4.1 Schema Mappings Verified
- **`AssetLineGridRow`**: Contains essential validation and review fields, including `row_version` for concurrent modification checking.
- **`AssetLineContextResponse`**: Fully structured JSON matching the sub-panel inputs (no generic empty objects).
- **`InlineEditDraftRequest`**: Transfers edits as drafts referencing `base_row_version`.
- **`BulkActionPreviewResponse`**: Returns tokens and eligible/skipped indices.

### 4.2 Security & RBAC Enforcement Plan
- All UI actions mapped to specific server permissions (e.g. `workbench:commit_edit`, `workbench:undo_redo`).
- **Viewer**: Read-only grid. No inline edit input activation.
- **Appraiser**: Inline editing active. Cannot trigger workflow transitions (e.g. QC completion) if blocking validation issues exist.
- **Reviewer**: Full access to approval, rejection, and gate overrides.

---

## 5. Audit Conclusion

The intake phase for Sprint 6 is complete and satisfies all Valora repository rules, design specifications, and security policies.

**Final Recommendation:** Proceed to engineering execution plans.
