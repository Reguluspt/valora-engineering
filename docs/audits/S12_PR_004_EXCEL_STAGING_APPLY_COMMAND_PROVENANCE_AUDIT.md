# S12-PR-004 - Excel Staging Apply Command and Provenance Audit

## Status

```text
S12-PR-004 CORRECTIVE IMPLEMENTATION COMPLETE - AWAITING POSTGRESQL CI AND INDEPENDENT RE-AUDIT
```

| Field | Value |
| --- | --- |
| Task | S12-PR-004 Excel Staging Apply Command and Provenance |
| Baseline main | `32024be43044097b185b6946499705f2560a9103` (S12-R-008 merge #9) |
| Branch | `s12-pr-004-excel-staging-apply-command-provenance` |
| Authority | ADR 0029 + staging contract section 15 (`contract_version = s12-pr-004-v1`) |
| Starting head (pre-corrective) | `f1190a55bcd6dd490710996cc75f0016e7c37b94` |
| Independent audit | Not passed (corrective findings C-1..C-7 addressed in this pass) |
| Draft PR | Not created in this session |

## Scope delivered

- Apply endpoint and application service with confirmed body, DRAFT-only, all-valid all-or-nothing
- Staging `FOR UPDATE` in Project -> batch -> staging lock order
- Success path: outer commit is final fallible step; response built from pre-commit scalars
- Lineage migration `e1f2a3b4c5d6` (nullable FKs RESTRICT; unique staging row id)
- Upload/validate reject applied batches
- Apply path security scanner blockers
- Expanded SQLite mapping/fault/lifecycle proofs; PostgreSQL matrix nodes skip without PG

## Corrective findings C-1..C-7

| ID | Resolution |
| --- | --- |
| C-1 | Removed post-commit refresh/query/assert; response pre-built before outer commit |
| C-2 | Staging query uses ordered `with_for_update()` |
| C-3 | PG Apply-vs-Apply + Apply-hold/Validate-wait with `pg_stat_activity` Lock wait (local skip without PG) |
| C-4 | Mapping after partial, savepoint fail, outer-commit fail, failure-audit persist fail, stale after newer apply |
| C-5 | Parametrized string/decimal/unit/currency/exclusion/order proofs |
| C-6 | Upload+Validate applied guards; lineage unique; alembic single head |
| C-7 | `check_apply_path_blockers` + isolated scanner tests |

## Local quality gates

| Gate | Result |
| --- | --- |
| Focused PR-004 + corrective + security blockers | **63 passed, 3 skipped** |
| Full backend pytest | **452 passed, 12 skipped, 20 warnings** |
| Backend Ruff | All checks passed |
| Security scanner | PASS (incl. Apply path blockers) |
| Alembic heads | single head `e1f2a3b4c5d6` |
| Worker | 1 passed |
| Frontend npm test | 80 passed / 15 files |

### Exact local skips (SKIPPED not PASS)

1. `test_pg_a` / Apply concurrency nodes without PostgreSQL (PR-004 Apply-vs-Apply and matrix)
2. Other historical PG skips from R004/R006/workbench/auth (repository baseline)

## Commit lineage

| Commit | Role |
| --- | --- |
| A `f6b492c67430c0186e56c527e7e36ba90755f131` | Initial implementation |
| B `f1190a55bcd6dd490710996cc75f0016e7c37b94` | Initial audit evidence |
| C `c37e01fb3c638498a969a1c2d2317387c9585150` | Atomicity, locks, tests, scanner |
| D this file | Audit-only corrective evidence |

## Remaining limitations

- Full PostgreSQL multi-session matrix (all serial orders with lock-wait) requires CI with PostgreSQL; local nodes SKIPPED
- Draft PR and authoritative CI not created in this session
- Independent re-audit still required
- No Ready/merge authority from this pass

## Final verdict

```text
S12-PR-004 CORRECTIVE IMPLEMENTATION COMPLETE - AWAITING POSTGRESQL CI AND INDEPENDENT RE-AUDIT
```
