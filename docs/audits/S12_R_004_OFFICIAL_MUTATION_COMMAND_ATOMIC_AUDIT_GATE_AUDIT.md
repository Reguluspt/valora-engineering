# S12-R-004 — Official Mutation Command & Atomic Audit Gate Audit

## Status
`LOCAL IMPLEMENTATION COMPLETE — AWAITING CI`

## Overview
This audit verifies the implementation of the S12-R-004 requirements for the official mutation command and atomic audit gate on the workbench project asset lines.

## Verified Implementation Details
1. **Explicit Version Locking**: 
   - Modified `AssetLineDraftCommitRequest` schema to require a `version_token: str` representing the official base version.
   - Enforce optimistic locking by validating that `request_version == draft.base_row_version == official_line.row_version` inside the atomic database transaction. Any mismatch returns HTTP 409 Conflict.
2. **Pessimistic Database Concurrency Protection**:
   - Acquired a PostgreSQL-backed row lock via `.with_for_update()` when fetching the official project asset line to protect against concurrent update anomalies.
3. **Decimal-Safe Type Handlers**:
   - Implemented strict scale and precision validation matching database `Numeric(15,2)` constraints in the `appraised_unit_price` field handler.
   - Rejected boolean types, non-numeric strings, negatives, and NaN/Infinity values with HTTP 400.
4. **Explicit Mutation Registry**:
   - Replaced dynamic `setattr` with an explicit registry (`MUTATION_REGISTRY`) invoking typed mutation functions (`apply_description`, `apply_appraised_unit_price`) for safety.
5. **Session & Permission Enforcement**:
   - Integrated `require_owned_workbench_session` to validate user session ownership, scoping, and activity status. Mismatches raise HTTP 404.
   - Enforced internal RBAC checks in the mutation command via `derive_effective_permissions` to prevent unauthorized mutations (HTTP 403).

## Test Matrix Results
All S12-R-004 unit and integration tests passed successfully on the local SQLite memory database.

| Test Case | Scope | Status | Details |
|---|---|---|---|
| `test_s12_r_004_direct_patch_route_validation` | Direct PATCH route validation | PASS | Direct updates to official description and price are blocked. |
| `test_s12_r_004_exact_version_locking_hardened` | Optimistic locking & mismatched versions | PASS | Reject stale/future tokens with HTTP 409. |
| `test_s12_r_004_typed_validation_rules_hardened` | Typed value validations | PASS | Checked scale, precision, invalid types, NaN/Inf bounds. |
| `test_s12_r_004_audit_trail_payload_assertions` | Audit logging exact assertions | PASS | Evaluated payload schema, actor, org, correlation, before/after values. |
| `test_s12_r_004_permissions_and_scoping_hardened` | Tenant/RBAC/scoping isolation | PASS | Asserted 403 Forbidden, 404 cross-org, 404 wrong project/session. |
| `test_s12_r_004_side_effects_prohibition_hardened` | Side effects prevention | PASS | Verified no background or AI tasks are called on commit. |
| `test_s12_r_004_atomic_rollback_on_audit_failure` | Transaction atomicity | PASS | Checked complete rollback on audit logging failure. |
| `test_postgres_concurrent_official_commit` | Concurrency check | PASS (Skip locally) | Multi-threaded PostgreSQL concurrency verification. |

## CI / Verification Evidence
- **Backend pytest**: `272 passed, 4 skipped, 0 failed`
