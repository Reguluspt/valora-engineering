# VALORA-FLUENT2-REMEDIATION-001

**Status:** READY FOR DEV — PR-LEVEL IMPLEMENTATION PLANS FROZEN
**Roadmap placement:** OS-G0 — Authority, visual-system & branch reconciliation
**Baseline branch:** `feat/operational-frontend-m365`
**Inventory baseline:** `bc31acd5eeb3742d9ecf0bb66a848704e3405a9a`
**Audit:** `docs/audits/2026-09-22__FRONTEND_ASTRYX_TO_FLUENT2_CODE_INVENTORY.md`

## 1. Goal

Remediate the production frontend from the current Astryx + custom dark/cyan/glassmorphic presentation into the current Microsoft Fluent 2 light product authority without redesigning domain semantics or performing an unnecessary big-bang runtime rewrite.

Completion of this contract is the OS-G0 visual-system gate required before broad new frontend capability is added.

## 2. Authority

Read in this order for this task:

1. `docs/design/VALORA_UIUX_HANDOFF_v2.3.md`
2. `docs/design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md`
3. directly applicable v2.3 addenda / approved visual baselines
4. `docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md`
5. this implementation contract
6. historical Astryx mapping only as low-level evidence, never product authority

Current visual contract:

- Microsoft Fluent 2 light;
- desktop-first;
- Vietnamese-first;
- data-heavy/table-first;
- one primary action/recovery action per context;
- current Cross-product State patterns;
- no dark/cyan/glassmorphic product language.

## 3. Non-goals

This task does not:

- change authoritative business semantics;
- redesign Case State or workflow stages;
- implement missing OS-G1+ capabilities;
- implement ADR-0045 runtime;
- open G9 live provider conformance;
- introduce a standalone NCCQ, Review Queue, Validation Dashboard, KSCL/QC approval or global Audit workflow;
- require adoption of a specific external Fluent React package.

A package may be introduced only if it reduces implementation risk and conforms to repository dependency/security gates. Visual conformance is the acceptance criterion, not package identity.

## 4. Implementation architecture

### 4.1 Semantic token layer

Replace legacy product tokens with a light semantic layer covering at minimum:

- canvas / surface / elevated surface;
- primary/secondary/disabled text;
- subtle/strong border;
- brand/primary action;
- success/warning/error/information;
- focus ring;
- interactive hover/pressed/selected;
- typography;
- spacing/density;
- radius/elevation.

Feature CSS must consume semantic tokens or shared component classes. New hard-coded dark/cyan visual values are forbidden except inside explicit historical/demo-only assets.

### 4.2 Shared primitives

Create/reconcile shared presentation primitives for:

- App shell/navigation;
- Button / icon action;
- Text field / select;
- Table/grid shell;
- Drawer/panel;
- Command bar/tool bar;
- Status/tag/badge;
- Banner/message bar;
- Empty/loading/error/retry/stale/conflict states;
- Skeleton/progress;
- dialog/confirmation surface.

Primitive behavior must preserve accessibility and keyboard/focus semantics.

### 4.3 Astryx retirement rule

Astryx may remain temporarily only while a production surface still imports a required primitive.

Retirement gate:

1. no production TS/TSX imports from `@astryxdesign/*`;
2. no production CSS imports from Astryx;
3. production build/tests pass;
4. screenshot baselines pass;
5. then remove `@astryxdesign/core`, `theme-neutral`, CLI and `AstryxIntegrationProbe`.

Do not remove the packages before the shell replacement is merged.

## 5. Runtime authority corrections required in OS-G0

The following are blockers, not optional cleanup:

- replace stale `UIUX_V23_AUTHORITY.branch = "docs/uiux-handoff-v2.2"` with current v2.3 authority metadata that does not depend on a superseded branch pointer;
- remove legacy Review Queue and standalone Validation Dashboard from production AppShell and production route rendering;
- keep any retained historical/demo Review Queue code behind the demo-only boundary;
- rename the product parent navigation from `Tài liệu OneDrive` to provider-neutral `Không gian tài liệu` or the exact current Vietnamese authority label;
- Microsoft/OneDrive/Word remain integration names inside the workspace, not the product domain name.

