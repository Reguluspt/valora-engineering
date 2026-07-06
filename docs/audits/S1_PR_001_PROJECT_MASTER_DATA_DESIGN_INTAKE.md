# S1-PR-001 Project + Master Data Design Intake

**Task ID:** S1-PR-001  
**Task name:** Sprint 1 Project + Master Data Design Intake  
**Audit date:** 2026-07-06  
**Sprint:** Sprint 1 - Project + Master Data  
**Final result:** PASS WITH FIXES

## Files Checked

Repo files:

- `README.md`
- `CODEX.md`
- `ENGINEERING_GUARDRAILS.md`
- `PR_RULES.md`
- `docs/01_SPRINT_0_PLAN.md`
- `docs/02_ENGINEERING_GUARDRAILS.md`
- `docs/03_DEFINITION_OF_DONE.md`
- `docs/04_MODULE_OWNERSHIP_MAP.md`
- `docs/audits/S0_PR_008_SPRINT_0_FINAL_ACCEPTANCE_AUDIT.md`
- `docs/adr/0001-record-architecture-decisions.md`

Final handoff files:

- `E:\Project Valora\valora-design-book-v1.2-final-full-package\README.md`
- `E:\Project Valora\valora-design-book-v1.2-final-full-package\manifest.json`
- `E:\Project Valora\valora-design-book-v1.2-final-full-package\05_FINAL_HANDOFF\02_ENGINEERING_HANDOFF_GATE.md`
- `E:\Project Valora\valora-design-book-v1.2-final-full-package\05_FINAL_HANDOFF\03_SPRINT_SEQUENCE_FINAL.md`
- `E:\Project Valora\valora-design-book-v1.2-final-full-package\05_FINAL_HANDOFF\04_FINAL_IMPLEMENTATION_GUARDRAILS.md`

Sprint 1 extracted slice files:

- `02_SOURCE_SLICES_COMPLETED\01_v1.2-alpha-project-master-data-completed\README.md`
- `02_SOURCE_SLICES_COMPLETED\01_v1.2-alpha-project-master-data-completed\01_SCOPE_AND_COMPLETION_GATE.md`
- `02_SOURCE_SLICES_COMPLETED\01_v1.2-alpha-project-master-data-completed\15_CROSS_REFERENCE_MAP.md`
- `02_SOURCE_SLICES_COMPLETED\01_v1.2-alpha-project-master-data-completed\CHANGELOG.md`
- `02_SOURCE_SLICES_COMPLETED\01_v1.2-alpha-project-master-data-completed\00_AUDIT_FIX_SUMMARY.md`

Sprint 1 source ZIP entries read without extraction:

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
- `15_CROSS_REFERENCE_MAP.md`

## Design Source Status

Result: PASS WITH FIXES.

The primary extracted Sprint 1 alpha design folder is incomplete. It contains only five files:

- `00_AUDIT_FIX_SUMMARY.md`
- `01_SCOPE_AND_COMPLETION_GATE.md`
- `15_CROSS_REFERENCE_MAP.md`
- `CHANGELOG.md`
- `README.md`

Detailed Sprint 1 design files are present in:

- `E:\Project Valora\valora-design-book-v1.2-final-full-package\01_SOURCE_ZIPS\valora-design-book-v1.2-alpha-project-master-data-completed.zip`

Missing requested design artifacts:

- `02_DESIGN_PRINCIPLES.md`
- `16_MIGRATION_AND_SEED_PLAN.md`
- `17_CODEX_PROMPTS_V1_2_ALPHA.md`

The missing artifacts should be fixed in the design package or acknowledged by ADR/design clarification before coding depends on them.

## Sprint 0 Foundation Readiness

Result: PASS.

`docs/audits/S0_PR_008_SPRINT_0_FINAL_ACCEPTANCE_AUDIT.md` reports:

- Final result: `PASS`
- Recommendation: `Ready Sprint 1`
- Backend FastAPI skeleton exists and `/health` works.
- Frontend React/Vite shell exists and remains Sprint 0-only.
- Worker Python skeleton exists and remains Sprint 0-only.
- Local infra scope is PostgreSQL, Redis, and MinIO only.
- CI pipeline covers backend tests, worker tests, frontend lint, and frontend build.
- Rule files and ADR template exist.
- No business/domain implementation was added in Sprint 0.

## Repo Structure Inspection

Result: PASS.

Observed Sprint 0 structure:

- `backend/app/modules/project_master_data/` exists as an empty bounded-context boundary with `README.md` and `__init__.py`.
- Backend, frontend, and worker source remain Sprint 0 skeletons.
- `docs/adr/0001-record-architecture-decisions.md` exists for implementation decisions.
- `docs/sprint-1/` was created for intake planning documents.

No Sprint 1 backend, frontend, worker, model, migration, API, or dependency code was added by this task.

## Entities Identified

Organization and identity:

- `OrganizationProfile`
- `User`
- `Role`
- `UserRole`
- `UserPermissionSnapshot`

Master Data:

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

Project:

- `Project`
- `ProjectAssetLine`
- `ProjectFile`

