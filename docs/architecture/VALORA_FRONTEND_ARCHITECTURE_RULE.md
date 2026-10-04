# VALORA Frontend Architecture Rule

**Status:** APPROVED BY PRODUCT OWNER

**Decision date:** 2026-10-04

**Project:** Valora

**Scope:** Frontend architecture / React + Fluent 2 presentation layer

**Applies to:** New frontend implementation and incremental remediation of existing frontend code

**Architecture context:** Linux Server + React/Fluent 2 + WinUI 3/WebView2 Windows Client

---

## 1. Executive decision

Valora adopts the following frontend architecture as the official layering rule:

```text
Design tokens
      ↓
Fluent primitives
      ↓
Valora shared components
      ↓
Feature components
      ↓
Screens
```

The purpose of this rule is to keep the user interface highly customizable without coupling visual changes to domain authority, backend behavior, or the Windows native shell.

The architecture must make large future UI/UX redesigns possible primarily through changes to design tokens and shared presentation components instead of requiring broad rewrites across individual screens.

---

## 2. Architectural goals

The Frontend Architecture Rule exists to achieve the following goals:

1. Keep Valora's visual system centralized and replaceable.
2. Prevent feature teams from creating isolated visual conventions.
3. Preserve Fluent 2 as the primitive UI foundation while allowing Valora-specific design language above it.
4. Separate presentation concerns from domain/business authority.
5. Reduce the cost and risk of future UI/UX redesigns.
6. Allow React UI to remain reusable inside the Windows WebView2 client and other future presentation surfaces.
7. Support incremental migration instead of forcing a high-risk frontend rewrite.
8. Maintain deterministic loading, empty, denied, stale, conflict, uncertain and error states across the product.

---

## 3. Layer model

### 3.1 Design tokens

Design tokens are the lowest Valora-owned visual authority layer.

Typical responsibilities include:

- color;
- semantic color roles;
- typography;
- spacing;
- radius;
- density;
- elevation;
- borders;
- layout constants;
- state visuals;
- focus/interaction states;
- responsive breakpoints where appropriate.

Feature code must not introduce arbitrary visual constants when an equivalent design token exists.

Example conceptual structure:

```text
frontend/
  design/
    tokens/
      color
      typography
      spacing
      radius
      density
      elevation
      semantic-state
```

A future corporate rebrand, density change, typography change or visual refresh should preferentially be implemented at this layer.

---

### 3.2 Fluent primitives

Fluent 2 remains the primitive component foundation for the React frontend.

Examples:

- Button;
- Input;
- Dialog;
- Menu;
- Tooltip;
- Tab;
- Checkbox;
- Spinner;
- primitive layout and interaction components.

Fluent primitives provide accessibility and interaction foundations.

Feature code should not bypass Fluent primitives by recreating equivalent primitive controls unless there is an accepted technical reason.

Valora-specific semantics must normally be introduced above this layer rather than by forking the primitive library.

---

### 3.3 Valora shared components

Valora shared components form the reusable product presentation system.

Examples may include:

```text
ValoraButton
ValoraDataGrid
ValoraCommandBar
ValoraDrawer
ValoraStatusBadge
ValoraStatePanel
ValoraEmptyState
ValoraErrorState
ValoraLoadingState
ValoraConfirmDialog
ValoraPageHeader
ValoraSection
ValoraSplitPane
ValoraEvidencePanel
```

This layer may standardize:

- Valora visual language;
- composition patterns;
- common interaction behavior;
- accessibility conventions;
- shared loading/error/empty patterns;
- standard confirmation and recovery UX;
- responsive layout conventions.

This layer must **not own business/domain authority**.

For example, `ValoraStatusBadge` may render a status supplied to it, but it must not decide whether an appraisal stage is actually complete.

---

### 3.4 Feature components

Feature components belong to a bounded product/domain area.

Examples:

```text
AssetReviewWorkspace
ComparableEvidencePanel
SupplierQuoteTable
AppraisalResultSummary
DocumentRevisionPanel
ReleaseReadinessPanel
```

Feature components may:

- compose shared Valora components;
- call feature hooks/API adapters;
- coordinate local presentation state;
- translate authoritative domain responses into UI presentation;
- implement feature-specific interactions.

Feature components must not establish a competing visual system.

They should consume shared components and design tokens instead of embedding unique color, spacing, typography or primitive behavior unless the requirement is genuinely feature-specific.

---

### 3.5 Screens

Screens are the highest presentation composition layer.

Typical responsibilities:

- route-level composition;
- page layout;
- feature placement;
- page-level loading and error orchestration;
- navigation context;
- deep-link/return context;
- screen-level responsive composition.

Screens should remain comparatively thin.

They must not become repositories for:

- domain authority;
- duplicated API rules;
- ad hoc CSS systems;
- arbitrary reusable components;
- business-state derivation that belongs on the server.

