# PR-04 NCC Selection API + UI Implementation Audit

**Date:** 2026-09-05
**Task:** `VALORA-PR04-IMPL-001`
**Implementers:** DeepSeek V4 Flash Vision Exp through OpenCode; accepted correction by Muse Spark
1.3 Free through OpenCode
**Gate executor:** Gemini 3.8 Flash High through Antigravity CLI
**Independent backend reviewer:** Nemotron 3.5 Lightning Free through OpenCode
**Authority:** `VALORA_UIUX_V2_3_PR04_NCC_SELECTION_API_UI_TASK_BRIEF.md`, ADR 0039, PR-03 persistence contract, Handoff v2.3 §2.1, NCC Selection Baseline Addendum, Cross-product State Pattern Addendum

## Summary

Implemented the tenant-safe NCC Selection read aggregate + explicit confirmation API and the
Vietnamese-first desktop NCC Selection screen. Evidence is presented only through embedded
server-verified metadata; the generic evidence endpoint was not edited and not called. All
accepted PR-01..PR-03 work is preserved unchanged.

## What was built

- **Backend read aggregate** `GET /api/v1/projects/{project_id}/ncc-selections` (`project:read`):
  KPIs + ordered asset-line aggregates with server-evaluated candidates (ADR 0039 D1/D2), current
  selection, history and stale state.
- **Backend confirm command** `POST /api/v1/projects/{project_id}/asset-lines/{line_id}/ncc-selection`
  (`project:update`): strict body (`extra="forbid"`), delegates to PR-03 `confirm_ncc_selection`,
  returns the committed current-selection representation, 409 carries the service error code.
- **Frontend**: canonical `/workbench/projects/{ref}/ncc-selection` route centralized in
  `contracts/valoraV23.ts`, wired through `App.tsx` + `AppShell`; Vietnamese desktop table + right
  drawer (eligible quotes / current / history), single-choice selection, explicit confirmation
  flow with one retained idempotency key, and the full cross-product state contract.

## Files changed

See the implementation contract:
`docs/implementation/VALORA_UIUX_V2_3_PR04_NCC_SELECTION_API_UI_CONTRACT.md`.

## Verification

Gemini executed the mechanical gate in the standard Python virtualenv and the live local
PostgreSQL environment. Credentials remained process-scoped.

### Backend

- Ruff on PR-04 files and dependent PR-03 NCC Selection files: PASS.
- Python compilation on PR-04 production/test files: PASS.
- PR-04 API plus PR-03 service tests: 31 passed, 0 failed.
- PR-03 PostgreSQL concurrency tests: 2 passed, 0 failed.
- Alembic: one head, `d4b7c9e2f1a6`.
- Full backend: 1,340 passed, 0 failed, 0 skipped, 0 deselected, 0 xfail.

### Frontend

- Initial full suite: 108 passed. Gemini then found three blocking contract gaps in 409 error-code
  mapping, evidence disclosure and keyboard row operation.
- Muse corrected those findings plus the accepted no-preselection, Vietnamese history-label and
  drawer-focus notes within `frontend/src/components/ncc-selection/**` and `frontend/src/i18n/vi.ts`.
- Correction re-gate: 24 test files / 115 tests passed; TypeScript reported 0 errors; production
  build passed with 184 modules and the demonstration-marker assertion passed.
- `git diff --check`: PASS.

## Independent review

- Nemotron backend/API/security review: PASS, no blocking findings.
- Gemini frontend/UX review initially failed with three blocking findings. After the Muse
  correction, Gemini re-review: PASS, no remaining blocking findings.
- Non-blocking backend test opportunities remain for the over-15-percent warning, variant identity
  candidate path and stale response/KPI path; accepted service coverage and the full gate remain
  green.

## Evidence boundary

Per coordinator decision, evidence is exposed only as embedded server-verified metadata
(`evidence_file_id`, `filename`, `status`). `backend/app/api/evidence.py` was not edited and not
called. The generic evidence endpoint remains out of scope for this PR.

## Scope respected

No migration, no case-state/resume wiring, no `AppraisedPriceDecision` mutation, no automatic
supplier selection, no silent stale rebind, no NCCQ aggregate/rule-check/legacy QC surface, no
M365/publishing/lineage refactor, no new dependencies, and no commit/push/PR.

## Notes

- The read aggregate reuses the PR-03 `is_ncc_selection_stale` and mirrors the D1/D2 predicate in
  `_candidate_for_quote_line` without changing the existing `_find_eligible_quote`.
- `NccSelectionCurrentHead`/`NccSelectionRevision` are read only; no existing PR-03 row is
  modified.
- Backend pytest and ruff were not executable in this workspace; the backend gate should be
  re-run in the CI/postgresql environment that PR-03 used.
