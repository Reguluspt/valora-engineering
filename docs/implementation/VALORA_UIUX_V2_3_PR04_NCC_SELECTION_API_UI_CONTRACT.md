# VALORA UI/UX v2.3 — PR-04 NCC Selection API + UI Implementation Contract

**Task:** `VALORA-PR04-IMPL-001`
**Status:** IMPLEMENTED / ENGINEERING GATE PASS
**Date:** 2026-09-05
**Implementers:** DeepSeek V4 Flash Vision Exp through OpenCode; correction by Muse Spark 1.3 Free
through OpenCode
**Authority:** `VALORA_UIUX_V2_3_PR04_NCC_SELECTION_API_UI_TASK_BRIEF.md`, ADR 0039, PR-03 persistence contract, Handoff v2.3 §2.1, NCC Selection Baseline Addendum, Cross-product State Pattern Addendum

## Scope

Expose the accepted PR-03 NCC Selection persistence as a tenant-safe project read aggregate and
explicit human confirmation API, then implement the approved Vietnamese-first desktop NCC
Selection screen. The UI reads server-owned eligibility, warnings, current selection and stale
state; it never derives workflow truth or monetary facts locally.

## Public contract boundary

### `GET /api/v1/projects/{project_id}/ncc-selections`

- Permission: `project:read`.
- Missing or foreign projects return `404` (`project_not_found`).
- Returns `NccSelectionAggregateResponse`: `project_id`, `kpis`, ordered `asset_lines`.
- `kpis`: `total_asset_lines`, `selected`, `unselected`, `stale`, `eligible_quotes`.
- Each asset line carries `asset_line_id`, `asset_name`, `unit_id`, `unit_name`, `quantity`,
  `appraised_unit_price`, `appraised_currency_id`, `current_selection` (nullable),
  `candidates` (server-evaluated D1/D2 eligible QuoteLines), `history`, and `state`
  (`unselected | selected | stale`).
- Evidence is exposed only as server-verified metadata (`evidence_file_id`, `filename`,
  `status`). The generic evidence endpoint is not used and not hardened.
- Nullable business values remain `null` (rendered as `—`); no zero is invented.

### `POST /api/v1/projects/{project_id}/asset-lines/{line_id}/ncc-selection`

- Permission: `project:update`.
- Strict body `NccSelectionConfirmRequest` (`extra="forbid"`): `quote_line_id`,
  `expected_selection_revision` (>= 0), `acknowledged_warning_codes`, `idempotency_key`
  (max 128), `confirmed` (strict bool).
- Delegates all validation, locking, snapshot, idempotency and audit work to the accepted PR-03
  `confirm_ncc_selection` service.
- Returns `NccSelectionCurrentResponse` (committed current-selection representation).
- `409` carries the service error code. The frontend maps `selection_revision_conflict` to
  `VERSION_CONFLICT`, reloads the aggregate, and requires explicit review and confirmation again.

## Files changed

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
- `frontend/src/components/layout/AppShell.tsx` (bounded canonical navigation wiring)
- `docs/implementation/VALORA_UIUX_V2_3_PR04_NCC_SELECTION_API_UI_CONTRACT.md`
- `docs/audits/2026-09-05__PR-04__NCC_SELECTION_API_UI_AUDIT.md`

## Frontend boundary

- Canonical project route `/workbench/projects/{projectRef}/ncc-selection` centralized in
  `contracts/valoraV23.ts` and wired through `App.tsx` + `AppShell` navigation. No raw route
  literals in production `.tsx`.
- Desktop-first, Fluent/Astryx-aligned, Vietnamese-first, data-heavy/table-first surface.
- KPI row, search + status filter (values preserved across retry), main table, right drawer with
  tabs (eligible quotes / current / history), single-choice candidate selection.
- Primary action `Xác nhận NCC đã chọn cho dòng này`. Warning visible before commit and
  non-blocking.
- Confirm flow keeps one idempotency key for retries of the same explicit confirmation attempt;
  a new key is created after reload/review.
- `409` → `VERSION_CONFLICT` → reload aggregate → explicit review and confirm again. No
  `window.confirm`, no auto-select, no silent stale rebind, no appraisal-price mutation.
- States follow the cross-product contract: `INITIAL_LOADING`, `EMPTY_FIRST_USE`,
  `EMPTY_NO_RESULTS`, `SECTION_ERROR`/`PAGE_ERROR`, `STALE_DATA`, `VERSION_CONFLICT`,
  `PARTIAL_SUCCESS`, retry.

## Evidence boundary

Per coordinator decision, evidence is presented only through embedded server-verified metadata.
`backend/app/api/evidence.py` is **not edited and not called**; it remains out of scope for this
PR. The generic evidence endpoint is not hardened here.

## Forbidden scope respected

- No new migration or persistence redesign.
- No case-state provider or resume persistence.
- No `AppraisedPriceDecision` mutation or appraisal-price authority change.
- No quote completion workflow, automatic supplier selection or silent stale rebind.
- No NCCQ intermediate/aggregate screen, standalone rule-check screen or legacy QC expansion.
- No M365, final-result generation, publishing, audit-lineage expansion or unrelated refactor.
- No commit, push, pull request or publication.
- No new dependencies.
