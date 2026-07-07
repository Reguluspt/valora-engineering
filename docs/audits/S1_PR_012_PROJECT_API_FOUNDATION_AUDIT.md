# S1-PR-012: Project API Foundation Audit

## Files Changed
- `backend/app/main.py` (Registered projects router)
- `backend/app/api/projects.py` (New file containing Project, ProjectAssetLine, and ProjectFile metadata endpoints)
- `backend/app/modules/project_master_data/schemas.py` (Appended schemas for Project, ProjectAssetLine, and ProjectFile)
- `backend/tests/test_projects_api.py` (New unit/integration tests for Project APIs)
- `backend/tests/test_master_data_api.py` (Removed test_no_projects_api_exists)

## Design Files Read
- `09_DATA_MODEL/01_PROJECT_MODEL.md`
- `09_DATA_MODEL/02_MASTER_DATA_MODEL.md`
- `12_API/03_PROJECT_API.md`
- `04_DOMAIN/04A_PROJECT_COMMANDS_EVENTS.md`
- `04_DOMAIN/07A_PROJECT_STATE_MACHINE.md`
- `13_SECURITY/03_AUTHORIZATION_RBAC.md`
- `14_ACCEPTANCE_TESTS/PROJECT_ACCEPTANCE_TESTS.md`

## Endpoints Added
- **Projects**:
  - `POST /api/v1/projects` (Create project draft)
  - `GET /api/v1/projects` (List projects with filtering and pagination)
  - `GET /api/v1/projects/{project_id}` (Get project details)
  - `PATCH /api/v1/projects/{project_id}` (Update draft fields, enforces row_version check)
  - `POST /api/v1/projects/{project_id}/archive` (Archive project)
  - `POST /api/v1/projects/{project_id}/cancel` (Cancel project)
- **Asset Lines**:
  - `POST /api/v1/projects/{project_id}/asset-lines` (Add asset line item)
  - `GET /api/v1/projects/{project_id}/asset-lines` (List line items)
  - `PATCH /api/v1/projects/{project_id}/asset-lines/{line_id}` (Update line item, version-checked)
- **Files**:
  - `POST /api/v1/projects/{project_id}/files` (Create metadata record, no storage upload)
  - `GET /api/v1/projects/{project_id}/files` (List file metadata records)

## Schemas Added
- Defined `ProjectCreate`, `ProjectUpdate`, `ProjectResponse`, `ProjectAssetLineCreate`, `ProjectAssetLineUpdate`, `ProjectAssetLineResponse`, `ProjectFileCreate`, and `ProjectFileResponse` schemas in `backend/app/modules/project_master_data/schemas.py`.

## Permission Checks Applied
- Applied `require_permission` checks on all endpoints:
  - `project:create` (Create project)
  - `project:read` (List/Get projects, list files)
  - `project:update` (Update project, create/update asset lines)
  - `project:archive` (Archive project)
  - `project:cancel` (Cancel project)
  - `project:asset_line:read` (List asset lines)
  - `project:file:upload` (Upload file metadata)

## Audit Event Behavior
- Creates audit trail events inside mutation endpoints:
  - `ProjectCreated`
  - `ProjectUpdated`
  - `ProjectArchived`
  - `ProjectCancelled`
  - `ProjectAssetLineCreated`
  - `ProjectAssetLineUpdated`
  - `ProjectFileUploaded`

## Tenant Scoping Behavior
- Validates that users can only query, list, and mutate projects belonging to their `organization_id` context.
- Validates customer relationship lies within the user's organization scope.

## File Metadata-Only Policy
- `POST /api/v1/projects/{project_id}/files` takes metadata parameters JSON only; no file blob upload, no S3 client execution, and no worker/OCR triggers are defined.

## Tests/Checks Run
- Executed `python -m pytest` inside `backend`.
- All 40 tests passed successfully.

## PostgreSQL Availability Result
- PostgreSQL is unavailable locally (Port 5432 closed). Migration updates and integration verification run using SQLite in-memory static pool.

## Scope Compliance
- Exclusively implemented Project API foundations, schemas, and tests.
- Zero Workbench, workflow engine, AI parsing, or document extraction code introduced.

## Forbidden Future-Sprint Scan Result
- Verified that querying advanced workflow transitions or workbench endpoints returns 404 (non-existent).
- Zero leaks of future-sprint business logic.

## Missing or Recommended Fixes
- None.

## Final Result
- **Result:** PASS
- **Recommendation:** Ready for Project API contract hardening.
