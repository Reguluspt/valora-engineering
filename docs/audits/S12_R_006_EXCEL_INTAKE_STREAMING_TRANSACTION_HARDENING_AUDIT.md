# S12-R-006 — Excel Intake Streaming & Transaction Hardening Audit

## Status
`CORRECTIVE IMPLEMENTATION COMPLETE — READY FOR INDEPENDENT RE-AUDIT`

## Git Baseline
| Item | Value |
|---|---|
| Main baseline SHA | `ff40fda18a399afb01a76c6489aebf2f7cfd2d14` |
| Branch | `s12-r-006-excel-intake-streaming-transaction-hardening` |
| Verified starting HEAD | `160c2799b7b09aa3e4966594506595cf8c1c64f2` |
| Draft PR | NOT CREATED |
| CI | PASS |

## Root Cause Matrix
| # | Defect | Before | After |
|---|---|---|---|
| 1 | Whole-file materialization | `spool.read()` + `BytesIO(file_bytes)` | SpooledTempFile fed directly to zipfile + openpyxl |
| 2 | Duplicate row accumulation | `staged_rows` + `raw_cells_list` | Single `staged_rows` list with `raw_cells` embedded |
| 3 | Request limit unenforced | `max_request_bytes` unused | Content-Length enforced on upload; actual byte counting authoritative |
| 4 | Wrong sheet name storage | `file.filename` as sheet name | Parser returns resolved sheet name; persisted correctly |
| 5 | Post-commit refresh | `db.refresh()` after success commit | Flush before commit; no fallible op after commit |
| 6 | Generic error classification | `parse_error`+`resource_limit` for everything | Typed `ParseError` with `error_code`+`limit_category` |
| 7 | Weak ZIP path validation | `startswith("/")` only | Normalized separators, Windows drive, UNC, NUL, `..` per component |
| 8 | Non-proof encrypted test | `setpassword()` doesn't encrypt entries | Validated `flag_bits & 0x1` |
| 9 | Incomplete limit tests | Missing boundary cases | Added: header at boundary, physical row, cell/row length, 5000/5001 proof |
| 10 | Missing mapping tests | No positional/alias tests | Added: column index, letter, extra column, first-alias-wins |
| 11 | No fault-injection tests | Only happy-path | Added: extension/ZIP/sheet/limit/exception failure preservation |
| 12 | Narrow static scanner | Only blocked `file.file.read()` | Blocks any `.read()` without args + `BytesIO(.read())` |
| 13 | Stale design contract | No hardening addendum | Section 13 addendum added |
| 14 | Inaccurate audit | Wrong file paths, test counts | Corrected herein |

## Architecture
```
backend/app/modules/excel_import/
  __init__.py
  domain/__init__.py                     — limits, extensions, aliases
  application/__init__.py                — compat bridge
  application/parse_workbook.py          — streaming parser with ParseError taxonomy
  application/replace_staging_rows.py    — atomic replacement + failure audit
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
1. Tenant-scope + `with_for_update()` row lock
2. Delete old staging + insert new + update batch + success audit in ONE TX
3. Single `db.commit()`
4. On failure: rollback (old staging preserved), then failure TX: FAILED status + failure audit

## Test Results

| Suite | Count | Status |
|---|---|---|
| Backend pytest | 358 | PASS (353 passed, 5 skipped) |
| Hardening tests | 25 | PASS (24 passed, 1 skipped) |
| Security blockers | 10 | PASS (10 passed) |
| Security scanner | — | PASS |

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
