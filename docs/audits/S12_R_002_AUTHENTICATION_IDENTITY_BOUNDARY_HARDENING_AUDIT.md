# S12-R-002 — Authentication Identity Boundary Hardening Audit

## A. Title and Final Status
- **Title**: S12-R-002 — Authentication Identity Boundary Hardening
- **Final Status**: **BLOCKED — ADR APPROVAL REQUIRED**

## B. Root Cause
The production backend currently reads the unauthenticated `X-User-Id` header from incoming requests to resolve current users and their roles/permissions in `backend/app/core/rbac.py`. This mechanism lacks signature verification and transport security, allowing a malicious client to easily forge user IDs and bypass tenant isolation.

## C. ADR/Design Authority
This audit proposes a new architecture decision record: [0026-authentication-identity-boundary-hardening-proposal.md](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/adr/0026-authentication-identity-boundary-hardening-proposal.md) to address the lack of specification in the existing codebase for token signatures, transport security, browser storage, and CSRF policy.

## D. Authentication Architecture
The proposed architecture recommends secure, HTTP-only cookie-backed sessions containing access and refresh tokens, instead of insecure header-based transport or stateless Bearer tokens exposed to XSS.

## E. Credential Transport
Alternative A (Secure Cookie Transport) is proposed:
- `__Host-Access-Token` (HttpOnly, Secure, SameSite=Strict, TTL = 15m)
- `__Host-Refresh-Token` (HttpOnly, Secure, SameSite=Strict, TTL = 30d)

## F. Identity Derivation
Authentication identities are resolved server-side by validating the incoming cookies. Fallback identities and client-side roles are prohibited.

## G. X-User-Id Removal
The use of `X-User-Id` will be set to 0 occurrences in production code, with `S12R-AUTH-001` configured to fail the build if it returns.

## H. User/Org Status Behavior
Inactive or deleted users and organizations must fail-closed immediately upon token decryption, resolving their status against the database.

## I. Authorization Behavior
Authentication and authorization remain strictly separated (401 Unauthorized vs. 403 Forbidden).

## J. Expiry/Revocation
Sessions are revoked on user logout, password changes, critical role modifications, and refresh token reuse detection.

## K. Refresh Rotation/Reuse
One-time use rotated refresh tokens will be enforced, tracking token hashes in the database. Detection of refresh token reuse will trigger immediate revocation of all user sessions.

## L. Frontend Integration
The API client will be configured to automatically pass credentials and handle 401 token refresh flows without looping.

## M. Logging/Redaction
Sensitive tokens, cookies, passwords, and secrets are redacted from logs and errors.

## N. Files Changed
- [0026-authentication-identity-boundary-hardening-proposal.md](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/adr/0026-authentication-identity-boundary-hardening-proposal.md)
- [S12_R_002_AUTHENTICATION_IDENTITY_BOUNDARY_HARDENING_AUDIT.md](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/audits/S12_R_002_AUTHENTICATION_IDENTITY_BOUNDARY_HARDENING_AUDIT.md)

## O. Migration Impact
A database migration will be required to define the `user_sessions` and `refresh_token_records` tables when this ADR proposal is approved.

## P. Tests Added
No code tests added in this phase due to the BLOCKED status.

## Q. Commands/Results
- `wc -l docs/remediation/S12_R_PRE_VALIDATION_REMEDIATION_SLICE.md`: 561
- `git hash-object docs/remediation/S12_R_PRE_VALIDATION_REMEDIATION_SLICE.md`: `d4b1408b1c30b27b203203498a4e318b467cade2`
- `sha256sum docs/remediation/S12_R_PRE_VALIDATION_REMEDIATION_SLICE.md`: `962039d1f1c9150bbfa7bc7c509b04599e2ce709a5f6857b59ece099deb6c96c` (raw LF bytes representation)

## R. CI SHA/Run
- Commit SHA: Pending push
- CI Run URL: Pending push

## S. Security Baseline Update
The baseline for `S12R-AUTH-001` will remain at current baseline levels until this proposal is approved for implementation.

## T. Known Limitations
Implementation of production auth is explicitly blocked pending ADR approval.

## U. Out-of-Scope Confirmation
Confirmed that no changes to other sprints or out-of-scope files were made.

## V. Final Verdict
**BLOCKED — ADR APPROVAL REQUIRED**
