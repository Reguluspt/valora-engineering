# S12-R-003 — Workbench Project & Session Tenant Scoping
## Final Audit Report

---

## A. Title and Final Status

- **Task ID**: S12-R-003
- **Title**: Workbench Project & Session Tenant Scoping
- **Final Status**: **PASS — CODE-BEARING HEAD VALIDATED — READY FOR REVIEW AFTER DOCUMENTATION-ONLY CI**

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
- `docs/adr/0027-workbench-session-cardinality-and-state-scope.md` (Created in this sprint)

---

## D. Implementation Details

### D1. Centralized Session Resolver
We implemented `require_owned_workbench_session` in `backend/app/modules/workflow_workbench/resolve_owned_session.py`:
- Validates that `WorkbenchSession.id == session_id`
- Validates user ownership: `session.user_id == current_user.id`
- Validates tenant boundary: `session.project.organization_id == current_user.organization_id`
- Optionally validates active state (`require_active=True`, default is True) and project context (`expected_project_id`)
- Runs the entire lookup scoping in a single SQL query:
  ```python
  query = (
      db.query(WorkbenchSession)
      .join(Project, Project.id == WorkbenchSession.project_id)
      .filter(
          WorkbenchSession.id == session_id,
          WorkbenchSession.user_id == current_user.id,
          Project.organization_id == current_user.organization_id,
      )
  )
  ```
- Mismatches (or inactive sessions when `require_active=True`) result in a safe `404 Not Found` to prevent ID harvesting/leakage.

### D2. Database Migration & Hardening
Created a hardened database unique index via Alembic in `backend/alembic/versions/db5977424e7b_create_active_session_unique_index.py`:
- `uq_active_session_per_user_project` on `workbench_sessions` for `(user_id, project_id)` where `status = 'active'`.
- Hardened with duplicate validation before creation:
  ```python
  res = bind.execute(sa.text(
      "SELECT user_id, project_id, COUNT(*) FROM workbench_sessions "
      "WHERE status = 'active' "
      "GROUP BY user_id, project_id "
      "HAVING COUNT(*) > 1"
  )).fetchall()
  ```
- Any duplicates halt migration with clear instructions matching the ADR runbook.

### D3. Target & Selection Isolation
- Implemented `resolve_workbench_target` validating that target IDs are valid UUIDs, are of type `project_asset_line`, and belong to the correct project.
- In `save_selection`, validated that the target type is `"project_asset_line"` (explicit allowlist). Each target ID is verified via the resolver. Failures roll back the transaction.

### D4. Concurrent Session Creation
- Refactored `create_session` to query existing active sessions.
- In concurrent races, attempts are made to insert within `db.begin_nested()` (savepoint).
- Unique constraint violations trigger a savepoint rollback, query the winning session, set response status to `200 OK`, and return the session cleanly without escaping `IntegrityError`s.

### D5. Atomic State Mutation
- State mutations (heartbeat, selection, layout, checkpoints, inline edits, undo/redo) and their respective `UserActionLog` logs are written and committed together in a single atomic transaction block. Any failures trigger an immediate rollback.

---

## E. State Endpoint Matrix

The active session boundary and permissions are enforced across all workbench actions as follows:

| Endpoint Group | Require Active Session | Owner Check | Same-Tenant User | Cross-Tenant User | Closed Session Response |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Open Session (POST)** | N/A | Opens/Resumes | opens/resumes own | opens/resumes own | N/A |
| **Get Session (GET)** | Yes | 200 OK | 404 Not Found | 404 Not Found | 404 Not Found |
| **Heartbeat (POST)** | Yes | 200 OK | 404 Not Found | 404 Not Found | 404 Not Found |
| **Close Session (POST)**| No (Allows False) | 200 OK | 404 Not Found | 404 Not Found | 200 OK (Idempotent) |
| **Layout (POST)** | Yes | 200 OK | 404 Not Found | 404 Not Found | 404 Not Found |
| **Grid View (GET/POST)**| Yes | 200 OK | 404 Not Found | 404 Not Found | 404 Not Found |
| **Selection (GET/POST)**| Yes | 200 OK | 404 Not Found | 404 Not Found | 404 Not Found |
| **Inline Edit (GET/POST)**| Yes | 200 OK | 404 Not Found | 404 Not Found | 404 Not Found |
| **Checkpoint (POST)** | Yes | 200 OK | 404 Not Found | 404 Not Found | 404 Not Found |
| **Undo/Redo (POST)** | Yes | 200 OK | 404 Not Found | 404 Not Found | 404 Not Found |
| **Panel State (GET/POST)**| Yes | 200 OK | 404 Not Found | 404 Not Found | 404 Not Found |
| **Notifications (GET)** | Yes | 200 OK | 404 Not Found | 404 Not Found | 404 Not Found |

