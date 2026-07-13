# S12-PR-002 — Excel File Upload & Parser Intake Audit

## A. Title and Final Status

- **Audit Reference**: S12-PR-002
- **Audit Title**: Excel File Upload & Parser Intake
- **Final Status**: **PASS**

---

## B. Files Changed

- [pyproject.toml](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/pyproject.toml)
- [VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md)
- [projects.py](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/api/projects.py)
- [assetImports.ts](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/api/assetImports.ts)
- [test_asset_imports.py](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/tests/test_asset_imports.py)
- [S12_PR_002_EXCEL_FILE_UPLOAD_PARSER_INTAKE_AUDIT.md](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/audits/S12_PR_002_EXCEL_FILE_UPLOAD_PARSER_INTAKE_AUDIT.md)

---

## C. Pre-flight Reading Summary

The following documents establish the boundary constraints for Excel file upload and parser intake:
1. **Design Book v1.3**: Mandates value-only parsing where formula evaluations, external workbook links, and macro scripting are not executed. Enforces friendly Vietnamese error shielding to hide stack traces and local server paths.
2. **VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md**: Establishes the sandboxed staging table lifecycle. Outlines mapping requirements and rules for raw cell preservation.
3. **Vietnamese i18n Dictionary**: Regulates localized messaging and labels. Ensure that technical indicators remain hidden behind friendly error templates.

---

## D. Parser Dependency Inspection

- **openpyxl**: Re-verified availability of the `.xlsx` file reader engine within the active Python run environment.
- **python-multipart**: Confirmed parsing support for `multipart/form-data` request payloads.
- **pyproject.toml**: Declared both `"openpyxl>=3.1.0"` and `"python-multipart>=0.0.9"` dependencies explicitly.

---

## E. Upload Route Summary

