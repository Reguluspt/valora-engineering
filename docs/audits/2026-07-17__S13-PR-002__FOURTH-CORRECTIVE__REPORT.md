# S13-PR-002 Fourth Corrective Report

**Task ID:** S13-PR-002 fourth corrective
**PR:** [#15](https://github.com/Reguluspt/valora-engineering/pull/15) — **DRAFT — NOT READY / NOT MERGED**
**Branch:** `s13-pr-002-legacy-workbook-source-artifact`
**Starting SHA:** `4d56228216440a5c592812a7b210a92baa0b49dd`
**Base main snapshot:** `949903f3912aa65f8b990852756aeef7981bca08`
**Re-audit closed:** `2026-07-17__S13-PR-002__THIRD-CORRECTIVE-INDEPENDENT-RE-AUDIT__4D56228__REPORT.md` (FAIL F-01…F-09)

## 1. Design / ADR sources

- Design Book v1.4 §5.1–§5.3
- ADR 0030
- S13–S16 remediation plan §S13-PR-002
- `CODEX.md`, `ENGINEERING_GUARDRAILS.md`, `PR_RULES.md`

## 2. Commits / files changed (this corrective)

| Path | Change |
| --- | --- |
| `backend/app/modules/excel_import/application/source_artifact_service.py` | `_sha256_object(expected_size)`; reconciler txn close; UTC timestamp retention; hash-count short-read truth |
| `backend/app/modules/excel_import/infrastructure/object_storage.py` | `FakeObjectStorage.truncate_open_to` clean EOF short-read |
| `backend/tests/fixtures/s13_pr_002/ole_builder.py` | Expanded BIFF threat fixtures (DCON*, EXTERNNAME, VBA BOUNDSHEET, binary NAME, truncated) |
| `backend/tests/test_s13_pr_002_fourth_corrective.py` | D-01…D-10 proof suite |
| `docs/audits/2026-07-17__S13-PR-002__FOURTH-CORRECTIVE__REPORT.md` | This report |

## 3. D-01…D-10 closure matrix

| ID | Implemented | Executable proof (local unless noted) | Honest residual |
| --- | --- | --- | --- |
| **D-01** short-read vs checksum | Yes — hash+count one pass; short_read / object_too_large → infra; full stream wrong digest → checksum_mismatch | `test_short_read_not_checksum_mismatch`, `test_true_checksum_mismatch_after_full_stream`, `test_pending_object_missing_marks_failed`, `test_object_too_large_is_infra_not_checksum` | Raised-timeout path covered by third suite + Fake fail_open_stream; S3 body wrap already present |
| **D-02** reconciler txn close | Yes — snapshot IDs then rollback; per-item finally; empty/skip leave `in_transaction()==False` | `test_reconciler_empty_run_closes_transaction`, `test_reconciler_skip_paths_close_transaction` | Real PG lock-idle probe not run locally (CI PG env) |
| **D-03** non-empty official lines | Yes — `_seed_prior_full` creates ProjectAssetLine + field snapshot | `test_threat_http_preserves_prior_official_and_staging` asserts line_count≥1 and field equality | — |
| **D-04** BIFF threat matrix | Yes — 12 threats via HTTP with prior current + staging + lines | parametrized `THREATS` HTTP 400 + preservation | Synthetic OLE only; not live Excel macros |
| **D-05** formula cache | Yes for xlsx (inject OOXML `<v>` cache); xls non-execution | `test_xlsx_cached_formula_value` exact 20; formula text remains in non-data_only mode; `test_xls_formula_value_not_formula_text` | xlrd 2.x does not surface BIFF formula cache as a known number; proves non-execution / no formula string as value |
| **D-06** boundaries | Sample exact/max+1 for sheets, rows, cols, row chars, merges, cell chars, total cells (xlsx+xls iter) + endpoint cell limit | named boundary tests + `test_endpoint_cell_limit_no_reservation` | Not every limit for both formats at endpoint (upload/file/request bytes, ZIP entries/expansion partial via prior suites) |
| **D-07** failure ordering / retention | Retention boundary, current never deleted, multi-item later infra keeps earlier failed | `test_orphan_retention_boundary`, `test_referenced_current_source_never_deleted`, `test_multi_item_later_error_keeps_earlier_failed` | Full failpoint matrix (reservation commit fail, stale generation race, delete-then-audit fail repair) **not** fully instrumented; prior third suite covers late ref-check + per-item commit |
| **D-08** PG constraints | Prior third suite + CI | Local skip without `TEST_DATABASE_URL`; CI must run third PG DML + fourth migration | Fourth suite does not re-duplicate every IntegrityError identity assertion |
| **D-09** migration round-trip | Yes — throwaway DB parent→f2a3b4c5d6e7→downgrade→head | `test_pg_migration_roundtrip_s13` (CI-required) | Local skip without PG |
| **D-10** docs / evidence | This report distinguishes implemented vs proven | Local raw counts below; exact-tip CI URL filled after green CI | — |

### Retention timezone fix (extra)

SQLite returns naive datetimes; `datetime.timestamp()` on naive values uses **local** time. On UTC+7 hosts both orphans appeared past retention. `_as_utc_timestamp()` treats naive as UTC wall-clock.

## 4. Local gates (pre-push)

```text
ruff check (touched paths)                     PASS
git diff --check                               PASS (CRLF warnings only)
alembic heads                                  f2a3b4c5d6e7 (single head)
python tests/check_security.py                 PASS
S13 suites (4 files)                           86 passed, 6 skipped
full backend pytest                            624 passed, 26 skipped
```

### Local skips (S13 four files)

```text
test_s13_pr_002_source_artifacts.py         MinIO — no S3_ENDPOINT_URL
test_s13_pr_002_second_corrective.py     PG — no TEST_DATABASE_URL
test_s13_pr_002_third_corrective.py      MinIO + PG
test_s13_pr_002_fourth_corrective.py     PG migration round-trip + MinIO
```

CI=true paths assert env is present (no silent skip of PG/MinIO proofs).

## 5. Exact-tip CI

```text
Final SHA:     <filled after push>
CI run URL:    <filled after green>
CI head match: required exact tip
Jobs:          backend / frontend / worker
```

## 6. Scope statement

Allowed only: `.xls`/`.xlsx` adapters, immutable source-artifact lifecycle/storage/reconcile, S13 ORM/Alembic invariants, synthetic fixtures/tests/audit docs for this slice.

**Not in this corrective:** S13-PR-003 structure discovery / Column Mapping Memory, Asset Identity Memory, Word extraction, AI/provider runtime, S12 staging/Apply mutation path changes, source-artifact mutation of staging or `ProjectAssetLine`.

## 7. Known limitations

1. D-07 full deterministic failpoint matrix incomplete (reservation/final-commit/stale-gen).
2. D-05 `.xls` exact numeric formula cache not proven under xlrd 2.x; non-execution proven.
3. D-06 not every bound for every format at HTTP layer.
4. D-08 constraint identity matrix still primarily third-corrective PG test + migration round-trip.
5. Independent re-audit still required before Ready/merge.

## 8. Final status

**DRAFT — NOT READY / NOT MERGED — AWAITING INDEPENDENT CODE RE-AUDIT.**
