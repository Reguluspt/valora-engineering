# VALORA OS-G6 — Product Completion and Visual Convergence Plan v1

**Status:** PRODUCT OWNER-AUTHORIZED GOVERNANCE PLAN / IMPLEMENTATION NOT OPENED
**Decision:** 2026-10-07 — [Issue #142](https://github.com/Reguluspt/valora-engineering/issues/142), `VALORA-TASK-UIUX-GOV-001-VISUAL-CONVERGENCE-ROADMAP-RECONCILIATION`.
**Scope:** Docs-only reconciliation; future OS-G6 work requires separately bounded owner tasks. This plan neither certifies Product Completion nor activates any product/runtime gate.

## 1. Authority and entry boundary

Read with the [Unified Roadmap](../VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md), [Frontend Architecture Rule](../architecture/VALORA_FRONTEND_ARCHITECTURE_RULE.md), [Engineering Guardrails](../../ENGINEERING_GUARDRAILS.md) and [UI/UX Authority Index](../design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md). The [UI/UX master](../design/VALORA_UIUX_HANDOFF_v2.3.md) and applicable current addenda retain product/interaction authority; accepted domain contracts retain business authority.

Dated verified baseline, 2026-10-07: main `dbcc4f5ca39803dffa360e4eddba064156335dd3`; [CI #625 / run 37639051093](https://github.com/Reguluspt/valora-engineering/actions/runs/37639051093) COMPLETED / SUCCESS. [A14 / Issue #139 certification](https://github.com/Reguluspt/valora-engineering/issues/139#issuecomment-6041091878) is CERTIFIED / CLOSED. Certified product/runtime boundary = **SUPPLIER_QUOTES**; after COMPLETE, `NO_AUTHORIZED_DOWNSTREAM_ACTION` remains product truth. **SUPPLIER_SELECTION and APPRAISAL_RESULT are UNAUTHORIZED; full OS-G2 is PARTIAL / INCOMPLETE.** Re-fetch live authority before any implementation; this snapshot is not evergreen main evidence.

Preserve the top-level sequence:

```text
OS-G2 Appraisal Core
→ OS-G3 Document Runtime
→ OS-G4 Release / Publishing
→ OS-G5 Template Intelligence / Fidelity
→ OS-G6 Product Completion
→ Windows Preview / Formal UAT
→ OS-G7 Valora Intelligence Platform & Assistant
```

No frontend/backend/worker code, schema/migration, API, RBAC, provider, UI redesign, Visual Convergence implementation, OS-G3 or Windows implementation, workflow YAML, AI runtime, skill installation or golden-baseline replacement is authorized by this task. Issue #141-owned process files remain outside this change.

## 2. Two visual acceptance levels

**OS-G2→OS-G5 = functional correctness first + Continuous Visual Integrity.** Product-wide pixel-level convergence is deferred; functional priority does not excuse serious usability, IA or architecture defects.

| Acceptance | Level 1 — Continuous Visual Integrity, OS-G2→OS-G5 | Level 2 — Final Visual Convergence, OS-G6 |
| --- | --- | --- |
| Foundation | Microsoft Fluent 2 light; tokens before arbitrary values; shared-component discipline | Hardened tokens, shared components and layout primitives across the product |
| Composition | Usable hierarchy, no broken layout, no serious IA contradiction | Typography, spacing, density, surface hierarchy, borders/elevation and desktop composition |
| Surfaces | New/materially changed surfaces preserve the approved product language | Navigation, page headers, command bars, data grids, drawers, forms and dialogs |
| States | Explicit loading, empty, error, stale, conflict, denied and uncertain states; preserve existing recovery semantics | Consistent status presentation and loading/empty/error patterns across products; never redefine domain status |
| Accessibility | Basic keyboard, focus and accessibility behavior | Keyboard, focus, contrast, zoom, table navigation, drawer/dialog focus and appropriate semantic markup/screen-reader proof |
| Evidence | Risk-appropriate component/browser checks and any existing task-required golden checks; no product-wide pixel-perfect requirement | Approved final visual baseline and reproducible golden screenshots / regression proof |
| Debt | Only recorded controlled presentation deviations with usability, IA and architecture intact | All registered deviations receive a supported Fix / Re-evaluate / Superseded disposition; unresolved convergence blockers prevent closure |

No feature-local visual system or architecture debt requiring a G6 rewrite may be deferred as ordinary visual debt. Existing task-specific acceptance and document structural/visual fidelity gates remain binding; this policy does not waive them. **OS-G6 MUST NOT close without Final Visual Convergence.**

## 3. OS-G6.0 — Product Scope Freeze / Rebaseline

Entry requires OS-G2→OS-G5 required functional completion under their owning gates, identified canonical product surfaces, identified approved UI/UX authority/mockups and a Visual Debt inventory. Rebaseline the product candidate to live certified main, its exact CI and current domain/workflow contracts.

Freeze the required product scope, authoritative fixtures and acceptance coverage. No feature expansion unless required to resolve a Product Completion blocker; true missing domain behavior returns to its owning domain gate, with separate authorization. G6 cannot manufacture missing downstream-stage authority.

## 4. OS-G6.1 — Functional North-star E2E Candidate

Prove this future authorized functional journey on one exact candidate SHA:

```text
Pre-case
→ Appraisal Core
→ PRICE_EVIDENCE
→ SUPPLIER_QUOTES
→ SUPPLIER_SELECTION
→ APPRAISAL_RESULT
→ Document
→ Release
```

Each stage must already have its owning authorization and functional closure. Inclusion here is a future coverage requirement, never current SUPPLIER_SELECTION / APPRAISAL_RESULT activation.

Domain/API/Case State/Next Action correctness comes first; final polish is not required at G6.1. Preserve unified contextual lineage, cross-product states, Resume context, template/document fidelity, negative/tenant/provider-uncertain paths and exact-SHA North-star evidence. Frontend may present server-authoritative completion/current stage; it must never derive either independently.

## 5. OS-G6.2 — VALORA Internal Business Trial

Use the explicit name **VALORA Internal Business Trial**. This is realistic business workflow evaluation inside Product Completion; it is not Formal UAT and cannot substitute for post-completion Windows Preview/UAT.

Exercise real/near-real appraisal work with appropriately private or anonymized data. Capture unnecessary steps, missing steps, extra/missing columns, information overload, drawer sizing, grid density, warning noise, Next Action clarity, navigation difficulty, context loss and real workflow friction.

Findings become primary UX input. Keep each finding traceable to its surface/context, observed problem, business impact, classification, decision and resolution/adjudication evidence. Recording a finding does not authorize a semantic change.

## 6. OS-G6.3 — UX Reconciliation

| Finding class | Decision / disposition |
| --- | --- |
| 1. Presentation-only | Resolve in G6 under approved visual authority and the presentation architecture. |
| 2. Interaction / UX without authority change | Obtain the Product Owner UX decision, then resolve in G6. |
| 3. Domain / Workflow semantic | Return to the owning domain authority/gate; separately authorize and prove the change before accepting it into the G6 candidate. |

Visual Convergence must never silently change business semantics, Case State, RBAC, mutation or human-confirmation boundaries. Warning noise remediation cannot silently turn Warning into Blocking, hide authoritative uncertainty or invent completion. Material semantic disputes remain blockers until the owning authority resolves them.

The final baseline derives from **Approved UI/UX Authority + Internal Business Trial Findings + Current Authoritative Workflow → Final OS-G6 Visual Baseline**. The Product Owner approves reconciled UX decisions; trial observations alone do not overrule authority.

Do not blindly pixel-clone historical mockups. Mockups remain visual authority for visual grammar, layout, hierarchy, density, Fluent 2, drawer/table composition and navigation patterns. **Current workflow/domain semantics always win over obsolete mockup semantics.** Preserve historical evidence and record the approved reconciliation instead of rewriting history.

## 7. OS-G6.4 — Design-System Hardening

Harden Color, Typography, Spacing, Radius, Elevation, Density, Borders, Semantic States and Layout Constants through the existing Valora architecture:

```text
Design Tokens → Fluent 2 Primitives → Valora Shared Components → Feature Components → Screens

Domain / Server → Application / API → Server-authoritative Read Models
→ Feature Presentation → Shared Components → Fluent → Tokens
```

Shared-component candidates may include `ValoraPageHeader`, `ValoraCommandBar`, `ValoraDataGrid`, `ValoraDrawer`, `ValoraStatusBadge`, `ValoraMessageBar`, `ValoraSection`, `ValoraFormField`, `ValoraEmptyState`, `ValoraErrorState`, `ValoraLoadingState`, `ValoraConfirmDialog` and `ValoraSplitPane`. These are candidates, not claims of existing code or an instruction to create every wrapper.

Use evidence of reuse; presentation components receive authoritative state and do not own business truth. Visual redesign must not change domain authority. React remains the main product UI; the Windows shell must not become the main presentation layer or acquire new native authority through a visual task.

## 8. OS-G6.5 — Visual Convergence

Prefer the following remediation order, highest-reuse shell/grid/drawer primitives first:

1. App Shell
2. Sidebar / Navigation
3. Page Header
4. Workbench Shell
5. DataGrid
6. Asset Context Drawer
7. PRICE_EVIDENCE
8. SUPPLIER_QUOTES
9. SUPPLIER_SELECTION
10. APPRAISAL_RESULT
11. Document Workspace
12. Release / Publishing
13. Dialog / Warning / Status / Empty states

Converge the Level 2 scope against the reconciled approved baseline. Token/shared-component/layout changes should carry most visual remediation; no business workflow rewrite is implied. Later surfaces in this list remain gated by their own functional authority before G6 entry.

## 9. OS-G6.6 — Accessibility + Visual Regression

After convergence, lock approved golden references with **fixed viewport + fixed authoritative fixture + fixed state + fixed route/context + fixed screenshot baseline**. Bind evidence to the exact candidate SHA and reference revision; changed source or baselines invalidate the affected acceptance evidence. Existing historical screenshots remain historical, and this docs task replaces none.

Cover states where applicable: default, selected, drawer open, loading, empty, blocked, stale, warning, conflict, denied, uncertain and completed. Record applicability rather than presenting unavailable domain states as completed behavior.

Verify keyboard, focus, contrast, zoom, table navigation, drawer focus, dialog focus and semantic markup/screen-reader behavior where appropriate. Golden screenshots supplement functional and accessibility checks; they do not prove server authority or justify domain changes.

## 10. OS-G6.7 — Exact-SHA Product Completion Certification

Require every row to PASS with evidence bound to the exact final product candidate/integrated main, as applicable:

| Required acceptance | Result required |
| --- | --- |
| Domain | PASS |
| API | PASS |
| Case State | PASS |
| North-star E2E | PASS |
| Business Trial findings resolved/adjudicated | PASS |
| Design System | PASS |
| Visual Convergence | PASS |
| Accessibility | PASS |
| Visual Regression | PASS |
| Exact-main CI | PASS |

Gate Owner owns integration and exact-main certification. Only after all required acceptance is established may the status become **OS-G6 PRODUCT COMPLETION — CERTIFIED / Software Completion**. Any source HEAD change invalidates prior exact-head review/CI; rebaseline and repeat applicable evidence. No earlier stage, trial, screenshot or inherited CI grants this status.

Formal Windows Preview / Formal UAT remains **after OS-G6 Software Completion** under the [Windows Preview brief](../implementation/VALORA_WINDOWS_PREVIEW_TASK_BRIEF.md). UAT cannot compensate for unfinished product runtime; global Visual Convergence must already be complete. Separately authorized Windows architecture/foundation work does not alter this order.

OS-G7 follows Windows Preview / Formal UAT in the top-level roadmap and begins only after stable Product Completion. Future Assistant presentation should reuse the hardened Valora components, with no separate visual language. The [AI Master Plan](../architecture/VALORA_AI_MASTER_PLAN_V1.md) remains architecture guidance, never AI/provider runtime authorization from this task.

## 11. Lightweight Visual Debt Register

Maintain the register here as a small current table; no new application/dashboard. Owning OS-G2→OS-G5 tasks record controlled presentation deviations and reference their evidence. No surface audit has been performed by this docs-only task; no debt entries are asserted below.

| Surface | Authority reference | Deviation | Reason deferred | Severity | Architecture violation | G6 disposition |
| --- | --- | --- | --- | --- | --- | --- |

Field rules:

- Surface names the affected view/component; authority reference identifies the applicable approved baseline/contract; deviation describes the observable difference; reason deferred explains why usability, IA and architecture remain intact.
- Severity is **Low / Medium / High**. Severity never permits a serious usability/IA defect to be deferred.
- Architecture violation is **Yes / No**. A Yes entry is routed for correction in the owning current task, not accepted as controlled visual debt; the flag makes misclassified debt visible.
- G6 disposition is **Fix / Re-evaluate / Superseded**. Fix requires resolution evidence; Re-evaluate requires an explicit decision against current authority before closure; Superseded names the replacing approved authority/surface and reason.
- Only controlled presentation debt may remain for G6. Architecture violations and serious usability/IA issues must be fixed under their owning tasks. A pending Re-evaluate is not a resolution; no unresolved convergence blocker may survive G6.7.

## 12. External Design Skill Advisory Policy

This Product Owner decision is binding. External design skills, including [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill/tree/b482f7a970abb98c4108d4a9f761e458c64cefc8), are **ADVISORY ONLY**. For design-skill use, apply this precedence within the existing project authority framework:

```text
Explicit Product Owner / Valora UIUX authority
> current domain/workflow/server truth
> Valora Frontend Architecture + Fluent 2 + tokens + shared components
> approved visual baselines + Internal Business Trial findings
> external design-skill heuristics
```

The first line means current approved authority in its named scope; illustrative mockup semantics cannot override domain/server truth. External advice cannot change domain/workflow/Case State/RBAC/mutation semantics or override Microsoft Fluent 2 light, desktop-first, Vietnamese-first, data-heavy/table-first language.

Reviewed upstream evidence at task authorization: repository `Leonxlnx/taste-skill`, exact observed revision **`b482f7a970abb98c4108d4a9f761e458c64cefc8`**, [MIT license](https://github.com/Leonxlnx/taste-skill/blob/b482f7a970abb98c4108d4a9f761e458c64cefc8/LICENSE). The default [design-taste-frontend v2](https://github.com/Leonxlnx/taste-skill/blob/b482f7a970abb98c4108d4a9f761e458c64cefc8/skills/taste-skill/SKILL.md) is experimental and excludes dashboards, data tables and multi-step product UI. This is pinned review evidence, not adoption or a moving-main claim.

| Phase / profile | Allowed advisory use |
| --- | --- |
| OS-G2→OS-G5 | Primarily visual audit/advisory; prefer `redesign-existing-projects` when relevant because it audits the existing stack and recommends targeted changes. |
| `gpt-taste` | Never the default design authority for core Valora UI; its high-motion/Awwwards/layout-variance orientation is not Valora's enterprise appraisal language. |
| `minimalist-ui` / other style skills | Isolated compatible heuristics only; never import an entire external design system. |
| OS-G6.3→OS-G6.5 | Stronger visual-quality audit heuristics are permitted after business authority is correct, within the approved task. |
| `image-to-code` | May assist analysis of approved mockup/golden references; current workflow semantics still win. |
| External visual reviewer | May supplement required reviews; never replace security/domain/high-risk gate reviewers. |

Do not pull moving external main into a gated task. When actually using an external skill, record its exact revision/version and the compatible heuristics applied so the use is reproducible and reviewable. Do not add Taste Skill as a frontend/runtime package dependency or install it into the project through this task. A future internal `valora-ui-visual-quality` skill requires a separate bounded task; it is not created now.

If a compatible external skill uses advisory dials, guidance is `DESIGN_VARIANCE: 2–3`, `MOTION_INTENSITY: 1–2`, `VISUAL_DENSITY: 7–8`. These are guidance only, not design tokens, domain rules or new product authority.

## 13. Delivery of this governance reconciliation

Issue #142 changes only the five named governance documents. Before freeze, fetch live main and inspect Issue #141: if #141 has merged/certified first, rebaseline this branch onto the new main, reconcile and validate before freezing. Verify links/paths, authority consistency and bounded changed paths; run `git diff --check` and available deterministic docs/link checks.

Freeze one clean HEAD; obtain one independent read-only cross-document review for MEDIUM governance/architecture risk, adding a second only if material authority ambiguity remains. Require repository CI SUCCESS on the exact frozen source HEAD. No source change afterward may reuse that evidence.

Delivery is a **Draft PR with Refs #142**. Do not Mark Ready, merge, close Issue #142, certify this reconciliation, start Visual Convergence or authorize SUPPLIER_SELECTION / APPRAISAL_RESULT. Gate Owner owns integration.
