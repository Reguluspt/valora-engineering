# S12-PR-004 - Excel Staging Apply Command and Provenance Audit

## Status

```text
S12-PR-004 ACCEPTANCE CLOSURE COMPLETE — AWAITING POSTGRESQL CI AND INDEPENDENT RE-AUDIT
```

| Field | Value |
| --- | --- |
| Task | S12-PR-004 Excel Staging Apply Command and Provenance |
| Baseline main | `32024be43044097b185b6946499705f2560a9103` (S12-R-008 merge #9) |
| Branch | `s12-pr-004-excel-staging-apply-command-provenance` |
| Authority | ADR 0029 + staging contract section 15 (`contract_version = s12-pr-004-v1`) |
| Starting head (pre-acceptance-closure) | `98fcffc8b300a186d47fcd70b355e5d6d03b8bfa` |
| Independent audit | Not passed (acceptance-closure A-1..A-8 addressed in this pass) |
| Draft PR | Not created in this session |

## Scope delivered

- Apply endpoint and application service with confirmed body, DRAFT-only, all-valid all-or-nothing
- Staging `FOR UPDATE` in Project -> batch -> staging lock order
- Success path: outer commit is final fallible step; response built from pre-commit scalars
- Lineage migration `e1f2a3b4c5d6` (nullable FKs RESTRICT; unique staging row id)
- Upload/validate reject applied batches
- Apply path security scanner blockers (AST fail-closed; missing files fail)
- Selected-tier unit/currency resolution (match ALL rows per tier, require exactly one ACTIVE)
- Expanded SQLite mapping/fault/lifecycle/immutability proofs; 7-node PostgreSQL matrix inventory (skip without PG)

## Corrective findings C-1..C-7 (prior pass)

| ID | Resolution |
| --- | --- |
| C-1 | Removed post-commit refresh/query/assert; response pre-built before outer commit |
| C-2 | Staging query uses ordered `with_for_update()` |
| C-3 | PG Apply-vs-Apply + Apply-hold/Validate-wait with `pg_stat_activity` Lock wait (local skip without PG) |
| C-4 | Mapping after partial, savepoint fail, outer-commit fail, failure-audit persist fail, stale after newer apply |
| C-5 | Parametrized string/decimal/unit/currency/exclusion/order proofs |
| C-6 | Upload+Validate applied guards; lineage unique; alembic single head |
| C-7 | `check_apply_path_blockers` + isolated scanner tests |

## Acceptance-closure findings A-1..A-8

| ID | Resolution |
| --- | --- |
| A-1 | Unit/currency selected-tier: match ALL rows at tier, zero→next, non-zero requires exactly one ACTIVE; no inactive→lower-tier fallthrough; currency symbols forbidden |
| A-2 | Seven named PG matrix nodes collected; real multi-session lock-wait helpers; local SKIP without PostgreSQL (SKIP ≠ PASS) |
| A-3 | Fault matrix expanded: flush-after-partial-insert, success-audit fail, outer-commit/savepoint/stale covered |
| A-4 | Mapping exhaustive: raw_price + quantity parametrize, unicode trim, name/desc bounds, forbidden fields inert |
| A-5 | Alembic single head `e1f2a3b4c5d6` + migration lineage column/RESTRICT/unique assertions |
| A-6 | Full-field `official_line_snapshot` helper; byte-equal pre/post Apply immutability of pre-existing lines |
| A-7 | Scanner fail-closed: missing apply/projects files, missing staging FOR UPDATE, setattr/raw_values |
| A-8 | Post-commit regression: success path has no ORM query/refresh after outer commit |

## Local quality gates (acceptance-closure head)

| Gate | Result |
| --- | --- |
| Focused PR-004 + acceptance + corrective + security blockers | **110 passed, 10 skipped** |
| Full backend pytest | **499 passed, 19 skipped, 20 warnings** |
| Backend Ruff | All checks passed |
| Security scanner | PASS (incl. Apply path blockers) |
| Alembic heads | single head `e1f2a3b4c5d6` |
| Worker | 1 passed |
| Frontend npm test | 80 passed / 15 files |

### Exact local skips (SKIPPED not PASS)

1. Seven PG matrix inventory nodes without PostgreSQL (`test_pg_matrix_node_inventory`)
2. Apply-vs-Apply / Apply-hold Validate-wait PG proofs without PostgreSQL
3. Other historical PG skips from R004/R006/workbench/auth (repository baseline)

## Commit lineage

| Commit | Role |
| --- | --- |
| A `f6b492c67430c0186e56c527e7e36ba90755f131` | Initial implementation |
| B `f1190a55bcd6dd490710996cc75f0016e7c37b94` | Initial audit evidence |
| C `c37e01fb3c638498a969a1c2d2317387c9585150` | Atomicity, locks, tests, scanner |
| D `98fcffc8b300a186d47fcd70b355e5d6d03b8bfa` | Audit-only corrective evidence |
| E `dfc46059869001029313f9b91c6f5b1ac0760ab9` | Mapping + acceptance matrices A-1..A-8 |
| F `7ab47696e4410aef2186ca1e9f6049cc08a75fec` | Audit-only acceptance-closure evidence |

## Remaining limitations

- Full PostgreSQL multi-session matrix (all serial orders with lock-wait) requires CI with PostgreSQL; local nodes SKIPPED
- Draft PR and authoritative CI not created in this session
- Independent re-audit still required
- No Ready/merge authority from this pass

## Final verdict

```text
S12-PR-004 ACCEPTANCE CLOSURE COMPLETE — AWAITING POSTGRESQL CI AND INDEPENDENT RE-AUDIT
```
