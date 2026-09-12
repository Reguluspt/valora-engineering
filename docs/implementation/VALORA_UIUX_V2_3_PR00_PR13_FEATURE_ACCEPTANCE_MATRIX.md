# VALORA UI/UX v2.3 — PR-00 through PR-13 Feature/Acceptance Matrix

**Status:** VERIFIED REPOSITORY AUDIT — CURRENT-STATE GATE
**Audit date:** 2026-09-12
**Verified baseline:** `origin/main` at `27d1cc630f97cb9b56fbfbb4c5bc04d4be305cc6`
**Scope:** Repository, merged pull requests, exact-head CI, migrations, tests, frontend routes and browser evidence

This matrix separates design, runtime, integration and acceptance evidence. `MERGED` means only that
the named pull request landed. It does not promote an absent frontend, browser check or end-to-end
journey to complete.

## Status vocabulary

- `PASS`: exact evidence exists at or is included in the verified baseline.
- `PARTIAL`: a bounded slice or reusable primitive exists, but the PR's product outcome does not.
- `NOT IMPLEMENTED`: no authorized runtime slice implements the outcome.
- `NOT EVIDENCED`: code may exist, but the requested acceptance class has no exact artifact.
- `N/A`: the column is intentionally outside that PR's accepted scope, not an omitted requirement.

## Design-authority keys

- `A0`: `VALORA_UIUX_HANDOFF_v2.3.md`, `VALORA_UIUX_V2_3_AUTHORITY_INDEX.md`, and
  `VALORA_UIUX_HANDOFF_v2.3_CROSS_PRODUCT_STATE_PATTERN_BASELINE_ADDENDUM.md`.
- `A1`: `VALORA_UIUX_HANDOFF_v2.3_CASE_OVERVIEW_ORCHESTRATION_BASELINE_ADDENDUM.md` and ADRs
  0036–0038.
- `A2`: `VALORA_UIUX_HANDOFF_v2.3_NCC_SELECTION_BASELINE_ADDENDUM.md`,
  `VALORA_UIUX_HANDOFF_v2.3_NCC_PRICE_WARNING_RULE_ADDENDUM.md`, and ADR 0039.
- `A3`: `VALORA_UIUX_HANDOFF_v2.3_M365_DOCUMENT_WORKSPACE_BASELINE_ADDENDUM.md` and ADR 0040.
- `A4`: the M365 Return/Revalidation contract and visual addenda, plus ADR 0041.
- `A5`: the Document Sync Version, Bulk Data Sync, Bulk Sync Preview, Sync Conflict Resolution,
  Bulk Sync Confirm/Execute and Bulk Sync Result addenda.
- `A6`: the Release Preparation, Release Exception Review, Release Confirmation, Document Publish
  and Post-Publish Success addenda.
- `A7`: `VALORA_UIUX_HANDOFF_v2.3_AUDIT_LINEAGE_ENTRYPOINT_BASELINE_ADDENDUM.md`.
- `A8`: the M365/Contract Document Workspace, document-set review, generic mapping/review,
  template-management, AI-template, managed-region, spreadsheet-fill, report and certificate addenda.
- `A9`: `VALORA_USER_FLOW_MINDMAP_v2.3.md` and the complete north-star flow in the v2.3 master.

## Feature/acceptance matrix

