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
| PR-07 Sync / Conflict | PASS — A4/A5 + accepted ADR 0042 and PR-07 contract | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED | PROBE/CONTROLLER LOCAL PASS — C1 `68/68`; EXACT CONTROLLER→NODE→PYTHON NO-NETWORK PASS; AUTHORIZED LIVE STOPPED AT `OAUTH_TOKEN_REJECTED`; C1 PROVIDER PROBE NOT RUN | NOT IMPLEMENTED | NOT IMPLEMENTED | BLOCKED — LIVE STOPPED AT `OAUTH_TOKEN_REJECTED`; NEW FRESH LIVE AUTHORITY REQUIRED | The accepted C1 candidate retains the exact item-ID route and frozen `If-Match`, moves conflict `fail` to one query parameter, and keeps a sourceUrl-only body. The 2026-09-16 authorized attempt completed OAuth but failed before provider at `LAUNCHER_VALIDATION` because the transient controller transferred an unavailable Python path; no retry occurred and cleanup restored the Entra baseline. That transient path is now replaced by a repository-owned controller that uses `sys.executable`, argv-array invocation and `shell=False`, invokes the launcher once, rejects direct unjournaled live probe execution and alternate live evidence directories, and blocks unresolved prior live attempts before OAuth/network. `ATTEMPT_FINISHED` alone is insufficient after provider mutation: only consistent allowlisted cancel/delete completion plus matching probe/controller terminal cleanup resolves the attempt; `PROBE_FINISHED` uses the exact producer schema, is mandatory after mutation, must precede no later probe stage and is reconciled before every resolution path. Each session-dependent stage requires its applicable session to be active at that position; closed-session reuse, probe activity while cancellation is pending, and empty journals remain blocked. Every cleanup pair that appears must be complete and ordered even when another path supplies the accepted deletion. The controller terminal uses an exact producer schema, deletion must follow the final mutation, Boolean exit codes are rejected, and malformed, contradictory, missing, failed or unknown cleanup stays blocked without automatic recovery. The controller uses a bounded OAuth `form_post` callback and writes sanitized durable snapshot/append-only journal evidence. The exact no-network controller-to-Node-to-Python path and failure branches pass locally without OAuth/Entra/Graph. Independent review passed on 2026-09-18 with no P0-P3 finding. The separately authorized attempt `fe63fa6a-c477-4566-a720-f56c74be2ea0` then received the bounded OAuth callback but failed closed at `OAUTH_TOKEN_REJECTED`; launcher, probe and provider mutation did not run, and no retry occurred. Local closeout is clean, and the Product Owner separately confirmed removal of the temporary secret and delegated `Files.ReadWrite` while preserving the PR-05 secret and delegated `Files.Read`. Entra secret/permission lifecycle remains evidence outside the controller. See PR-07 provider conformance runbook | Exact-item OneDrive Personal fresh final commit, stale `412`, identity/concurrent-byte preservation and probe-item cleanup remain unproven for C1; the provider was not invoked | Keep D6 unchanged; diagnose `OAUTH_TOKEN_REJECTED` without retry, then require new fresh action-time approval for any later live attempt; keep PR-07 runtime/migrations and PR-08 gated |
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

## Operational frontend entry: merged baseline gap and unmerged candidate

At the verified merged baseline, backend capability was not the blocker for the basic session and
project entry path: login, refresh, logout, `/me`, CSRF and project-list endpoints existed, while the
production frontend did not call them as an operational flow. The table below remains the historical
baseline observation; it must not be read as the state of the later unmerged candidate.

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

### Unmerged operational candidate — 2026-09-13

Branch `feat/operational-frontend-m365` on base `6af3c86` implements the bounded closure without a
schema migration, Graph write or PR-07 runtime. This is candidate evidence only; it does not change
the merged PR-05/PR-06 rows above.

