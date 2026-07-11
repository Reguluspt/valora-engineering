# ADR 0028: Official Mutation Command and Atomic Audit Gate

## Status
Accepted

## Context
During Phase S12-R-004, the application required introducing strict security and integrity controls over mutations of project asset line fields (such as `description` and `appraised_unit_price`). Prior to S12-R-004, users could potentially bypass the live workbench validation and audit logging flows by issuing direct `PATCH` requests to the resource endpoints. Furthermore, we needed a robust transaction safety mechanism (optimistic version locking and atomic rollbacks) and validation layers.

## Decision
1. **Command Pattern Separation**: Separated write/commit logic out of the controller routing layers into a specialized, reusable command `execute_commit_asset_line_draft`.
2. **Direct Mutation Bypass Protection**: Hardened the standard `PATCH /api/v1/projects/{project_id}/asset-lines/{line_id}` route to reject direct mutations to restricted fields (`description`, `appraised_unit_price`, `review_status`, and `validation_status`) with `400 Bad Request` and user-friendly messages.
3. **Exact Optimistic Version Lock**: Strictly enforce version locking based on exact version equality (`draft.base_row_version == official_line.row_version`). Stale or future versions reject with `409 Conflict`.
4. **Atomic Rollback and Transaction Boundary**: Ensure database commit and audit trail operations occur atomically. If audit trail logging fails, or any other exception is raised, the database transaction is rolled back.
5. **Strict Field Validation Handlers**:
   - `description`: Verified as a string up to 5000 characters. Reject dictionaries, arrays, lists, booleans, and floats.
   - `appraised_unit_price`: Verified as a positive numeric type (int, float, Decimal) with scale at most 2 decimal places. Reject negative values, NaN, and Infinity.

## Consequences
- Clean separation of concern, leaving controllers simple and thin.
- Higher level of security and data integrity.
- Safe audit trails for all operations.
- Clean rollback handling prevents orphaned database mutations when background audit logging fails.
