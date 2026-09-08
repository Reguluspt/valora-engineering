# PR-01 — Case State Endpoint Implementation Audit

**Task:** `VALORA-PR01-IMPL-004`
**Status:** OWNER CLOSEOUT COMPLETE LOCALLY
**Date:** 2026-09-05
**Branch:** `pr-01-case-state-projection-foundation`
**Baseline HEAD:** `aa5cd3a433e0f94d7b53c3331ef2145a2c672767`

## Scope

This separately authorized slice exposes the accepted computed-on-read provider/aggregator through:

```text
GET /api/v1/projects/{project_id}/case-state
```

It adds a bounded public response schema and focused HTTP/PostgreSQL evidence. It does not add
projection persistence, cache, migration, resume context, frontend wiring, downstream providers,
commit, push or pull-request publication.

## Implemented Contract

The endpoint returns the opaque `case_version`, total bounded `current_stage`, one typed
`next_action`, all 16 ordered stage results, separate blocker/warning/stale collections and all 16
capabilities. The four accepted prefix providers are available; the 12 downstream stages remain
explicit `NOT_AVAILABLE`. `stale` is empty because this slice has no authoritative stale provider.

Internal provider `facts` and per-stage `fact_token` values are not exposed. Authentication yields
`401`; inactive or unauthorized actors receive typed `403 case_state_forbidden`; missing and
cross-tenant projects receive the same safe `404 project_not_found`. Typed projection failures are
mapped to a safe Vietnamese `500 case_state_projection_failed` response without internal detail.

The route supplies the existing SQLAlchemy session to the accepted projection service. It performs
no write, flush, commit, rollback, audit-event creation or `FOR UPDATE` lock.

## PostgreSQL Fixture Corrections

The authorized fixture-repair round made two test-only corrections:

1. The historical Column Mapping migration round-trip now removes the later
   `preliminary_analysis_snapshots` table before directly downgrading the older mapping migration,
   preserving dependency order in its isolated schema.
2. The concurrent refresh-token proof now honors `TEST_DATABASE_URL`, verifies that its auth tables
   are already migrated and fails in CI when PostgreSQL is unavailable. It no longer assumes a
   hard-coded port or attempts to mutate the shared schema by running Alembic in a subprocess.

No production migration was changed by these corrections.

## Verification Evidence

- endpoint and current design-contract tests after implementation: `8 passed`;
- endpoint test set after blocker/warning coverage: `4 passed`;
- PostgreSQL endpoint plus endpoint tests: `7 passed`, `0 skipped`;
- complete relevant PR-01 packet with `CI=true`: `231 passed`, `0 failed`, `0 skipped`;
- repaired migration fixture plus endpoint/design packet: `10 passed`, `0 skipped`;
- repaired concurrent refresh-token PostgreSQL proof: `1 passed`, `0 skipped`;
- final full backend suite on PostgreSQL and local MinIO: `1306 passed`, `0 failed`, `0 skipped`;
- Ruff, Python compile, `git diff --check` and Alembic single head `c159fab13c3a`: PASS;
- independent Qwen acceptance review: `PASS`, no blocking or high-confidence finding.

## Conclusion

`VALORA-PR01-IMPL-004` passed local technical acceptance and received Product Owner closeout through
the subsequent instruction to proceed on 2026-09-05. That instruction opens the separately scoped
PR-02 frontend hub wiring task; publication remains outside this audit.
