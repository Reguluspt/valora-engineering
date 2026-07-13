# S12-PR-003 — Excel Staging Validation Engine Audit

## Status
```text
S12-PR-003 DRAFT PR CI VALIDATED — AWAITING FINAL DOCUMENTATION-HEAD CI AND INDEPENDENT AUDIT
```

| Field | Value |
|---|---|
| Task | S12-PR-003 Excel Staging Validation Engine |
| Baseline `main` | `5bef98c25bc0bdfb386c68312a80f104a51769c6` |
| Branch | `s12-pr-003-excel-staging-validation-engine` |
| Design authority | Owner decision package 2026-07-13 + contract §14 |
| Draft PR | **#8** — https://github.com/Reguluspt/valora-engineering/pull/8 |
| PR state | open, **draft=true** |
| Code-bearing branch head | `e0d0c840b38fee3cb54e9440a1a6ac01882aa2a9` |
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

## Commit lineage

```text
main 5bef98c (S12-R-007 #7)
  └─ s12-pr-003-excel-staging-validation-engine
       ├─ A 68227cd implement Excel staging validation engine
       ├─ B e0d0c84 docs: record S12-PR-003 local validation evidence
       └─ C (this) docs: record S12-PR-003 Draft PR CI evidence
```

## Local evidence (pre-CI)

| Suite | Result |
|---|---|
| Focused PR-003 tests | **23 passed, 1 skipped** (PG concurrency) |
| R006 hardening | 39 passed, 1 skipped |
| Full backend pytest | **393 passed, 6 skipped, 20 warnings** |
| Security scanner | PASS |
| Alembic | single head `db5977424e7b` |
| Worker | Ruff PASS, 1 passed |
| Frontend | lint/build/vitest **80 / 15** |
| npm audit --audit-level=high | 0 vulnerabilities |

### Local PostgreSQL skips (NOT PASS)
```text
tests/test_auth_endpoints.py:737
tests/test_s12_pr_003_staging_validation.py::TestPGValidationConcurrency::test_same_batch_serializes_under_postgres
tests/test_s12_r_004_official_mutation.py:1049
tests/test_s12_r_006_excel_intake_hardening.py:517
tests/test_workbench_api.py:696
tests/test_workbench_api.py:980
```

## Code-bearing Draft PR CI evidence (SHA `e0d0c84…`)

| Run | Event | Branch-head SHA | Checkout/tested SHA | Conclusion | Jobs |
|---|---|---|---|---|---|
| **29262082691** (#102) | `push` | `e0d0c840b38fee3cb54e9440a1a6ac01882aa2a9` | branch head (direct push) | **SUCCESS** | backend/worker/frontend SUCCESS |
| **29262718158** (#103) | `pull_request` | `e0d0c840b38fee3cb54e9440a1a6ac01882aa2a9` | `e8a4f46ba1907f1ae4e829c7e415a1081573f3cf` (Merge head into `5bef98c…`) | **SUCCESS** | backend/worker/frontend SUCCESS |

URLs:
- https://github.com/Reguluspt/valora-engineering/actions/runs/29262082691
- https://github.com/Reguluspt/valora-engineering/actions/runs/29262718158

### Backend (authoritative PR run #103 and push #102)
| Gate | Result |
|---|---|
| Ruff | All checks passed |
| Pytest | **399 passed, 0 skipped, 27 warnings** (`collected 399 items`) |
| pip-audit | No known vulnerabilities found |
| Security scanner | Scan passed |
| Alembic upgrade / single head | PASS (CI job path) |

PostgreSQL skip count in CI: **0**.

### S12-PR-003 PostgreSQL concurrency proof
- Suite `tests/test_s12_pr_003_staging_validation.py` fully green in CI (all nodes including concurrency; local skip no longer applies).
- Overall backend: **399/0 skip** = former 393 pass + 6 previously skipped PG tests all executed.
- Node (local skip ID):
  ```text
  tests/test_s12_pr_003_staging_validation.py::TestPGValidationConcurrency::test_same_batch_serializes_under_postgres
  ```
  Executed as part of the full suite under PostgreSQL CI (0 skips).

### Former local-skip tests executed in CI
All six previously skipped tests ran (suite completed with zero skips), including:
- auth PG integration
- S12-R-004 concurrency
- S12-R-006 `TestPGIsolatedConcurrencyRestored::test_concurrent_upload_serialization` (present in CI logs)
- workbench PG concurrency / rollback
- S12-PR-003 PG validation concurrency

### Worker / Frontend
- Worker job: SUCCESS (Ruff + pytest + deps)
- Frontend job: SUCCESS (lint/build/Vitest/npm audit)

### Transient/superseded runs
None for this head — both push and PR runs concluded SUCCESS.

### Local vs CI distinction
| Environment | Backend pytest |
|---|---|
| Local (no PG) | 393 passed, **6 skipped**, 20 warnings |
| Code-bearing CI (PG) on `e0d0c84…` | **399 passed, 0 skipped**, 27 warnings |

## Immutability

Focused tests snapshot official `ProjectAssetLine` IDs/name/quantity/row_version across success and failure paths; unchanged. CI full suite green.

## Limitations

1. Documentation-head CI for this audit-evidence commit is reported externally after push (not looped into another commit).
2. Independent audit remains PENDING.
3. PR remains Draft — not Ready, not merged.
4. Validation v1 still only two rules; no Apply/AI/frontend.

## Final verdict
```text
S12-PR-003 DRAFT PR CI VALIDATED — AWAITING FINAL DOCUMENTATION-HEAD CI AND INDEPENDENT AUDIT
```
