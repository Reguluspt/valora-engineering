# PR-01a — Official Intake Runtime Foundation Audit

**Date:** 2026-09-01
**Status:** IMPLEMENTED LOCALLY — baseline PASS with explicit MinIO exclusions
**Branch:** `pr-01-case-state-projection-foundation`
**Authority:** accepted ADR 0037

## Implemented

- immutable/versioned `PreliminaryResultArtifact` persistence foundation;
- append-only, one-per-Project `ProjectOfficialIntakeCommit` fact;
- linear Alembic migration `e3f4a5b6c7d8`;
- internal `CommitProjectOfficialIntake` service;
- active actor/organization and safe tenant scope;
- Project → artifact lock order and optimistic version checks;
- idempotent replay and digest conflict handling;
- direct Project/ProjectAssetLine Blocking registry with Warning kept non-blocking;
- atomic success audit and rollback on audit failure;
- no Project legacy status transition and no price promotion.

## Verification

- focused official-intake service plus UI/UX v2.3 design-contract tests:
  `17 passed`;
- full backend baseline against local PostgreSQL: `1083 passed`, `0 failed`,
  `9 skipped`; all skips are existing MinIO integration cases because
  `S3_ENDPOINT_URL` is not configured and are not counted as PASS;
- PostgreSQL migration-isolation and concurrent-refresh regression cases:
  `2 passed` after activating the repository virtual environment;
- full frontend unit baseline: `19` files / `90` tests passed;
- backend Ruff, frontend lint, and frontend production build: PASS;
- Alembic single head: `e3f4a5b6c7d8`;
- local PostgreSQL upgrade, downgrade to the prior head, and upgrade to head:
  PASS;
- `alembic check`: `No new upgrade operations detected`.

## Explicitly deferred

- preliminary-result generation command/API;
- official-intake HTTP endpoint and permission code;
- PostgreSQL concurrency proof;
- Global Case State provider and GET endpoint;
- frontend/resume wiring;
- nine MinIO integration cases until local `S3_ENDPOINT_URL` is configured;
- GitHub push.
