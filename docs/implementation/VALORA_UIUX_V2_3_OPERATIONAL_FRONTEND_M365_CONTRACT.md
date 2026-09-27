# VALORA UI/UX v2.3 — Operational Frontend and M365 Entry Contract

**Task:** `VALORA-OPS-ENTRY-001`
**Status:** IMPLEMENTED ON DRAFT PR #32 — HISTORICAL BOUNDED CONTRACT
**Date:** 2026-09-12
**Authority:** Product Owner request, accepted ADR 0040/0041, accepted PR-05/PR-06 contracts,
and the UI/UX v2.3 document-workspace and Return/Revalidation addenda

**2026-09-21 current-product amendment:** This is historical bounded implementation evidence. Current parent product surface is provider-neutral `Không gian tài liệu / Bộ tài liệu hồ sơ`; Microsoft 365/OneDrive/Word are integrations, not the domain workspace name. Current visual authority is Microsoft Fluent 2 light. Provider-centric labels and dark/cyan styling from the historical operational frontend are remediation debt, not accepted product UX.

## Purpose and boundary

Close the operational path from login to a tenant-scoped project and the already accepted OneDrive
Personal PR-05/PR-06 capabilities. The slice adds only the read surfaces and frontend orchestration
needed to connect an account, select an existing DOCX, adopt it as the first canonical revision,
open it in Word, and display server-computed revalidation/readiness.

This contract does not authorize OneDrive for Business, SharePoint, Graph writes, document sync,
conflict decisions, publishing, release state, a browser Word editor, or PDF export. PR-07 remains a
separate acceptance gate.

## Session and account contract

- The frontend restores a cookie-backed session with `GET /api/v1/auth/me`; it never stores access
  or refresh tokens.
- Login uses organization slug, email, and password against the existing strict auth API. Logout
  uses the existing CSRF-protected command and clears local account state even when the server has
  already invalidated the session.
- The shell displays the authenticated user's name/email and organization slug from `/me`.
- Navigation and actions may be hidden or disabled from `/me.permissions`, but every API remains
  authoritative and fails closed through tenant and RBAC checks.
- `GET /api/v1/projects` is the only source for the project picker. An empty or failed response is
  rendered truthfully; no demo project is synthesized.

## OAuth callback and connection status

### Callback

`GET /api/v1/m365/onedrive/oauth/callback` keeps the accepted single-use OAuth state, session
binding, Personal-drive verification, credential-vault, and audit behavior. After completion it
returns `303 See Other` to the configured `M365_FRONTEND_RETURN_URI`.

The return URI is fixed configuration, must be an absolute HTTP(S) URL whose origin exactly matches
an allowed CORS origin, and is never accepted from request parameters or OAuth state. The redirect
fragment/query may contain only a bounded result code:

- `m365=connected` after a successful connection commit;
- `m365=failed&reason=<sanitized-code>` after an expected OAuth/integration failure.

Authorization code, OAuth state, PKCE material, tokens, provider payloads, connection ID, drive ID,
user ID, organization ID, and exception text must never appear in the redirect. The frontend return
page treats the result as presentation context only and fetches authoritative connection status.

### Connection read model

`GET /api/v1/m365/onedrive/connection` requires an authenticated active session and returns only the
connection owned by the current organization/user:

```json
{
  "connection_id": "opaque UUID or null",
  "drive_id": "stable drive ID or null",
  "status": "not_connected | active | error | revoked",
  "last_verified_at": "timestamp or null"
}
```

An absent connection is a successful `not_connected` read, not a hidden foreign lookup. Microsoft
account subject, credential IDs, scopes, token cache, secrets, and provider responses are excluded.

## Provision/adopt selection contract

### Read-only options

`GET /api/v1/m365/onedrive/projects/{project_id}/adoption-options` requires `project:update`, resolves
the tenant-owned project and actor-owned active OneDrive Personal connection, and returns:

- display-safe project identity and a server-authored adoption snapshot;
- active, current, tenant-owned DOCX template versions with a valid accepted Managed Region
  manifest;