---

## F. Verification Evidence

### F0. Full-Suite Local Run

```
Command : python -m pytest backend/tests -rs
Result  : 265 passed, 3 skipped, 0 failed  (26.98s)
```

**Skipped tests (local — no PostgreSQL configured):**

| # | File | Line | Reason |
|---|------|------|--------|
| 1 | `test_auth_endpoints.py` | 737 | `PostgreSQL not available. Skipping integration test.` |
| 2 | `test_workbench_api.py` | 696 | `PostgreSQL not configured (TEST_DATABASE_URL/DATABASE_URL absent or not postgres). Skipping concurrent integration test — awaiting CI with PostgreSQL service.` |
| 3 | `test_workbench_api.py` | 980 | `PostgreSQL not configured (TEST_DATABASE_URL/DATABASE_URL absent or not postgres). Skipping PostgreSQL unexpected-error rollback test — awaiting CI with PostgreSQL service.` |

All three skipped tests are PostgreSQL-gated: they `pytest.fail` (not skip) when `CI=true` and the database URL is absent.

---

### F1. Added Verification Tests

The following test cases are in `backend/tests/test_workbench_api.py`:

1. **`test_workbench_tenant_and_user_isolation`**: Verifies that a user from Org A cannot create or access a session in Org B, and users cannot access other users' sessions.

2. **`test_active_session_policy_resume`**: Verifies that multiple creation requests for the same project resume the same session (returning HTTP 200), and closing a session blocks subsequent heartbeats.

3. **`test_explicit_target_validation`**: Verifies that saving drafts with unknown targets or target IDs belonging to other projects are rejected with HTTP 404.

4. **`test_permission_revocation`**: Verifies that revoking the role/permission makes subsequent heartbeat, selection, and panel-state requests fail with HTTP 403, with zero state mutations or action logs written.

5. **`test_state_endpoints_matrix`**: Asserts the exact behavior described in the **State Endpoint Matrix** across all endpoints.

6. **`test_selection_validation_isolation_and_rollback`**: Verifies that pre-validation logic prevents mutation when the target list contains cross-project IDs. This is **pre-validation evidence**, not transaction rollback evidence — the selection is rejected before any DB write occurs.

7. **`test_postgres_concurrent_session_create`** *(PostgreSQL-gated)*: A multi-threaded integration test. In CI (`CI=true`), `pytest.fail` if `TEST_DATABASE_URL` is absent or the migration index `uq_active_session_per_user_project` is missing. Locally skips with a clear reason. Asserts: exactly one HTTP 201 and one HTTP 200 from concurrent threads, same session ID returned, exactly one active session row, one audit event, one `UserActionLog` in DB.
   - **Local result**: SKIPPED — PostgreSQL not configured (awaiting CI).

8. **`test_create_session_unexpected_error_rolls_back`** *(SQLite, partial evidence)*: Monkeypatches `log_audit_event` to raise `RuntimeError` during session creation. Asserts: exception propagates (no HTTP 200/201 returned), no `AuditEvent` or `UserActionLog` rows are committed. **Note**: SQLite `StaticPool` auto-commits on `SAVEPOINT RELEASE`, so the `WorkbenchSession` row-count assertion is intentionally omitted from this test. Full DB-level rollback evidence (0 ACTIVE session rows) is provided exclusively by `test_postgres_create_session_unexpected_error_rolls_back` on PostgreSQL.