Future-sprint references to defer:

- `CanonicalAsset`
- `AssetVariant`
- `TaxonomyNode`
- `TechnicalSpecification`
- `QuoteBatch`
- `AppraisedPriceDecision`
- `GeneratedDocument`
- `WorkflowTransition`
- `KnowledgeQueueItem`

## APIs Identified

Authentication endpoints:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/password-reset/request`
- `POST /api/v1/auth/password-reset/confirm`

Project endpoints:

- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `PATCH /api/v1/projects/{project_id}`
- `POST /api/v1/projects/{project_id}/files`
- `POST /api/v1/projects/{project_id}/review/start`
- `POST /api/v1/projects/{project_id}/review/complete`
- `POST /api/v1/projects/{project_id}/documents/generate-draft`
- `POST /api/v1/projects/{project_id}/qc/submit`
- `POST /api/v1/projects/{project_id}/reject`
- `POST /api/v1/projects/{project_id}/approve`
- `POST /api/v1/projects/{project_id}/archive`

Master Data endpoints:

- Customer create/list/update/deactivate/merge.
- Supplier create/list/update/deactivate/merge.
- Country create/list.
- Province create/list.
- Brand create/list.
- Manufacturer create/list.
- Unit create/list.
- Currency create/list.
- Signer profile create/list/update.

## Permissions Identified

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

Master Data permissions:

- `master_data:customer:*`
- `master_data:supplier:*`
- `master_data:reference:*`
- `master_data:brand:*`
- `master_data:unit:*`
- `master_data:currency:create`
- `master_data:signer:create`
- `master_data:signer:update`

Role baseline:

- `owner`
- `admin`
- `appraiser`
- `reviewer`
- `knowledge_curator`
- `viewer`

## Acceptance Tests Identified

Project acceptance areas:

- Project creation.
- Duplicate project code rejection.
- Inactive customer rejection.
- Project file upload.
- Review guard behavior.
- Project approval.
- Archive knowledge-update/defer reason behavior.
- Pagination, filter, search, and PATCH.
- Archived project read-only behavior.
- Start review.
- Reject requires reason.
- Same email across organizations with organization slug login.

Master Data acceptance areas:

- Customer create, duplicate tax code, fuzzy duplicate warning, deactivate, merge, search, pagination, and PATCH.
- Supplier create and merge.
- Viewer cannot create customer.
- Country and province create/list.
- Brand create/list.
- Unit create/list.
- Signer profile create/list/update.
- UserRole effective roles and revoked-role behavior.

## ADRs And Clarifications Needed

- Persistence stack, ORM, migration tool, transaction pattern, and test database strategy.
- Auth/session strategy and password hashing package.
- RBAC enforcement shape and permission snapshot behavior.
- Audit/event persistence approach for command/event design.
- Fuzzy duplicate matching algorithm and warning threshold.
- File upload storage policy for Sprint 1.
- Policy for Sprint 1 handling of future-sprint Project workflow endpoints.
- Migration and seed plan source gap because `16_MIGRATION_AND_SEED_PLAN.md` is missing.

## Sprint 1 Scope Compliance

Result: PASS.

This intake only created documentation. It did not:

- Implement database models.
- Add migrations.
- Implement APIs.
- Add dependencies.
- Implement auth/RBAC logic.
- Modify backend source code.
- Modify frontend source code.
- Modify worker source code.
- Modify the design reference package.
- Invent domain behavior outside the Design Book.

## Checks Run

- `git status --short` before edits: clean.
- `rg --files` in current repo: confirmed Sprint 0 skeleton and audit files.
- `Get-ChildItem` on extracted Sprint 1 slice: confirmed incomplete extracted design folder.
- Source ZIP entry listing via .NET `System.IO.Compression.ZipFile`: confirmed detailed data model, API, security, acceptance test, and domain entries exist in ZIP.

Final post-write checks should confirm only allowed files changed.

## Documents Created

- `docs/audits/S1_PR_001_PROJECT_MASTER_DATA_DESIGN_INTAKE.md`
- `docs/sprint-1/PROJECT_MASTER_DATA_IMPLEMENTATION_PLAN.md`
- `docs/sprint-1/PROJECT_MASTER_DATA_PR_BREAKDOWN.md`

## Recommended Fixes

- Add or restore missing extracted design files:
  - `02_DESIGN_PRINCIPLES.md`
  - `16_MIGRATION_AND_SEED_PLAN.md`
  - `17_CODEX_PROMPTS_V1_2_ALPHA.md`
- Create ADRs before coding starts for persistence, auth/session, RBAC, audit/events, fuzzy duplicate matching, file upload storage, and future-slice endpoint handling.
- Treat detailed Sprint 1 source ZIP entries as the implementation reference until the extracted package is corrected.

## Final Result

PASS WITH FIXES.

Sprint 1 design intake is complete and the implementation plan/PR breakdown exist. Sprint 1 can proceed to ADR resolution and then implementation PRs. Coding should not begin until the missing/ambiguous design points listed above are resolved or assigned to ADRs.
