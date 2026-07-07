# S1-PR-009: Auth / RBAC Foundation Audit

## Files Changed
- `backend/pyproject.toml` (Modified dependencies)
- `backend/app/core/security.py` (New file with password hashing)
- `backend/app/core/rbac.py` (New file with RBAC resolution and dependencies)
- `backend/tests/test_auth_rbac_foundation.py` (New file with backend tests)

## Design Files Read
- `13_SECURITY/02_AUTHENTICATION.md`
- `13_SECURITY/03_AUTHORIZATION_RBAC.md`
- `09_DATA_MODEL/02_MASTER_DATA_MODEL.md`
- `docs/adr/0003-auth-session-password-hashing-strategy.md`
- `docs/adr/0004-rbac-enforcement-and-permission-snapshot.md`

## Dependencies Added
- `argon2-cffi` (version `25.1.0` / configured `>=23.1.0` in `pyproject.toml`): Added for secure, modern password hashing utilizing the Argon2id algorithm, compliant with ADR 0003.

## Auth Foundation Implemented
- Created `hash_password(password)` and `verify_password(password, hashed_password)` utilities using `argon2.PasswordHasher` (Argon2id).
- Verified that plaintext passwords are never stored and incorrect passwords fail verification.

## RBAC Helper Behavior
- Created `derive_effective_permissions(user, db)` to resolve permissions from active `UserRole` mappings.
- Rejects permissions if:
  - User status is not active.
  - Organization status is not active.
  - Role mapping is marked inactive (`is_active = False`) or revoked (`revoked_at` is set).
- Enforces deny-by-default behavior: returns empty permission set if no matching active roles exist.
- Created `require_permission(permission_code)` FastAPI dependency shape using a mockable header `X-User-Id` placeholder `get_current_user` dependency.

## Tests/Checks Run
- Executed `python -m pytest` in `backend` directory.
- All 28 tests passed successfully (including 7 new security and RBAC foundation tests).

## Scope Compliance
- No login/logout endpoint was implemented.
- No password reset endpoint was implemented.
- No session cookies or JWT mechanism was implemented.
- No frontend changes.
- No database model modifications or migrations were created.
- No business CRUD logic or routers were added.

## Forbidden API/Business/Future-Sprint Scan
- Checked file changes using `git status` and manual code inspection.
- Confirmed zero future-sprint logic leaks.

## Missing or Recommended Fixes
- None at this stage. The foundation is complete and correct.

## Final Result
- **Result:** PASS
- **Recommendation:** Ready for next PR (Sprint 1 APIs implementation).