- one bounded page of direct OneDrive children for `parent_item_id=root` or a stable folder item ID.

The Graph adapter uses delegated `Files.Read` only. It returns folders plus DOCX files, at most 100
visible entries, indicates truncation without exposing `@odata.nextLink`, and performs no write or
persistence of the provider listing. Each item contains only stable item ID, kind, display name,
size/modified time where applicable, and safe web URL for a file. Names and paths are display data,
never identity.

The server-authored snapshot has contract `valora-operational-adoption-v1` and contains only current
project lineage needed by the accepted D9 first-lineage producer. The frontend passes it unchanged
to provision. It is not a PR-07 protected-value snapshot, sync base, conflict input, release fact, or
permission to overwrite data.

### Adoption command

The existing strict `POST .../documents/provision` remains the canonical producer. The operational
frontend selects exactly one active template version and one DOCX item returned by adoption-options,
supplies a human-readable title, the unchanged server snapshot, and a fresh idempotency key.

The backend still re-resolves project, template, connection, item identity/content, Managed Regions,
tenant authority, and idempotency. Client labels, folder paths, file names, and callback status do not
authorize adoption. Folders and non-DOCX items cannot be provisioned.

## Canonical document list and return/revalidation UI

`GET /api/v1/m365/onedrive/projects/{project_id}/documents` requires `project:read` and returns each
tenant-owned canonical document's current revision, display-safe binding, and the accepted PR-06
readiness projection. Old revisions and foreign records cannot become current by presentation order.

The frontend:

- opens only the backend-provided `web_url` in a new browser context;
- records a local, non-sensitive handoff marker and requests one revalidation when focus returns;
- also offers one explicit “Kiểm tra thay đổi” action;
- renders exactly the five backend classifications and backend-computed freshness/readiness;
- presents one primary recovery action for the current state;
- never derives inside/outside Managed Region change, conflict, safety, or release readiness.

`EXTERNAL_CHANGE_OUTSIDE_MANAGED` is not labeled a conflict. `EXTERNAL_CHANGE_IN_MANAGED` remains a
blocking detected change awaiting the separately accepted PR-07 behavior. A failed or unavailable
check preserves prior information only as visibly stale context.

## Security, failure, and privacy invariants

- Cookie and CSRF behavior stays governed by the accepted auth boundary; all frontend mutations use
  the shared credentialed API client.
- Tenant/RBAC denial occurs before Graph access. Missing or foreign project/document identifiers use
  the established hidden-not-found behavior.
- Provider network, auth, throttle, malformed payload, and identity failures map to sanitized stable
  API errors; raw provider bodies and secrets are never logged or rendered.
- The callback URI is not an open redirect. Provider URLs are not accepted as API base URLs.
- No account switch is silently adopted. Reconnect follows the accepted subject/drive invariant.
- No new database migration is required for these read models and frontend orchestration.

## Acceptance

The slice is accepted only when:

1. unit/API tests cover session restore/login/logout, tenant/RBAC denial, callback redirect
   sanitization, connection absent/active reads, bounded folder/DOCX selection, snapshot authority,
   canonical document listing, strict provision input, and the five readiness presentations;
2. frontend tests prove real API clients, auth gating, account context, real project selection,
   permission-aware M365 actions, adopt submission, return/focus revalidation, and no frontend
   classification recomputation;
3. browser acceptance covers desktop and laptop login → project → OneDrive workspace, loading/empty/
   error/retry states, callback return, folder selection, document state, and console closeout;
4. any browser provider fixture is identified as simulated and is not claimed as live Microsoft
   evidence; existing PR-05/PR-06 live-provider evidence remains the provider proof;
5. backend/frontend static checks, focused suites, full suites, production build, security checks,
   and a clean-tree audit pass with no relevant skips.

Implementation, local tests, and local commits are authorized by the Product Owner's request. Push,
merge, deployment, release, PR-07 runtime, and later PR runtime remain separately gated.
