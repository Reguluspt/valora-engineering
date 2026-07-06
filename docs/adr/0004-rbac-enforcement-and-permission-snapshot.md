# ADR 0004 - RBAC Enforcement and Permission Snapshot

## Status

Proposed

## Context

The Sprint 1 alpha design defines roles, UserRole, project permissions, and master data permissions. It also states that server-side authorization is required and frontend visibility is not security. Sprint 1 needs a consistent server-side permission enforcement shape before APIs are implemented.

## Decision

Use server-side permission dependencies for all protected API endpoints.

RBAC behavior:

- Roles are assigned through active `UserRole` records.
- Effective permissions are derived from active roles only.
- Revoked or inactive `UserRole` records must not grant permissions.
- Permission checks are deny-by-default.
- Every organization-scoped permission check includes authenticated `organization_id`.
- Endpoint code declares the required permission using a dependency/helper such as `require_permission("project:create")`.
- Project and Master Data queries must also enforce tenant scope in the data access layer.

`UserPermissionSnapshot` policy:

- Store a snapshot only when needed for auditability, performance, or acceptance-test clarity.
- A snapshot is a derived/cache record, not the source of truth.
- Role and UserRole records remain the source of truth for current permissions.
- Snapshot refresh rules must be deterministic if implemented.

Seed policy:

- Seed standard roles and the Sprint 1 permission mappings derived from the security design.
- Do not seed production users, customers, suppliers, or projects.

## Consequences

- API implementation has a consistent permission boundary.
- Tests can verify viewer/appraiser/reviewer behavior from the design.
- Tenant scoping remains server-side and explicit.
- Permission snapshots cannot silently override role assignment truth.

## Design References

- `ENGINEERING_GUARDRAILS.md`
- `docs/04_MODULE_OWNERSHIP_MAP.md`
- `valora-design-book-v1.2-final-full-package/05_FINAL_HANDOFF/04_FINAL_IMPLEMENTATION_GUARDRAILS.md`
- `v1.2-alpha-project-master-data-completed/09_DATA_MODEL/02_MASTER_DATA_MODEL.md`
- `v1.2-alpha-project-master-data-completed/13_SECURITY/03_AUTHORIZATION_RBAC.md`
- `v1.2-alpha-project-master-data-completed/14_ACCEPTANCE_TESTS/PROJECT_ACCEPTANCE_TESTS.md`
- `v1.2-alpha-project-master-data-completed/14_ACCEPTANCE_TESTS/MASTER_DATA_ACCEPTANCE_TESTS.md`

## Sprint 1 Scope Impact

This ADR unblocks Sprint 1 auth/RBAC implementation and permission tests for Project and Master Data APIs.

## What Is Explicitly Not Implemented Yet

- No RBAC code.
- No permission dependency implementation.
- No role seed migration.
- No UserPermissionSnapshot table.
- No auth middleware.
- No frontend permission UI.

## Risks / Follow-up

- Confirm exact role-to-permission matrix during implementation from `13_SECURITY/03_AUTHORIZATION_RBAC.md`.
- Confirm whether snapshots are required in Sprint 1 or can be deferred until performance/audit needs justify them.
- Confirm audit event content for role assignment and revocation.
