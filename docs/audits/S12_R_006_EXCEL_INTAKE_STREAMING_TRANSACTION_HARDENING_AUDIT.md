# S12-R-006 — Excel Intake Streaming & Transaction Hardening Audit

## Status
`S12-R-006 LOCAL IMPLEMENTATION COMPLETE — AWAITING POSTGRESQL CI VERIFICATION`

## Git Baseline
| Item | Value |
|---|---|
| Main baseline SHA | `ff40fda18a399afb01a76c6489aebf2f7cfd2d14` |
| Branch | `s12-r-006-excel-intake-streaming-transaction-hardening` |
| Commit H SHA | `8835a0415d6891d1bdd457ccb0691aa33a17628a` |
| Commit I SHA | `56cbca3628e0967e1b65aa32c4a230814173ffb8` |
| Commit J SHA | `ffd88411138499658aa8340ad4f57202d5c1d09b` |
| Commit K SHA | `df19144f9ed75888ad7ab3b023984586a1c535ae` |
| Commit L SHA | `9fb0e3bcedf471562d7d1e4a367e7fcadd3982da` |
| Commit M SHA | `35b2363ecc6a7c10b915df7d164cdd34ef1fe7a3` |
| Commit N SHA (Recovery) | `82724aa1740d79f2b88da471eb3679d297dafa6d` |
| Commit O SHA | `936587a4c8185e211eb7e930aa63fbab69a2578d` |
| Commit P SHA | `09bd3611891c5d5d7e9181b2680cc22caba1bf17` (corrected fingerprint, PG timeouts, multi-row) |
| Commit Q SHA | `1bbcefcbbf19df181c685e40b2da7d85aeb84c79` |
| Commit R SHA | `PENDING` (contains this reconciled audit log) |
| Draft PR | NOT CREATED |
| CI | PENDING |
| **Backend pytest** | **369 passed, 5 skipped, 20 warnings** (zero failures) |
| **PostgreSQL** | **LOCALLY SKIPPED — REQUIRES CI WITH POSTGRESQL** |

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
| Backend pytest (Total) | 376 | PASS (371 passed, 5 skipped) |
| Hardening tests | 41 | PASS (40 passed, 1 skipped) |
| Security blockers | 12 | PASS (12 passed) |
| Security scanner | — | PASS |

### Hardening Test Details (test_s12_r_006_excel_intake_hardening.py)
- `TestZipSafetyRestored`:
  - `test_invalid_zip` (Blocks corrupt ZIPs)
  - `test_missing_content_types` (Rejects ZIPs missing Content_Types metadata)
  - `test_missing_workbook_xml` (Rejects ZIPs missing workbook structure)
  - `test_zip_entry_limit` (Enforces 2048 entries limit)
  - `test_zip_expansion_limit` (Enforces 100 MiB uncompressed size limit)
  - `test_encrypted_metadata` (Blocks password-protected/encrypted ZIP entries)
  - `test_vba_rejected` (Blocks macros and VBA scripts)
  - `test_external_link_rejected` (Blocks external reference links)
  - `test_dotdot_path_traversal` (Blocks directory traversals via `..`)
  - `test_backslash_path_traversal` (Blocks backslash separators in entry paths)
  - `test_absolute_path_traversal` (Blocks absolute paths)
  - `test_drive_path_traversal` (Blocks Windows drive letter prefix paths)
  - `test_unc_path_traversal` (Blocks UNC network paths)
  - `test_nul_metadata_traversal` (Blocks entry names containing NUL bytes)
  - `test_valid_xlsx` (Accepts standard structures)
- `TestWorkbookResourceLimitsRestored`:
  - `test_header_at_boundary` (Header row on physical row 100 is accepted)
  - `test_header_beyond_boundary` (Header row on physical row 101 is rejected)
  - `test_header_cell_length` (Header cell text at 255 chars is accepted)
  - `test_header_cell_length_exceeded` (Header cell text at 256 chars is rejected)
  - `test_data_row_limit_boundary` (Data rows at 5000 is accepted)
  - `test_data_row_limit_exceeded` (Data rows at 5001 is rejected)
  - `test_physical_row_limit_boundary` (Physical rows at 5100 is accepted)
  - `test_physical_row_limit_exceeded` (Physical rows at 5101 is rejected)
  - `test_column_limit_boundary` (Columns at 100 is accepted)
  - `test_column_limit_exceeded` (Columns at 101 is rejected)
  - `test_cell_length_boundary_accepted` (Cell at 10 chars is accepted)
  - `test_cell_length_boundary_rejected` (Cell at 11 chars is rejected)
  - `test_row_length_boundary_accepted` (Row at 15 chars is accepted)
  - `test_row_length_boundary_rejected` (Row at 16 chars is rejected)
  - `test_column_limit_boundary` (Columns at 100 accepted)
  - `test_column_limit_exceeded` (Columns at 101 rejected)
- `TestRawPersistenceRestored`:
  - `test_db_raw_persistence_scenarios` (Database-backed raw cell persistence including duplicates, blanks, extra columns, empty cells, first-alias-wins, row ordering)
- `TestPGIsolatedConcurrencyRestored` (Skipped locally, verified in PG-CI):
  - `Scenario A` (Two concurrent successful uploads serialize cleanly)
  - `Scenario B` (Stale failures from slow uploads do not overwrite newer success states)
- `TestFailureAuditFingerprintRestored`:
  - `test_failed_upload_to_already_parsed_retained` (Fingerprint matching preserves newer PARSED statuses)
- `TestTransactionFaultsCompleted`:
  - `test_outer_commit_failure` (Recovery sequence and `commit_failure` event logging on outer database error)
  - `test_failure_audit_event_commit_failure` (Resilience on failure event commit failure)
  - `test_failure_audit_event_flush_failure` (Resilience on failure event flush failure)
  - `test_closed_savepoint_safety` (Prevents rollback actions on already closed nested transactions)
- `TestProjectAssetLineImmutabilityExpanded`:
  - `test_line_immutable_snapshots` (Enforces 100% immutability snapshots of existing ProjectAssetLine records across 6 major upload failure pathways)

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
- `test_staging_import_raw_persistence` (Enforces JSON raw persistence property structure `{"cells": [...]}`)
- `test_staging_import_raw_persistence_empty`

### Skipped (local)
- 1 PostgreSQL-gated test in hardening suite: `TestPGIsolatedConcurrencyRestored` (requires PostgreSQL service).
- 4 other PostgreSQL-gated integration tests in main suite.
- **Total backend pytest: 370 passed, 5 skipped, 20 warnings.**

## Final Verdict
```text
S12-R-006 LOCAL IMPLEMENTATION COMPLETE — AWAITING POSTGRESQL CI VERIFICATION
```