## 6. Surface acceptance

### Shell / navigation

Must use Fluent 2 light semantics and current v2.3 IA. No legacy global review/validation entries. Active, hover, focus and disabled states must be distinguishable without cyan-neon styling.

### Shared states

`EmptyState`, `ErrorState`, `LoadingState`, conflict/RBAC/session/API banners must conform to the Cross-product State Contract. Default user-facing copy must be Vietnamese-first. Technical codes/details may be secondary only when current Error Registry permits them.

### Case Overview / Project List

Preserve current projection and navigation behavior. Replace hard-coded dark/cyan visual layer with the current Orchestration Hub/shell baseline.

### Workbench

Preserve data loading, virtualization, drafts, undo/redo, session/RBAC/concurrency and commit behavior.

Replace presentation debt and old S13 IA. The old right-panel arrangement is not grandfathered by implementation history; current approved S13 authority controls the resulting layout.

### NCC Selection

Preserve current API/selection/revision/stale behavior. Remediate table, KPI, drawer, status and action presentation to the approved NCC Selection baseline.

### Document Workspace / M365 Return

Preserve G8 Exchange/revalidation mechanics. Product parent surface must be provider-neutral. Runtime wording must not imply that Word Save or M365 version creates a DocumentRevision. Current Working-change review semantics win over historical explicit-reimport wording.

## 7. Verification gates

Every implementation PR must pass:

- TypeScript/lint/build/unit tests;
- production-bundle isolation check;
- relevant focused tests;
- no new forbidden route/legacy surface;
- no new dark/cyan/glass token introduction;
- no new Astryx import outside the explicit temporary allowlist;
- browser acceptance for affected route;
- screenshot comparison against approved authority baseline when one exists;
- keyboard focus and basic accessibility check for changed interactive components.

Final closeout requires exact-head CI.

## 8. PR / task breakdown

### F2-PR-001 — Runtime authority ratchet and legacy-route removal

**Scope**
- `frontend/src/contracts/valoraV23.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/layout/AppShell.tsx`
- route tests / production bundle tests

**Tasks**
- remove stale v2.2 branch/tip runtime authority marker;
- remove production navigation/rendering for Review Queue and standalone Validation Dashboard;
- preserve demo-only history behind demo boundary if still useful;
- change parent document navigation to provider-neutral label;
- add ratchet tests preventing forbidden routes from becoming production navigation again.

**Acceptance**
- no reachable production Review Queue/Validation Dashboard;
- current v2.3 authority metadata only;
- existing valid project/workbench/overview/NCC/doc routes remain functional.

### F2-PR-002 — Fluent 2 light token and shared-style foundation

**Scope**
- `frontend/src/index.css`
- new shared visual token/component stylesheet/module(s)
- package policy tests

**Tasks**
- introduce light semantic token layer;
- stop product code from depending on legacy dark/cyan/glass variables;
- establish focus/hover/selected/disabled/status semantics;
- add static ratchet for new dark/cyan legacy token usage;
- keep Astryx CSS imports only if still needed by the temporary shell and explicitly allowlisted.

**Acceptance**
- foundation can render both migrated and temporarily unmigrated routes during transition;
- no broad feature visual migration in this PR.

### F2-PR-003 — Shell, login and shared state primitives

**Scope**
- `AppShell.tsx`
- `LoginPage.tsx`, `session.css`
- common state components
- Workbench header/footer/session status shared chrome

**Tasks**
- replace Astryx shell/SideNav production dependency;
- migrate login and global/shared state surfaces;
- Vietnamese-first defaults;
- shared Fluent buttons/fields/message/status primitives.

**Acceptance**
- production shell has no Astryx import;
- auth/project navigation still works;
- common loading/error/empty/conflict/RBAC visuals are light and consistent.

### F2-PR-004 — Case Overview and Project List golden remediation

**Scope**
- Case Overview TSX/CSS
- Project List TSX/CSS

**Tasks**
- migrate visual layer to current orchestration/shell authority;
- preserve Case State projection/next-action behavior;
- add screenshot baselines.

**Acceptance**
- no dark/cyan hard-coded page foundation;
- browser + screenshot acceptance.

### F2-PR-005 — Workbench / current S13 IA remediation