| Candidate capability | Current candidate evidence | Verdict |
|---|---|---|
| Login/session/logout and account context | Cookie/CSRF clients, boot-time `/me`, session gate, login and App Shell account/organization context | LOCAL PASS — UNMERGED |
| Real project selection | API-backed project list with loading, empty, denied/error and navigation states | LOCAL PASS — UNMERGED |
| OneDrive Personal callback/connection | Fixed allow-listed callback return, authoritative connection read model and permission-aware connect state | LOCAL PASS — UNMERGED |
| Provision/adopt selection | Server-owned operational snapshot, bounded folder/DOCX listing, active template selection and canonical provision | LOCAL PASS — UNMERGED |
| Return/revalidation/readiness | Callback and focus re-observation, five server classifications, `recovery_code`/`next_action` rendering and canonical document list | LOCAL PASS — UNMERGED |
| Automated/browser evidence | Frontend unit/API tests, backend API/service/adapter tests and simulated-provider desktop/laptop browser closeout | LOCAL PASS — exact counts below |
| Residual acceptance | Exact-head CI, isolated PostgreSQL rerun and live Entra/browser/provider callback on this candidate | NOT EVIDENCED ON CANDIDATE |

## Next bounded scopes and dependencies

1. **Operational entry and OneDrive Personal frontend closure.** The bounded implementation is a
   local unmerged candidate. Preserve its no-Graph-write boundary and obtain exact-head CI plus any
   required live callback/browser evidence before promoting it to merged acceptance.
2. **PR-07 — accepted, provider conformance first.** ADR 0042 and the implementation contract were
   accepted by the Product Owner on 2026-09-13. Contract stop condition 332 keeps runtime and
   migrations paused until a bounded live OneDrive Personal spike proves exact-item final-commit
   enforcement of `If-Match`. A user-controlled callback eventually completed one exact OAuth
   state/PKCE flow and acquired delegated `Files.ReadWrite`, but the probe stopped at upload-session
   creation with HTTP `400`. The minimized rerun on 2026-09-13 then returned HTTP
   `409 nameAlreadyExists` at upload-session creation, again before staging or final commit. Its
   isolated item was moved to the recycle bin; temporary secrets and configured `Files.ReadWrite`
   were removed (user consent revocation was not verified). Official Microsoft documentation review
   then produced a local exact-item candidate: session creation keeps frozen `If-Match` and
   `deferCommit: true`, relies on the documented default conflict behavior `fail`, and leaves the
   accepted final-commit guards unchanged. The single bounded rerun on 2026-09-15 progressed through
   session creation, staging and pre-commit preservation, but the provider rejected the fresh
   exact-item `sourceUrl` final PUT with HTTP `400`; the stale branch was not reached. Item and Entra
   cleanup were verified. A separately authorized C1 live attempt on 2026-09-15 then completed one
   OAuth state/PKCE flow and obtained a token reporting delegated `Files.ReadWrite`, but its single
   probe launcher exited `1` with stderr and no parseable sanitized JSON. It was not retried, and no
   provider outcome or probe-item cleanup can be claimed. Temporary Entra state, clipboard and runner
   memory were cleaned while the PR-05 secret and `Files.Read` were preserved. Because the probe was
   not invoked and produced no new provider evidence, D6 remains unchanged. On 2026-09-16, the
   repository-owned absolute-Python Node launcher, cleanup hardening and exact no-network surface
   passed `28/28` focused tests, Node syntax, Ruff, diff-check and independent review. The Product
   Owner then separately approved exactly one live attempt. One OAuth callback completed, but the
   launcher stopped at `LAUNCHER_VALIDATION` because the Python executable path was unavailable in
   that execution boundary; dependency preflight and the provider probe were not reached. No retry
   occurred. The exact temporary secret and configured `Files.ReadWrite` were removed while the
   PR-05 secret and `Files.Read` were preserved; clipboard clearing and no port-8000 listener were
   verified. D6 therefore remains unchanged. A repository-owned controller now removes the transient
   PowerShell/Python-path transfer, selects `sys.executable`, calls the Node launcher once through an
   argv array with `shell=False`, and persists sanitized atomic JSON plus append-only JSONL evidence.
   The exact controller-to-Node-to-Python no-network path and failure branches pass locally; the
   combined focused suite passes `68/68`. The controller now uses a bounded OAuth `form_post`
   callback, rejects direct unjournaled live probe execution, journals provider and cleanup
   boundaries, derives the recovery item name from the attempt UUID, and blocks a new live run when
   prior evidence is malformed, contradictory or lacks the required terminal cleanup proof. The
   guard validates `PROBE_FINISHED` against the exact producer schema, requires it after mutation,
   reconciles probe/controller terminal reports before every resolution path, validates the exact
   `ATTEMPT_FINISHED` schema, rejects later probe stages, unordered cleanup pairs and Boolean exit
   codes, requires an applicable session to remain active at each session-dependent stage, rejects
   closed-session reuse, probe activity while cancellation is pending and empty journals, rejects
   every incomplete or unordered cleanup pair, and requires deletion after the final provider
   mutation.
   `ATTEMPT_FINISHED` alone cannot clear a mutation-bearing attempt; no automatic cleanup recovery
   is attempted. Entra secret/permission lifecycle remains separate evidence outside this recorder.
   Independent review passed on 2026-09-18 with no P0-P3 finding. The Product Owner then separately
   approved exactly one live attempt. Attempt `fe63fa6a-c477-4566-a720-f56c74be2ea0` received the
   bounded OAuth callback but failed closed at `OAUTH_TOKEN_REJECTED`; launcher, probe and provider
   mutation did not run, and no retry occurred. Local closeout is clean. The Product Owner separately
   confirmed removal of the temporary Entra secret and delegated `Files.ReadWrite` while preserving
   the PR-05 secret and delegated `Files.Read`. Diagnose the token rejection without claiming
   provider evidence, then obtain a new action-time Product Owner approval before any later live
   attempt. PR-07 runtime/migrations and PR-08 remain gated.
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

