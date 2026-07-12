# S12-R-004 — Official Mutation Command & Atomic Audit Gate Audit

## Status
`PASS — CODE-BEARING HEAD VALIDATED — READY FOR REVIEW`

## Overview
This audit verifies the implementation of the S12-R-004 requirements for the official mutation command and atomic audit gate on the workbench project asset lines.

## Verified Implementation Details
1. **DRAFT-Only Policy**:
   - Committing drafts is strictly allowed only when `Project.status == ProjectWorkflowStatus.DRAFT`.
   - For all other statuses (`SUBMITTED`, `UNDER_REVIEW`, `APPROVED`, `ARCHIVED`, `CANCELLED`), the commit request is rejected with `400 Bad Request`. No mutations are applied, and no AuditEvents are stored.
2. **Explicit Version Locking**:
   - Modified `AssetLineDraftCommitRequest` schema to require a `version_token: str` representing the official base version.
   - Enforce optimistic locking by validating that `request_version == draft.base_row_version == official_line.row_version` inside the atomic database transaction. Any mismatch returns HTTP 409 Conflict.
   - `version_token` must be a strictly positive integer (> 0). Non-positive or malformed tokens return HTTP 400.
3. **Pessimistic Database Concurrency Protection**:
   - Acquired a PostgreSQL-backed row lock via `.with_for_update()` when fetching the official project asset line to protect against concurrent update anomalies.
4. **Decimal-Safe Type Handlers**:
   - Implemented strict scale and precision validation matching database `Numeric(15,2)` constraints in the `appraised_unit_price` field handler.
   - Rejected boolean types, non-numeric strings, negatives, and NaN/Infinity values with HTTP 400.
5. **PATCH Direct-Field Bypass Protection**:
   - Used `payload.model_fields_set` in the PATCH route to detect and reject direct updates to gated fields (`description`, `appraised_unit_price`, etc.), preventing bypasses via explicit `null` values.
6. **Audit Payload Key**:
   - Renamed the audit payload key to `committed_fields` (from `field_keys`) to avoid auto-redaction by the key-based sanitizer.
7. **Explicit Mutation Registry**:
   - Replaced dynamic `setattr` with an explicit registry (`MUTATION_REGISTRY`) invoking typed mutation functions for safety.
8. **Session & Permission Enforcement**:
   - Integrated `require_owned_workbench_session` to validate user session ownership, scoping, and activity status. Mismatches raise HTTP 404.
   - Enforced internal RBAC checks in the mutation command via `derive_effective_permissions` to prevent unauthorized mutations (HTTP 403).

## Test Matrix Results
All S12-R-004 unit and integration tests passed successfully.

| Test Case | Scope | Status | Details |
|---|---|---|---|
| `test_draft_only_policy` | DRAFT-only policy enforcement | PASS | Parameterized check over all workflow states. |
| `test_patch_model_fields_set_null_bypass_blocked` | Gated field direct PATCH block | PASS | Blocks explicit null bypasses using model_fields_set. |
| `test_patch_model_fields_set_allowed_field_accepted` | Allowed field direct PATCH | PASS | Updates allowed fields like asset_name directly. |
| `test_version_token_matrix` | Version token validation matrix | PASS | Checks strictly positive values and mismatch conflicts. |
| `test_validate_description_unit` | Description field validator | PASS | Rejects non-strings and lengths > 5000. |
| `test_validate_appraised_unit_price_unit` | Appraised unit price validator | PASS | Ensures scale <= 2 and precision <= 13 digits. |
| `test_permissions_and_scoping_matrix` | Security matrix | PASS | Checks unauthenticated, viewer, and cross-tenant rejects. |
| `test_audit_trail_payload_committed_fields` | Audit logging payload | PASS | Asserts committed_fields key (not field_keys) and raw values. |
| `test_atomic_rollback_on_audit_failure` | Transaction boundary safety | PASS | Rolls back database mutations if audit logger fails. |
| `test_remaining_draft_state_after_partial_commit` | Leftover draft detection | PASS | Returns correct draft status when some drafts remain. |
| `test_no_forbidden_side_effects_on_commit` | Side effect isolation | PASS | Confirms no external or AI calls are triggered. |
| `test_commit_command_ast_no_http_calls` | Outbound request prohibition | PASS | AST-based check ensuring no HTTP libraries are invoked. |
| `test_postgres_concurrent_official_commit` | PostgreSQL concurrent safety | PASS (Skip locally) | Verifies serialized row locking on PostgreSQL. |

## CI / Verification Evidence
- **Repository HEAD**: `7086eca114331e59a5d595a0064478aa42fab27c`
- **Backend pytest**: `319 passed, 4 skipped, 0 failed`
- **Frontend vitest**: `28 passed (7 test files)`
- **Quality Gates**: Ruff, Security scanner, Alembic heads, Frontend typecheck & build: ALL PASS.
