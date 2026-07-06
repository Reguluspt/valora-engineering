# Sprint 1 Project + Master Data Implementation Plan

**Task ID:** S1-PR-001  
**Sprint:** Sprint 1 - Project + Master Data  
**Status:** Design intake only  
**Result:** PASS WITH FIXES

## Design Sources

Primary repo and guardrail sources:

- `README.md`
- `CODEX.md`
- `ENGINEERING_GUARDRAILS.md`
- `PR_RULES.md`
- `docs/01_SPRINT_0_PLAN.md`
- `docs/02_ENGINEERING_GUARDRAILS.md`
- `docs/03_DEFINITION_OF_DONE.md`
- `docs/04_MODULE_OWNERSHIP_MAP.md`
- `docs/audits/S0_PR_008_SPRINT_0_FINAL_ACCEPTANCE_AUDIT.md`

Final handoff sources:

- `E:\Project Valora\valora-design-book-v1.2-final-full-package\README.md`
- `E:\Project Valora\valora-design-book-v1.2-final-full-package\manifest.json`
- `E:\Project Valora\valora-design-book-v1.2-final-full-package\05_FINAL_HANDOFF\02_ENGINEERING_HANDOFF_GATE.md`
- `E:\Project Valora\valora-design-book-v1.2-final-full-package\05_FINAL_HANDOFF\03_SPRINT_SEQUENCE_FINAL.md`
- `E:\Project Valora\valora-design-book-v1.2-final-full-package\05_FINAL_HANDOFF\04_FINAL_IMPLEMENTATION_GUARDRAILS.md`

Sprint 1 alpha slice sources:

- `02_SOURCE_SLICES_COMPLETED\01_v1.2-alpha-project-master-data-completed\README.md`
- `02_SOURCE_SLICES_COMPLETED\01_v1.2-alpha-project-master-data-completed\01_SCOPE_AND_COMPLETION_GATE.md`
- `02_SOURCE_SLICES_COMPLETED\01_v1.2-alpha-project-master-data-completed\15_CROSS_REFERENCE_MAP.md`
- `01_SOURCE_ZIPS\valora-design-book-v1.2-alpha-project-master-data-completed.zip`
  - `09_DATA_MODEL/01_PROJECT_MODEL.md`
  - `09_DATA_MODEL/02_MASTER_DATA_MODEL.md`
  - `12_API/03_PROJECT_API.md`
  - `12_API/05_MASTER_DATA_API.md`
  - `13_SECURITY/02_AUTHENTICATION.md`
  - `13_SECURITY/03_AUTHORIZATION_RBAC.md`
  - `14_ACCEPTANCE_TESTS/PROJECT_ACCEPTANCE_TESTS.md`
  - `14_ACCEPTANCE_TESTS/MASTER_DATA_ACCEPTANCE_TESTS.md`
  - `04_DOMAIN/04A_PROJECT_COMMANDS_EVENTS.md`
  - `04_DOMAIN/04B_MASTER_DATA_COMMANDS_EVENTS.md`
  - `04_DOMAIN/07A_PROJECT_STATE_MACHINE.md`

The extracted Sprint 1 slice is incomplete. Several requested files were read from the source ZIP without extraction. The requested `02_DESIGN_PRINCIPLES.md`, `16_MIGRATION_AND_SEED_PLAN.md`, and `17_CODEX_PROMPTS_V1_2_ALPHA.md` were not present in the extracted folder or ZIP and must be treated as missing design artifacts.

## Sprint 0 Readiness

Sprint 0 is ready for Sprint 1 according to `docs/audits/S0_PR_008_SPRINT_0_FINAL_ACCEPTANCE_AUDIT.md`:

- Final result: `PASS`
- Recommendation: `Ready Sprint 1`
- Backend, frontend, worker, local infra, CI, rule files, and ADR template are present.
- No business/domain implementation is present in the Sprint 0 baseline.

## Entities To Implement

### Organization, User, Role Baseline

From `09_DATA_MODEL/02_MASTER_DATA_MODEL.md` and `13_SECURITY/02_AUTHENTICATION.md`:

- `OrganizationProfile`
- `User`
- `Role`
- `UserRole`
- `UserPermissionSnapshot`

Design rules:

- Login identity is `organization_slug + email`.
- Standard roles are `owner`, `admin`, `appraiser`, `reviewer`, `knowledge_curator`, and `viewer`.
- Effective roles derive from active `UserRole` assignments.
- Password storage must use a hash only; Argon2id or bcrypt is specified by design, but package choice is an ADR.

### Master Data

From `09_DATA_MODEL/02_MASTER_DATA_MODEL.md`:

- `Customer`
- `CustomerAlias`
- `Supplier`
- `SupplierAlias`
- `Country`
- `Province`
- `Brand`
- `Manufacturer`
- `Unit`
- `Currency`
- `SignerProfile`

Design rules:

- Referenced master data should be soft deactivated, not hard deleted.
- Customer and supplier merge operations preserve aliases and audit history.
- `Country` exists before country assignment to `Brand` or `Manufacturer`.
- `Unit` and `Currency` codes are unique.

