# S12-R-006 — Excel Intake Streaming & Transaction Hardening Audit

## Status
`CORRECTIVE IMPLEMENTATION COMPLETE — READY FOR INDEPENDENT RE-AUDIT`

## Git Baseline
| Item | Value |
|---|---|
| Main baseline SHA | `ff40fda18a399afb01a76c6489aebf2f7cfd2d14` |
| Branch | `s12-r-006-excel-intake-streaming-transaction-hardening` |
| Original implementation SHA | `9f2d607c3e381aa9dce40f10f892495edddaf9f5` (Commit A) |
| Original audit SHA | `6b0f234135d745d63c377d809d1fb64bfb677998` (Commit B) |
| Corrective code SHA | `97b827a43a3faec8e65716be6c39676d43a6a046` (Commit C) |
| Corrective audit SHA | `PENDING` (Commit D) |
| Draft PR | NOT CREATED |
| CI | PENDING |

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
| Backend pytest | 365 | PASS (5 skipped) |
| Hardening tests | 34 | PASS (33 passed, 1 skipped) |
| Security blockers | 8 | PASS (unbounded read, BytesIO copy, list(iter_rows), chunked, streaming) |
| Security scanner | — | PASS |

### Skipped (local)
5 PostgreSQL-gated: `test_auth_endpoints.py:737`, `test_s12_r_004_official_mutation.py:1049`, `test_s12_r_006_excel_intake_hardening.py:376`, `test_workbench_api.py:696`, `test_workbench_api.py:980`
SKIPPED — REQUIRES CI WITH POSTGRESQL

## Known Limitations
- No PostgreSQL concurrency test locally
- No API-level row-limit integration test (parser unit tests cover)

## Out of Scope
- Validation Engine, Apply, AI mapping
- No model/migration/frontend/worker/CI changes
- No ProjectAssetLine mutation

## Final Verdict
```text
CORRECTIVE IMPLEMENTATION COMPLETE — READY FOR INDEPENDENT RE-AUDIT
```
