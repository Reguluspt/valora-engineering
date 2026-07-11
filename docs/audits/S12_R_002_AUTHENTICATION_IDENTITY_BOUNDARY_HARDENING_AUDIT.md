# S12-R-002 — Authentication Identity Boundary Hardening Audit

## A. Title and Final Status
- **Title**: S12-R-002 — Authentication Identity Boundary Hardening
- **Final Status**: **PASS**

## B. Root Cause
The production backend read user identities directly from the unauthenticated `X-User-Id` header without verification or secure sessions, leaving the system vulnerable to user impersonation and cross-tenant data leaks.

## C. ADR/Design Authority
This sprint implements [0026-authentication-identity-boundary-hardening-proposal.md](docs/adr/0026-authentication-identity-boundary-hardening-proposal.md) which was revised and moved to `Accepted` status. It defines database-backed opaque sessions, token rotation, and synchronizer CSRF tokens.

## D. Authentication Architecture
The architecture utilizes opaque secure cookies (`__Host-Access-Token` and `__Host-Refresh-Token` in production) instead of JWTs or client-side storage, ensuring maximum security against XSS.

## E. Credential Transport
Credentials are transported using:
- Secure HttpOnly access cookie (15-minute lifespan).
- Secure HttpOnly rotating refresh cookie (30-day absolute lifespan).
- Synchronizer CSRF cookie (30-day lifespan).

## F. Identity Derivation
The current user is derived server-side in `get_current_user` by looking up the database session record corresponding to the access token's SHA-256 hash.

## H. User/Org Status Behavior
If a user or organization status is not `ACTIVE`, requests are immediately rejected (fail-closed check).

## I. Authorization Behavior
Missing credentials return 401, while authenticated requests lacking permissions return 403. Both return unified Vietnamese error payloads compliant with the friendly error registry.

## K. Refresh Rotation/Reuse
Refresh tokens are rotated on use. If a reused refresh token is detected, the entire session family is revoked. Concurrency is handled using PostgreSQL row-level locks (`with_for_update`).

## L. Frontend Integration
The client API at [client.ts](frontend/src/api/client.ts) is configured to send cookies automatically (`credentials: "include"`) and includes synchronizer CSRF headers. It retries 401 requests exactly once using a deduplicated refresh call.

## N. Files Changed
- [0026-authentication-identity-boundary-hardening-proposal.md](docs/adr/0026-authentication-identity-boundary-hardening-proposal.md)
- [models.py](backend/app/modules/project_master_data/models.py)
- [rbac.py](backend/app/core/rbac.py)
- [main.py](backend/app/main.py)
- [auth.py](backend/app/api/auth.py)
- [client.ts](frontend/src/api/client.ts)
- [check_security.py](backend/tests/check_security.py)
- [conftest.py](backend/tests/conftest.py)
- [test_auth_endpoints.py](backend/tests/test_auth_endpoints.py)
- [test_auth_rbac_foundation.py](backend/tests/test_auth_rbac_foundation.py)

## O. Migration Impact
Introduced table creation migration script at `backend/alembic/versions/2f938d127521_create_user_sessions_and_refresh_tokens.py`.

## P. Tests Added
- `test_login_flow_success_and_failure`
- `test_me_endpoint_requires_auth`
- `test_refresh_token_rotation_and_reuse_detection`
- `test_csrf_missing_fails`
- `test_inactive_user_fail_closed`

## Q. Commands/Results
- `wc -l docs/remediation/S12_R_PRE_VALIDATION_REMEDIATION_SLICE.md`: 561
- `git hash-object docs/remediation/S12_R_PRE_VALIDATION_REMEDIATION_SLICE.md`: `d4b1408b1c30b27b203203498a4e318b467cade2`
- `sha256sum docs/remediation/S12_R_PRE_VALIDATION_REMEDIATION_SLICE.md`: `962039d1f1c9150bbfa7bc7c509b04599e2ce709a5f6857b59ece099deb6c96c`

## R. CI SHA/Run
- Codebase Commit SHA: `fe48cc79b39dd5cf715f7668fcb4e40c2a24bfca`
- Draft PR: PR #2

## V. Final Verdict
**PASS**