### Project

From `09_DATA_MODEL/01_PROJECT_MODEL.md`:

- `Project`
- `ProjectAssetLine`
- `ProjectFile`

Project enums:

- `ProjectWorkflowStatus`: `draft`, `files_uploaded`, `imported`, `ai_parsed`, `reviewing`, `review_completed`, `document_drafted`, `qc_review`, `rejected`, `approved`, `knowledge_update`, `archived`, `cancelled`
- `KnowledgeUpdateStatus`: `not_started`, `pending`, `in_progress`, `completed`, `deferred`

Project asset line enums:

- `AssetLineReviewStatus`: `raw`, `parsed`, `identity_suggested`, `identity_rejected`, `identity_approved`, `taxonomy_suggested`, `taxonomy_rejected`, `taxonomy_approved`, `knowledge_matched`, `review_required`, `approved`, `locked`, `excluded`
- `AssetLineValidationStatus`: `not_validated`, `valid`, `has_warnings`, `has_errors`

Project file enums:

- `ProjectFileCategory`: `unknown`, `customer_excel`, `report`, `certificate`, `contract`, `supplier_quote`, `catalogue`, `photo`, `qc_form`, `payment`, `other`
- `FileProcessingStatus`: `uploaded`, `queued`, `processing`, `processed`, `failed`, `ignored`

Important Sprint 1 boundary:

- Fields referencing future entities such as asset identity, taxonomy, technical specifications, quotes, appraised price, generated documents, workflow transitions, and knowledge updates may be represented only as nullable placeholders where the Sprint 1 model requires them.
- Future behavior must not be implemented in Sprint 1.

## Tables And Migrations Expected

Exact table names should be confirmed during the persistence ADR and kept consistent with the repo's selected ORM/migration conventions. Expected tables are:

- `organization_profiles`
- `users`
- `roles`
- `user_roles`
- `user_permission_snapshots`
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

Expected migration/seed baseline:

- Create Sprint 1 schema for organization, user, role, master data, project, project asset line, and project file storage.
- Seed standard roles.
- Seed baseline RBAC permissions from `13_SECURITY/03_AUTHORIZATION_RBAC.md`.
- Seed required reference data only if explicitly specified by design or test fixture needs.
- Do not seed production customer, supplier, project, or private organization data.

Missing direct source:

- `16_MIGRATION_AND_SEED_PLAN.md` is not present in the extracted slice or source ZIP. The migration/seed plan above is derived from data model and security sources and should be validated by ADR or design clarification before coding.

## API Endpoints Expected

### Authentication

