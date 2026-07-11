# ADR 0026 - Authentication & Identity Boundary Hardening

## Status

Accepted

## Context

The Valora codebase currently uses an insecure `X-User-Id` header to identify users in the backend APIs without signature verification or true authentication. This leaves the system open to identity spoofing and cross-tenant data access. 

To resolve this root cause, Sprint S12-R-002 requires hardening the authentication boundaries. This ADR extends and supersedes the incomplete session design in **ADR 0003**.

## Decision

We implement a hardened, database-backed opaque token session management and CSRF defense:

### 1. Token & Session Lifespans
- **Opaque Access Token**:
  - Generated using cryptographically secure pseudorandom numbers (CSPRNG, minimum 256 bits of entropy).
  - TTL (Time-To-Live): 15 minutes.
  - Cookie key: `__Host-Access-Token` in production, `access_token` in local development.
- **Opaque Refresh Token**:
  - Generated using CSPRNG (minimum 256 bits of entropy).
  - TTL: 30 days absolute expiry.
  - Cookie key: `__Host-Refresh-Token` in production, `refresh_token` in local development.
- **Session Timeouts**:
  - **Idle Session Timeout**: 30 minutes. Extends on activity (sliding window).
  - **Absolute Session Timeout**: 7 days. Forces re-authentication regardless of activity.
  - If either timeout is reached, the session is marked as `expired` and revoked.

### 2. CSRF Mitigation: Synchronizer Token Pattern
- A CSRF token is cryptographically generated and tied directly to the `UserSession`.
- Stored as a hash (SHA-256) in the database under `UserSession`.
- Transported to the frontend via a separate non-HttpOnly cookie `XSRF-TOKEN`, and sent back by the client in the `X-CSRF-Token` header.
- Enforced centrally at the backend for all unsafe request methods (`POST`, `PUT`, `PATCH`, `DELETE`) except for explicitly exempted routes (e.g. `/api/v1/auth/login`, health checks).
- The server validates this token using constant-time comparison (`hmac.compare_digest`) on all state-changing methods (`POST`, `PUT`, `PATCH`, `DELETE`), token refresh, and logout.
- **Origin/Referer Policy**: Verifies that the request `Origin` (or fallback `Referer` if `Origin` is absent) matches the configured allowed CORS origins, comparing scheme, hostname, and port exactly. Substring matching is prohibited.
- **Fetch Metadata**: Enforces checks (`Sec-Fetch-Site: same-origin`) for browsers supporting it.

### 3. Cookie & Deployment Policy
- Production requires HTTPS only. Secure cookies are always enforced.
- Cross-Origin Resource Sharing (CORS) must use an exact explicit allowlist; wildcards (`*`) are prohibited. `allow_credentials=true` must be set.
- Cookie clearing uses identical cookie attributes (`Path=/`, `SameSite=Strict`, `Secure`, `HttpOnly`, without `Domain`).
- **Refresh Failure Cookie Clearing**: If a refresh token request fails (e.g. expired or suspicious reuse), the server returns a response that immediately instructs the browser to clear the auth cookies.

### 4. Rate Limiting & Failed Login Throttling
- **Security Risk Acceptance**: Login rate limiting and brute force protection are deferred to the infrastructure layer (e.g. Nginx rate limit, WAF rules).
  - *Risk Owner*: Application Security Lead.
  - *Remediation target*: Implemented in Sprint 13 environment rollout.
- **Failed Login Tracking**: Failed login attempts are logged in the security audits trail to track potential brute force attacks.

### 5. Security Audit Log Event Policy
- Log security audit events using the core audit service for the following auth lifecycles:
  - `auth.session.created`: When a user successfully logs in.
  - `auth.session.refreshed`: When a session is successfully rotated.
  - `auth.session.revoked`: When a user logs out or a session is ended.
  - `auth.refresh.reuse_detected`: Critical event logged when refresh token replay is detected.
- Raw passwords, raw access/refresh tokens, and CSRF token values are strictly redacted from audit payloads.

### 6. Database Schema
We introduce two database entities: `UserSession` and `RefreshTokenRecord` in the database schema to track sessions and token rotation lineage.
- **Self-referencing Foreign Key**: `RefreshTokenRecord` contains `replaced_by_token_id` referencing itself to track rotation lineages.
- **Index Optimization**: Indexes are added on `user_session_id`, `token_family_id`, `status`, and `expires_at`.
