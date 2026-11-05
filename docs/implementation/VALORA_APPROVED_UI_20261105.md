# VALORA approved interface integration — 5 November 2026

## Task contract

**Task:** `VALORA-UI-20261105` — integrate the Product Owner's approved interface into the existing production React frontend.

**Owner instruction:** “Anh đồng ý giao diện này, em áp dụng vào giao diện chính thức của Valora cho anh nhé”. This is implementation authorization for the approved presentation and sidebar behavior. It supersedes earlier mockup-only timing within this presentation scope; it does not redefine server-side appraisal, evidence, approval or release semantics.

**Design reference:** `valora-design-review-20261104`, source commit `ae331c6839499ffd885fd4e24ba1c2cec0a54199`. Approved reference: pale gray canvas, white rounded surfaces, navy actions, blue selection, compact data workspace, adjacent detail panel, inline sliding navigation with persistent icons and exactly one toggle inside the sidebar. No duplicate breadcrumb toggle or floating navigation overlay.

**Baseline:** `origin/main` at `eee881df17c7b4805b53739ae887cc98e2afebc0`; CODEX blob `dbb64fe5fc9946b1c8b0ac4a5fe477397bea0e0e`; CI #690 / run [41659178795](https://github.com/Reguluspt/valora-engineering/actions/runs/41659178795), completed SUCCESS for this exact SHA. Dedicated checkout `/workspace/valora-official-ui`, branch `feat/approved-valora-ui-20261105`.

**PROJECT AUTHORITY READY: YES** for bounded presentation implementation. Current domain and UAT authority is retained; neither the mockup nor this change certifies production deployment or physical Fold7 acceptance.

**Risk:** Medium — shared presentation, responsive navigation and data-table composition. Existing command payloads, provenance, state transitions, authentication and RBAC remain the authority. Root verification and independent visual/accessibility review support the change; no new domain command is introduced.

**Named authority:** current owner instruction; CODEX §§1, 8.1 and 10; ENGINEERING_GUARDRAILS; PR_RULES; [Frontend Architecture Rule](../architecture/VALORA_FRONTEND_ARCHITECTURE_RULE.md), particularly token-first layering, server authority, explicit error states and approved visual baselines. Frontend architecture applicability: APPLIES.

**Allowed scope:** semantic design tokens and shared primitives; application shell/navigation; presentation of existing preliminary analysis, case overview, workbench, results and list screens; local search/filter/selection/detail visibility; accessible keyboard/touch behavior; focused component and browser checks. Read existing API fields for source specifications/unit/customer price; keep missing or unavailable values truthful.

**Out of scope:** synthetic mockup data or its localStorage persistence, new APIs/database migrations, new evidence/source provenance or attachment admission, changing per-line/whole-set professional approval contracts, quantities/price formulas beyond existing commands, AI/provider calls, native bridge, production credentials or protected R2 data resets. Unsupported mockup business capabilities must not appear operational merely because the visual controls exist.

**Parallel ownership:** shell/tokens/shared primitives; preliminary-analysis presentation; root integration and neighboring screen consistency. No overlapping edits; freeze, commit, remote integration and CI serialize under the root agent.

## Acceptance and verification

- Approved visual language is applied through the existing frontend and current live data adapters.
- All existing routes and permission-derived actions remain available under the same conditions.
- Sidebar expands/collapses inline, retains icons, uses one reachable toggle, and works at desktop, 832px and 390px widths without a scrim or scroll lock.
- Preliminary tables wrap long content and remain horizontally scrollable inside their region. The official virtualized asset grid retains its 44px row geometry and shows full values through contextual detail. Opening either detail view preserves edited values; below 1180px the detail becomes a dedicated workspace view, with the mounted grid hidden until the detail closes.
- Loading, empty, denied, stale, uncertain and error states retain their meanings.
- Existing command/CAS/idempotency/human confirmation behavior remains intact; no mockup fixture enters the production bundle.
- T0/T1: affected shell, analysis, overview, workbench and visual-system regressions; T2: frontend lint, build, test and audit; browser smoke at desktop/Fold-sized/phone viewports. T3 real backend mutation suite N/A for presentation-only scope, without claiming backend or physical-device certification. T4: exact candidate CI and exact main CI for any authorized merge.
- Recheck live main before freeze; stop on material baseline drift, safety/tenant ambiguity or a domain/API change needed to implement a presentation request. Complete the bounded UI candidate before reporting any remaining release/access gap.

