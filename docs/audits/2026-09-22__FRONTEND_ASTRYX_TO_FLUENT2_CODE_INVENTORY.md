# 2026-09-22 — Frontend Astryx → Fluent 2 Code Inventory

**Status:** COMPLETE — CODE-LEVEL REMEDIATION INVENTORY
**Branch:** `feat/operational-frontend-m365` / Draft PR #32
**Audited head:** `bc31acd5eeb3742d9ecf0bb66a848704e3405a9a`
**Scope:** production frontend visual/runtime code, routing and direct design-system dependencies.
**Authority:** UI/UX Handoff v2.3 + Authority Index + applicable addenda for product/visual semantics; Unified Roadmap v2.3 for sequencing.

> **2026-09-23 current disposition:** This is a code-inventory snapshot at audited head `bc31acd…`, not current branch state. F2-PR-001/#34, F2-PR-002/#36 and F2-PR-003/#38 subsequently merged on integration head `d725bbc…` (CI #454 SUCCESS), removing the legacy global Review Queue/Validation Dashboard production routes, establishing Fluent 2 light token/shared-style foundations, and replacing production Astryx shell/login/shared-state TS/TSX usage. Use `VALORA-FLUENT2-REMEDIATION-001.md` plus F2-PR-004…008 plans for current residual debt.

## 1. Executive finding

The current frontend is not simply “an Astryx UI.” It is a mixed stack:

1. Astryx packages/global styles are loaded at application level;
2. Astryx `AppShell` / `SideNav` primitives are used directly in production navigation;
3. most feature surfaces are custom React + dark/cyan CSS or inline styles;
4. legacy Review Queue and standalone Validation Dashboard remain reachable from production routing;
5. a stale runtime authority pointer still references `docs/uiux-handoff-v2.2`.

Therefore remediation must be dependency-ordered rather than a package-only replacement.

## 2. Inventory summary

Live frontend tree contains 123 files. The production UI inventory contains 42 non-test `.tsx`/`.css` files.

Direct Astryx coupling:

- `frontend/package.json` / lockfile — `@astryxdesign/core`, `@astryxdesign/theme-neutral`, CLI.
- `frontend/src/index.css` — imports Astryx reset, core and neutral theme.
- `frontend/src/components/layout/AppShell.tsx` — imports Astryx AppShell/SideNav primitives.
- `frontend/src/components/common/AstryxIntegrationProbe.tsx` — historical integration probe.

Custom styling debt is broader than direct Astryx coupling:

- `index.css` defines dark `--bg-primary/#0b0c10`, cyan accents, glass shadows/background.
- dedicated dark/cyan CSS exists in login, Project List, Case Overview, NCC Selection and M365 Workspace.
- at least 23 production UI files use inline style objects, especially Workbench/grid/panel/review/state code.
- legacy routes `/workbench/queue` and `/workbench/validation` remain production reachable.
- `frontend/src/contracts/valoraV23.ts` still declares `branch: "docs/uiux-handoff-v2.2"`.

## 3. File-level disposition

### P0 — authority, routing and dependency ratchet

| File | Finding | Required disposition |
|---|---|---|
| `frontend/src/contracts/valoraV23.ts` | stale v2.2 branch/tip authority metadata; legacy production route constants | REPLACE stale authority metadata with v2.3 canonical references; deprecate/remove production legacy routes |
| `frontend/src/App.tsx` | renders Review Queue and standalone Validation Dashboard routes | REMOVE from production routing; preserve only explicitly isolated demo/history if needed |
| `frontend/src/components/layout/AppShell.tsx` | Astryx AppShell/SideNav; dark/cyan logo; links to legacy surfaces; “Tài liệu OneDrive” provider-specific parent label | REPLACE shell/nav presentation; provider-neutral `Không gian tài liệu`; remove legacy nav |
| `frontend/src/index.css` | Astryx global imports + dark/cyan/glass token foundation | REPLACE with Fluent 2 light semantic-token foundation |
| `frontend/package.json` / lockfile | Astryx runtime + CLI dependencies | KEEP temporarily during migration; REMOVE only after last production import/style dependency is gone |
| `AstryxIntegrationProbe.tsx` | historical compile probe | DELETE after Astryx retirement gate |

### P1 — shared shell/state primitives

