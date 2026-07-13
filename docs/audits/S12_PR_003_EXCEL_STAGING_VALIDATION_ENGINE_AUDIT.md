# S12-PR-003 — Excel Staging Validation Engine Audit

## Status
```text
S12-PR-003 LOCAL IMPLEMENTATION COMPLETE - AWAITING POSTGRESQL CI VERIFICATION
```

| Field | Value |
|---|---|
| Task | S12-PR-003 Excel Staging Validation Engine |
| Baseline `main` | `5bef98c25bc0bdfb386c68312a80f104a51769c6` |
| Branch | `s12-pr-003-excel-staging-validation-engine` |
| Design authority | Owner decision package 2026-07-13 + contract §14 |
| Draft PR | **not created** (owner-controlled per prompt) |
| CI | **PENDING** after push |
| Independent audit | **PENDING** |

## Design authority applied

| Decision | Implementation |
|---|---|
| D1 Endpoint | `POST /api/v1/projects/{project_id}/asset-imports/{batch_id}/validate`, `workbench:edit`, no body |
| D2 States | Allow `parsed`/`validation_failed`/`ready_for_review`; 409 otherwise |
| D3 Outcomes | Success → `ready_for_review` even with invalid rows; `validation_failed` = engine failure only |
| D4 Rules | V1-001 asset name required; V1-002 quantity finite decimal; warnings always empty |
| D5–D8 | Counters, rerun, FOR UPDATE + fingerprint recovery, success/failure audits |

Contract amendment: `docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md` §14
Supersedes illustrative `year_missing` for validation v1.

## Code paths

```text
backend/app/modules/excel_import/domain/validation_rules.py
backend/app/modules/excel_import/application/validate_staging.py
backend/app/api/projects.py  (thin adapter)
backend/tests/test_s12_pr_003_staging_validation.py
```

No migration. No frontend/worker/dependency/workflow changes. No Apply. No `ProjectAssetLine` mutation.

## Local evidence (raw summary)

| Suite | Result |
|---|---|
| Focused PR-003 tests | **23 passed, 1 skipped** (PG concurrency) |
| R006 hardening | 39 passed, 1 skipped |
| Security blockers | included in full suite |
| Full backend pytest | **393 passed, 6 skipped, 20 warnings** |
| Security scanner | PASS |
| Alembic | single head `db5977424e7b` |
| Worker | Ruff PASS, 1 passed |
| Frontend | lint/build/vitest green |
| npm audit --audit-level=high | 0 vulnerabilities |

### Local PostgreSQL skip (not PASS)
```text
tests/test_s12_pr_003_staging_validation.py::TestPGValidationConcurrency::test_same_batch_serializes_under_postgres
SKIPPED LOCALLY - REQUIRES CI WITH POSTGRESQL
```
(plus historical R006/auth/workbench PG skips in full suite)

## Immutability

Focused tests snapshot official `ProjectAssetLine` IDs/name/quantity/row_version across success and failure paths; unchanged.

## Limitations

1. PostgreSQL concurrency must execute in CI (local skip when no PG).
2. No Draft PR in this agent pass (prompt forbids creating PR).
3. Validation v1 has only two rules; no year/price/currency/unit rules.
4. No automatic post-upload validation.
5. Independent audit not performed by implementer.

## Final verdict
```text
S12-PR-003 LOCAL IMPLEMENTATION COMPLETE - AWAITING POSTGRESQL CI VERIFICATION
```
