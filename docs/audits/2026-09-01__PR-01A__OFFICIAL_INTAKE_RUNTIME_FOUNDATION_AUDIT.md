# PR-01a — Official Intake Runtime Foundation Audit

**Date:** 2026-09-01
**Status:** INDEPENDENT GATE PASS — authority closeout complete locally
**Branch:** `pr-01-case-state-projection-foundation`
**Authority:** accepted ADR 0037 plus Product Owner authority closeout, 2026-09-02
**Reviewed closeout:** `f0e7c731d0ea5b5a7817ab3f819cce4422ff7885`

## Implemented

- immutable/versioned `PreliminaryResultArtifact` persistence foundation;
- append-only, one-per-Project `ProjectOfficialIntakeCommit` fact;
- linear Alembic migration `e3f4a5b6c7d8`;
- internal `CommitProjectOfficialIntake` service;
- active actor/organization and safe tenant scope;
- explicit `project:official_intake:commit` enforcement through the existing organization-scoped
  RBAC model, re-evaluating active/non-revoked role bindings before every invocation and replay;
- no Project ACL, seeded-role grant or HTTP surface;
- scoped Project → scoped artifact → idempotency resolution/recheck lock order and optimistic
  version checks;
- deterministic concurrent replay, typed digest reuse and typed already-committed handling. The
  replay proof pauses worker A only after its Project `FOR UPDATE` has returned, starts worker B,
  and releases A only after PostgreSQL reports B blocked by A on that Project lock through
  `pg_stat_activity`, `pg_blocking_pids(...)` and a matching granted/ungranted `pg_locks` edge.
  Its `after_cursor_execute` trace also records relevant completed SQL for both workers and asserts
  that each successful/replay path starts exactly Project lock → artifact lock → idempotency
  resolution;
- exact v1 `OPEN` + `BLOCKING` registry for `project | Project` and
  `project_asset_line | ProjectAssetLine`, with Warning/resolved/ignored/unknown/other-Project/
  cross-tenant issues non-blocking and no extra rule/category filters or bypass;
- atomic success audit and rollback on audit failure;
- no Project legacy status transition and no price promotion.

## Verification environment

Commands below were run against the local Docker PostgreSQL and MinIO services. Credential values
are intentionally redacted; the environment variable names are recorded exactly.

- repository root: `F:\Project Valora\valora-engineering`;
- backend working directory where stated: `F:\Project Valora\valora-engineering\backend`;
- focused PostgreSQL tests: `TEST_DATABASE_URL=<redacted-local-postgresql-url>`;
- full backend suite: `TEST_DATABASE_URL=<redacted-local-postgresql-url>`,
  `S3_ENDPOINT_URL=http://localhost:9000`, `S3_ACCESS_KEY_ID=<redacted>`,
  `S3_SECRET_ACCESS_KEY=<redacted>`, `S3_BUCKET=valora-local`, `S3_REGION=us-east-1`, with
  `..\.venv\Scripts` prepended to `PATH`;
- Alembic: `POSTGRES_HOST=localhost`, `POSTGRES_PORT=5432`, `POSTGRES_DB=valora`,
  `POSTGRES_USER=<redacted>`, `POSTGRES_PASSWORD=<redacted>`.

## Reproducible commands and results

From the repository root, the deterministic Project-row-lock proof was run directly:

```powershell
$env:TEST_DATABASE_URL='<redacted-local-postgresql-url>'
1..10 | ForEach-Object {
    .\.venv\Scripts\python.exe -m pytest backend/tests/test_pr01_official_intake_postgresql.py::test_postgresql_concurrent_same_request_observes_lock_order_and_replays -q --disable-warnings
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
```

Result: 10/10 invocations passed; each reported `1 passed`, `0 failed`, `0 skipped` and
`13 warnings`. Run times were `0.34s`, `0.36s`, `0.36s`, `0.34s`, `0.36s`, `0.34s`, `0.37s`,
`0.36s`, `0.38s` and `0.35s`.

The whole PostgreSQL concurrency file then reported `3 passed`, `0 failed`, `0 skipped`,
`13 warnings` in `0.55s`.

The complete focused packet was then run from the repository root:

```powershell
$env:TEST_DATABASE_URL='<redacted-local-postgresql-url>'
.\.venv\Scripts\python.exe -m pytest backend/tests/test_pr01_official_intake_service.py backend/tests/test_pr01_official_intake_postgresql.py -q
```

