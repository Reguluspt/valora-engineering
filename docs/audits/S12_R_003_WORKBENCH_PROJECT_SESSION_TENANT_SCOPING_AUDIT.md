# S12-R-003 — Workbench Project & Session Tenant Scoping
## Final Audit Report

---

## A. Title and Final Status

- **Task ID**: S12-R-003
- **Title**: Workbench Project & Session Tenant Scoping
- **Final Status**: **PASS**

---

## B. Root Cause Remediation

All Workbench endpoints previously loaded or saved states utilizing raw session or target IDs without validating tenant boundaries or ownership. We have remediated this by:
1. Creating a centralized FastAPI dependency `require_owned_workbench_session` checking session presence, user ownership, and tenant boundary.
2. Restricting target IDs to their respective project/tenant contexts using `resolve_workbench_target`.
3. Restricting state lookups (like layouts, grid views, panel states, selections, checkpoints, stack entries, and notifications) to the active session owner.
4. Implementing the **one active session per user + project** policy by reusing/resuming the active session if one already exists.

---

## C. ADR / Design Authority

All session constraints, target checking allowlists, and tenant separation boundaries are aligned with:
- `docs/design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md`
- `docs/design/VALORA_NON_IT_ERROR_MESSAGE_REGISTRY.md`
- `docs/adr/0026-authentication-identity-boundary-hardening-proposal.md`

---

## D. Implementation Details

### D1. Centralized Session Resolver
We implemented `require_owned_workbench_session` in [resolve_owned_session.py](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/modules/workflow_workbench/resolve_owned_session.py):
- Validates that `WorkbenchSession.id == session_id`
- Validates user ownership: `session.user_id == current_user.id`
- Validates tenant boundary: `session.project.organization_id == current_user.organization_id`
- Optionally validates active state (`require_active=True`) and project context (`expected_project_id`)
- Mismatches result in a safe `404 Not Found` to prevent ID harvesting/leakage.

### D2. Database Migration
Created a database unique index via Alembic:
`uq_active_session_per_user_project` on `workbench_sessions` for `(user_id, project_id)` where `status = 'active'`.

### D3. Target Validation
Implemented `resolve_workbench_target` validating that target IDs are valid UUIDs, are of type `project_asset_line`, and belong to the correct project.

### D4. Explicit Close Lifecycle
Implemented `POST /api/v1/workbench/sessions/{session_id}/close` transitioning the session status to `closed` and logging a `workbench.session.ended` audit event inside the same transaction.

---

## E. Verification Evidence

We ran the backend test suite consisting of 260 unit, integration, and acceptance tests:

- **Command Run**: `python -m pytest`
- **Result**: **PASS** (259 passed, 1 skipped)

### E1. Added Verification Tests
The following verification test cases were added in [test_workbench_api.py](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/tests/test_workbench_api.py):
1. `test_workbench_tenant_and_user_isolation`: Verifies that a user from Org A cannot create or access a session in Org B, and users cannot access other users' sessions.
2. `test_active_session_policy_resume`: Verifies that multiple creation requests for the same project resume the same session, and closing a session block subsequent heartbeats.
3. `test_explicit_target_validation`: Verifies that saving drafts with unknown targets or target IDs belonging to other projects are rejected with HTTP 404.

### E2. Local Quality Gates (Ruff & Security)
- **Ruff Linter**: Checked via `python -m ruff check backend` -> **PASS** (0 errors, no new ignores).
- **Security Scanner**: Checked via `python tests/check_security.py` -> **PASS** (0 un-baselined violations).
- **Database Migrations Check**: Checked via `alembic heads` -> **PASS** (exactly one active head: `db5977424e7b (head)`).
- **X-User-Id Restriction**: Verified that no new tests use the legacy header; they use the database-backed cookie authentication via `login_user_in_test`.
