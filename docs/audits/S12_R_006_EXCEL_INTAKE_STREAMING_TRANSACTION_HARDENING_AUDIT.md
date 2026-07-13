# S12-R-006 — Excel Intake Streaming & Transaction Hardening Audit

## Status
`S12-R-006 LOCAL IMPLEMENTATION COMPLETE — AWAITING POSTGRESQL CI VERIFICATION`

## Git Baseline
| Item | Value |
|---|---|
| Main baseline SHA | `ff40fda18a399afb01a76c6489aebf2f7cfd2d14` |
| Branch | `s12-r-006-excel-intake-streaming-transaction-hardening` |
| Commit Q SHA | `1bbcefcbbf19df181c685e40b2da7d85aeb84c79` |
| Commit S SHA | `219e711774ed72c2ec6fed3c7447c35a2bfce7ac` |
| Commit R SHA (prior remote HEAD) | `d30ca7a98241e62303911276a12e3de453568dd6` |
| Commit T SHA (test collection restore) | `472ceb132536f3e8d8c055478f8d17a4acb10686` |
| Commit U SHA | this audit-only reconciliation commit (see branch HEAD after push) |
| Draft PR | NOT CREATED |
| CI | PENDING — PostgreSQL-gated tests not verified in this local run |
| **Backend pytest** | **370 passed, 5 skipped, 20 warnings** (zero failures) |
| **PostgreSQL** | **LOCALLY SKIPPED — REQUIRES CI WITH POSTGRESQL** |

### Lineage note
Order is forward-only: `… → Q → S → R → T → U`. Earlier corrective commits were not rewritten.

## Corrective work in Commit T
| Defect | Evidence | Fix |
|---|---|---|
| `test_outer_commit_failure` nested inside `test_success_audit_event_failure` | pytest collected only one outer-commit test; hardening suite 38 pass + 1 skip | Moved method to class-level indent so both node IDs collect |
| Incorrect staging name assertions (`Old0` vs seeded `O0`) | Would fail after collection restore | Assert exact seeded IDs + `O0/O1/O2` + batch metadata |
| pysqlite SAVEPOINT/RELEASE permanently committed outer work | RELEASE left replacement visible after `Session.rollback()`; fingerprint mismatch; zero `commit_failure` audits | Apply SQLAlchemy documented SQLite savepoint recipe on in-memory test engine only (`isolation_level=None` + explicit `BEGIN`) |
| Weak newer-success proof | Only checked filename/status | Assert full newer generation (sheet, total_rows, staging IDs/values, success audit) and zero stale `commit_failure` events |

No production runtime change was required. Transaction path in `import_service.py` already:
1. captures pre-fingerprint before replacement;
2. uses nested savepoint for replace + success audit;
3. outer `db.commit()`;
4. on post-savepoint failure: `db.rollback()` then `_recover_commit_failure` with fingerprint equality guard.

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

API adapter: `backend/app/api/projects.py`  
Primary tests: `backend/tests/test_s12_r_006_excel_intake_hardening.py`  
Security: `backend/tests/test_check_security_blockers.py`, `backend/tests/check_security.py`  
Design contract: `docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md`

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
| commit_failure | 500 | — |
| unexpected_error | 500 | — |

## Transaction Sequence
1. Tenant-scope + `with_for_update()` row lock on the batch record
2. Capture generation fingerprint (status, filename, sheet, total_rows, staging row IDs, latest success audit id)
3. Delete old staging + insert new + update batch + success audit in ONE nested transaction savepoint (`db.begin_nested()`)
4. RELEASE savepoint, then single outer `db.commit()`
5. On pre-release failure: rollback savepoint (old staging preserved), record failure AuditEvent if safe
6. On post-release outer commit failure: outer `db.rollback()`, re-lock batch, recompute fingerprint; if equal to pre-fingerprint log `commit_failure`; if mismatched (newer generation) abort failure logging

## Collected commit-failure node IDs
```text
tests/test_s12_r_006_excel_intake_hardening.py::TestTransactionFaultsCompleted::test_outer_commit_failure
tests/test_s12_r_006_excel_intake_hardening.py::TestTransactionFaultsCompleted::test_outer_commit_failure_with_newer_concurrent_success
```

## Local gate results (raw observed)

| Gate | Result |
|---|---|
| Backend ruff (`app` + `tests`) | All checks passed |
| Hardening collect-only | **40 tests collected** |
| Hardening suite | **39 passed, 1 skipped** |
| Both outer-commit tests | **2 passed** |
| Security blockers | **12 passed** |
| Security scanner `check_security.py` | Scan passed |
| Alembic heads | `db5977424e7b (head)` single head |
| Full backend pytest | **370 passed, 5 skipped, 20 warnings** |
| Worker ruff | All checks passed |
| Worker pytest | **1 passed** |
| Frontend lint (`tsc --noEmit`) | pass |
| Frontend build | pass (vite 6.4.3) |
| Frontend vitest | **15 files / 80 tests passed** |
| npm audit (`--omit=dev`) | **0 vulnerabilities** |

### Exact PostgreSQL skips (local)
```text
SKIPPED LOCALLY — REQUIRES CI WITH POSTGRESQL
tests/test_auth_endpoints.py::... (line 737) PostgreSQL not available
tests/test_s12_r_004_official_mutation.py (line 1049) No PostgreSQL URL configured
tests/test_s12_r_006_excel_intake_hardening.py::TestPGIsolatedConcurrencyRestored::test_concurrent_upload_serialization
tests/test_workbench_api.py (line 696) concurrent integration test
tests/test_workbench_api.py (line 980) unexpected-error rollback test
```

These skips are **not** counted as PASS.

## Preservation evidence (Commit T tests)

### Normal outer-commit failure (`test_outer_commit_failure`)
- Original staging IDs (`seeded_staging_ids`) and values `O0/O1/O2` retained after failed outer commit
- No `ProjectAssetImportBatchUploaded` success audit retained from the failed attempt
- Exactly one `ProjectAssetImportBatchUploadFailed` with `error_code=commit_failure`
- Batch filename/sheet/total_rows remain pre-attempt; status becomes `FAILED` via recovery audit path
- Orchestrator returns HTTP 500 with Vietnamese system error detail

### Newer-success protection (`test_outer_commit_failure_with_newer_concurrent_success`)
- After failed attempt rollback window, a full newer generation is landed (filename, sheet, total_rows=2, staging N0/N1, success audit)
- Recovery fingerprint mismatch prevents stale `commit_failure` logging
- Final batch remains `PARSED` / `newer_success.xlsx` / `NewerSheet` / total_rows=2
- Zero stale `commit_failure` AuditEvents on the newer generation

### ProjectAssetLine immutability
- `TestProjectAssetLineImmutabilityExpanded::test_line_immutable_snapshots` remains in suite and passed (6 failure-path snapshots)

## Remaining limitations
1. PostgreSQL concurrency and integration tests are **not** executed in this local environment; CI with PostgreSQL is required before claiming full environment parity.
2. Draft PR is intentionally **not** created by this task.
3. SQLite StaticPool cannot host a true second DB connection; newer-success concurrency is simulated in the recovery window on the same session with the real commit path. True multi-connection serialization remains the PG-gated test.
4. Untracked handoff / foreign onboarding files outside this task were left untouched.

## Final Verdict
```text
S12-R-006 LOCAL IMPLEMENTATION COMPLETE — AWAITING POSTGRESQL CI VERIFICATION
```
