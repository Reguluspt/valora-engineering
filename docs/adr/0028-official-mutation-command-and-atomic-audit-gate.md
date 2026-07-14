# ADR 0028: Official Mutation Command and Atomic Audit Gate

## Status
Accepted

## Context
During Phase S12-R-004, the application required introducing strict security and integrity controls over mutations of project asset line fields (such as `description` and `appraised_unit_price`). Prior to S12-R-004, users could potentially bypass the live workbench validation and audit logging flows by issuing direct `PATCH` requests to the resource endpoints. Furthermore, we needed a robust transaction safety mechanism (optimistic version locking and atomic rollbacks) and strict validation layers.

## Decision

### 1. Command Pattern Separation
Separated write/commit logic out of the controller routing layers into a specialized, reusable command `execute_commit_asset_line_draft`.

### 2. Direct Mutation Bypass Protection
Hardened the standard `PATCH /api/v1/projects/{project_id}/asset-lines/{line_id}` route to reject direct mutations to restricted fields (`description`, `appraised_unit_price`, `review_status`, and `validation_status`) with `400 Bad Request` and user-friendly messages.

The check uses `payload.model_fields_set` (not `is not None`) to block both explicit `null` values and explicit field presence, preventing null-bypass attacks.

### 3. Exact Optimistic Version Lock
Strictly enforce version locking based on exact version equality (`draft.base_row_version == official_line.row_version`). Stale or future versions reject with `409 Conflict`.

`version_token` must be a strictly positive integer (> 0). Zero and negative values are rejected with `400`.

### 4. DRAFT-Only Policy — APPROVED by User
Official draft commit is **allowed only while `Project.status == DRAFT`**.

For every other `ProjectWorkflowStatus` (`SUBMITTED`, `UNDER_REVIEW`, `APPROVED`, `ARCHIVED`, `CANCELLED`):
- Reject official draft commit with `400 Bad Request`.
- Official line remains unchanged.
- `row_version` remains unchanged.
- Drafts remain unchanged.
- No `draft-commit` `AuditEvent` is persisted.

Corrections after DRAFT must use a future approved change-request or reversal workflow.

### 5. Atomic Rollback and Transaction Boundary
Database commit and audit trail operations occur atomically. If audit trail logging fails, or any other exception is raised, the database transaction is rolled back.

### 6. Strict Field Validation Handlers
- `description`: Must be an explicit `str`. All other types (bool, int, float, dict, list, etc.) are rejected with `400`. Max length 5000 characters.
- `appraised_unit_price`: Must be a positive numeric value (int, float, Decimal string). Reject booleans, lists, dicts, NaN, Infinity, negative values, values with more than 2 decimal places, and values exceeding 13 integer digits.

### 7. Audit Payload Key
The audit payload uses `committed_fields` (not `field_keys`) to avoid auto-redaction by the sanitizer (which redacts any key containing the substring `"key"`).

## Consequences
- Clean separation of concern; controllers remain thin and focused.
- Higher level of security and data integrity.
- Safe audit trails for all operations using the `committed_fields` key.
- Clean rollback handling prevents orphaned database mutations when background audit logging fails.
- The DRAFT-only policy ensures workflow state integrity and prevents unauthorized mutations after a project has advanced beyond Draft.

## Addendum — Excel Staging Apply command (2026-07-14)

**Status:** Owner-approved addendum; does not rewrite the historical ADR body above.
**Related:** ADR 0029, `VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md` §15, S12-PR-004.

### Clarifications

1. **Excel Staging Apply** is a **separate** human-confirmed, DRAFT-only official-mutation command (`ApplyProjectAssetImportBatch`). It is not a direct `PATCH` bypass and is not the draft-commit command.
2. **Direct PATCH** of restricted fields (`description`, `appraised_unit_price`, `review_status`, `validation_status`) remains blocked as decided in this ADR.
3. **Description on create via Apply:** the owner explicitly authorizes setting `description` **only** through the approved Apply handler, using the same string-type and max-length 5000 safeguards defined in §6 of this ADR. This does not authorize Apply to set `appraised_unit_price`, `review_status`, or `validation_status` from spreadsheet values.
4. **Spreadsheet-sourced** `proposed_appraised_unit_price`, `proposed_review_status`, and `proposed_validation_status` remain forbidden inputs for official promotion.
5. **Subsequent edits** of restricted fields on existing official lines remain under this ADR’s draft-commit / version-token rules.
6. **Excel upload and validation** continue to never mutate official `ProjectAssetLine` rows.
