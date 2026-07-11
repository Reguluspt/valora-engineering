# S12-PR-001 — Excel Import Contract & Staging Model Audit

## A. Title and Final Status

- **Audit Reference**: S12-PR-001
- **Audit Title**: Excel Import Contract & Staging Model
- **Final Status**: **PASS**

---

## B. Files Changed

- [VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md)
- [models.py](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/modules/project_master_data/models.py)
- [workbench_schemas.py](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/modules/project_master_data/workbench_schemas.py)
- [projects.py](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/api/projects.py)
- [a87a9b6da9a4_create_asset_import_staging_tables.py](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/alembic/versions/a87a9b6da9a4_create_asset_import_staging_tables.py)
- [test_asset_imports.py](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/tests/test_asset_imports.py)
- [assetImports.ts](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/api/assetImports.ts)
- [S12_PR_001_EXCEL_IMPORT_CONTRACT_STAGING_MODEL_AUDIT.md](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/audits/S12_PR_001_EXCEL_IMPORT_CONTRACT_STAGING_MODEL_AUDIT.md)

---

## C. Pre-flight Reading Summary

The following documents establish the foundation for Sprint 12 and the Excel Import Pipeline module:
1. **Design Book v1.3**: Mandates that Excel uploads must stage records inside isolated staging tables first, prohibiting direct mutation of `ProjectAssetLine` table elements. Staging validation errors must be masked, translating parser errors into clean, business-friendly errors.
2. **Vietnamese i18n Dictionary & Non-IT Error Message Registry**: Requires validation rules to output friendly messages using Vietnamese labels (e.g. `Đang chờ kiểm tra`, `Hợp lệ`, `Không hợp lệ`, `Có cảnh báo`). Technical metadata (like internal parser exceptions, database row tokens) must remain hidden from non-IT end-users.
3. **Multi-Tenant Boundaries**: Requires tenant organization scoping (`organization_id` filters) across all routes and tables to prevent ID harvesting.

---

## D. Existing Project Asset Model Inspection

Inspected the `ProjectAssetLine` model fields:
- Core fields include `project_id`, `asset_name`, `description`, `quantity`, `unit_id`, `raw_price`, `raw_price_currency_id`, `appraised_unit_price`, `appraised_currency_id`, `review_status`, and `validation_status`.
- Concurrency control fields (`row_version`, `version_token`) are managed internally.
- Multi-tenancy boundaries are checked at the API layer by looking up the associated Project's `organization_id` against the current user's profile.

---

## E. Import Staging Strategy Chosen

The staging layer isolates Excel ingestion by storing rows inside `ProjectAssetImportStagingRow` entries linked to a `ProjectAssetImportBatch` status record.
- Staged rows do not write to or mutate `ProjectAssetLine`.
- Preservation of original spreadsheet structures is guaranteed by storing cells as string key-value pairs in `raw_values` JSON.

---

## F. Staging Model Summary

Implemented the following database tables in `models.py`:
1. **`project_asset_import_batches`**:
   - `id`: UUID Primary Key
   - `organization_id`: UUID FK to `organization_profiles.id`
   - `project_id`: UUID FK to `projects.id`
   - `source_filename`: String(255)
   - `source_sheet_name`: String(100) (optional)
   - `status`: String(50) (created, parsing, parsed, validation_failed, ready_for_review, applied, failed)
   - `total_rows`, `valid_rows`, `invalid_rows`, `warning_rows`: Integers
   - `created_by_user_id`: UUID FK to `users.id`
2. **`project_asset_import_staging_rows`**:
   - `id`: UUID Primary Key
   - `import_batch_id`: UUID FK to `project_asset_import_batches.id`
   - `source_row_number`: Integer
   - `raw_values`, `mapped_values`, `normalized_preview`: JSON
   - `validation_status`: String(50) (pending, valid, invalid, warning)
   - `validation_errors`, `validation_warnings`: JSON list
   - Mapped properties: `proposed_asset_name`, `proposed_description`, `proposed_quantity`, `proposed_unit`, `proposed_raw_price`, `proposed_currency`, `proposed_appraised_unit_price`, `proposed_review_status`, `proposed_validation_status`

---

## G. Migration Summary