| Files | Finding | Required disposition |
|---|---|---|
| `WorkbenchHeader.tsx`, `WorkbenchFooter.tsx`, `WorkbenchLayout.tsx` | legacy action/status language and extensive inline styling | REMAP to shared Fluent tokens/components; remove QC/approval-style affordances that are no longer product authority |
| `WorkbenchRightPanelShell.tsx` | old four-tab right-panel IA + cyan tab styling | REPLACE according to current S13 authority; do not preserve old IA merely because code exists |
| `ApiErrorBanner.tsx`, `ConflictWarning.tsx`, `EmptyState.tsx`, `ErrorState.tsx`, `LoadingState.tsx`, `RbacLockNotice.tsx`, `StatusBadge.tsx` | custom/inline states; some English defaults and technical wording | REMAP to Cross-product State Contract + Vietnamese-first Fluent patterns |
| `WorkbenchSessionStatus.tsx` | custom dark banners/status strips | REMAP to shared state/status primitives |
| `AssetGridToolbar.tsx`, `InlineDraftCell.tsx`, `UndoRedoControls.tsx` | inline dark inputs/actions | REMAP to shared form/command primitives |

### P2 — active product surfaces

| Surface / files | Finding | Required disposition |
|---|---|---|
| Login: `LoginPage.tsx`, `session.css` | dark grid/cyan login treatment | REPLACE with Fluent 2 light authentication surface |
| Project List: `ProjectListPage.tsx`, `projectList.css` | dark/cyan list; provider/workbench legacy copy exists | REMAP to current shell/navigation baseline |
| Case Overview: `CaseOverviewPage.tsx`, `caseOverview.css` | heavily hard-coded dark/cyan orchestration page | REPLACE visual layer against Orchestration Hub authority; preserve data/projection semantics |
| Workbench: `AssetGrid.tsx` + panels/drafts/session files | 45+ inline style blocks in grid alone; old status vocabulary/IA mixed with current runtime | REMAP incrementally; preserve API/concurrency/draft behavior, replace presentation/IA only |
| NCC Selection: `NccSelectionPage/Table/Drawer/Kpis.tsx`, `nccSelection.css` | dark token fallbacks and cyan primary/focus patterns | REPLACE visual layer against NCC Selection baseline |
| Document Workspace/M365: `M365WorkspacePage.tsx`, `m365Workspace.css` | provider-branded parent surface, dark/cyan styling; explicit re-import copy remains in runtime | REMAP parent surface to provider-neutral Document Workspace and current Working-change review semantics; preserve Exchange mechanics |
| M365 Return | embedded in `M365WorkspacePage.tsx` | dark full-page callback | REMAP to current M365 Return/Revalidation visual authority |

No dedicated production NCCQ route/component was found. NCCQ remains golden/reference evidence and must not be reintroduced as a standalone intermediate workflow.

### P3 — remove/isolate legacy product surfaces

| Files | Disposition |
|---|---|
| `ReviewQueueDashboard.tsx`, `ReviewActionPanel.tsx`, `RoleGateNotice.tsx`, associated production test | REMOVE from production path; if retained for history/demo, move behind demo-only build boundary |
| legacy Validation Dashboard branch in `App.tsx` | REMOVE standalone route |
| `DemoReviewQueuePage.tsx` + demo fixtures | MAY remain demo-only if production bundle assertion proves isolation |

Local domain-specific review surfaces remain allowed where current authority explicitly defines them; this disposition only removes the legacy global reviewer axis.

## 4. Migration invariants

- No change to domain facts, API mutation semantics, tenant/RBAC, CAS/versioning or audit lineage merely for visual remediation.
- Fluent 2 conformance is a visual/interaction contract, not a requirement to adopt a particular package in one step.
- Retained Astryx primitive is temporary implementation detail only and must not leak Astryx visual language.
- Dark/cyan/glassmorphic tokens may not remain as fallback product styling.
- Production route removal must not delete historical evidence or demo-only fixtures unless separately justified.
- Golden-screen acceptance requires screenshot/visual-regression evidence.
- Vietnamese-first copy and Cross-product State semantics apply to shared states.

## 5. Recommended migration order

```text
P0 authority/routing ratchet
→ Fluent semantic-token + shared primitive foundation
→ App shell/auth/shared states
→ Case Overview + Project List
→ Workbench / current S13 IA
→ NCC Selection
→ provider-neutral Document Workspace + M365 Return
→ residual surface sweep
→ screenshot regression + Astryx dependency retirement
```

This sequence closes the highest-leverage shared dependencies before feature-by-feature visual migration and avoids a big-bang rewrite.
