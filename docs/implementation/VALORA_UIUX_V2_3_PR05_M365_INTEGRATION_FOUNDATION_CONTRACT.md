# VALORA UI/UX v2.3 — PR-05 OneDrive Personal Integration Foundation Contract

**Task:** `VALORA-PR05-IMPL-001` **Status:** IMPLEMENTED FOUNDATION — HISTORICAL BOUNDED ACCEPTANCE **Date:** 2026-09-12 **Authority:** ADR 0040 and the PR-05 task brief

**2026-09-21 current-authority note:** PR-05 remains valid provider/identity/OAuth foundation only. Product parent surface is provider-neutral `Không gian tài liệu`; OneDrive Personal is an integration. PR-05 does not define current visual authority, Document Workspace naming, Working-change promotion or development sequencing. Those are governed by UI/UX Handoff v2.3, Unified Roadmap v2.3 and ADR 0043–0045.

## Scope

PR-05 establishes the bounded foundation for the signed-in user's OneDrive Personal account. It creates canonical document identity, immutable document revisions, delegated Microsoft consumer authorization, encrypted token custody and immutable binding of one revision to one existing OneDrive file. OneDrive for Business and SharePoint are deferred.

## Implemented contract

### Canonical document identity

- `DocumentRecord` is the stable business document identity inside one organization and project.
- `DocumentRevision` is append-only and records immutable Data Snapshot and content SHA-256 digests.
- `DocumentRevisionCurrentHead` is the explicit current pointer; a revision is never inferred from a rendered filename or legacy generated-document row.
- The first-revision command is tenant-scoped, permission-gated, idempotent and atomically commits the record, revision, head and sanitized `AuditEvent`.

### OneDrive Personal authorization

- Runtime authority is fixed to `https://login.microsoftonline.com/consumers`.
- The supported flow is delegated authorization code with MSAL-managed PKCE, state and nonce validation.
- Runtime asks only for Graph `Files.Read`; no write, application-only or tenant-wide permission is introduced.
- Connection activation validates the consumer issuer/account subject and `/me/drive` response, including `driveType == personal`.
- One VALORA organization/user may bind one verified personal Microsoft account and drive. A silent account or drive switch is rejected.

### Credential custody

- Domain rows contain no access token, refresh token, authorization code, client secret or token cache columns.
- OAuth flow material and the MSAL token cache are encrypted with AES-256-GCM in the infrastructure-only `m365_encrypted_credentials` table.
- Deployment supplies the versioned keyring outside the database. Ciphertext is bound to organization, user, credential ID and purpose through authenticated associated data.
- Reads support transparent key rotation; replacement writes use the active key version.
- OAuth state is stored only as SHA-256, bound to an active VALORA session and consumed once before any provider exchange.
- The callback query is redacted at the ASGI server boundary so authorization codes, state and Microsoft client metadata do not enter HTTP access logs; the unmodified query remains available only to the callback application scope.

### Immutable file binding

- File identity is `connection_id + drive_id + drive_item_id`; filename and path are metadata only.
- Graph is read before the locked database mutation. The command then revalidates actor, project, document head, connection and observed drive identity.
- `M365RevisionBinding` captures eTag, cTag, version ID when available, timestamp, size, name, path and web URL as one immutable baseline.
- The same semantic command replays idempotently; conflicting reuse fails closed. Concurrent document creation, OAuth callback and binding behavior are proven on PostgreSQL.

## Internal HTTP bridge

- `POST /api/v1/m365/onedrive/authorize` requires an authenticated active session and `project:update` before provider components are constructed.
- `GET /api/v1/m365/onedrive/oauth/callback` is the internal redirect bridge required by delegated OAuth. It accepts no VALORA business mutation payload and returns only connection ID, drive ID and status.
- No public document-create or file-bind API and no frontend are introduced in PR-05.

## Explicitly deferred

- OneDrive for Business and work/school accounts.
- SharePoint sites, document libraries, `Sites.Selected` and provisioning.
- Upload, overwrite, move, delete, sharing, folder creation or any Graph write permission.
- Delta queries, webhooks, revalidation classification, sync/conflict resolution and publishing.

## Implementation files

- `backend/alembic/versions/f4c8d2a1b7e9_create_onedrive_personal_foundation.py`
- `backend/app/modules/document_workspace/**`
- `backend/app/modules/m365_integration/**`
- `backend/app/api/m365.py`
- `backend/app/core/config.py`, `backend/app/db/__init__.py`, `backend/app/main.py`
- `backend/tests/test_pr05_m365_foundation.py`
- `backend/tests/test_pr05_m365_postgresql.py`

Two existing test harnesses received bounded compatibility updates: the S13 isolated model-parity test registers PR-05 as later schema, and the auth PostgreSQL test uses the configured test URL and portable `python -m alembic` invocation.

## Audit evidence

- `docs/audits/2026-09-12__PR-05__M365_INTEGRATION_FOUNDATION_AUDIT.md`
- Engineering verification uses fake OAuth/Graph providers and isolated local PostgreSQL.
- Full backend gate: 1,360 passed, 0 failed, 0 skipped with `CI=true`.
- Live delegated verification passed on 2026-09-12 against an owner-controlled OneDrive Personal account: Graph returned a personal default drive, one active connection was persisted and the MSAL token cache remained encrypted under vault key version `v1`.