Added Alembic migration `a87a9b6da9a4_create_asset_import_staging_tables.py`:
- Creates tables `project_asset_import_batches` and `project_asset_import_staging_rows`.
- Configures foreign keys linking to organizations, projects, users, and parent batches with cascading deletes where appropriate.
- Adds database indexes for `organization_id`, `project_id`, `import_batch_id`, and `validation_status` columns.

---

## H. API Route Summary

Implemented the following FastAPI routes in `projects.py`:
1. **`POST /api/v1/projects/{project_id}/asset-imports`**: Creates a batch metadata entry. Permission: `workbench:edit`.
2. **`GET /api/v1/projects/{project_id}/asset-imports`**: Lists project batches. Permission: `project:read`.
3. **`GET /api/v1/projects/{project_id}/asset-imports/{batch_id}/rows`**: Lists staging rows for a batch. Permission: `project:read`. Supports limit, offset, and `validation_status` filtering.

---

## I. RBAC / Scoping Summary

- **Scoping**: All endpoints verify the project's `organization_id` against `current_user.organization_id`. Access to projects, batches, or staging rows outside the user's organization returns a `404 Not Found` error.
- **RBAC**: Creating a batch requires `workbench:edit` permission. Listing batches or staging rows requires `project:read` permission.

---

## J. Official Data Immutability Statement

Verified that creating an import batch or adding staging rows does not add or alter any lines in the official `ProjectAssetLine` table. Staging tables are completely isolated from production valuation query endpoints.

---

## K. Frontend API Contract Summary

Created frontend declarations and client calls in `frontend/src/api/assetImports.ts`:
- Types: `ProjectAssetImportBatchResponse`, `ProjectAssetImportBatchCreate`, `ProjectAssetImportStagingRowResponse`, `ProjectAssetImportStagingRowPaginationResponse`.
- Client methods: `createAssetImportBatch`, `fetchAssetImportBatches`, and `fetchAssetImportRows`.

---

## L. i18n / Error UX Statement

Staging rows capture validation messages in structured objects containing `field` and `message_key` properties. Raw database logs or stack traces are not written to the client payload.

---

## M. Runtime/User-Visible Behavior Changed

**Runtime/User-Visible Behavior Changed**:
No direct visible UI change. Frontend API contract methods were added, but no user-facing upload interface or page element has been mounted in this PR.

---

## N. Tests / Quality Gates Run

### Backend Tests
- **Command**: `python -m pytest` in the `backend` folder
- **Result**: **208 passed** (including the new `tests/test_asset_imports.py` suite covering creation, listing, scoping, and validation limits).

### Frontend Tests
- **Command**: `npm run lint` and `npm run build` in the `frontend` folder
- **Result**: **Passed** (TypeScript type check compiles clean; production build is operational).
- **Command**: `npx vitest run --globals`
- **Result**: **21 passed**.

---

## O. Risks/Deferred Items

1. **Excel Sheet Parser**: File stream uploading, chunked processing, and database validation pipeline runs remain deferred to subsequent Sprint 12 PRs.
2. **Apply to Workbench**: Auto-populating staged rows into official project asset lines remains deferred.
3. **AI Mapping**: Advisory mapper card suggestions are out-of-scope for this PR.

---

## P. Design Consistency Check

- Design Book v1.3 checked: **Yes**
- Sprint 10 final acceptance checked: **Yes**
- Sprint 11 final acceptance checked: **Yes**
- Live Workbench API contract checked: **Yes**
- ProjectAssetLine model checked: **Yes**
- Import staging boundary checked: **Yes**
- RBAC/scoping checked: **Yes**
- Runtime behavior statement verified from git diff: **Yes**
- Audit file lists every changed file: **Yes**
- No official ProjectAssetLine mutation introduced: **Yes**
- No apply-to-workbench/import commit introduced: **Yes**
- No Excel upload UI introduced: **Yes**
- No AI mapping/import introduced: **Yes**
- No Gemini/DeepSeek runtime integration introduced: **Yes**
- No report generation introduced: **Yes**
- No dashboard/revenue/CRM scope introduced: **Yes**
- No backend auth/JWT change introduced: **Yes**
- No raw technical errors exposed to users: **Yes**
- No local file paths exposed to users: **Yes**
- No new English user-facing labels introduced: **Yes**
