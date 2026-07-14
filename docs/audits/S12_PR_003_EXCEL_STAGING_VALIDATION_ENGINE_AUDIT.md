# S12-PR-003 — Excel Staging Validation Engine Audit

## Status
```text
S12-PR-003 CORRECTIVE-HEAD CI PASS — AWAITING INDEPENDENT RE-AUDIT
```

| Field | Value |
|---|---|
| Task | S12-PR-003 Excel Staging Validation Engine |
| Independent audit (prior) | **PASS WITH FIXES** (merge blocked pending corrective proof) |
| Baseline `main` | `5bef98c25bc0bdfb386c68312a80f104a51769c6` |
| Branch | `s12-pr-003-excel-staging-validation-engine` |
| Draft PR | **#8** — https://github.com/Reguluspt/valora-engineering/pull/8 (open, draft=true) |
| Corrective code head | `d92de3ae42fd3668d1923c34429720d376798c49` |
| Independent re-audit | **PENDING** |

## Independent audit findings (F-1…F-5) and resolution

| ID | Finding | Resolution |
|---|---|---|
| F-1 | Fingerprint `str()` collapsed `None` vs `"None"` | `validation_inputs` now stores raw `(proposed_asset_name, proposed_quantity)` null-aware pairs |
| F-2 | Same-batch PG test allowed worker failures | PG-A asserts both threads succeed, `errors==[]`, 2 success audits, 0 failure audits, exact rows/counters |
| F-3 | Incomplete PG matrix | Added PG-A, PG-B (both serial orders), PG-C (stale failure vs newer upload), PG-D (different batches) |
| F-4 | Weak fault-injection | Exact snapshots + failure audit cardinality/payload for rule/flush/savepoint/outer-commit/audit-persist/stale paths |
| F-5 | Evidence claims | This section lists exact nodes and CI counts |

## Design authority (unchanged)

Contract §14 + owner package 2026-07-13. Rules v1 unchanged: asset_name_required, quantity_invalid; warnings always empty; success → ready_for_review; engine failure → validation_failed + fingerprint-guarded failure audit.

## Corrective code commits

| Commit | SHA | Paths |
|---|---|---|
| Strengthen proof | `d1e939736b61da54c4fd93c1096817db3bafe5e5` | `validate_staging.py`, `test_s12_pr_003_staging_validation.py` |
| PG-B barrier fix | `d92de3ae42fd3668d1923c34429720d376798c49` | `test_s12_pr_003_staging_validation.py` only |

## Exact tests added/strengthened

### Fingerprint (SQLite unit)
- `TestFingerprintNullAwareness::test_fingerprint_differs_null_vs_literal_none_asset_name`
- `…_quantity`
- `…_empty_string_vs_null`
- `…_identical_typed_inputs_same_generation`
- `…_row_order_deterministic_by_id`

### Fault injection (SQLite)
- `test_rule_evaluation_failure_records_exact_failure_audit`
- `test_flush_failure_after_audit_preserves_generation`
- `test_savepoint_commit_failure_preserves_generation`
- `test_outer_commit_failure_exact_failure_audit`
- `test_failure_audit_persistence_failure_preserves_pre_attempt`
- `test_stale_failure_does_not_overwrite_newer_generation`

### PostgreSQL (CI-required; local skip without PG)
- `TestPGValidationConcurrency::test_pg_a_two_validations_same_batch_both_succeed`
- `…::test_pg_b_upload_then_validation_serial_orders`
- `…::test_pg_c_stale_validation_failure_vs_newer_success`
- `…::test_pg_d_different_batches_independent`

## Local results (corrective)

| Suite | Result |
|---|---|
| Focused PR-003 | **31 passed, 4 skipped** (PG matrix) |
| Full backend | **401 passed, 9 skipped, 20 warnings** |
| R006 + security blockers | green |
| Security scanner | PASS |
| Alembic | `db5977424e7b` |
| Worker | 1 passed |
| Frontend | 80 / 15 |
| npm audit --audit-level=high | 0 vulnerabilities |

Local PG skips are **SKIPPED**, not PASS.

## Code-bearing corrective CI (head `d92de3a…`)

| Run | Event | Conclusion | Backend |
|---|---|---|---|
| **29309650043** (#108) | push | SUCCESS | **410 passed, 0 skipped, 27 warnings** |
| **29309651857** (#109) | pull_request | SUCCESS | **410 passed, 0 skipped, 27 warnings** |

- https://github.com/Reguluspt/valora-engineering/actions/runs/29309650043
- https://github.com/Reguluspt/valora-engineering/actions/runs/29309651857

Jobs: backend/worker/frontend SUCCESS. PostgreSQL skip count: **0**. All four PG matrix tests executed.

Prior failed code-bearing attempt on `d1e9397` (PG-B barrier bug) superseded by `d92de3a` fix; do not treat failed runs as authoritative.

## Documentation-head CI

Recorded externally after this audit-only commit (no evidence loop).

## Limitations

- Independent re-audit still required.
- PR remains Draft.
- Validation rule catalog still v1 only (two rules).
- No Apply/AI/frontend.

## Final verdict
```text
S12-PR-003 CORRECTIVE-HEAD CI PASS — AWAITING INDEPENDENT RE-AUDIT
```
