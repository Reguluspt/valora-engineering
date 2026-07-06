# ADR 0002 - Persistence, ORM, and Migration Strategy

## Status

Proposed

## Context

Sprint 1 introduces Project and Master Data persistence. The Sprint 0 repo has no database domain models or migration tooling yet. The design source requires PostgreSQL-backed Project, ProjectAssetLine, ProjectFile, Organization/User/Role, Customer/Supplier, and reference data storage, but the missing `16_MIGRATION_AND_SEED_PLAN.md` means repository conventions must be clarified before coding.

## Decision

Use SQLAlchemy 2.x ORM with Alembic migrations and PostgreSQL as the authoritative application database.

Persistence conventions:

- Use UUID primary keys for domain tables.
- Use timezone-aware timestamps for `created_at`, `updated_at`, and lifecycle timestamps.
- Use `row_version` as the optimistic locking convention on mutable aggregate/root tables.
- Use explicit foreign keys for Sprint 1-owned entities.
- Use nullable UUID placeholder columns only where the Sprint 1 Project model references future-sprint entities.
- Keep tenant scoping explicit through `organization_id` on organization-scoped tables.
- Use Alembic revisions for all schema changes after the persistence foundation PR.

Test database strategy:

- Backend tests use an isolated PostgreSQL test database when PostgreSQL is available.
- Tests must create and tear down schema state through migrations or a migration-equivalent test fixture.
- SQLite is not the authoritative test target for behavior that depends on PostgreSQL constraints, UUIDs, transactions, or locking.
- If local PostgreSQL is unavailable, tests must document the limitation and CI must provide PostgreSQL coverage before merge.

## Consequences

- Sprint 1 implementation can add SQLAlchemy and Alembic in the implementation PR that owns persistence setup.
- Migration history becomes the source of schema evolution.
- UUID and timestamp conventions are consistent across Project and Master Data.
- PostgreSQL-specific behavior is tested on PostgreSQL rather than hidden by SQLite differences.

## Design References

- `CODEX.md`
- `ENGINEERING_GUARDRAILS.md`
- `PR_RULES.md`
- `docs/adr/0001-record-architecture-decisions.md`
- `docs/sprint-1/PROJECT_MASTER_DATA_IMPLEMENTATION_PLAN.md`
- `valora-design-book-v1.2-final-full-package/05_FINAL_HANDOFF/04_FINAL_IMPLEMENTATION_GUARDRAILS.md`
- `v1.2-alpha-project-master-data-completed/09_DATA_MODEL/01_PROJECT_MODEL.md`
- `v1.2-alpha-project-master-data-completed/09_DATA_MODEL/02_MASTER_DATA_MODEL.md`

## Sprint 1 Scope Impact

This ADR unblocks the Sprint 1 persistence foundation and later Project/Master Data model PRs. It does not itself create models, migrations, or dependencies.

## What Is Explicitly Not Implemented Yet

- No SQLAlchemy models.
- No Alembic environment.
- No migrations.
- No database sessions.
- No tests.
- No dependency changes.

## Risks / Follow-up

- Confirm sync versus async SQLAlchemy usage during persistence implementation.
- Confirm CI PostgreSQL service configuration in the persistence PR.
- Confirm exact table and index names in migrations.
- Revisit `row_version` handling when workflow concurrency behavior becomes more detailed.
