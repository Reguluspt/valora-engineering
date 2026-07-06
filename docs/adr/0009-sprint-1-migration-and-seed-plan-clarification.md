# ADR 0009 - Sprint 1 Migration and Seed Plan Clarification

## Status

Proposed

## Context

S1-PR-001 found that `16_MIGRATION_AND_SEED_PLAN.md` is missing from both the extracted Sprint 1 slice and the source ZIP. Sprint 1 still needs a migration and seed plan derived from the available data model and security design files.

## Decision

Derive the Sprint 1 migration and seed plan from the alpha data model and security sources.

Migration plan:

- Create schema through Alembic migrations after ADR 0002 is implemented.
- Include tables for Sprint 1-owned entities only:
  - `organization_profiles`
  - `users`
  - `roles`
  - `user_roles`
  - `user_permission_snapshots` if ADR 0004 implementation chooses to persist snapshots in Sprint 1
  - `customers`
  - `customer_aliases`
  - `suppliers`
  - `supplier_aliases`
  - `countries`
  - `provinces`
  - `brands`
  - `manufacturers`
  - `units`
  - `currencies`
  - `signer_profiles`
  - `projects`
  - `project_asset_lines`
  - `project_files`
  - minimal audit/event table or tables from ADR 0005
- Add UUID primary keys, tenant foreign keys where required, timestamps, and `row_version` where mutable.
- Add uniqueness constraints required by design, including project code per organization and reference-data code uniqueness where specified.

Seed plan:

- Seed standard roles only:
  - `owner`
  - `admin`
  - `appraiser`
  - `reviewer`
  - `knowledge_curator`
  - `viewer`
- Seed Sprint 1 permission names and role-permission mappings from `13_SECURITY/03_AUTHORIZATION_RBAC.md`.
- Seed only deterministic local/test fixtures required by tests, not production business data.
- Do not seed real customers, suppliers, projects, files, passwords, secrets, or production organization data.

## Consequences

- Sprint 1 can proceed despite the missing migration/seed design artifact.
- Seeds stay limited to roles and permissions.
- Any broader seed data requires explicit design source or a later ADR/change request.

## Design References

- `docs/audits/S1_PR_001_PROJECT_MASTER_DATA_DESIGN_INTAKE.md`
- `docs/sprint-1/PROJECT_MASTER_DATA_IMPLEMENTATION_PLAN.md`
- `v1.2-alpha-project-master-data-completed/09_DATA_MODEL/01_PROJECT_MODEL.md`
- `v1.2-alpha-project-master-data-completed/09_DATA_MODEL/02_MASTER_DATA_MODEL.md`
- `v1.2-alpha-project-master-data-completed/13_SECURITY/03_AUTHORIZATION_RBAC.md`
- `v1.2-alpha-project-master-data-completed/14_ACCEPTANCE_TESTS/PROJECT_ACCEPTANCE_TESTS.md`
- `v1.2-alpha-project-master-data-completed/14_ACCEPTANCE_TESTS/MASTER_DATA_ACCEPTANCE_TESTS.md`

## Sprint 1 Scope Impact

This ADR resolves the missing `16_MIGRATION_AND_SEED_PLAN.md` blocker for Sprint 1 implementation planning.

## What Is Explicitly Not Implemented Yet

- No migrations.
- No seed files.
- No models.
- No roles or permissions inserted.
- No test fixtures.

## Risks / Follow-up

- If the missing migration/seed artifact is later restored and conflicts with this ADR, escalate for design reconciliation before changing implementation.
- Confirm exact role-permission mappings during RBAC implementation.
- Confirm whether `user_permission_snapshots` is implemented in Sprint 1 or deferred.
