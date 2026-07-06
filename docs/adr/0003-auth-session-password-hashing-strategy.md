# ADR 0003 - Auth Session and Password Hashing Strategy

## Status

Proposed

## Context

The Sprint 1 alpha design defines authentication endpoints and fixes login identity to `organization_slug + email`. It requires storing only password hashes and allows Argon2id or bcrypt. Sprint 1 needs enough auth foundation for Project and Master Data permissions, but this task must not implement auth logic.

## Decision

Use a Sprint 1 baseline auth design:

- Login identity is `organization_slug + email`.
- Store password hashes only.
- Use Argon2id as the preferred password hashing algorithm.
- If Argon2id support is unavailable or unsuitable during implementation, bcrypt is the allowed fallback.
- Prefer secure, HTTP-only cookie-backed sessions for browser clients.
- Session validation is server-side and tenant-aware.
- `GET /api/v1/auth/me` returns the authenticated user, organization context, active roles, and effective permissions needed by Sprint 1.
- Password reset endpoints may be scaffolded only if required by the Sprint 1 implementation task; reset token storage and expiry must be server-side.

Security baseline:

- No plaintext passwords.
- No tokens in source code.
- No production secrets.
- No cross-organization login by email alone.
- No frontend-only authorization.

## Consequences

- Sprint 1 implementation has a clear identity key and hash policy.
- Session behavior can support server-side RBAC checks without exposing sensitive credentials.
- Full security hardening remains reserved for the security hardening sprint unless explicitly required earlier.

## Design References

- `CODEX.md`
- `ENGINEERING_GUARDRAILS.md`
- `valora-design-book-v1.2-final-full-package/05_FINAL_HANDOFF/04_FINAL_IMPLEMENTATION_GUARDRAILS.md`
- `v1.2-alpha-project-master-data-completed/13_SECURITY/02_AUTHENTICATION.md`
- `v1.2-alpha-project-master-data-completed/13_SECURITY/03_AUTHORIZATION_RBAC.md`
- `v1.2-alpha-project-master-data-completed/14_ACCEPTANCE_TESTS/MASTER_DATA_ACCEPTANCE_TESTS.md`

## Sprint 1 Scope Impact

This ADR unblocks Organization/User/Role and auth baseline design for Sprint 1. Implementation must stay limited to the endpoints and behavior required by Project and Master Data access control.

## What Is Explicitly Not Implemented Yet

- No auth endpoints.
- No password hashing dependency.
- No session store.
- No middleware.
- No password reset implementation.
- No MFA or external identity provider.
- No security admin UI.

## Risks / Follow-up

- Choose concrete Argon2id or bcrypt library during the implementation PR dependency checklist.
- Confirm cookie settings for local development versus production.
- Confirm whether session state is database-backed or Redis-backed in Sprint 1.
- Security hardening beyond Sprint 1 remains deferred.