**Scope**
- Workbench layout/grid/toolbar/draft controls/panels/session presentation
- current S13 route only

**Tasks**
- remove old right-panel IA;
- migrate grid, command controls, inline draft visuals and context surfaces;
- preserve virtualization/draft/session/concurrency logic;
- remove QC/approval affordances that are not current product authority.

**Acceptance**
- current S13 approved IA represented;
- no global reviewer workflow introduced;
- focused Workbench behavioral tests remain green;
- screenshot acceptance.

### F2-PR-006 — NCC Selection golden remediation

**Scope**
- NCC Selection page/table/KPIs/drawer/CSS

**Tasks**
- migrate to Fluent table/drawer/status/action semantics;
- preserve selection revision/stale/warning behavior;
- ensure one primary action per context.

**Acceptance**
- focused NCC tests + browser/screenshot acceptance;
- no standalone NCCQ intermediate route.

### F2-PR-007 — Provider-neutral Document Workspace + M365 Return remediation

**Scope**
- `M365WorkspacePage.tsx`, `m365Workspace.css`
- M365 focused tests

**Tasks**
- provider-neutral product parent surface;
- Fluent light workspace/return presentation;
- reconcile user-facing copy with current Working Change Observation semantics;
- preserve Exchange/read/revalidation mechanics.

**Acceptance**
- Word Save/M365 version never presented as authoritative Revision creation;
- M365 remains integration surface;
- current focused tests + screenshot acceptance.

### F2-PR-008 — Residual sweep, visual regression and Astryx retirement

**Scope**
- remaining production UI files;
- package.json/lockfile;
- `AstryxIntegrationProbe.tsx`;
- CI/static visual-system ratchets.

**Tasks**
- remove last production Astryx imports/CSS imports;
- remove Astryx packages/CLI/probe;
- scan production UI for legacy dark/cyan/glass values and forbidden routes;
- run full golden-screen visual regression suite;
- update closeout evidence.

**Acceptance**
- zero production Astryx dependency/import;
- zero reachable legacy global Review Queue/Validation Dashboard;
- all defined golden screenshots accepted;
- exact-head CI green.

## 8.1 Detailed implementation packets

- `VALORA-FLUENT2-F2-PR-001_IMPLEMENTATION_PLAN.md`
- `VALORA-FLUENT2-F2-PR-002_IMPLEMENTATION_PLAN.md`
- `VALORA-FLUENT2-F2-PR-003_IMPLEMENTATION_PLAN.md`
- `VALORA-FLUENT2-F2-PR-004_IMPLEMENTATION_PLAN.md`
- `VALORA-FLUENT2-F2-PR-005_IMPLEMENTATION_PLAN.md`
- `VALORA-FLUENT2-F2-PR-006_IMPLEMENTATION_PLAN.md`
- `VALORA-FLUENT2-F2-PR-007_IMPLEMENTATION_PLAN.md`
- `VALORA-FLUENT2-F2-PR-008_IMPLEMENTATION_PLAN.md`

These packets are the task-ready execution layer. If a packet conflicts with a newer explicit Design Authority decision, the newer authority wins and the packet must be amended before coding.

## 9. Dependency order

```text
F2-PR-001
→ F2-PR-002
→ F2-PR-003
→ F2-PR-004
→ F2-PR-005
→ F2-PR-006
→ F2-PR-007
→ F2-PR-008
```

F2-PR-004 through F2-PR-007 may be parallelized only after F2-PR-003 has established stable shared primitives and only if they do not edit the same shared style foundation.

## 10. Definition of Done

VALORA-FLUENT2-REMEDIATION-001 is complete only when:

1. production runtime authority points to v2.3;
2. legacy global Review Queue/Validation Dashboard are unreachable in production;
3. production shell and shared primitives conform to Fluent 2 light;
4. authority-defined golden surfaces are remediated with screenshot evidence;
5. Workbench uses current S13 IA;
6. Document Workspace is provider-neutral;
7. no new dark/cyan/glassmorphic product styling exists;
8. Astryx production imports/styles/packages are retired or an explicit bounded exception is approved;
9. exact-head CI passes;
10. closeout audit records the final file inventory and any accepted residual debt.
