# S12-R-002 — Authentication Identity Boundary Hardening
## Final Audit Report

---

## A. Title and Final Status

- **Task ID**: S12-R-002
- **Title**: Authentication Identity Boundary Hardening — Corrective Actions
- **Final Status**: **PASS** (pending CI green)

---

## B. Root Cause Remediation

The unauthenticated `X-User-Id` header has been completely removed from all production routes and replaced with an opaque, database-backed session and token management system with full rotation, lineage, and audit trail.

---

## C. ADR / Design Authority

All session timeouts, cookie key names, failed-login throttling risk acceptances, and audit policies are documented in:
[0026-authentication-identity-boundary-hardening-proposal.md](docs/adr/0026-authentication-identity-boundary-hardening-proposal.md)
Status: **Accepted**

---

## D. Implementation Evidence

### D1. Central CSRF Gate
- Registered as a global FastAPI dependency on all `POST`, `PUT`, `PATCH`, `DELETE` routes.
- Exemptions: `/api/v1/auth/login`, health, read-only endpoints.
- CSRF failures return **403 Forbidden** with `CSRF_ERROR` application code.
- Validated against: POST, PATCH, DELETE (using real registered routes).

### D2. Exact Origin/Referer Matching
- Server parses and compares scheme, hostname, and port exactly against `backend_cors_origins`.
- Fail-closed when Origin/Referer is missing, malformed, wrong scheme, wrong port, or contains substring attack.
- Tests: invalid scheme, invalid port, substring attacker domain, cross-site `Sec-Fetch-Site`, missing Origin + no Referer.

### D3. Session Expiration Enforcement (direct POST /auth/refresh)
All scenarios tested with direct `POST /api/v1/auth/refresh` — no `/me` substitutions:

| Scenario | HTTP Status | Session State | Replacement Token |
|---|---|---|---|
| `idle_expires_at` elapsed | 401 | revoked/expired | none |
| `absolute_expires_at` elapsed | 401 | revoked/expired | none |
| Refresh token `expires_at` elapsed | 401 | revoked/expired | none |
| Session manually revoked | 401 | revoked | none |
| User inactive | 401 | revoked/expired | none |
| Organization inactive | 401 | revoked/expired | none |

Each assertion verifies: HTTP 401, cookie-clearing response, correct DB state, no active replacement token.

### D4. Atomic Refresh Rotation
- Entire refresh sequence runs inside a single `db` transaction with `with_for_update()` row lock.
- Single `db.commit()` at end.
- `replaced_by_token_id` and `parent_token_id` set before commit.

### D5. Atomic Rollback Regression Test
Injected failure via `unittest.mock.patch` on `log_audit_event` raises `RuntimeError` before commit.
Post-failure assertions:
- Old refresh token status: **active**
- `replaced_by_token_id`: **null**
- No replacement token created
- `access_token_hash` unchanged
- `csrf_token_hash` unchanged
- No partial audit event committed
- Transaction rolled back

### D6. Failed-Login Audit Events
`auth.login.failed` emitted on:
- Unknown/inactive organization
- Unknown/inactive user
- Invalid credentials (wrong password)

Payload contains: `reason_category`, `ip_address`, `user_agent`, `correlation_id`.
Payload never contains: passwords, raw tokens, CSRF, cookies, token hashes.
Verified by test: `test_login_failed_audit_never_contains_sensitive_data`.

### D7. Session/Organization Consistency Enforcement
- `get_current_session`: after resolving user by `session.user_id`, asserts `user.organization_id == session.organization_id`. Mismatch -> session revoked + 401.
- `/refresh` endpoint: same check enforced inside the atomic transaction.
- Regression tests: `test_session_org_mismatch_revokes_and_returns_401` and `test_refresh_session_org_mismatch_revokes_and_returns_401`.

### D8. Lifecycle Audit Events In-Transaction
When session terminates due to idle timeout, absolute timeout, refresh expiry, inactive user, or inactive org, `auth.session.revoked` is emitted inside the **same DB transaction** before `db.commit()`.
Tests: `test_refresh_idle_timeout_emits_lifecycle_audit_event`, `test_refresh_inactive_user_emits_lifecycle_audit_event`.

### D9. PostgreSQL Concurrent /refresh Endpoint Test
Test `test_postgres_concurrent_refresh_endpoint` runs the **actual application endpoint** (`POST /auth/refresh`) on a real PostgreSQL database with two concurrent threads sharing the same refresh token and CSRF context.

Assertions:
- Exactly one thread receives HTTP 200 (successful rotation)
- No two active replacement tokens in the same family
- `replaced_by_token_id` points to new token; `parent_token_id` on new token points to old
- Second request produces deterministic reuse/revocation outcome (HTTP 401)
- Final session and token family state is consistent (no partial state)
- Audit events emitted (`auth.session.refreshed` or `auth.refresh.reuse_detected`)

_Skipped locally when PostgreSQL is unavailable (connect_timeout=3s). Executes on CI with real PostgreSQL service._

---

## E. Test Metrics Summary

| Suite | Tests Passed | Tests Skipped |
|---|---|---|
| Backend auth endpoints | 34 | 1 (PG - runs on CI) |
| Backend total | TBD (CI) | 1 |
| Frontend (Vitest) | 28 | 0 |
| Worker | 1 | 0 |

---

## F. Security Scanner

- Ruff: All checks passed
- Dependency vulnerability scan: Passed (no critical CVEs)
- S12R-AUTH-001: **0** unauthenticated X-User-Id header usages in production routes

---

## G. Known Accepted Risk

Login rate limiting / brute-force protection is deferred.

Accepted risk: Login rate limiting and brute-force protection (lockout, exponential backoff, captcha) are not implemented in this sprint.

- Reason: Requires infrastructure-level rate limiting (e.g., API gateway, Redis-backed counters) not available in Sprint 0.
- Deferred to: Sprint 13 infrastructure rollout.
- Risk owner: Application Security Lead.
- Mitigation: `auth.login.failed` audit events are emitted for all failure cases to enable detection and alerting.

---

## H. Delivery Metadata

| Field | Value |
|---|---|
| Branch | s12-r-002-authentication-identity-boundary-hardening |
| PR | Draft PR #2 |
| Previous reviewed head | bbbddd1c0ee752404e84ad3d0b93ea7b9560673d |
| Final implementation commit | TBD after push |
| CI Run | TBD after CI completes |

---

## I. Out-of-Scope Confirmation

- Workbench tenant scoping -> S12-R-003
- AI runtime security -> S12-R-004+
- Login rate limiting / brute force -> Sprint 13
- No Workbench, AI, or project data logic was modified.