| PR | Design authority | Backend | Frontend | API integration | Migration | Unit/integration test | Browser acceptance | E2E | Merge status | Exact evidence | Residual gap | Next gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PR-00 Authority Alignment Guard | PASS — A0 + lightweight implementation contract | PASS — ratchet constants only; no runtime semantics by contract | PASS — ratchet constants only | N/A | N/A | PASS | N/A | N/A | MERGED through PR #29 / `2775cb9` | `backend/app/contracts/uiux_v23.py`; `frontend/src/contracts/valoraV23.ts`; backend and frontend contract tests | None inside ratchet scope; runtime adoption belongs to later PRs | Preserve ratchets while later slices adopt them |
| PR-01 Case State prefix + durable official intake | PASS — A0/A1 and PR-01 contracts | PARTIAL — computed case-state provider plus official-intake and preliminary snapshot/result facts | N/A — assigned to PR-02 | PASS — `GET /api/v1/projects/{project_id}/case-state` | PASS — `e3f4a5b6c7d8`, `f9e8d7c6b5a4`, `c159fab13c3a` | PASS — service, endpoint and PostgreSQL suites | N/A | NOT EVIDENCED | MERGED through PR #29 / `2775cb9` | `case_state_projection.py`; official-intake/preliminary services; `test_pr01_*`; exact-head PR #29 and main CI | Only 4-stage prefix is available; 12 downstream stages remain truthfully `NOT_AVAILABLE`; resume persistence remains deferred | Extend projection only when each downstream domain owns durable completion facts and routes |
| PR-02 Case Overview frontend | PASS — A0/A1 | N/A — consumes PR-01 | PASS — real Case State client, route, orchestration page and state handling | PASS — frontend calls PR-01 endpoint and resolves project reference | N/A | PASS — API, hook, component and route tests | PASS — desktop `1440x900`, laptop `1024x768`, loading/error/retry/route/console closeout | NOT EVIDENCED — no whole-product journey | MERGED through PR #29 / `2775cb9` | `CaseOverviewPage.tsx`; `caseState.ts`; `PR-02_BROWSER_ACCEPTANCE_CLOSEOUT.md`; corrective content from `69ecd97` is present on `main` | Page is reachable only by URL/project reference; no operational login or real project picker | Operational entry gate, then include Case Overview in PR-13 E2E |
| PR-03 NCC Selection persistence | PASS — A2, ADR 0039 and PR-03 contract | PASS — append-only tenant-safe current head/revisions and stale checks | N/A | N/A | PASS — `d4b7c9e2f1a6`; upgrade/downgrade/upgrade regression included | PASS — service and PostgreSQL suites | N/A | NOT EVIDENCED | MERGED through PR #29 / `2775cb9` | `ncc_selection_service.py`; project master-data models; `test_pr03_ncc_selection_*`; round-trip content from `ad3faad` is present on `main` | None inside persistence-only scope | Remains a prerequisite for PR-10 lineage wiring |
| PR-04 NCC Selection API + UI | PASS — A0/A2 and PR-04 contract | PASS — read aggregate and explicit confirmation command | PASS — Vietnamese table/drawer, stale/conflict states and explicit confirmation | PASS — real read/confirm API client | N/A — reuses PR-03 | PASS — API/client/hook/component suites | NOT EVIDENCED — implementation review/build is not a pixel-level browser artifact | NOT EVIDENCED | MERGED through PR #29 / `2775cb9` | `projects.py` NCC routes; `nccSelection.ts`; `components/ncc-selection/**`; PR-04 audit; exact-head CI | Formal desktop/laptop browser acceptance and north-star journey are absent | Add browser acceptance when this surface changes or at PR-13 E2E |
| PR-05 OneDrive Personal foundation | PASS — A3, ADR 0040 and PR-05 contract | PASS — delegated OAuth, tenant/user connection, encrypted credential vault, Graph adapter and document binding primitives | NOT IMPLEMENTED | PARTIAL — authorize/callback exist; no frontend caller and no user-facing connection-status/return flow | PASS — `f4c8d2a1b7e9` | PASS — fake-provider, PostgreSQL and live-account acceptance | NOT EVIDENCED | NOT EVIDENCED | MERGED by PR #30 / `42a87fc` | `m365_integration/**`; `api/m365.py`; `test_pr05_m365_*`; PR #30 CI | Operational connect UI, callback return target, connection-state surface and bind/adopt journey are absent | Contract the operational M365 entry gaps, then implement OneDrive Personal UI only |
| PR-06 OneDrive Personal return/revalidation | PASS — A4, ADR 0041 and PR-06 contract | PASS — canonical provision, immutable baseline, five-way classification and computed readiness | NOT IMPLEMENTED | PARTIAL — provision, baseline, readiness and revalidate endpoints exist; no frontend caller | PASS — `a6d9e4c2b8f1`; single Alembic head | PASS — service/API/provision/PostgreSQL and live OneDrive Personal acceptance | NOT EVIDENCED | NOT EVIDENCED | MERGED by PR #31 / `27d1cc6` | `provision_document_service.py`; `revalidation_service.py`; `api/m365.py`; `test_pr06_m365_*`; PR #31 and exact-main CI | No UI for provision/adopt, return/focus revalidation, five outcomes or readiness; no protected value snapshot for PR-07 | Complete operational M365 frontend; accept PR-07 snapshot/sync ADR before writes |
| PR-07 Sync / Conflict | PASS — A4/A5 at semantic/visual level; architecture contract insufficient | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT STARTED | Repository search finds only v2.3 constants and PR-06 digests/readiness; ADR 0041 explicitly defers protected values and write/conflict semantics | Protected value snapshot, three-way comparison persistence, transaction/idempotency boundary, conflict decisions and write safety are undecided | ADR + implementation contract first; no Graph write or runtime mutation before acceptance |
| PR-08 Release Domain Foundation | PASS — A6 | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT STARTED | No release aggregate/model/service/API/UI found; publishing names occur only in v2.3 constants/presentation | Release aggregate, exceptions, manifest inputs, revision locking and authorization semantics are absent | Contract/ADR release aggregate and exception/readiness invariants after PR-07 |
| PR-09 Publishing Commit / Success | PASS — A6 | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT STARTED | No `Release`, `ReleaseManifest`, publish command or post-publish runtime found | Atomic commit, immutable manifest/locked revisions, uncertain-commit recovery and success projection are absent | Implement only after PR-08 foundation; prove atomicity/idempotency and immutable success read model |
| PR-10 Audit / Lineage Wiring | PASS — A7 plus domain authorities | PARTIAL — reusable audit, document, knowledge and NCC lineage primitives exist; no unified context-first projection | PARTIAL — isolated lineage panel/history affordances exist; no canonical five-entry-point wiring | NOT IMPLEMENTED for canonical deep-link context | N/A until contract decides whether persistence changes | PARTIAL — legacy primitive tests only; no PR-10 contract suite | NOT EVIDENCED | NOT EVIDENCED | NOT STARTED | Existing `AuditEvent`, document workspace, knowledge and NCC history primitives; no canonical `context_type/context_id/return_target` integration | Capability-specific entry points, missing-link semantics, deep-link/return target and cross-domain lineage tests are absent | Contract the projection/reference boundary; require ADR only if persistence or primitive semantics change |
| PR-11 Cross-product State Sweep | PASS — A0 | PARTIAL — domain errors/states exist unevenly | PARTIAL — shared loading/error/empty components and PR-02/04 local states exist; no product-wide sweep | PARTIAL — no uniform retry/uncertain-mutation behavior | N/A unless a discovered backend fact is missing | PARTIAL — component-local tests only | NOT EVIDENCED | NOT EVIDENCED | NOT STARTED | `components/common/**`; PR-02 and PR-04 state tests; repository still contains legacy placeholders | All production surfaces have not proven the 17-state contract, one recovery CTA, offline and partial-success behavior | Inventory every production route/API, close gaps per domain, then browser-test representative states |
| PR-12 Template Fidelity | PASS — A8 | PARTIAL — legacy template/document-engine primitives exist, not the v2.3 product flow | NOT IMPLEMENTED for v2.3 workspace/template flow | NOT IMPLEMENTED end to end | PARTIAL — historical document/template schema only; no PR-12 migration | PARTIAL — historical backend primitives only | NOT EVIDENCED | NOT EVIDENCED | NOT STARTED | `document_workspace/**`, document engine/intelligence APIs and models exist; frontend has no document/template surface | Workspace, template upload/mapping/test-fill/review/save, managed-region fidelity and report/certificate flows are absent | Freeze a bounded fidelity contract against real templates; implement after PR-11 and required PR-07 sync semantics |
| PR-13 North-star E2E | PASS — A0/A9 and all governing addenda | NOT IMPLEMENTED as a complete journey | NOT IMPLEMENTED as a complete journey | NOT IMPLEMENTED as a complete journey | N/A except defects discovered by the journey | NOT IMPLEMENTED for the journey | NOT IMPLEMENTED for the journey | NOT IMPLEMENTED — no Playwright/Cypress/Selenium harness found | NOT STARTED | Repository file search finds no E2E framework/config/spec; only unit/integration suites exist | No exact-SHA proof from authentication through the final supported published outcome | Add deterministic E2E harness and fixtures after PR-07–12; pass North-star, failure/retry, tenant and immutability journeys |

