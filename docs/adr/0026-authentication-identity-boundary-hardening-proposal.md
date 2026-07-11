# ADR 0026 - Authentication & Identity Boundary Hardening Proposal

## Status

Proposed (Pending Approval)

## Context

The Valora codebase currently uses an insecure `X-User-Id` header to identify users in the backend APIs without signature verification or true authentication. This leaves the system open to identity spoofing and cross-tenant data access. 

To resolve this root cause, Sprint S12-R-002 requires hardening the authentication boundaries. According to the architecture guidelines:
1. `ADR 0003` specifies a login identity of `organization_slug + email` and Argon2id password hashing, recommending secure, HTTP-only cookie-backed sessions.
2. The Security Hardening Data Model (`13_SECURITY_HARDENING_MODEL.md`) defines schema structures for `UserSession` and `RefreshTokenRecord`.

However, the existing ADR package lacks concrete, finalized technical details regarding the following critical design aspects:
- Token format and signing keys (JWT symmetric vs. asymmetric).
- Credential transport (Cookie-based vs. Bearer Token).
- CSRF protection mechanisms for cookie-based transport.
- Token storage rules for browser clients.
- Refresh token reuse detection flow.

This proposal outlines the alternatives and trade-offs to establish an approved security architecture before implementation proceeds.

## Proposed Decisions & Alternatives Analysis

### 1. Token Transport Mechanism

#### Alternative A: Secure, HTTP-Only Cookie-Backed Sessions (Recommended)
- **Mechanism**: The backend issues an access token and a refresh token inside secure, HTTP-only cookies (`__Host-Access-Token` and `__Host-Refresh-Token`).
- **Security Posture**: Highly resistant to Cross-Site Scripting (XSS) because JavaScript cannot read HTTP-only cookies.
- **Trade-offs**: Requires protection against Cross-Site Request Forgery (CSRF). Requires configuring cookie settings (`SameSite=Strict`, `Secure`, `HttpOnly`, `Path=/`).

#### Alternative B: Authorization Bearer Token
- **Mechanism**: The backend returns access and refresh tokens in the JSON response payload. The frontend stores them in `localStorage` or memory, appending `Authorization: Bearer <access_token>` to request headers.
- **Security Posture**: Immune to CSRF by default since browser doesn't automatically attach headers. Highly vulnerable to token theft via XSS if stored in `localStorage`/`sessionStorage`.
- **Trade-offs**: Simpler cross-domain configuration, but higher vulnerability to token theft.

**Decision**: **Alternative A (Cookie-Backed Sessions)** is proposed to maximize XSS protection.

---

### 2. Access Token Format & Signature Verification

- **Mechanism**: JSON Web Tokens (JWT) containing standard claims:
  - `sub`: User UUID
  - `org`: Organization UUID
  - `exp`: Expiration timestamp (15 minutes)
  - `jti`: Session/Token unique identifier
- **Signing**: Symmetric HMAC-SHA256 (`HS256`) using a strong server-side `JWT_SECRET_KEY` loaded from secure environment variables.
- **Backdoor Check**: The database is the source-of-truth. Every API call parses the JWT and validates the status of both User (must be `ACTIVE`) and Organization (must be `ACTIVE`) against the database.

---

### 3. CSRF Protection Policy

- **Mechanism**: Standard Double Submit Cookie or Custom Request Header.
- **Recommended Implementation**: Custom request header (`X-XSRF-TOKEN`). The frontend reads a CSRF token from a standard non-HttpOnly cookie (`XSRF-TOKEN`) and attaches it in the header. The server verifies that the header value matches the cookie.
- **Security Posture**: Prevents unauthorized cross-site requests since a malicious site cannot read the cookie to copy its value into the header.

---

### 4. Refresh Token Rotation (RTR) and Reuse Detection

- **Mechanism**: Refresh tokens are one-time use (rotated on every refresh).
- **Database Tracking**: Hashed refresh tokens are stored in the `refresh_token_records` table linked to a `UserSession`.
- **Reuse Detection**: If the database receives a rotated refresh token, it marks the entire `UserSession` as `suspicious` and immediately revokes all active sessions for that user.

---

### 5. Database Schema for Session & Refresh Tokens

If approved, the migration will create two tables:
1. `user_sessions`:
   - `id`: UUID (Primary Key)
   - `user_id`: UUID (Foreign Key → `users.id`, nullable=False)
   - `organization_id`: UUID (Foreign Key → `organizations.id`, nullable=False)
   - `session_status`: Enum (`active`, `expired`, `revoked`, `suspicious`, default=`active`)
   - `ip_address`: String
   - `user_agent`: Text
   - `expires_at`: Timestamp (nullable=False)
   - `revoked_at`: Timestamp
   - `created_at`: Timestamp (nullable=False)
2. `refresh_token_records`:
   - `id`: UUID (Primary Key)
   - `user_session_id`: UUID (Foreign Key → `user_sessions.id`, nullable=False)
   - `token_hash`: String (SHA-256 hash of refresh token, nullable=False)
   - `status`: Enum (`active`, `rotated`, `revoked`, `reused_detected`, default=`active`)
   - `issued_at`: Timestamp (nullable=False)
   - `expires_at`: Timestamp (nullable=False)
   - `rotated_at`: Timestamp

## Security Trade-off Matrix

| Area | Option | Pros | Cons |
|---|---|---|---|
| **Transport** | Secure Cookie | High XSS resistance | Needs CSRF mitigation |
| **Transport** | Bearer Token | Simple API consumption | Token theft via XSS |
| **Verification** | DB-backed State | Real-time status sync | DB query overhead |
| **Verification** | Stateless JWT | Fast execution | Revoked sessions stay valid until exp |

## Conclusion & Action Required

To prevent insecure and non-compliant auth implementations, the production boundary hardening requires formal sign-off on this ADR.

**Verdict**: **BLOCKED — ADR APPROVAL REQUIRED**
