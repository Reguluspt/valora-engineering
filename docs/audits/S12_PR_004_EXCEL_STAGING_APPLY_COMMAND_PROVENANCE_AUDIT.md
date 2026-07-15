# S12-PR-004 - Excel Staging Apply Command and Provenance Audit

## Status

```text
S12-PR-004 PROOF MATRIX IMPLEMENTED — AWAITING POSTGRESQL CI AND INDEPENDENT RE-AUDIT
```

| Field | Value |
| --- | --- |
| Task | S12-PR-004 Excel Staging Apply Command and Provenance |
| Baseline main | `32024be43044097b185b6946499705f2560a9103` (S12-R-008 merge #9) |
| Branch | `s12-pr-004-excel-staging-apply-command-provenance` |
| Authority | ADR 0029 + staging contract section 15 (`contract_version = s12-pr-004-v1`) |
| Starting head (pre-proof-matrix) | `ade92f18acb4b3a7116a6b79b128827a5af73b93` |
| Independent audit | Not passed (proof-matrix M-1..M-7 addressed in this pass) |
| Draft PR | Not created in this session |

## Scope delivered

- Apply endpoint and application service with confirmed body, DRAFT-only, all-valid all-or-nothing
- Staging `FOR UPDATE` in Project -> batch -> staging lock order
- Success path: outer commit is final fallible step; response built from pre-commit scalars
- Lineage migration `e1f2a3b4c5d6` (nullable FKs RESTRICT; unique staging row id)
- Upload/validate reject applied batches
- Apply path security scanner blockers (AST fail-closed; missing files; update/merge/upsert/delete; workbench:edit)
- Selected-tier unit/currency resolution
- Executable proof matrix: 7 real PG nodes, migration behavioral proofs, 3 stale-generation recoveries

## Corrective findings C-1..C-7 (prior)

| ID | Resolution |
| --- | --- |
| C-1 | Post-commit boundary fixed |
| C-2 | Staging ordered `with_for_update()` |
| C-3 | PG matrix skeleton (later replaced by M-1) |
| C-4 | Fault injection matrix |
| C-5 | Mapping parametrize |
| C-6 | Lifecycle + single head |
| C-7 | Apply path scanner |

## Acceptance-closure A-1..A-8 (prior)

| ID | Resolution |
| --- | --- |
| A-1 | Selected-tier all-row resolution |
| A-2 | Seven node IDs collected (bodies completed in M-1) |
| A-3..A-8 | Fault, mapping, migration head, immutability helper, scanner, post-commit |

## Proof-matrix findings M-1..M-7

| ID | Resolution |
| --- | --- |
| M-1 | Seven real PG node bodies using production entry points (Apply, Upload orchestrator, Validate service, `archive_project` workflow status path); each publishes waiter `pg_backend_pid` and asserts `wait_event_type == Lock`; no placeholder lock-only transactions |
| M-2 | Executable migration proof: inspect nullable columns/indexes/FKs RESTRICT/unique; DML RESTRICT on batch+staging delete; unique `source_staging_row_id`; script chain `db5977424e7b` ↔ `e1f2a3b4c5d6`; single head (PG skip local) |
| M-3 | Three stale-generation recoveries with complete generations: after newer Upload+Validate; after newer Validation; after newer Apply with official rows+lineage |
| M-4 | `official_line_snapshot` used across precondition/mapping/fault/stale/PG nodes; ordered audit tuples with payload key sets |
| M-5 | Exact Decimal persistence; no rounding at scale; scientific fit/overflow; accent preservation; forbidden inputs explicit defaults |
| M-6 | Scanner blocks update/merge/upsert/bulk/delete and pre-existing line assigns; workbench:edit + command delegation retained |
| M-7 | Commit F SHA corrected to `ade92f18acb4b3a7116a6b79b128827a5af73b93`; this audit-only enclosing commit identified as `this audit-only enclosing commit; verify with git log` (do not embed self-SHA) |

### M-1 node inventory (real holders/waiters)

| Node ID | Holder | Waiter | Local |
| --- | --- | --- | --- |
| `pg_apply_vs_apply_lock_wait` | real Apply | real Apply | SKIPPED without PG |
| `pg_upload_holds_apply_waits` | real Upload orchestrator | real Apply | SKIPPED without PG |
| `pg_apply_holds_upload_waits` | real Apply | real Upload orchestrator | SKIPPED without PG |
| `pg_validate_holds_apply_waits` | real Validate service | real Apply | SKIPPED without PG |
| `pg_apply_holds_validate_waits` | real Apply | real Validate service | SKIPPED without PG |
| `pg_workflow_holds_apply_waits` | real `archive_project` | real Apply | SKIPPED without PG |
| `pg_apply_holds_workflow_waits` | real Apply | real `archive_project` | SKIPPED without PG |

Placeholder `_run_pg_serial_node` removed from acceptance_closure. Bodies live in `tests/test_s12_pr_004_proof_matrix.py`.

### M-3 stale-generation tests

1. `TestM3StaleGenerationRecovery::test_stale_after_newer_upload`
2. `TestM3StaleGenerationRecovery::test_stale_after_newer_validation`
3. `TestM3StaleGenerationRecovery::test_stale_after_newer_apply`

## Local quality gates (proof-matrix head)

| Gate | Result |
| --- | --- |
| Focused PR-004 + proof + corrective + acceptance + security blockers | **149 passed, 11 skipped** |
| Full backend pytest | **538 passed, 20 skipped, 20 warnings** |
| Backend Ruff | All checks passed |
| Security scanner | PASS (incl. Apply path blockers) |
| Alembic heads | single head `e1f2a3b4c5d6` |
| Worker Ruff/pytest | PASS / 1 passed |
| Frontend Vitest | 80 passed / 15 files |
| Frontend build | PASS |

### Exact local skips (SKIPPED not PASS)

1. `test_pg_proof_matrix_node[pg_apply_vs_apply_lock_wait]`
2. `test_pg_proof_matrix_node[pg_upload_holds_apply_waits]`
3. `test_pg_proof_matrix_node[pg_apply_holds_upload_waits]`
4. `test_pg_proof_matrix_node[pg_validate_holds_apply_waits]`
5. `test_pg_proof_matrix_node[pg_apply_holds_validate_waits]`
6. `test_pg_proof_matrix_node[pg_workflow_holds_apply_waits]`
7. `test_pg_proof_matrix_node[pg_apply_holds_workflow_waits]`
8. `TestM2ExecutableMigration::test_lineage_migration_upgrade_downgrade_restrict_unique`
9. Other historical PG skips (R004/R006/workbench/auth and prior PR-004 concurrency helpers)

## Commit lineage

| Commit | Role |
| --- | --- |
| A `f6b492c67430c0186e56c527e7e36ba90755f131` | Initial implementation |
| B `f1190a55bcd6dd490710996cc75f0016e7c37b94` | Initial audit evidence |
| C `c37e01fb3c638498a969a1c2d2317387c9585150` | Atomicity, locks, tests, scanner |
| D `98fcffc8b300a186d47fcd70b355e5d6d03b8bfa` | Audit-only corrective evidence |
| E `dfc46059869001029313f9b91c6f5b1ac0760ab9` | Mapping + acceptance matrices A-1..A-8 |
| F `ade92f18acb4b3a7116a6b79b128827a5af73b93` | Audit-only acceptance-closure evidence (corrected; not 7ab4769…) |
| G `26642295f82ccc1e73882df317814433f39b1e2b` | Proof matrix implementation M-1..M-6 |
| H this audit-only enclosing commit; verify with `git log` | Reconcile executable proof evidence |

## Remaining limitations

- Full PostgreSQL multi-session matrix requires CI with PostgreSQL; local nodes SKIPPED
- Live Alembic downgrade/upgrade against shared CI database is intentionally non-destructive; reversible proof uses script chain + live FK/unique DML + inspect
- Draft PR and authoritative CI not created in this session
- Independent re-audit still required
- No Ready/merge authority from this pass

## Final verdict

```text
S12-PR-004 PROOF MATRIX IMPLEMENTED — AWAITING POSTGRESQL CI AND INDEPENDENT RE-AUDIT
```