## Merge and CI evidence

- PR #28 merged on 2026-09-12 into the PR-01 integration branch at `8c7544d6`; its feature content,
  browser correction and migration regression were then included in the PR #29 rollup.
- PR #29 merged PR-00 through PR-04 to `main` at `2775cb9a96a8067be3e558a84c96bb69566859cb`.
  Exact head CI run `34702350516` passed backend, frontend, worker and whitespace jobs.
- PR #30 merged PR-05 at `42a87fca1a90f5b94724a4ca0d7a83fa5dec1699`. Exact head CI run
  `34703114918` passed the same jobs.
- PR #31 merged PR-06 at `27d1cc630f97cb9b56fbfbb4c5bc04d4be305cc6`. Exact head CI run
  `34703512925` passed the same jobs.
- Exact `main` SHA CI run `34703818281` passed backend static checks, migration smoke/single-head,
  backend tests, dependency audit, security/secret scan, frontend lint/build/unit/dependency audit,
  worker checks/tests/audit and committed-whitespace.

## Current operational frontend entry gap

Backend capability is not the blocker for the basic session and project entry path: login, refresh,
logout, `/me`, CSRF and project-list endpoints already exist. The production frontend does not call
them as an operational flow.

| Required entry capability | Current repository evidence | Verdict |
|---|---|---|
| Login + organization context | Backend accepts organization slug/email/password; frontend has no auth API or login route | MISSING |
| Session restoration | API client attempts refresh only after a 401; no boot-time `/me` restoration or auth gate | MISSING |
| Logout | Backend logout endpoint clears session cookies; no frontend action | MISSING |
| Account/organization context | Backend `/me` returns user, organization, roles and permissions; App Shell does not render it | MISSING |
| Real project selection | Backend `GET /api/v1/projects` exists; frontend project-list route renders static “Chọn hồ sơ” text and has no list client | PLACEHOLDER |
| OneDrive Personal connect | Backend authorize/callback exists; frontend has no M365 client or route | MISSING |
| Bind/adopt or canonical provision | Backend binding/provision primitives exist; frontend has no template/document/connection selection path | MISSING; CONTRACT GAP |
| Return/revalidation/readiness | Backend read/revalidate endpoints exist; frontend has no focus/return orchestration or five-state/readiness UI | MISSING |