Implemented the upload endpoint in `projects.py`:
- **Route**: `POST /api/v1/projects/{project_id}/asset-imports/{batch_id}/upload`
- **Request Type**: `multipart/form-data` with form field parameter `file`
- **Permissions**: `workbench:edit`
- **Scoping**: Verifies project and batch match the user's `organization_id`. Invalid project or batch lookups yield a safe `404 Not Found` response.
- **Extension validation**: Blocks any tệp format other than `.xlsx` with a friendly error payload.
- **Sanitized Filename**: Splitting path operators (`/`, `\`) isolates and stores only the base name (e.g. `assets.xlsx`) to prevent traversal vulnerability.

---

## F. Excel Parser Behavior

- **Read-Only / Data Only Mode**: Loads sheets with `data_only=True` and `read_only=True` to extract cell values and cached evaluations safely without executing formula code or vba macros.
- **Header Normalization**: Columns are trimmed, lowercase-converted, and space/hyphen normalized using underscores (e.g. `Tên tài sản` -> `ten_tai_san` / `tên_tài_sản`).
- **Empty Rows**: Rows with no cell values are skipped.
- **Size Capping**: Capped row iteration limit bounds processing to a maximum of 5,000 data lines per upload.
- **Formula Treatment**: Evaluates cell strings without executing them as code. Programmatically generated Excel sheets with no calculated values read as empty strings.

---

## G. Column Mapping Summary

Maps column headers onto target fields using deterministic aliases matching the following attributes:
- `proposed_asset_name`: asset_name, ten_tai_san, tên_tài_sản, name
- `proposed_description`: description, mo_ta, mô_tả, specification, thong_so, thông_số
- `proposed_quantity`: quantity, so_luong, số_lượng, qty
- `proposed_unit`: unit, don_vi, đơn_vị
- `proposed_raw_price`: raw_price, gia_goc, giá_gốc, cost, price
- `proposed_currency`: currency, tien_te, tiền_tệ
- `proposed_appraised_unit_price`: appraised_unit_price, gia_tham_dinh, giá_thẩm_định, appraised_price

---

## H. Staging Row Creation Summary

For each non-empty data row:
- Inserts a record in `project_asset_import_staging_rows`.
- Stores raw strings in `raw_values` mapping headers to cell contents.
- Assigns mapping results to `mapped_values` JSON.
- Defaults status to `pending`.
- Overwrites previous staging rows on re-upload to allow clean retries.

---

## I. Batch Status/Counter Behavior

- **State Transitions**: Set to `parsing` during load, transitioning to `parsed` on success or `failed` on parsing exception.
- **Counters**: Updates `total_rows` to the number of parsed rows. Resets validation states (`valid_rows`, `invalid_rows`, `warning_rows`) to `0`.

---

## J. RBAC/Scoping Summary

- Routes are organization-scoped (`organization_id` filters) and require `X-User-Id` authentication headers.
- Accessing cross-org project or batch IDs returns a safe `404 Not Found`.
- Gated actions verify standard roles: creating/uploading requires `workbench:edit`, listing requires `project:read`.

---

## K. Official Data Immutability Statement

Verified that file uploads write exclusively to isolated staging rows and batches. Under no circumstances do uploads modify the official `ProjectAssetLine` table.

---

## L. Frontend API Contract Summary

Implemented the upload call in `frontend/src/api/assetImports.ts`:
- **Method**: `uploadAssetImportWorkbook(projectId, batchId, file)`
- Utilizes standard `FormData` serialization.

---

## M. i18n/Error UX Statement

Upload failure messages use friendly Vietnamese phrasing (e.g. tệp format block message or workbook read errors) and shield stack traces. Brand masking remains intact.

---

## N. Runtime/User-Visible Behavior Changed

**Runtime/User-Visible Behavior Changed**:
No direct visible UI change. Excel upload/parser intake API and frontend API method were added, but no user-facing upload UI was mounted.

---

## O. Tests/Quality Gates Run

- **Backend Pytest**: **209 passed** (including `test_excel_upload_and_parser` checking extension filtering, cross-org blocking, empty row skipping, header mapping, value extraction, and official data immutability).
- **Frontend build/lint checks**: **Passed** (`npm run lint` and `npm run build` returned 0 errors, vitest returned **21 passed**).

---

## P. Risks/Deferred Items

1. **Staging Validation Engine**: Detailed schema checks and data type verification checks remain deferred to the next PR.
2. **Apply to Workbench**: Writing staged rows into the official workbench valuation records is out of scope.
3. **AI-assisted Mappings**: LLM column match suggestions remain deferred.

---

## Q. Design Consistency Check

- Design Book v1.3 checked: **Yes**
- Sprint 11 final acceptance checked: **Yes**
- S12-PR-001 staging contract checked: **Yes**
- Import staging boundary checked: **Yes**
- Parser value-only behavior checked: **Yes**
- Formula/macro non-execution checked: **Yes**
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
- No raw parser stack traces exposed to users: **Yes**
- No local file paths stored or exposed: **Yes**
- No new English user-facing labels introduced: **Yes**

---

## Remediation / current-state addendum (S12-R-007 — 2026-07-13)

### Original status at audit time
- First Excel upload/parser intake landed (often described as inline in `projects.py`).
- Audit referenced local `file:///` paths and contemporaneous test counts (~209 backend / 21 frontend).
- Described organization scoping with **`X-User-Id` authentication headers** (pre-R-002 production identity model).
- Raw values described as header-keyed maps; silent truncate / overwrite behaviors were remediation targets.

### Statements superseded
| Historical statement | Current authority |
|---|---|
| Production identity via `X-User-Id` | **Superseded by S12-R-002** — authenticated session/token; tests may still override deps |
| Parser primarily inline in `projects.py` | **Superseded by S12-R-006** module `backend/app/modules/excel_import/` (`parse_workbook`, `replace_staging_rows`, `import_service`) |
| Raw values keyed only by normalized headers | **Superseded** — positional `raw_values.cells` structure |
| Soft truncate at 5000 / weak limits | **Superseded** — hard limits with typed `ParseError` codes (413/400) |
| Overwrite staging before successful commit | **Superseded** — nested savepoint; failure preserves prior generation |
| Local filesystem `file:///` links | Non-portable; use repo-relative paths |
| Test counts ~209 / 21 | Historical only; current suite larger (see R-006 CI 375/0) |

### Replacement sources
- S12-R-002 audit + merge `b025b97` (#2)
- S12-R-006 audit + merge `54872c7` (#6)
- `docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md`
- Security scanner rules in `backend/tests/check_security.py`

### Current state
S12-PR-002 is the historical introduction of upload intake. **Current production intake behavior on `main` is the R-006 hardened path.**

### Evidence limitations
Do not implement Validation Engine from this audit. S12-PR-003 remains blocked on S12-R-007 process gates.