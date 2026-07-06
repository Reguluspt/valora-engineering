# Sprint 1 Project + Master Data PR Breakdown

**Task ID:** S1-PR-001  
**Sprint:** Sprint 1 - Project + Master Data  
**Status:** Proposed implementation sequence  
**Result:** PASS WITH FIXES

## Sequencing Rules

- Keep each PR small and independently auditable.
- Do not implement future sprint behavior behind Sprint 1 names.
- Resolve required ADRs before the PR that depends on them.
- Every implementation PR must update or add tests for its own behavior.
- Design reference package remains read-only.

## S1-PR-002 - Persistence/ORM Foundation

Purpose:

- Establish persistence and migration baseline needed for Sprint 1.

Likely scope:

- Select and configure ORM/migration tooling after ADR approval.
- Add local test database setup conventions.
- Add base migration structure.
- Keep domain tables minimal and defer actual Project/Master Data schema to later PRs.

Primary design references:

- `05_FINAL_HANDOFF/04_FINAL_IMPLEMENTATION_GUARDRAILS.md`
- `docs/adr/0001-record-architecture-decisions.md`
- Sprint 1 `09_DATA_MODEL/*`

Tests/checks:

- Migration tooling smoke test.
- Backend pytest baseline still passes.

Out of scope:

- Business tables beyond persistence bootstrap unless ADR explicitly includes a base metadata table.
- Project CRUD.
- Master Data CRUD.

Required ADRs:

- Persistence stack, migration tool, transaction pattern, test database strategy.

## S1-PR-003 - Organization/User/Role Baseline

Purpose:

- Implement the organization and user identity foundation required before Project and Master Data permissions.

Likely scope:

- `OrganizationProfile`
- `User`
- `Role`
- `UserRole`
- `UserPermissionSnapshot` if needed by the selected RBAC design
- Standard role seed data: `owner`, `admin`, `appraiser`, `reviewer`, `knowledge_curator`, `viewer`
- Login identity data rule: `organization_slug + email`

Primary design references:

- `09_DATA_MODEL/02_MASTER_DATA_MODEL.md`
- `13_SECURITY/02_AUTHENTICATION.md`
- `13_SECURITY/03_AUTHORIZATION_RBAC.md`
- `14_ACCEPTANCE_TESTS/MASTER_DATA_ACCEPTANCE_TESTS.md`

Tests/checks:

- Organization slug plus email uniqueness behavior.
- UserRole active/revoked role derivation.
- No auth business flow beyond agreed Sprint 1 baseline.

Out of scope:

- Full production auth hardening beyond design-approved Sprint 1 baseline.
- Security admin UI.

Required ADRs:

- Auth/session strategy.
- Password hash package choice.
- RBAC enforcement shape.

## S1-PR-004 - Master Data Reference Tables

Purpose:

- Implement low-risk reference data foundations before customer/supplier/project workflows depend on them.

Likely scope:

- `Country`
- `Province`
- `Unit`
- `Currency`
- Basic create/list behavior where specified.
- Unique code constraints for `Unit` and `Currency`.
- Country prerequisite for province and country-assigned records.

Primary design references:

- `09_DATA_MODEL/02_MASTER_DATA_MODEL.md`
- `12_API/05_MASTER_DATA_API.md`
- `13_SECURITY/03_AUTHORIZATION_RBAC.md`
- `14_ACCEPTANCE_TESTS/MASTER_DATA_ACCEPTANCE_TESTS.md`

Tests/checks:

- Create/list countries.
- Create/list provinces.
- Create/list units.
- Create/list currencies.
- Permission checks for reference creation.

Out of scope:

- Bulk import.
- External reference data synchronization.
- Production seed packs not specified by design.

## S1-PR-005 - Customer/Supplier/Brand/Manufacturer/Unit/Country/Province

Purpose:

- Implement the main Master Data APIs and behavior required by Project creation.

Likely scope:

- `Customer`
- `CustomerAlias`
- `Supplier`
- `SupplierAlias`
- `Brand`
- `Manufacturer`
- `SignerProfile`
- Customer and supplier create/list/update/deactivate/merge.
- Brand/manufacturer create/list.
- Signer create/list/update.
- Search and pagination for customer/supplier lists.

Primary design references:

- `09_DATA_MODEL/02_MASTER_DATA_MODEL.md`
- `12_API/05_MASTER_DATA_API.md`
- `04_DOMAIN/04B_MASTER_DATA_COMMANDS_EVENTS.md`
- `13_SECURITY/03_AUTHORIZATION_RBAC.md`
- `14_ACCEPTANCE_TESTS/MASTER_DATA_ACCEPTANCE_TESTS.md`

Tests/checks:

- Customer create.
- Duplicate customer tax code rejected.
- Customer deactivate.
- Customer merge preserves alias.
- Supplier create and merge.
- Customer search/pagination.
- Customer PATCH.
- Brand create.
- Signer create/update.
- Viewer cannot create customer.

Out of scope:

- Fuzzy duplicate warning until ADR defines deterministic matching.
- Vendor enrichment.
- Business behavior for future document or knowledge modules.

Required ADRs:

- Fuzzy duplicate algorithm and warning semantics.
- Audit/event persistence for master data mutations.

## S1-PR-006 - Project Model + ProjectAssetLine Initial Model

Purpose:

- Implement Project persistence shape without implementing future sprint workflows.

Likely scope:

- `Project`
- `ProjectAssetLine`
- `ProjectFile`
- Project workflow status and knowledge update status enums.
- Asset line review and validation status enums.
- Project file category and processing status enums.
- Project code uniqueness per organization.
- Active customer validation.
- Non-negative fee/value validation.
- Read-only behavior for archived projects.