## Provider execution record for the verified baseline audit

- Gemini `gemini-3.1-pro-high`: unavailable in the current environment; the Gemini CLI and exact
  model were not available. No substitute Gemini, Claude or Kimi model was used.
- DeepSeek `opencode-go/deepseek-v4.1-flash`: completed a read-only repository survey and exact-diff
  challenge; it identified the absent operational frontend and the PR-07 protected-value/transaction
  authority gap. It made no edits.
- Codex: sole writer and verifier for this audit. Before architecture-impacting runtime work, retry
  the exact Gemini challenge. If it remains unavailable, continue Codex-only under the Product
  Owner's stated fallback while retaining an explicit independent-review gap.

### Operational candidate review record — 2026-09-13

- Gemini `gemini-3.1-pro-high`: the first corrective attempt returned `INVALID REVIEW` and was
  discarded. A fresh project run then proved branch/HEAD, the exact operational snapshot contract,
  ADR status and frontend test count; it found no P0–P3 issue and returned `READY`.
- DeepSeek `opencode-go/deepseek-v4.1-flash`: the first final review returned `BLOCKED` on a
  read-only-user reconnect action and replay ordering. Both were corrected with regression tests.
  The corrective review found no P0–P2 issue and returned `READY`; its three P3 hardening notes were
  also closed by direct authorize denial, invalid callback-origin tests and `.env.example` config.
- DeepSeek created an unintended local `diff.txt` while reviewing despite read-only instructions.
  Codex inspected and removed that generated artifact; no provider-authored source change remains.
- Codex remains the sole source/document writer. No Claude, Kimi or substitute model was used.

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

### Verification performed on the unmerged operational candidate

```text
frontend: npm test                                          29 files / 137 tests PASS
frontend: npm run lint                                      PASS
frontend: npm run build                                     PASS; production marker assertion PASS
frontend: npm audit --audit-level=high                      PASS; 0 vulnerabilities
backend: operational/PR-05/PR-06 focused tests             72 passed
backend: full pytest after runtime fixes                   1332 passed / 95 skipped / 23 warnings
backend: python -m ruff check app tests                     PASS
backend: python -m alembic heads                            a6d9e4c2b8f1 (single head)
repository: git diff --check                                PASS
repository: targeted secret and prohibited-write scans      PASS
browser: simulated provider, 1440x900 and 1024x768         PASS; zero console warnings/errors
Gemini architecture/security challenge                      READY; no P0-P3
DeepSeek corrective implementation review                   READY; no P0-P2
```

The full backend run completed before three final test-only hardening cases were added; the runtime
code did not change afterward and all three cases pass in the final focused run. The 95 local skips
remain explicitly unverified PostgreSQL/MinIO gates. This candidate has no exact-head CI or new live
OneDrive Personal browser/provider run.
