# ADR 0026 - Authentication & Identity Boundary Hardening

## Status

Accepted

## Context

The Valora codebase currently uses an insecure `X-User-Id` header to identify users in the backend APIs without signature verification or true authentication. This leaves the system open to identity spoofing and cross-tenant data access. 

To resolve this root cause, Sprint S12-R-002 requires hardening the authentication boundaries. This ADR extends and supersedes the incomplete session design in **ADR 0003**.

## Decision

We implement a hardened, database-backed opaque token session management and CSRF defense:

### 1. Token Specifications
- **Opaque Access Token**:
  - Generated using cryptographically secure pseudorandom numbers (CSPRNG, minimum 256 bits of entropy).
  - TTL (Time-To-Live): 15 minutes.
  - Stored on the server/DB as a SHA-256 hash; the raw token is never written to logs or database persistence.
  - Transported in cookie: `__Host-Access-Token` with flags `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/`, and no `Domain` attribute.
- **Opaque Refresh Token**:
  - Generated using CSPRNG (minimum 256 bits of entropy).
  - TTL: 30 days absolute expiry.
  - One-time use: Rotated on every token refresh request.
  - Stored in the database as a SHA-256 hash.
  - Lineage tracking: Links each record to a `token_family_id` and tracks `parent_token_id` and `replaced_by_token_id`.
  - Concurrency safety: Token refresh operations use database transactions with row-level locks or compare-and-swap to prevent race conditions.
  - Reuse detection: If a rotated/already-consumed refresh token is reuse-attempted, the entire `UserSession` and associated token family are immediately marked as `revoked`.

### 2. CSRF Mitigation: Synchronizer Token Pattern
- A CSRF token is cryptographically generated and tied directly to the `UserSession`.
- Stored as a hash (SHA-256) in the database under `UserSession`.
- Transported to the frontend via a separate non-HttpOnly cookie or returning in login response, and sent back by the client in the `X-CSRF-Token` header.
- The server validates this token using constant-time comparison (`hmac.compare_digest`) on all state-changing methods (`POST`, `PUT`, `PATCH`, `DELETE`), token refresh, and logout.
- Defense-in-depth: Verify `Origin` and `Referer` headers, and enforce Fetch Metadata checks (`Sec-Fetch-Site: same-origin`).

### 3. Cookie & Deployment Policy
- Production requires HTTPS only. Secure cookies are always enforced.
- Cross-Origin Resource Sharing (CORS) must use an exact explicit allowlist; wildcards (`*`) are prohibited. `allow_credentials=true` must be set.
- Cookie clearing uses identical cookie attributes (`Path=/`, `SameSite=Strict`, `Secure`, `HttpOnly`, without `Domain`).

### 4. Database Schema
We introduce two database entities: `UserSession` and `RefreshTokenRecord` in the database schema to track sessions and token rotation lineage.

## Consequences

- Insecure `X-User-Id` spoofing is fully blocked.
- Session hijacking and CSRF vulnerabilities are mitigated via secure cookie flags and synchronizer token patterns.
- Token refresh races are handled safely via row locks.
