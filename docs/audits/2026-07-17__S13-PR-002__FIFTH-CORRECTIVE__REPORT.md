# S13-PR-002 Fifth Corrective Report

**Task ID:** S13-PR-002 fifth corrective
**PR:** #15 Draft — NOT READY / NOT MERGED
**Branch:** `s13-pr-002-legacy-workbook-source-artifact`
**Starting SHA:** `85c46a50fa2fc8485460d1f7d5915c5ac313bc6d`
**Base main:** `949903f3912aa65f8b990852756aeef7981bca08`

Exact final tip SHA and CI URL are recorded in the discovery artifact after green CI
(no post-CI docs-only commit on this branch tip).

## Files changed

| Path | Role |
| --- | --- |
| `source_artifact_service.py` | E-01 upload size-aware verify; E-02 clean-session ownership |
| `xls_safety.py` | E-03 BIFF FORMULA numeric cache extract (no eval) |
| `xls_adapter.py` | Overlay formula cache when xlrd returns empty |
| `ole_builder.py` | `write_xls_formula_cached` fixture |
| `test_s13_pr_002_fifth_corrective.py` | E-01…E-08 executable proofs |
| `test_s13_pr_002_fourth_corrective.py` | Align txn tests with clean-session model |
| This report | Evidence (no placeholders for local gates) |

## E-01…E-08 closure

| ID | Fix | Primary tests |
| --- | --- | --- |
| E-01 | Upload read-back uses `_sha256_object(..., expected_size=)` | `test_e01_upload_short_read_not_checksum_mismatch` |
| E-02 | Clean-session precondition (409) before any query; owns session only when clean | `test_e02_reconciler_rejects_dirty_caller_session`, empty/skip txn tests |
| E-03 | BIFF FORMULA IEEE cache extract + adapter overlay; exact 6.0 | `test_e03_xls_exact_cached_formula_value` |
| E-04 | Boundary matrix xlsx/xls inspect + iter + zip + merges + endpoints | `test_e04_*` |
| E-05 | Failpoints: reservation, missing/short/timeout/checksum, residual→orphan, retention, max_items, multi-item | `test_e05_*` |
| E-06 | `IntegrityError` + `orig.diag.constraint_name` matrix | `test_e06_pg_constraint_identity_matrix` (CI PG) |
| E-07 | Throwaway `CREATE DATABASE` full RT + checks/FKs/indexes | `test_e07_throwaway_pg_migration_roundtrip` (CI PG) |
| E-08 | Local gates below; CI tip in discovery | `test_e08_s3_minio_roundtrip_ci` |

## Local gates (pre-push)

```text
ruff check (touched)     PASS
check_security.py        PASS
alembic heads            f2a3b4c5d6e7
S13 five suites          116 passed, 9 skipped
full backend pytest      654 passed, 29 skipped
```

### Local skips (env)

PostgreSQL / MinIO tests skip without `TEST_DATABASE_URL` / `S3_ENDPOINT_URL`.
CI=true requires those env vars (no silent skip).

## Scope

Allowed S13-PR-002 only. No S13-PR-003, AI, Word, S12 Apply mutation of staging/lines.

## Status

**DRAFT — NOT READY / NOT MERGED — AWAITING INDEPENDENT CODE RE-AUDIT.**