---

## 4. Dependency direction

Dependencies flow downward only:

```text
Screens
   ↓
Feature components
   ↓
Valora shared components
   ↓
Fluent primitives
   ↓
Design tokens
```

Higher layers may depend on lower layers.

Lower layers must not depend on feature or screen code.

Examples:

### Allowed

```text
AssetReviewScreen
  → AssetReviewWorkspace
  → ValoraDataGrid
  → Fluent DataGrid primitive
  → Valora density/color tokens
```

### Forbidden

```text
ValoraDataGrid
  → AssetReviewService
```

or:

```text
designTokens
  → feature-specific business logic
```

---

## 5. Server-authoritative boundary

This frontend architecture does not alter Valora's server-authoritative product model.

The frontend may present and coordinate authoritative state, but must not invent it.

Examples of server-authoritative concepts include:

- Case State;
- Current Stage;
- Next Action;
- RBAC/permission state;
- authoritative Result;
- DocumentRevision;
- Release readiness;
- Published state;
- tenant/organization identity;
- mutation result and conflict state.

A redesign must not introduce logic such as:

```text
if UI conditions appear satisfied:
    stage = COMPLETE
```

when the authoritative backend has not declared that state.

The correct direction remains:

```text
Domain / Server Authority
        ↓
API / Read Model
        ↓
Feature presentation
        ↓
Shared UI components
        ↓
Rendered screen
```

---

## 6. Windows Client relationship

Valora's selected client architecture is:

```text
Linux Server
      ↓
HTTPS / API / server-hosted web
      ↓
React + Fluent 2
      ↓
WebView2
      ↓
WinUI 3 native shell
```

The React frontend remains the primary product UI.

WinUI 3 should remain focused on native-shell responsibilities and explicitly authorized Windows capabilities.

Therefore most changes to:

- typography;
- colors;
- density;
- navigation presentation;
- tables;
- forms;
- workspaces;
- drawers;
- dashboards;
- page composition;

should not require a rewrite of the Windows Client.

Native changes are required only when the product change affects native capabilities or the typed native bridge.

---

## 7. Native bridge boundary

Frontend architecture must not use UI customization as a reason to expand native authority.

Native bridge capabilities remain typed, versioned and allowlisted.

Examples of potentially valid native capabilities include:

- file picker;
- bounded Save As;
- open eligible files in Word/Excel;
- controlled deep links;
- controlled notifications;
- drag/drop mediation;
- explicitly permitted external navigation.

The frontend must not gain generic native abilities such as:

```text
execute_process(any)
read_file(any)
write_file(any)
run_powershell(any)
```

through this architecture.

---

## 8. Mandatory implementation rules

The following rules apply to new frontend work:

### Rule 1 — Token-first visual values

Do not introduce new arbitrary colors, spacing, typography, radius or density values when a valid token exists.

### Rule 2 — Prefer Fluent primitives

Do not recreate standard controls that Fluent 2 already provides unless the task contains an accepted reason.

### Rule 3 — Reuse Valora shared components

Repeated product patterns should become shared Valora components instead of being copied across features.

### Rule 4 — No business authority in shared components

Shared components receive state; they do not decide product truth.

### Rule 5 — Feature isolation

Feature-specific presentation logic belongs in the feature layer and should not leak into global primitives.

### Rule 6 — Thin screens

Screens compose. They should not become monolithic repositories of styling, domain logic and API behavior.

### Rule 7 — No frontend-authoritative workflow state

The frontend must not infer authoritative business completion when that state belongs to the backend/domain.

### Rule 8 — Preserve state semantics

Loading, empty, unavailable, denied, stale, conflict, uncertain, partial-success and error states must remain explicit.

### Rule 9 — No native-shell coupling for ordinary UI

A normal UI redesign must not require native WinUI changes unless a native capability boundary is actually affected.

### Rule 10 — Accessibility remains part of component acceptance

Shared components and feature compositions must preserve keyboard, focus, semantic and accessibility behavior inherited from or built upon Fluent 2.

---

## 9. Anti-patterns

The following patterns should be rejected during implementation/review unless explicitly justified.

### 9.1 Feature-local visual systems

```text
Feature A
 → custom colors
 → custom typography
 → custom button
 → custom dialog

Feature B
 → another custom set
```

This creates expensive redesign and inconsistent UX.

---

### 9.2 Screen-level business authority

A screen must not decide that a domain operation succeeded simply because a local interaction completed.

---

### 9.3 Duplicated shared components

If multiple features independently create similar:

- status badges;
- error panels;
- confirmation dialogs;
- data grids;
- command bars;
- drawers;

the implementation should be evaluated for promotion into the shared component layer.

---

### 9.4 Primitive bypass

Raw HTML/CSS or a custom control should not silently replace a suitable Fluent primitive only for convenience.

