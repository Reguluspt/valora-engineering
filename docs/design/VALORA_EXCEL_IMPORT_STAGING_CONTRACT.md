# Excel Import Staging Contract

- **Status**: Authoritative API & Domain Contract
- **Sprint Target**: S12-PR-001

---

## 1. Purpose
This document establishes the architecture, lifecycle, and staging boundary for importing asset lists from Excel spreadsheets into Project Valora. It ensures that uploaded records are staged, mapped, and validated within a secure environment before they can be promoted to the official valuation master records.

## 2. Relationship to Authoritative Contracts
- **Relationship to Design Book v1.3**: Implements the staging boundary of the Excel Import Pipeline module. Aligns with the Non-IT UX registry to present clear validation errors. Enforces AI-assistance guardrails (AI cannot auto-approve or auto-import).
- **Relationship to Sprint 11 Live Workbench Loop**: Staged records do not appear in the Live Workbench grid. Staged data remains in a separate sandbox layer. A separate, future "Apply" action will copy valid staging lines to the official `ProjectAssetLine` table, which the Workbench then loads.
- **Relationship to Vietnamese i18n Dictionary**: Keys for validation results and import status tags are translated to user-friendly Vietnamese labels (e.g., `Đang chờ kiểm tra`, `Hợp lệ`, `Không hợp lệ`, `Có cảnh báo`).

## 3. Import Lifecycle
The import process is structured across the following stages:

```mermaid
graph TD
    Upload[1. Upload Excel File] --> CreateBatch[2. Create Import Batch]
    CreateBatch --> ParseSheet[3. Parse Spreadsheet Cells]
    ParseSheet --> ValidateStaging[4. Validate Staging Rows]
    ValidateStaging --> ReviewValidation[5. Review Staging Grid]
    ReviewValidation --> ApplyOfficial[6. Apply Staged Rows]
    ApplyOfficial --> Workbench[7. Open in Live Workbench]
```

*Note: S12-PR-001 implements step 2 and defines the structures for steps 3 and 4. Actual parsing, file upload streams, and the apply-to-workbench action (steps 5-7) are deferred to subsequent PRs.*

## 4. Staging vs. Official Data Boundary
Under no circumstances do import staging rows write to, mutate, or affect the official `ProjectAssetLine` table. 
- **Read Isolation**: Staged rows are stored in the `project_asset_import_staging_rows` table. They are completely excluded from the `/api/v1/projects/{project_id}/asset-lines` endpoint.
- **Write Isolation**: Staging data is read-only for standard valuation calculations. It exists solely to allow mapping corrections and validation review by users.

## 5. Excel Source Handling & Raw Value Preservation
- **Treat Cells as Values**: All cells are treated as raw string values. Formulating or running Excel macro logic is forbidden.
- **Traceability**: The database keeps a copy of the raw cell values originally retrieved from the spreadsheet column positions in the `raw_values` JSON dictionary. This ensures complete auditability and error diagnostic capabilities.
- **No Absolute Path Exposure**: File path mappings on the server are masked. The batch stores only the user-visible filename (e.g., `assets.xlsx`) to prevent directory traversal or internal path leakage.

## 6. Column Mapping Assumptions
During ingestion, the parser maps spreadsheet columns to staging row target fields:
- `asset_name` -> `proposed_asset_name`
- `description` -> `proposed_description`
- `quantity` -> `proposed_quantity`
- `unit` -> `proposed_unit`
- `raw_price` -> `proposed_raw_price`
- `currency` -> `proposed_currency`

These mapped properties are validated prior to being applied to official tables.

## 7. Validation Status Model
Staged rows are assigned one of four validation statuses:
- **`pending`** (`Đang chờ kiểm tra`): The row has been parsed but validation rules have not run yet.
- **`valid`** (`Hợp lệ`): The row has passed all schema checks and is ready to be applied.
- **`warning`** (`Có cảnh báo`): The row has minor validation discrepancies but can be applied (with warnings noted).
- **`invalid`** (`Không hợp lệ`): The row contains severe validation errors (e.g. invalid quantity format, missing asset name) and cannot be applied until corrected.

## 8. Error Behavior & Non-IT Shielding
- Parser exceptions or data type mismatches are converted into clean, business-friendly errors stored in the `validation_errors` JSON array.
- Technical details such as ORM constraint names, SQL trace dumps, or parser library exception traces are kept on the server and never exposed in the API.

## 9. RBAC & Multi-Tenant Scoping
- **Multi-Tenant Scoping**: All routes enforce active `organization_id` verification. Users cannot create, retrieve, or query batches and staging rows associated with projects belonging to another tenant organization.
- **Permissions**:
  - `POST /api/v1/projects/{project_id}/asset-imports`: Requires `workbench:edit` (as this prepares data modification).
  - `GET /api/v1/projects/{project_id}/asset-imports`: Requires `project:read`.
  - `GET /api/v1/projects/{project_id}/asset-imports/{batch_id}/rows`: Requires `project:read`.

## 10. AI Guardrails
AI integration is strictly advisory. AI cannot auto-map, auto-approve, or auto-apply import staging rows. All final mappings and promotion to official records require explicit human confirmation.

## 11. API Route Contract

### A. Create Import Batch Metadata
- **Route**: `POST /api/v1/projects/{project_id}/asset-imports`
- **Permission**: `workbench:edit`
- **Request Body**:
  ```json
  {
    "source_filename": "assets.xlsx",
    "source_sheet_name": "Sheet1"
  }
  ```
- **Response Shape**:
  ```json
  {
    "id": "uuid-string",
    "project_id": "uuid-string",
    "status": "created",
    "source_filename": "assets.xlsx",
    "source_sheet_name": "Sheet1",
    "total_rows": 0,
    "valid_rows": 0,
    "invalid_rows": 0,
    "warning_rows": 0,
    "created_at": "iso-datetime",
    "updated_at": "iso-datetime"
  }
  ```

### B. List Import Batches
- **Route**: `GET /api/v1/projects/{project_id}/asset-imports`
- **Permission**: `project:read`
- **Response Shape**:
  ```json
  [
    {
      "id": "uuid-string",
      "project_id": "uuid-string",
      "status": "ready_for_review",
      "source_filename": "assets.xlsx",
      "source_sheet_name": "Sheet1",
      "total_rows": 120,
      "valid_rows": 98,
      "invalid_rows": 12,
      "warning_rows": 10,
      "created_at": "iso-datetime"
    }
  ]
  ```

### C. List Staging Rows
- **Route**: `GET /api/v1/projects/{project_id}/asset-imports/{batch_id}/rows`
- **Permission**: `project:read`
- **Query Params**:
  - `limit` (default 50)
  - `offset` (default 0)
  - `validation_status` (optional: pending | valid | invalid | warning)
- **Response Shape**:
  ```json
  {
    "project_id": "uuid-string",
    "import_batch_id": "uuid-string",
    "items": [
      {
        "id": "uuid-string",
        "import_batch_id": "uuid-string",
        "source_row_number": 12,
        "proposed_asset_name": "Máy xúc Komatsu PC200",
        "proposed_quantity": "1",
        "proposed_unit": "cái",
        "proposed_raw_price": "100000000",
        "proposed_currency": "VND",
        "validation_status": "warning",
        "validation_errors": [],
        "validation_warnings": [
          {
            "field": "year",
            "message_key": "excel.validation.year_missing"
          }
        ]
      }
    ],
    "total": 1,
    "limit": 50,
    "offset": 0
  }
  ```