**Skills used:** repository session/bootstrap and live-authority/bootstrap (CONTENT_LOADED at baseline); dev-handoff (CONTENT_LOADED); Personal Context for locating prior work only. No external visual skill or runtime dependency added. OpenViking is non-authoritative; optional recall unused, automatic recall/capture/injection OFF; fallback is the repository operating protocol.

## Delivery evidence

### Implemented

- Shared semantic palette and rounded surfaces; navy primary actions, blue selections, readable status colors, compact headers and a single inline sidebar toggle. Desktop/tablet preference stores only a UI boolean; phone navigation starts compact and collapses after choosing a route.
- Preliminary analysis uses the existing staging rows and immutable snapshot contracts, with search/filter/pagination, multiline source information, four inline price/basis editors, adjacent detail and a dedicated detail view on narrow screens. Editing a filtered row retains its original identity and manual proposed price. Busy, loading, uncertain and confirmation states disable editing.
- Case overview presents the existing sixteen server-authoritative stages in seven readable groups, with full ordered detail available. Unavailable stages are explicitly labeled. Existing blockers and next actions remain visible.
- Workbench context is in the layout on desktop and occupies the work area at widths below 1180px; the grid stays mounted while hidden, and the panel does not change element type at a breakpoint. Existing evidence dialogs, command controls and focus return remain intact.
- Recovery remains reachable in the app utility bar. Completion and project-list surfaces use the same spacing and wrapping language.

### Local Saturation

- Final baseline re-fetch: main remains `eee881df17c7b4805b53739ae887cc98e2afebc0`.
- `npm run lint`: PASS.
- `npm test -- --reporter=dot`: **70 files / 576 tests PASS**. The first full run exposed an unguarded `window` reference in the new viewport listener; this was fixed and both affected tests and the full suite passed afterward.
- `npm run build`: PASS, including production-bundle assertion that demonstration data and legacy surface markers are absent. Vite's existing large-bundle warning remains; no dependency or chunking changes are included.
- `npm audit --audit-level=high`: PASS, zero reported vulnerabilities.
- Visual-system ratchet after the final phone header adjustment: **20 tests PASS**.
- `git diff --check`: PASS. Scope review: no backend, API client, migration, auth, RBAC, model or dependency edits.
- Browser smoke uses the existing repository synthetic acceptance API with the actual React app in a temporary QA harness outside the repository. It does not use the static mockup or a real customer environment. Verified desktop (1363/1440px), Fold-sized (832px) and phone (390px) layouts; one sidebar toggle; 216px expanded / 76px compact / 56px phone rail; main content moves with the rail; phone navigation collapses; selected draft values survive detail/back and sidebar operations; keyboard row activation opens the Workbench context and closing restores the mounted grid. These viewport checks do not certify a physical Fold7 or production backend.
- Independent static integration review found no remaining blocker after removing an intermediate modal implementation. This is supplemental Medium-scope review, not formal Reviewer A/B certification.

### Remote integration and runtime deployment

The source candidate is ready for a frozen-head Draft PR and required CI. Record final PR, candidate SHA, CI run, guarded merge and exact-main CI in the PR delivery record. The owner explicitly authorized applying this approved interface to the official app; source integration proceeds under that instruction, while preserving GitHub's enforced checks and review rules.

No production deployment was performed during local validation. The repository has no configured live origin/deploy workflow or completed release manifest. `infra/server` provides deployment foundations; a runtime host, artifact/image selection and operator access are still needed to update a running installation. The protected local R2 synthetic UAT environment is not selected as a deployment target by this UI task.
