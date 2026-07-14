# S12-PR-003 — Excel Staging Validation Engine Audit

## Status
```text
S12-PR-003 MICRO-CORRECTIVE CI PASS — AWAITING INDEPENDENT RE-AUDIT
```

| Field | Value |
|---|---|
| Task | S12-PR-003 Excel Staging Validation Engine |
| Independent re-audit (prior) | **PASS WITH FIXES** (merge blocked pending micro-corrective proof) |
| Baseline `main` | `5bef98c25bc0bdfb386c68312a80f104a51769c6` |
| Branch | `s12-pr-003-excel-staging-validation-engine` |
| Draft PR | **#8** — https://github.com/Reguluspt/valora-engineering/pull/8 (open, draft=true) |
| Micro-corrective test head | `060656ee411675d94b5c237022efb523a826dc32` |
| Independent re-audit after micro-corrective | **PENDING** |

## Closed findings (do not reopen without new failing proof)

| ID | Status | Evidence |
|---|---|---|
| F-1 null-aware fingerprint | Closed | `build_validation_fingerprint()` stores raw `(proposed_asset_name, proposed_quantity)` pairs |
| F-2 / PG-A both workers succeed | Closed | Both threads terminate; `errors==[]`; 2 success audits; 0 failure audits |
| Prior code-bearing CI (`d92de3a…`) | Historical green | Runs `29309650043` / `29309651857` — 410 passed, 0 skipped |
| Prior doc-head CI (`e6916c3…`) | Historical green | Runs `29309763245` / `29309765175` — 410 passed, 0 skipped |
| Failed run on `d1e9397…` | Superseded | Run `29309479822` not authoritative |

## Micro-corrective findings R-1…R-4

| ID | Finding | Resolution |
|---|---|---|
| R-1 | PG-B used sleep / sequential finish as lock proof | Both orders observe the second backend in `pg_stat_activity.wait_event_type == 'Lock'` before releasing the first holder |
| R-2 | PG-C/D incomplete snapshots | Exact status, counters, ordered rows/validation fields, exact audit cardinality/order, official-line immutability |
| R-3 | Fault injections not at real flush/savepoint/persist points | Explicit post-audit `db.flush()`, real nested savepoint release fail, outer commit fail, failure-audit after stage, full pre/post snapshots |
| R-4 | Audit overstatement | This document lists only nodes and assertions present in the test file and raw CI logs |

## Design authority (unchanged)

Contract §14 + owner package 2026-07-13. Rules v1 unchanged: `asset_name_required`, `quantity_invalid`; warnings always empty; success → `ready_for_review`; engine failure → `validation_failed` + fingerprint-guarded failure audit. Staging-only; never mutates `ProjectAssetLine`.

## Micro-corrective commits

| Commit | SHA | Paths |
|---|---|---|
| Test-only lock/rollback proof | `060656ee411675d94b5c237022efb523a826dc32` | `backend/tests/test_s12_pr_003_staging_validation.py` only |
| Audit-only evidence | this commit | `docs/audits/S12_PR_003_EXCEL_STAGING_VALIDATION_ENGINE_AUDIT.md` only |

No production code changed in the micro-corrective pass.

## Exact test inventory (micro-corrective nodes)

### Fingerprint (SQLite unit) — unchanged
- `TestFingerprintNullAwareness::test_fingerprint_differs_null_vs_literal_none_asset_name`
- `…_quantity`
- `…_empty_string_vs_null`
- `…_identical_typed_inputs_same_generation`
- `…_row_order_deterministic_by_id`

### Fault injection (SQLite) — R-3
| Node | Injection point |
|---|---|
| `test_rule_evaluation_failure_records_exact_failure_audit` | `_apply_validation_to_rows` raises |
| `test_flush_failure_after_audit_preserves_generation` | explicit `db.flush()` after `_record_success_audit` staged (flush restored for recovery) |
| `test_savepoint_commit_failure_preserves_generation` | real nested savepoint `commit()`/release raises after success path staged |
| `test_outer_commit_failure_exact_failure_audit` | first outer `db.commit()` raises |
| `test_failure_audit_persistence_failure_preserves_pre_attempt` | after `_record_failure_audit` stages status+audit, raise before recover commit |
| `test_stale_failure_does_not_overwrite_newer_generation` | newer generation committed before recover; fingerprint mismatch |