The bounded frontend entry slice must use cookie/CSRF behavior already enforced by the backend,
preserve organization context, expose permission-aware states, list real projects, and remove the
static project-list placeholder. It must not add SharePoint, OneDrive for Business, Graph writes,
sync/conflict behavior or preview-only bypasses. The M365 callback/connection-state and
document/template-selection gaps require a small accepted contract before that part is implemented.

## Next bounded scopes and dependencies

1. **Operational entry and OneDrive Personal frontend closure.** Implement login, boot-time session
   restoration, logout, account/organization context and real project selection against existing
   APIs. First contract the missing M365 callback return target, connection-state read model and
   provision/adopt selection boundary; then connect PR-05/06 without Graph writes.
2. **PR-07 — contract/ADR first.** Define immutable protected value snapshots, normalized value
   identity, three-way comparison inputs, conflict-decision persistence, optimistic concurrency,
   idempotency, transaction/commit boundaries, uncertain-write recovery, Graph permission/write
   boundary, audit and published-revision denial. Runtime remains prohibited until accepted.
3. **PR-08 — Release Domain Foundation.** After PR-07, define and implement release preparation,
   exception review, readiness inputs, manifest candidate and revision-lock preconditions without
   publishing.
4. **PR-09 — Publishing Commit/Success.** After PR-08, implement the explicit atomic publish command,
   final immutable Release Manifest/locked revisions/audit and truthful post-publish read model.
5. **PR-10 — Audit/Lineage Wiring.** After PR-03, PR-07 and PR-09, wire capability-specific entry
   points and deep-link return context. Reuse existing primitives; require an ADR before any generic
   cross-domain persistence or semantic rewrite.
6. **PR-11 — State Sweep.** After PR-02 and PR-10, inventory each production surface against all 17
   states and recovery rules; close real gaps and browser-test representative failure/retry paths.
7. **PR-12 — Template Fidelity.** After PR-11 and the required sync semantics, freeze representative
   real-template fixtures and implement the authorized workspace, mapping, test-fill, review and
   managed-region fidelity flows without a fake Word/Excel editor.
8. **PR-13 — North-star E2E.** After PR-07 through PR-12, add the browser E2E harness and prove the
   supported journey from authentication and real project selection through publishing success,
   including tenant denial, conflict/retry, immutable release and audit/lineage return context.

## Windows Preview gate

Windows Preview is not authorized by this audit. `VALORA-WIN-PREVIEW-001` may start only after the
operational frontend entry, PR-07 through PR-13 and Software Completion pass on one exact merged
candidate SHA. The preview packages that accepted product for isolated Windows UAT; it does not
provide a place to discover or complete business features.

## Provider execution record and next plan

- Gemini `gemini-3.1-pro-high`: unavailable in the current environment; the Gemini CLI and exact
  model were not available. No substitute Gemini, Claude or Kimi model was used.
- DeepSeek `opencode-go/deepseek-v4.1-flash`: completed a read-only repository survey and exact-diff
  challenge; it identified the absent operational frontend and the PR-07 protected-value/transaction
  authority gap. It made no edits.
- Codex: sole writer and verifier for this audit. Before architecture-impacting runtime work, retry
  the exact Gemini challenge. If it remains unavailable, continue Codex-only under the Product
  Owner's stated fallback while retaining an explicit independent-review gap.

## Verification performed on the audited baseline

```text
git fetch origin --prune                                      PASS
git rev-parse origin/main                                     27d1cc630f97cb9b56fbfbb4c5bc04d4be305cc6
frontend: npm ci                                              PASS; 0 vulnerabilities
frontend: npm run lint                                        PASS
frontend: npm test -- --reporter=verbose                      25 files / 120 tests PASS
frontend: npm run build                                       PASS; production marker assertion PASS
backend: selected PR-00 through PR-06 non-PostgreSQL tests     315 passed
backend: python -m alembic heads                              a6d9e4c2b8f1 (single head)
exact-main GitHub Actions run 34703818281                     PASS all jobs
```

Local PostgreSQL suites were not rerun because no isolated local database was provisioned for this
read-only audit. The exact-main CI backend job ran migration smoke, single-head and the full backend
suite without skips; the PR task briefs retain their PostgreSQL and live OneDrive Personal evidence.