From `13_SECURITY/02_AUTHENTICATION.md`:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/password-reset/request`
- `POST /api/v1/auth/password-reset/confirm`

Sprint 1 intake note:

- Auth/RBAC implementation is not part of this intake. It should be handled by a dedicated Sprint 1 PR only after ADRs settle session/cookie and password hashing choices.

### Project

From `12_API/03_PROJECT_API.md`:

- `POST /api/v1/projects` - `project:create`
- `GET /api/v1/projects` - `project:read`
- `GET /api/v1/projects/{project_id}` - `project:read`
- `PATCH /api/v1/projects/{project_id}` - `project:update`
- `POST /api/v1/projects/{project_id}/files` - `project:file:upload`
- `POST /api/v1/projects/{project_id}/review/start` - `project:update`
- `POST /api/v1/projects/{project_id}/review/complete` - `project:review:complete`
- `POST /api/v1/projects/{project_id}/documents/generate-draft` - `project:update`
- `POST /api/v1/projects/{project_id}/qc/submit` - `project:update`
- `POST /api/v1/projects/{project_id}/reject` - `project:reject`
- `POST /api/v1/projects/{project_id}/approve` - `project:approve`
- `POST /api/v1/projects/{project_id}/archive` - `project:archive`

Sprint 1 intake note:

- Document generation, AI parsing, knowledge update, taxonomy, identity, and pricing behavior belong to later sprints. For Sprint 1, these endpoints need an ADR/design decision: implement only the allowed command/state skeleton, defer the endpoint, or return an explicit not-yet-implemented response without side effects.

### Master Data

From `12_API/05_MASTER_DATA_API.md`:

- Customer create, list, update, deactivate, merge
- Supplier create, list, update, deactivate, merge
- Country create, list
- Province create, list
- Brand create, list
- Manufacturer create, list
- Unit create, list
- Currency create, list
- Signer profile create, list, update

## Permission And RBAC References

Primary source: `13_SECURITY/03_AUTHORIZATION_RBAC.md`.

Project permissions:

- `project:create`
- `project:read`
- `project:update`
- `project:file:upload`
- `project:asset_line:read`
- `project:review:complete`
- `project:approve`
- `project:reject`
- `project:archive`
- `project:cancel`

Master data permissions:

- `master_data:customer:*`
- `master_data:supplier:*`
- `master_data:reference:*`
- `master_data:brand:*`
- `master_data:unit:*`
- `master_data:currency:create`
- `master_data:signer:create`
- `master_data:signer:update`

Acceptance reference examples:

- Viewer cannot create project.
- Appraiser can create project.
- Reviewer can approve project.
- Viewer cannot create customer.
- Revoked user role is removed from effective permissions.

## Acceptance Tests To Implement

### Project Acceptance

From `14_ACCEPTANCE_TESTS/PROJECT_ACCEPTANCE_TESTS.md`:

- Create project.
- Duplicate project code rejected.
- Inactive customer rejected.
- Upload project file.
- Review guard fails without approved identity.
- Approve project.
- Archive requires knowledge update or defer reason.
- Archive with deferred knowledge update.
- Project pagination.
- Project filter/search/update PATCH.
- Archived project is read-only.
- Start review.
- Reject requires reason.
- Same email can log in to different organizations using organization slug.

Sprint 1 boundary:

- Tests involving identity approval, taxonomy approval, AI parsing, document generation, pricing, or knowledge update should be implemented only as far as Sprint 1 is allowed to model state and guard rails. Full future-sprint behavior must be deferred.

### Master Data Acceptance

From `14_ACCEPTANCE_TESTS/MASTER_DATA_ACCEPTANCE_TESTS.md`:

- Create customer.
- Reject duplicate tax code.
- Fuzzy duplicate customer warning.
- Deactivate customer.
- Merge customer.
- Create supplier.
- Merge supplier.
- Viewer cannot create customer.
- Customer search and pagination.
- Patch customer.
- Create country and province.
- Create brand.
- Create unit.
- Create signer profile.
- UserRole determines login roles.
- Revoked role removal.

Sprint 1 boundary:

- Fuzzy duplicate matching needs ADR/design clarification before implementation because the algorithm and threshold are not specified in the design files read.

## Suggested PR Sequence

1. `S1-PR-002` - Persistence and migration foundation.
2. `S1-PR-003` - Organization/User/Role baseline.
3. `S1-PR-004` - Reference master data tables.
4. `S1-PR-005` - Customer/Supplier/Brand/Manufacturer/Unit/Country/Province APIs.
5. `S1-PR-006` - Project model and initial ProjectAssetLine/ProjectFile model.
6. `S1-PR-007` - Project commands/API skeleton within Sprint 1 scope.
7. `S1-PR-008` - RBAC/permission seed baseline.
8. `S1-PR-009` - Sprint 1 acceptance tests.
9. `S1-PR-010` - Sprint 1 final audit.

## ADRs Needed Before Coding

- Persistence stack: ORM, migration tool, async/sync database pattern, transaction boundaries, and test database strategy.
- Auth/session strategy: secure HTTP-only cookie versus token mechanics, password hash package selection, password reset token storage, and local test defaults.
- RBAC enforcement shape: dependency/middleware design, permission cache or snapshot behavior, and seed ownership.
- Audit/event persistence: whether command/event records are stored in Sprint 1 and how audit history is represented.
- Fuzzy duplicate detection: algorithm, thresholds, blocking versus warning behavior, and test determinism.
- File upload storage: whether Sprint 1 writes project file metadata only or integrates MinIO local storage.
- Future-slice workflow endpoints: how Sprint 1 handles document generation, AI parsing, knowledge update, identity, taxonomy, and pricing references without implementing later sprint behavior.
- Migration and seed plan: required because `16_MIGRATION_AND_SEED_PLAN.md` is missing from available design artifacts.

## Risks And Ambiguities

- The extracted Sprint 1 design folder is incomplete and does not contain several files named in the task.
- `02_DESIGN_PRINCIPLES.md`, `16_MIGRATION_AND_SEED_PLAN.md`, and `17_CODEX_PROMPTS_V1_2_ALPHA.md` are missing from both extracted slice and source ZIP.
- Project workflow APIs reference later sprint behavior, including AI parsing, document generation, taxonomy, identity, pricing, and knowledge update.
- Project asset line approval guards depend on future Sprint 2 and Sprint 3 entities.
- Fuzzy duplicate warnings are required by acceptance tests but algorithmic behavior is not specified.
- Auth endpoints are documented in the Sprint 1 slice, but the task forbids implementing auth/RBAC logic during this intake.
- Final table naming and migration conventions are not yet established in the Sprint 0 repo.

## Not In Sprint 1

Do not implement:

- Taxonomy behavior or taxonomy pages.
- Asset identity canonicalization or matching behavior.
- Technical specification extraction or KTKT workflows.
- Quote batch or appraised price decision behavior.
- Knowledge evidence workflows.
- AI parsing or AI governance behavior.
- Document drafting/rendering/generation behavior.
- Workflow Workbench UI.
- Security administration UI.
- Production deployment, cloud infrastructure, or paid external services.
- Any domain behavior not present in the Design Book.

## Scope Statement

This plan is a design intake artifact only. No backend source, frontend source, worker source, migrations, APIs, dependencies, models, or design reference files were changed by S1-PR-001.