Result: `32 passed`, `0 failed`, `0 skipped`, `13 warnings` in `2.91s` (29 service cases and
3 PostgreSQL-only two-session concurrency cases).

The full backend suite was run after the deterministic-lock correction, from the backend working
directory:

```powershell
$venvScripts=(Resolve-Path '..\.venv\Scripts').Path
$env:Path=$venvScripts + ';' + $env:Path
$env:TEST_DATABASE_URL='<redacted-local-postgresql-url>'
$env:S3_ENDPOINT_URL='http://localhost:9000'
$env:S3_ACCESS_KEY_ID='<redacted>'
$env:S3_SECRET_ACCESS_KEY='<redacted>'
$env:S3_BUCKET='valora-local'
$env:S3_REGION='us-east-1'
..\.venv\Scripts\python.exe -m pytest tests -q
```

Result: `1111 passed`, `0 failed`, `0 skipped`, `28 warnings` in `201.03s`.

Alembic was verified from the backend working directory with the five `POSTGRES_*` variables named
above:

```powershell
..\.venv\Scripts\python.exe -m alembic heads
..\.venv\Scripts\python.exe -m alembic current
..\.venv\Scripts\python.exe -m alembic check
```

Results: `heads` = `e3f4a5b6c7d8 (head)`; `current` = `e3f4a5b6c7d8 (head)`; `check` =
`No new upgrade operations detected.`

The security guardrail tests were run from the backend working directory:

```powershell
..\.venv\Scripts\python.exe -m pytest tests\test_check_security.py tests\test_check_security_blockers.py -q
```

Result: `27 passed`, `0 failed`, `0 skipped`, `13 warnings` in `0.42s`.

The stock whole-tree scanner was also invoked from the repository root:

```powershell
.\.venv\Scripts\python.exe backend\tests\check_security.py
```

This invocation is **not recorded as PASS**. It exited `1`: the scanner descended into the local
`.venv`, reported third-party-package false positives, then terminated before a whole-tree verdict
with `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x93 in position 2848`. To obtain a
source-scoped guardrail result without changing the scanner, its existing checks were called from
the backend working directory with `root='.'`:

```powershell
..\.venv\Scripts\python.exe -c "from tests.check_security import check_secret_placeholders, check_security_baseline_and_blockers, check_apply_path_blockers; root='.'; failures=check_secret_placeholders(root)+check_security_baseline_and_blockers(root)+check_apply_path_blockers(root); print(f'Source-filtered scan failures: {failures}'); raise SystemExit(1 if failures else 0)"
```

Result: `Source-filtered scan failures: 0`, exit `0`. This is evidence for the backend source tree,
not a substitute claim that the stock whole-tree scanner passed.

Finally, from the repository root:

```powershell
.\.venv\Scripts\python.exe -m ruff check backend/app/modules/project_master_data/application/official_intake_service.py backend/tests/test_pr01_official_intake_service.py backend/tests/test_pr01_official_intake_postgresql.py
git diff --check
```

Results: Ruff `All checks passed!`; `git diff --check` exit `0` with no whitespace errors (Git
printed only line-ending conversion warnings).

The earlier foundation evidence at `23de078` remains historical: full backend `1083 passed` with
9 explicit MinIO skips, PostgreSQL migration-isolation/concurrent-refresh `2 passed`, frontend
`19` files / `90` tests, backend/frontend lint and build PASS, Alembic single head
`e3f4a5b6c7d8`, round-trip migration PASS and `alembic check` clean. It is not relabeled as
evidence for the reviewed authority-closeout commit.

## Independent gate conclusion

The authority-closeout correction at `f0e7c73` passed independent review. The exact permission,
blocker registry, tenant-safe replay behavior, deterministic PostgreSQL lock-order proof and atomic
audit boundary match the accepted contract. PR-01a is complete locally. This conclusion does not
authorize an HTTP endpoint, artifact-generation workflow, seeded-role grant or Global Case State
provider.

## Explicitly deferred

- preliminary-result generation command/API;
- official-intake HTTP endpoint;
- permission assignment to seeded roles;
- Global Case State provider and GET endpoint;
- frontend/resume wiring;
- GitHub push.