Matched-fingerprint failure assertions (rule/flush/savepoint/outer-commit):
- staging generation + counters + row validation fields preserved from pre-attempt;
- batch becomes `validation_failed`;
- exactly one new failure audit; zero new success audits;
- failure payload keys exact: `rule_set_version`, `organization_id`, `project_id`, `batch_id`, `source_status`, `error_code`;
- `error_code == validation_engine_failed`;
- client detail is safe Vietnamese without technical exception text;
- full `ProjectAssetLine` snapshot unchanged.

Failure-audit persistence failure: full pre-attempt snapshot (including status and zero failure audits) restored.

Stale failure: complete newer generation + success audit IDs unchanged; zero failure audits added.

### PostgreSQL concurrency (CI-required; local skip without PG)

**Lock-wait observation method (R-1):** for each PG-B order, the second worker publishes `pg_backend_pid()` on its session, then enters the real upload/validation path that issues `SELECT … FOR UPDATE`. The test polls `pg_stat_activity` until `wait_event_type = 'Lock'` for that PID. No sleep is used as synchronization proof (bounded poll only while waiting for the observed lock wait). Hooks/monkeypatches restored in `finally`.

| Node | Proof |
|---|---|
| `TestPGValidationConcurrency::test_pg_a_two_validations_same_batch_both_succeed` | both succeed; 2 success / 0 failure; exact rows/counters |
| `…::test_pg_b_upload_then_validation_serial_orders` **order 1** | upload holds lock (SlowXlsx mid-read); validation Lock-wait observed; release → upload then validation; final `ready_for_review` + exact NewU generation; audits **Uploaded → ValidationSucceeded**; 0 failures |
| `…::test_pg_b_…` **order 2** | validation holds lock after FOR UPDATE (gated `build_validation_fingerprint`); upload Lock-wait observed; release → validation then upload replace; final complete `parsed` NewU generation; audits **ValidationSucceeded → Uploaded**; 0 failures |
| `…::test_pg_c_stale_validation_failure_vs_newer_success` | exact newer parsed generation (filename/sheet/counters/rows/validation fields); exactly 1 upload success; 0 validation success; 0 failure audits; line immutable |
| `…::test_pg_d_different_batches_independent` | per batch exact status/counters/rows/validation; 1 success / 0 failure each; no audit cross-contamination; both lines immutable |

## Local results (micro-corrective)

| Suite | Result |
|---|---|
| Focused PR-003 | **31 passed, 4 skipped** (PG-A…D) |
| Full backend | **401 passed, 9 skipped, 20 warnings** |
| R006 + security blockers | green |
| Security scanner | PASS |
| Ruff (backend) | All checks passed |
| Alembic heads | single head `db5977424e7b` |
| Worker | 1 passed |
| Frontend `npm test` | 80 passed / 15 files |
| npm audit --audit-level=high | 0 vulnerabilities |

### Exact local skips (SKIPPED ≠ PASS)
1. `tests/test_auth_endpoints.py` — PostgreSQL not available
2. `test_pg_a_two_validations_same_batch_both_succeed`
3. `test_pg_b_upload_then_validation_serial_orders`
4. `test_pg_c_stale_validation_failure_vs_newer_success`
5. `test_pg_d_different_batches_independent`
6. `tests/test_s12_r_004_official_mutation.py` — PG concurrency
7. `tests/test_s12_r_006_excel_intake_hardening.py` — PG concurrency
8. `tests/test_workbench_api.py` concurrent integration
9. `tests/test_workbench_api.py` unexpected-error rollback

## Code-bearing micro-corrective CI (head `060656e…`)

| Run | Event | Conclusion | Backend |
|---|---|---|---|
| **29311905024** (#112) | push | SUCCESS | **410 passed, 0 skipped, 27 warnings** |
| **29311906952** (#113) | pull_request | SUCCESS | **410 passed, 0 skipped, 27 warnings** |

- https://github.com/Reguluspt/valora-engineering/actions/runs/29311905024
- https://github.com/Reguluspt/valora-engineering/actions/runs/29311906952

Jobs: backend / worker / frontend SUCCESS. PostgreSQL skip count: **0**. All four PG matrix tests executed under CI.

## Documentation-head CI

Recorded after this audit-only commit (no further evidence-loop commit).

## Limitations

- Independent re-audit still required after this micro-corrective.
- PR remains Draft.
- Validation rule catalog still v1 only (two rules).
- No Apply / AI / frontend import UX in this task.
- SQLite fault injection proves transaction/recovery semantics; real multi-session locking is proven only on PostgreSQL in CI.

## Final verdict
```text
S12-PR-003 MICRO-CORRECTIVE CI PASS — AWAITING INDEPENDENT RE-AUDIT
```
