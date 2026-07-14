# S12-PR-004 â€” Excel Staging Apply Command & Provenance Audit

## Status

```text
S12-PR-004 LOCAL IMPLEMENTATION COMPLETE â€” AWAITING DRAFT PR, CI, AND INDEPENDENT AUDIT
```

| Field | Value |
| --- | --- |
| Task | S12-PR-004 Excel Staging Apply Command & Provenance |
| Baseline `main` | `32024be43044097b185b6946499705f2560a9103` (S12-R-008 merge #9) |
| Branch | `s12-pr-004-excel-staging-apply-command-provenance` |
| Authority | ADR 0029 + staging contract Â§15 (`contract_version = s12-pr-004-v1`) |
| Draft PR | **Not created** in this session (independent audit first) |

## Scope delivered

- `POST /api/v1/projects/{project_id}/asset-imports/{batch_id}/apply` with `{ "confirm": true }`
- Application service under `excel_import/application/apply_staging.py`
- Lineage columns on `ProjectAssetLine` + Alembic migration `e1f2a3b4c5d6`
- Upload/validate reject `applied` batches
- Focused tests `tests/test_s12_pr_004_staging_apply.py` (+ PG Apply-vs-Apply skip without PG)

## Local quality gates

| Gate | Result |
| --- | --- |
| Focused PR-004 | **11 passed, 1 skipped** (PG concurrency) |
| Full backend pytest | **412 passed, 10 skipped, 20 warnings** |
| Backend Ruff | All checks passed |
| Alembic heads | single head `e1f2a3b4c5d6` |
| Worker | 1 passed |
| Frontend `npm test` | 80 passed / 15 files |

Local PostgreSQL skips are **SKIPPED**, not PASS.

## Commit lineage

| Commit | Role |
| --- | --- |
| A | `f6b492c67430c0186e56c527e7e36ba90755f131` |
| B | This audit-only evidence file |

## Remaining

- Draft PR + PostgreSQL CI (0 skips required for concurrency claims)
- Independent audit
- No Ready/merge in this session

## Final verdict

```text
S12-PR-004 LOCAL IMPLEMENTATION COMPLETE â€” AWAITING DRAFT PR, CI, AND INDEPENDENT AUDIT
```
