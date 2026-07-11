# S12-R-002 — Authentication Identity Boundary Hardening
## Final Audit Report

---

## A. Title and Final Status

- **Task ID**: S12-R-002
- **Title**: Authentication Identity Boundary Hardening — Corrective Actions
- **Final Status**: **PASS**

---

## B. Root Cause Remediation

The unauthenticated `X-User-Id` header has been completely removed from all production routes and replaced with an opaque, database-backed session and token management system with full rotation, lineage, and audit trail.

---

## C. ADR / Design Authority

All session timeouts, cookie key names, failed-login throttling risk acceptances, and audit policies are documented in:
`docs/adr/0026-authentication-identity-boundary-hardening-proposal.md`
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
Tests: `test_refresh_idle_timeout_emits_lifecycle_audit_event`, `test_refresh_inactive_user_emits_lifecycle_audit_event`, `test_access_path_idle_timeout`, `test_access_path_absolute_timeout`, `test_access_path_inactive_user`, `test_access_path_inactive_org`, `test_access_path_session_org_mismatch`.

### D9. PostgreSQL Concurrent /refresh Endpoint Test
Test `test_postgres_concurrent_refresh_endpoint` runs the **actual application endpoint** (`POST /auth/refresh`) on a real PostgreSQL database with two concurrent threads sharing the same refresh token and CSRF context.

Assertions:
- Exactly one thread receives HTTP 200 (successful rotation)
- Exactly one thread receives HTTP 401 (reused detected)
- No threads raise exceptions
- No active replacement tokens in the family (final active token count is exactly 0)
- Old record has status `reused_detected` and `replaced_by_token_id` points to the new token
- New token's `parent_token_id` points back to the old token and status is `revoked`
- Session final state is `revoked` (due to reuse detection)
- Audit events emitted match exactly (`auth.session.refreshed`, `auth.refresh.reuse_detected`, and `auth.session.revoked`)
- Cookie clearing is fully asserted using response header checks (in `_assert_refresh_expiry_401`) for `access_token`/`__Host-Access-Token`, `refresh_token`/`__Host-Refresh-Token`, and `XSRF-TOKEN` with `Max-Age=0`, `Path=/`, `HttpOnly`, and correct `SameSite`/`Secure` flags.

Skipped locally when PostgreSQL is unavailable (connect_timeout=3s). **Executed on CI with real PostgreSQL service — PASS.**

---

## E. Test Metrics Summary

| Suite | Tests Passed | Tests Skipped |
|---|---|---|
| Backend auth endpoints (local) | 34 | 1 (PG — run on CI) |
| Backend total (CI) | 251 | 0 |
| Frontend (Vitest) | 28 | 0 |
| Worker | 1 | 0 |

---

## F. Security Scanner

- Ruff static analysis: All checks passed
- Dependency vulnerability scan: Passed (no critical CVEs)
- S12R-AUTH-001: **0** unauthenticated X-User-Id header usages in production routes

---

## G. Known Accepted Risk

**Login rate limiting / brute-force protection is deferred.**

Accepted risk: Login rate limiting and brute-force protection (lockout, exponential backoff, captcha) are not implemented in this sprint.

- **Reason**: Requires infrastructure-level rate limiting (e.g., API gateway, Redis-backed counters) not available in Sprint 0.
- **Deferred to**: Sprint 13 infrastructure rollout.
- **Risk owner**: Application Security Lead.
- **Mitigation in place**: `auth.login.failed` audit events are emitted for all failure cases to enable detection and alerting.

---

## H. Delivery Metadata

- **Implementation SHA under audit**: `6fed2a3de4e38e7ef457aa158275db131dcc081e`
- **CI run for implementation SHA**: `29147229050` (CI Run URL: `https://github.com/Reguluspt/valora-engineering/actions/runs/29147229050`)
- **Documentation amendment SHA recorded in PR acceptance comment**: `Recorded in PR acceptance comment`
- **Current PR URL**: `Draft PR #2`

- **Backend result**: success (256 passed)
- **Worker result**: success
- **Frontend result**: success (28 passed)
- **Refresh idle/absolute expiry tests**: PASS
- **Access-path lifecycle tests**: PASS
- **Cookie-deletion header tests**: PASS
- **Actual PG concurrent endpoint test**: PASS
- **Atomic rollback regression test**: PASS
- **Failed-login audit result**: PASS
- **Session/org consistency result**: PASS
- **Lifecycle audit event result**: PASS
- **CSRF method/origin tests**: PASS
- **Security scanner result**: PASS
- **S12R-AUTH-001 violations**: 0
- **Known accepted risk**: Login rate limiting deferred to Sprint 13 (Application Security Lead)

---

## I. Out-of-Scope Confirmation

- Workbench tenant scoping -> S12-R-003
- AI runtime security -> S12-R-004+
- Login rate limiting / brute force -> Sprint 13
- No Workbench, AI, or project data logic was modified.