---

### 9.5 Native-first presentation logic

Ordinary product UI must not migrate into WinUI simply because the Windows app exists.

The native shell is not the primary product presentation layer.

---

## 10. Migration strategy — ratchet, not rewrite

This architecture does **not** authorize or require an immediate full frontend refactor.

Valora will use an incremental ratchet strategy.

### New code

All new frontend implementation must follow this layering rule.

### Modified existing code

When an existing feature is materially changed, the touched area should move toward this architecture where practical.

### Untouched legacy code

Legacy components outside the active task scope do not need to be rewritten merely for architectural purity.

### Promotion rule

If a task discovers a reusable pattern, promote it only when there is enough evidence that it is genuinely shared.

Avoid premature abstraction.

The preferred migration pattern is:

```text
existing feature touched
        ↓
identify duplicated/local visual pattern
        ↓
normalize token usage
        ↓
reuse Fluent primitive
        ↓
promote stable reusable pattern to Valora shared component
        ↓
feature consumes shared component
```

---

## 11. Recommended repository organization

Exact paths remain subject to the live repository, but the conceptual structure should follow:

```text
frontend/src/
  design/
    tokens/
    theme/

  components/
    shared/
      data-grid/
      command-bar/
      drawer/
      status/
      states/
      dialogs/
      layout/

  features/
    asset-review/
    asset-workbench/
    price-evidence/
    supplier-quotes/
    appraisal-result/
    documents/
    release/

  pages/
    ...

  routes/
    ...
```

Repository reality takes precedence over this illustrative structure. Do not restructure solely to match this example unless an implementation task justifies it.

---

## 12. UI customization impact

Under this architecture, most visual redesign work should fall into three categories.

### Low-cost customization

Primarily:

```text
Design tokens
+
Valora shared components
```

Examples:

- brand colors;
- typography;
- density;
- border radius;
- elevation;
- spacing;
- status presentation.

### Medium-cost customization

Primarily:

```text
Shared components
+
Feature components
```

Examples:

- new table layout;
- workspace redesign;
- drawer/panel interaction;
- dashboard restructuring;
- navigation presentation.

### High-cost product changes

Require coordination beyond presentation:

```text
Feature UI
+
API
+
Domain authority
+
RBAC/Audit
+
possibly native bridge
```

Examples:

- new workflow stage;
- new authoritative command;
- changed approval semantics;
- new document mutation authority;
- new native Windows capability.

---

## 13. Acceptance checklist for frontend PRs

A frontend PR should answer, as applicable:

- [ ] Are new visual constants represented by existing/new design tokens?
- [ ] Are Fluent primitives reused where appropriate?
- [ ] Are repeated Valora patterns using shared components?
- [ ] Is feature-specific behavior contained within the feature layer?
- [ ] Is the screen primarily composition rather than business logic?
- [ ] Does the frontend rely on server-authoritative state instead of inferring product truth?
- [ ] Are loading/empty/error/denied/stale/conflict/uncertain states handled correctly?
- [ ] Does the change avoid unnecessary WinUI/native coupling?
- [ ] Are shared components free of domain-specific authority?
- [ ] Are accessibility/focus/keyboard behaviors preserved?
- [ ] Are relevant visual/component/browser tests updated?
- [ ] Does the implementation avoid creating a second visual system?

Not every PR needs every form of testing. Test scope remains risk- and task-based under the current Valora operating protocol.

---

## 14. Architectural invariants

The following invariants should remain true:

```text
Visual authority
    belongs to tokens/shared presentation system.

Business authority
    belongs to server/domain.

Native OS authority
    belongs to the bounded WinUI/native bridge.

Feature logic
    does not create a competing design system.

Screens
    compose rather than redefine architecture.
```

---

## 15. Expected long-term benefit

With this rule preserved, a future Valora UI/UX redesign should be able to retain:

```text
Backend/domain
API
authentication/session
RBAC
audit
document engine
release semantics
Windows native shell
typed native bridge
```

while replacing or substantially changing:

```text
Design tokens
Valora shared components
Feature presentation
Screen composition
```

This substantially reduces the cost of future rebranding, UX modernization and product-surface redesign.

---

## 16. Product Owner decision

The Product Owner has approved the following architecture as the official Valora frontend layering rule:

```text
Design tokens
      ↓
Fluent primitives
      ↓
Valora shared components
      ↓
Feature components
      ↓
Screens
```

This decision is an architectural constraint for future frontend implementation.

It does **not** by itself authorize:

- a full frontend rewrite;
- a mass refactor;
- a new runtime gate;
- changes to business authority;
- expansion of Windows native capabilities;
- changes to current Product/OS-G sequencing.

Implementation should follow the incremental ratchet strategy and be incorporated into future frontend work as relevant.

---

**End of document**
