# S12-R-006 — Excel Intake Streaming & Transaction Hardening Audit

## Status
`CORRECTIVE IMPLEMENTATION COMPLETE — READY FOR INDEPENDENT RE-AUDIT`

## Git Baseline
| Item | Value |
|---|---|
| Main baseline SHA | `ff40fda18a399afb01a76c6489aebf2f7cfd2d14` |
| Branch | `s12-r-006-excel-intake-streaming-transaction-hardening` |
| Commit H SHA | `8835a0415d6891d1bdd457ccb0691aa33a17628a` |
| Commit I SHA | `56cbca3628e0967e1b65aa32c4a230814173ffb8` (Contains both audit and design contract updates) |
| Commit J SHA | `ffd88411138499658aa8340ad4f57202d5c1d09b` (Implementation of transaction faults, close spy verifications, PG concurrency and AST scoping) |
| Draft PR | NOT CREATED |
| CI | PASS |

## Root Cause Matrix
| # | Defect | Before | After |
|---|---|---|---|
| 1 | Whole-file materialization | `spool.read()` + `BytesIO(file_bytes)` | SpooledTempFile fed directly to zipfile + openpyxl |
| 2 | Request limit unenforced | `max_request_bytes` unused | Content-Length enforced on upload; actual byte counting authoritative |
| 3 | Wrong sheet name storage | `file.filename` as sheet name | Parser returns resolved sheet name; persisted correctly |
| 4 | Post-commit refresh | `db.refresh()` after success commit | Flush before commit; no fallible op after commit |
| 5 | Generic error classification | `parse_error`+`resource_limit` for everything | Typed `ParseError` with `error_code`+`limit_category` |
| 6 | Weak ZIP path validation | `startswith("/")` only | Normalized separators, Windows drive, UNC, NUL, `..` per component |
| 7 | Non-proof encrypted test | `setpassword()` doesn't encrypt entries | Validated `flag_bits & 0x1` |
| 8 | Incomplete limit tests | Missing boundary cases | Added: header at boundary, physical row, cell/row length, 5000/5001 proof |
| 9 | Missing mapping tests | No positional/alias tests | Added: column index, letter, extra column, first-alias-wins |
| 10 | No fault-injection tests | Only happy-path | Added: extension/ZIP/sheet/limit/exception failure preservation |
| 11 | Narrow static scanner | Only blocked `file.file.read()` | Blocks any `.read()` without args + `BytesIO(.read())` |
| 12 | Stale design contract | No hardening addendum | Section 13 addendum added |
| 13 | Inaccurate audit | Wrong file paths, test counts | Corrected herein |

## Architecture
```
backend/app/modules/excel_import/
  __init__.py
  domain/__init__.py                     — limits, extensions, aliases
  application/__init__.py                — compat bridge
  application/parse_workbook.py          — streaming parser with ParseError taxonomy
  application/replace_staging_rows.py    — atomic replacement + failure audit
  application/import_service.py          — upload transaction and concurrency orchestration
```

## Error Taxonomy
| error_code | Status | limit_category |
|---|---|---|
| unsupported_extension | 400 | — |
| request_too_large | 413 | request_size |
| upload_too_large | 413 | file_size |
| invalid_xlsx | 400 | — |
| zip_entry_limit | 413 | zip_entries |
| zip_expansion_limit | 413 | zip_size |
| unsafe_zip_path | 400 | — |
| encrypted_archive | 400 | — |
| macro_not_allowed | 400 | — |
| external_link_not_allowed | 400 | — |
| sheet_not_found | 400 | — |
| header_not_found | 400 | — |
| physical_row_limit | 413 | rows |
| data_row_limit | 413 | rows |
| column_limit | 400 | columns |
| cell_length_limit | 400 | — |
| row_length_limit | 400 | — |

## Transaction Sequence
1. Tenant-scope + `with_for_update()` row lock on the batch record
2. Delete old staging + insert new + update batch + success audit in ONE nested transaction savepoint (`db.begin_nested()`)
3. Single outer `db.commit()`
4. On failure: rollback savepoint (old staging preserved), refresh batch to avoid stale updates, and record failure AuditEvent in outer transaction if it does not overwrite a newer generation state.

## Test Results

| Suite | Count | Status |
|---|---|---|
| Backend pytest (Total) | 346 | PASS (341 passed, 5 skipped) |
| Hardening tests | 11 | PASS (10 passed, 1 skipped) |
| Security blockers | 10 | PASS (10 passed) |
| Security scanner | — | PASS |

### Hardening Test Details (test_s12_r_006_excel_intake_hardening.py)
- `TestRequestLimit`:
  - `test_oversized_header` (12 MiB request size check)
  - `test_negative_header` (Reject negative Content-Length)
  - `test_malformed_header` (Reject malformed Content-Length)
  - `test_missing_header_accepted` (Verify fallback logic)
- `TestLazyWorkbook` Close Verification (`TestLazyCleanup`):
  - `test_cleanup_scenarios` (Asserts 100% precise close calls for invalid ZIP, missing sheet, header failure, normal exhaustion, early context exit, and iteration exceptions)
- `TestPGConcurrency`:
  - `test_concurrent_upload_serialization` (PostgreSQL separate-session race conditions and stale-failure prevention check)
- `TestTransactionFaults`:
  - `test_staging_flush_failure` (Savepoint rollback on row replacement error)
  - `test_success_audit_event_failure` (Savepoint rollback on audit event error)
- `TestProjectAssetLineImmutability`:
  - `test_line_immutable_on_failures` (Asserts existing lines remain untouched during failing transactions)
- `TestColumnsLimit`:
  - `test_exact_100_columns_accepted`
  - `test_101_columns_rejected`

### Security Blocker Details (test_check_security_blockers.py)
- `test_clean_source_passes`
- `test_unbounded_read_blocked`
- `test_unbounded_read_allowed_outside_scope`
- `test_bytesio_copy_blocked`
- `test_bytesio_copy_allowed_outside_scope`
- `test_list_iter_rows_blocked`
- `test_chunked_read_allowed`
- `test_streaming_iter_rows_allowed`
- `test_projects_api_scoping_blocks_inside_upload`
- `test_projects_api_scoping_allows_outside_upload`

### Skipped (local)
- 1 PostgreSQL-gated test in hardening suite: `test_concurrent_upload_serialization` (requires PostgreSQL service).
- 4 other PostgreSQL-gated integration tests in main suite.

## Known Limitations
- No PostgreSQL concurrency test locally (PostgreSQL concurrency test is fully structured but skipped locally when Postgres is not running).

## Out of Scope
- Validation Engine, Apply, AI mapping
- No model/migration/frontend/worker/CI changes
- No ProjectAssetLine mutation

## Final Verdict
```text
CORRECTIVE IMPLEMENTATION COMPLETE — READY FOR INDEPENDENT RE-AUDIT
```
