# VALORA UI/UX v2.3 — PR-04 NCC Selection API + UI Task Brief

**Task ID:** `VALORA-PR04-IMPL-001`
**Status:** ENGINEERING GATE PASS
**Date:** 2026-09-05
**Coordinator:** Codex
**Implementers:** DeepSeek V4 Flash Vision Exp through OpenCode (initial implementation); Muse
Spark 1.3 Free through OpenCode (accepted correction)

## Objective

Expose the accepted PR-03 NCC Selection persistence as a tenant-safe project read aggregate and
explicit human confirmation API, then implement the approved Vietnamese-first desktop NCC Selection
screen. The UI reads server-owned eligibility, warnings, current selection and stale state; it never
derives workflow truth or monetary facts locally.

## Authority

- `docs/adr/0039-tenant-safe-ncc-selection-revisions.md`
- `docs/implementation/VALORA_UIUX_V2_3_PR03_NCC_SELECTION_PERSISTENCE_CONTRACT.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.3.md` section 2.1
- `docs/design/VALORA_UIUX_HANDOFF_v2.3_NCC_SELECTION_BASELINE_ADDENDUM.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.3_CROSS_PRODUCT_STATE_PATTERN_BASELINE_ADDENDUM.md`
- existing API authentication, CSRF, error and route conventions

Repository authority outranks OpenViking recall and provider suggestions.

## Public contract boundary

- `GET /api/v1/projects/{project_id}/ncc-selections`
  - permission: existing `project:read`;
  - tenant-hidden missing or foreign projects return 404;
  - returns project KPIs and ordered asset-line aggregates containing asset facts, server-evaluated
    candidate eligibility, current selection, history and stale state;
  - nullable business values remain null and are rendered as `—`, never invented as zero.
- `POST /api/v1/projects/{project_id}/asset-lines/{line_id}/ncc-selection`
  - permission: existing `project:update`;
  - strict body: `quote_line_id`, `expected_selection_revision`,
    `acknowledged_warning_codes`, `idempotency_key`, `confirmed`;
  - delegates all validation, locking, snapshots, idempotency and audit work to the accepted PR-03
    `confirm_ncc_selection` service;
  - returns the committed current-selection representation;
  - 409 uses the service error code. Frontend maps selection revision conflict to
    `VERSION_CONFLICT`, reloads the aggregate, and requires explicit review and confirmation again.

API schemas must forbid unknown request fields. The frontend must retain one idempotency key only
for retries of the same explicit confirmation attempt and create a new key after reload/review.

## UI acceptance criteria

- Add a canonical project route for NCC Selection and wire it through the existing application shell.
- Desktop-first, Fluent/Astryx-aligned, Vietnamese-first, data-heavy/table-first surface.
- KPI row: total asset lines, selected, unselected, stale/review-required and eligible quotes.
- Search and status filter preserve values across retry; search error is not an empty result.
- Main table columns follow the accepted baseline: asset, unit, quantity, current price, selected
  supplier/price, difference, difference percent, warnings and state.
- Selecting a row opens a right-side detail drawer with tabs for eligible quotes, current selection
  and selection history. Candidate selection is single-choice.
- Warning is visible before commit and remains non-blocking. The primary action is
  `Xác nhận NCC đã chọn cho dòng này`.
- Loading, empty-first-use, empty-no-results, section error, page error, stale data, version conflict,
  session recovery and retry states follow the cross-product state contract.
- The UI does not use `window.confirm`, does not auto-select a supplier, does not silently rebind a
  stale quote and does not mutate appraisal price.
- Evidence is shown only through tenant-safe metadata. The aggregate may expose the verified
  evidence ID, filename and status already resolved through the PR-03 organization check. The UI
  provides an accessible `Xem thông tin chứng cứ` action that reveals this metadata in the drawer.
  It must not call or link to the generic `GET /api/v1/evidence/files/{id}` endpoint because that
  endpoint is not project/tenant scoped. Direct file opening or download is deferred to a separately
  authorized evidence-access hardening task.

## Accepted implementation allowlist

- `backend/app/api/projects.py`
- `backend/app/modules/project_master_data/schemas.py`
- `backend/app/modules/project_master_data/application/ncc_selection_service.py`
- `backend/tests/test_pr04_ncc_selection_api.py`
- `frontend/src/App.tsx`
- `frontend/src/api/nccSelection.ts`
- `frontend/src/api/__tests__/nccSelection.test.ts`
- `frontend/src/contracts/valoraV23.ts`
- `frontend/src/contracts/__tests__/valoraV23.test.ts`
- `frontend/src/i18n/vi.ts`
- `frontend/src/components/ncc-selection/**`
- `frontend/src/components/layout/**` only for bounded canonical navigation wiring
- `docs/implementation/VALORA_UIUX_V2_3_PR04_NCC_SELECTION_API_UI_TASK_BRIEF.md`
- `docs/implementation/VALORA_UIUX_V2_3_PR04_NCC_SELECTION_API_UI_CONTRACT.md`
- `docs/audits/2026-09-05__PR-04__NCC_SELECTION_API_UI_AUDIT.md`

Any extra production file requires Codex coordinator review before edit.

## Forbidden scope

- no new migration or persistence redesign;
- no case-state provider or resume persistence;
- no `AppraisedPriceDecision` mutation or appraisal-price authority change;
- no quote completion workflow, automatic supplier selection or silent stale rebind;
- no NCCQ intermediate/aggregate screen, standalone rule-check screen or legacy QC expansion;
- no M365, final-result generation, publishing, audit-lineage expansion or unrelated refactor;
- no commit, push, pull request or publication.

## Required verification

- focused API tests for permission, tenant hiding, response shape, strict input, idempotent replay,
  validation errors and 409 conflict;
- focused frontend API/component/route tests covering loading, empty, success, warning, confirm,
  retry, section error and version conflict;
- existing PR-03 service and PostgreSQL concurrency tests;
- frontend typecheck, test and production build;
- relevant backend suite, Ruff, Python compilation and `git diff --check`;
- Qwen-compatible read-only review for backend/API/security and Gemini through `agy` for
  frontend/UX/visual code; Nemotron is the accepted substitute when Qwen is quota-limited;
- Gemini through `agy` executes all mechanical checks above in the standard virtualenv and
  PostgreSQL environment and returns compact result counts;
- Codex performs the final scope/authority gate and reruns only targeted ambiguous or conflicting
  checks unless the provider gate is unavailable.

## Stop conditions

Stop before implementation and return a compact BLOCKED report if the accepted sources cannot
determine candidate membership, permission behavior, tenant-safe evidence presentation, response
shape needed by the baseline, or a conflict-safe frontend retry flow without domain invention.

## Coordinator resolution after survey

DeepSeek reported that the generic evidence-file endpoint is ID-only, uses a different permission
and is outside this allowlist. Codex resolved the gap by accepting the embedded, server-verified
metadata presentation above. PR-04 must not edit or call `backend/app/api/evidence.py`. All other
survey boundaries were accepted for implementation.