9. **`test_postgres_create_session_unexpected_error_rolls_back`** *(PostgreSQL-gated, authoritative rollback evidence)*: Full PostgreSQL-backed evidence. Patches `log_audit_event` to raise `RuntimeError` after `WorkbenchSession` has been flushed (savepoint released). Verifies that `db.rollback()` correctly reverts the entire transaction under PostgreSQL's MVCC — leaving 0 ACTIVE `WorkbenchSession`, 0 `workbench.session.started` `AuditEvent`, and 0 `session_start` `UserActionLog` for the test user+project. CI fail-fast enforced.
   - **Local result**: SKIPPED — PostgreSQL not configured (awaiting CI).

10. **`test_heartbeat_atomic_rollback`**: Simulates heartbeat error by monkeypatching `log_action` to raise `RuntimeError`. Asserts that `row_version` and `last_active_at` remain unmodified and no `UserActionLog` is written — confirming atomic rollback on heartbeat failure.

11. **`test_selection_atomic_rollback`**: Monkeypatches `log_action` to raise `RuntimeError` during a selection update. Asserts that the selection state cache and `WorkbenchSelection` DB record remain unchanged — confirming atomic rollback on selection failure. This is the **transaction rollback evidence** for the selection endpoint.

12. **`test_closed_session_matrix`**: Matrix validation across all 15 endpoints asserting safe HTTP 404 when the session is closed. Each assertion is followed by `assert_zero_mutation()` which verifies that no new `AuditEvent` or `UserActionLog` rows were written. Also asserts the closed status in the DB.

---

### F2. Local Quality Gates

| Check | Command | Result |
|-------|---------|--------|
| Ruff Linter | `python -m ruff check backend` | **PASS** — 0 errors, no new ignores |
| Security Scanner | `python tests/check_security.py` | **PASS** — 0 un-baselined violations |
| Alembic Migration | `alembic heads` | **PASS** — single head: `db5977424e7b` |
| X-User-Id Restriction | Manual review | **PASS** — all new tests use `login_user_in_test` (cookie-backed auth) |

---

### F3. CI Evidence Corrections Applied

- **`ci.yml` `Run backend tests` step**: Added `env` block with `CI=true`, `VALORA_ENV=test`, `POSTGRES_HOST/PORT/DB/USER/PASSWORD`, and `TEST_DATABASE_URL` (`postgresql+psycopg://valora:valora_local_password@localhost:5432/valora`). Changed command from `pytest` to `pytest -rs`.
- **Alembic subprocess removed** from `test_postgres_concurrent_session_create`: CI is responsible for running `alembic upgrade head` in the dedicated migration step before tests run. Test pre-checks for the index `uq_active_session_per_user_project` and `pytest.fail`s in CI if absent.
- **`save_selection` error message**: Changed from type-echoing `"Loại đối tượng {type} không hợp lệ."` to generic `"Loại đối tượng được chọn không được hỗ trợ."` to prevent user-input reflection.
- **New test added**: `test_postgres_create_session_unexpected_error_rolls_back` — authoritative PostgreSQL rollback evidence, replacing the partial SQLite-only assertion.

---

### F4. Validated CI / Git Delivery Evidence

| Item | Value |
|------|-------|
| Validated code-bearing head SHA | `5a05988e83bedca1e58100971fcf243c490f448e` |
| PR | `#3` |
| Validated CI run ID | `29157970074` |
| Backend pytest | **PASS — 268 passed, 0 skipped, 14 warnings in 21.87s** |
| PostgreSQL auth integration | **PASS** |
| PostgreSQL concurrent session creation | **PASS** |
| PostgreSQL unexpected-error rollback | **PASS** |
| Ruff | **PASS** |
| Alembic migration smoke test | **PASS** |
| Single migration head | **PASS — db5977424e7b** |
| Python dependency vulnerability scan | **PASS** |
| Security policy and secret scan | **PASS** |
| Worker CI | **PASS** |
| Frontend CI | **PASS** |

The SHA above is the final code-bearing implementation head validated by CI.
Any subsequent commit for this audit evidence must be documentation-only and
must pass the repository CI before the pull request is marked ready for review.