Primary design references:

- `09_DATA_MODEL/01_PROJECT_MODEL.md`
- `04_DOMAIN/04A_PROJECT_COMMANDS_EVENTS.md`
- `04_DOMAIN/07A_PROJECT_STATE_MACHINE.md`
- `14_ACCEPTANCE_TESTS/PROJECT_ACCEPTANCE_TESTS.md`

Tests/checks:

- Create project persistence.
- Duplicate project code rejected.
- Inactive customer rejected.
- Archived project read-only.
- Project list pagination/search/filter.

Out of scope:

- AI parsing.
- Taxonomy approval behavior.
- Asset identity approval behavior.
- Pricing/appraised decision behavior.
- Document generation.
- Knowledge update processing.

Required ADRs:

- Future-slice nullable reference handling.
- Workflow command skeleton policy.

## S1-PR-007 - Project Commands/API Skeleton

Purpose:

- Expose Sprint 1-safe Project API behavior aligned to the design without implementing later sprint engines.

Likely scope:

- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `PATCH /api/v1/projects/{project_id}`
- `POST /api/v1/projects/{project_id}/files`
- Sprint 1-safe review/start, review/complete, reject, approve, archive command handling if ADR-approved.
- Explicit handling for future-slice endpoints that cannot perform real behavior in Sprint 1.

Primary design references:

- `12_API/03_PROJECT_API.md`
- `04_DOMAIN/04A_PROJECT_COMMANDS_EVENTS.md`
- `04_DOMAIN/07A_PROJECT_STATE_MACHINE.md`
- `13_SECURITY/03_AUTHORIZATION_RBAC.md`

Tests/checks:

- Project create/read/list/update.
- File metadata upload behavior.
- Start review.
- Reject requires reason.
- Approve guard behavior within Sprint 1 limits.
- Archive deferred knowledge update reason behavior if ADR-approved.

Out of scope:

- Real file processing.
- OCR, AI, document rendering, knowledge update jobs.
- Workbench UI.

Required ADRs:

- File storage and metadata-only policy.
- Future-slice endpoint response policy.

## S1-PR-008 - RBAC/Permission Seed Baseline

Purpose:

- Seed and enforce the permission baseline needed for Sprint 1 APIs.

Likely scope:

- Project permission seeds.
- Master Data permission seeds.
- Role-permission mappings from the design.
- Backend permission dependency/middleware.
- UserRole active/revoked effective permission behavior.

Primary design references:

- `13_SECURITY/03_AUTHORIZATION_RBAC.md`
- `13_SECURITY/02_AUTHENTICATION.md`
- `14_ACCEPTANCE_TESTS/MASTER_DATA_ACCEPTANCE_TESTS.md`
- `14_ACCEPTANCE_TESTS/PROJECT_ACCEPTANCE_TESTS.md`

Tests/checks:

- Viewer cannot create project.
- Appraiser can create project.
- Reviewer can approve project.
- Viewer cannot create customer.
- Revoked role no longer grants permissions.

Out of scope:

- Security admin UI.
- Multi-factor authentication.
- External identity provider integration.

Required ADRs:

- RBAC enforcement shape.
- Permission snapshot refresh behavior.

## S1-PR-009 - Sprint 1 Acceptance Tests

Purpose:

- Consolidate Sprint 1 acceptance coverage from the Project and Master Data test design files.

Likely scope:

- Project acceptance tests that are fully Sprint 1-safe.
- Master Data acceptance tests.
- Auth/RBAC tests needed by Sprint 1 endpoints.
- Document deferred tests where design depends on later sprint behavior.

Primary design references:

- `14_ACCEPTANCE_TESTS/PROJECT_ACCEPTANCE_TESTS.md`
- `14_ACCEPTANCE_TESTS/MASTER_DATA_ACCEPTANCE_TESTS.md`
- `15_CROSS_REFERENCE_MAP.md`

Tests/checks:

- Backend pytest suite passes.
- CI still covers backend, worker, and frontend baselines.
- No frontend/worker business behavior added unless explicitly planned in later Sprint 1 PRs.

Out of scope:

- UI end-to-end tests for Workbench or project pages.
- Future sprint behavior tests beyond explicit deferral assertions.

## S1-PR-010 - Sprint 1 Final Audit

Purpose:

- Verify Sprint 1 completion against design, guardrails, tests, and scope boundaries.

Likely scope:

- Confirm all accepted Sprint 1 PRs match design references.
- Confirm ADRs exist for implementation choices.
- Confirm no future-sprint behavior was implemented.
- Confirm tests and CI pass.
- Confirm no secrets/cache/build artifacts are tracked.
- Produce final Sprint 1 audit report.

Primary design references:

- Final handoff guardrails.
- Sprint 1 alpha slice sources.
- All Sprint 1 audit reports.

Tests/checks:

- Backend pytest.
- Worker pytest if untouched should still pass.
- Frontend lint/build if untouched should still pass.
- Git status and tracked artifact scan.
- Forbidden future-sprint logic scan.

Out of scope:

- Any new implementation.
- Design package modification.

## Deferred Non-Blockers And Gates

Coding should not start until these are resolved or intentionally assigned to the correct PR:

- Persistence and migration ADR.
- Auth/session/password hashing ADR.
- RBAC enforcement ADR.
- Audit/event persistence ADR.
- File upload storage policy ADR.
- Fuzzy duplicate matching ADR.
- Future-slice endpoint handling ADR.
- Missing `16_MIGRATION_AND_SEED_PLAN.md` design artifact clarification.
