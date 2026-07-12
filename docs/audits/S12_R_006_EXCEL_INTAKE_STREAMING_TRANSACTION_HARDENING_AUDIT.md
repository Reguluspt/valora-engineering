# S12-R-006 — Excel Intake Streaming & Transaction Hardening Audit

## Status
`LOCAL IMPLEMENTATION COMPLETE — READY FOR INDEPENDENT RE-AUDIT`

## Git Baseline
| Item | Value |
|---|---|
| Main baseline SHA | `ff40fda18a399afb01a76c6489aebf2f7cfd2d14` |
| Branch | `s12-r-006-excel-intake-streaming-transaction-hardening` |
| Draft PR | NOT CREATED |
| CI | PENDING |

## Root Cause Matrix

| # | Defect | Before | After |
|---|---|---|---|
| 1 | Unbounded file read | `file.file.read()` | SpooledTemporaryFile + chunked copy |
| 2 | Row materialization | `list(ws.iter_rows(...))` | Streaming `for row in ws.iter_rows(...)` |
| 3 | Silent truncation | Break at 5000 rows | Reject entire upload at 5001 |
| 4 | Sheet fallback | Silent fallback to first sheet | Exact match or error |
| 5 | Pre-parse delete | DB commit before parse success | Single atomic transaction |
| 6 | Header-keyed raw_values | Dict keys = header text → duplicates overwrite | Positional `cells` array |
| 7 | Blank headers lost | `""` key in dict | Column index/letter preserved |
| 8 | Missing ZIP/XLSX validation | No ZIP safety checks | Archive entry/expansion/encryption/VBA/external-link checks |
| 9 | Case-sensitive extension | `.xlsx` only | `.XLSX` accepted; `.xls/.xlsm/.xlsb` blocked |
| 10 | No failure audit | Only success audit | `ProjectAssetImportBatchUploadFailed` event |
| 11 | Inline parser logic | 175-line function in projects.py | Module: `excel_import/application/parse_workbook.py` |
| 12 | Audit after commit | Separate commit for audit | Staging replacement + audit in one transaction |

## Architecture

```
backend/app/modules/excel_import/
  __init__.py
  domain/__init__.py   — immutable limits, extensions, aliases
  application/
    __init__.py         — parse_uploaded_workbook (bounded streaming parser)
    replace_staging_rows.py — atomic replacement + success/failure audit
```

## Resource Limits (Default Production)

| Limit | Value |
|---|---|
| Max upload bytes | 10 MiB |
| Max request bytes | 12 MiB |
| Read chunk | 64 KiB |
| Max ZIP entries | 2048 |
| Max uncompressed ZIP | 100 MiB |
| Header search rows | 100 |
| Max data rows | 5000 (accepted) |
| 5001 data rows | Whole-upload rejection |
| Max physical rows | 5100 |
| Max columns | 100 |
| Max cell chars | 10000 |
| Max row chars | 100000 |

## ZIP/XLSX Policy
- Required parts: `[Content_Types].xml`, `xl/workbook.xml`
- Rejected: encrypted entries, VBA parts (`xl/vbaProject.bin`), external links (`xl/externalLinks/*`)
- Rejected: absolute paths, parent traversal entries
- `openpyxl` options: `read_only=True`, `data_only=True`, `keep_links=False`, `keep_vba=False`
- No external resource access, no formula evaluation, no macro execution

## Raw Cell Preservation
Stored as `raw_values: {"cells": [...]}` with positional representation:
```json
{
  "cells": [
    {"column_index": 1, "column_letter": "A", "header": "Tên tài sản", "value": "abc"},
    {"column_index": 2, "column_letter": "B", "header": "Tên tài sản", "value": "def"}
  ]
}
```
- Duplicate headers preserved separately (different column_letter)
- Blank headers preserved (empty string header, position only)
- Column order preserved
- Empty formula cells produce empty string values

## Transaction Sequence
1. Tenant-scope project + batch
2. `with_for_update()` row lock on batch
3. Delete old staging rows (in same transaction)
4. Insert new staging rows
5. Update batch filename/sheet/status/counters
6. Append `ProjectAssetImportBatchUploaded` AuditEvent
7. Single `db.commit()`

On failure:
1. Rollback replacement transaction (old staging preserved)
2. New transaction: set batch status to FAILED
3. Append `ProjectAssetImportBatchUploadFailed` AuditEvent
4. Commit failure atomically
5. Error payload: only sanitized filename, sheet, error code, limit category, previous row count

## Changed Files
```
backend/app/api/projects.py                               — removed inline parser, thin adapter only
backend/app/modules/excel_import/__init__.py              — new module init
backend/app/modules/excel_import/domain/__init__.py       — immutable limits/config
backend/app/modules/excel_import/application/__init__.py  — streaming parser
backend/app/modules/excel_import/application/replace_staging_rows.py — atomic replacement
backend/tests/check_security.py                           — +2 fail-closed blockers
backend/tests/test_check_security_blockers.py             — +4 security tests
backend/tests/test_asset_imports.py                       — raw_values format update
backend/tests/test_s12_r_006_excel_intake_hardening.py    — 16 new tests
```

## Test Results

| Suite | Tests | Status |
|---|---|---|
| Existing backend (all) | 329 | PASS (4 skipped) |
| New hardening tests | 16 | PASS |
| Security blocker tests | 7 | PASS (2 existing + 4 new file-read + 1 streaming) |
| **Total backend** | **341** | **PASS (4 skipped)** |

### Hardening Test Coverage
- File bounds: uppercase .XLSX accepted, .xls rejected, chunked limit exceeded
- ZIP safety: invalid ZIP, too many entries, encrypted
- Sheet selection: missing sheet, empty workbook
- Row limits: 5000 accepted, 5001 rejected
- Column limits: 100 accepted, 101 rejected
- Raw cells: duplicate headers, blank headers preserved
- Formula safety: not evaluated, string value only
- Re-upload: staging preserved on failure (invalid file)

### Static Security Scan
- Unbounded `file.file.read()` → BLOCKED
- `list(ws.iter_rows(...))` → BLOCKED
- Chunked read → allowed
- Streaming iteration → allowed

## Known Limitations
- PostgreSQL concurrency tests: not implemented locally (requires CI)
- No direct API-level row-limit test (parser unit tests cover this)
- Sheet selection test: empty workbook produces error from openpyxl (parse layer catches)

## Out of Scope
- Validation Engine (S12-PR-003)
- Apply/import to ProjectAssetLine
- AI-assisted column mapping
- No model/migration changes
- No frontend/worker changes
- No CI workflow changes

## Final Verdict
```text
LOCAL IMPLEMENTATION COMPLETE — READY FOR INDEPENDENT RE-AUDIT
```
