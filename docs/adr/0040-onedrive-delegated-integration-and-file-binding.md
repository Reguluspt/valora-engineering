# ADR 0040 — OneDrive Personal delegated integration and immutable file binding

**Status:** ACCEPTED — PRODUCT OWNER AUTHORIZED IMPLEMENTATION **Date:** 2026-09-12 **Task:** `VALORA-PR05-IMPL-001`

## Context

UI/UX v2.3 requires VALORA to manage business data, Data Snapshot, lineage, sync state, Document Revision and Release Manifest while Microsoft 365 owns the Word file and its file versions. PR-06 Return/Revalidation and PR-07 Sync/Conflict need a tenant-safe, durable baseline that distinguishes a VALORA Document Revision from an observed Microsoft 365 file version.

The Product Owner has narrowed PR-05 to the signed-in user's OneDrive Personal account. OneDrive for Business, SharePoint sites and document libraries are deferred to later, separately authorized integration slices.

The current repository does not provide the required baseline:

- no Microsoft Graph, OneDrive or SharePoint runtime exists;
- no provider credential or token-storage boundary exists;
- legacy `GeneratedDocument` is a render output, not an approved canonical Document Revision;
- legacy document endpoints are not a safe source for the new integration contract;
- no durable drive/item identity, M365 version observation or revision binding exists.

Microsoft Graph identifies a file by drive and drive-item ID. A drive item also exposes `eTag`, `cTag`, `webUrl` and version history. The download URL is short-lived and must not be persisted. The signed-in user's default OneDrive is addressed through `/me/drive`, which supports delegated personal Microsoft accounts and not application-only access.

## Proposed decision

### D1. OneDrive Personal first, using consumer delegated access

PR-05 uses the OAuth 2.0 authorization-code flow through a supported Microsoft authentication library. The user grants access through a personal Microsoft account. The app registration must allow personal Microsoft accounts, and runtime authorization uses the Microsoft identity platform `consumers` authority so work or school accounts cannot enter this connection flow.

The initial permission contract is delegated `Files.Read` plus `offline_access` and the minimum OpenID Connect scopes required for sign-in. PR-05 has no Graph write operation. A later sync-write slice must request incremental write consent rather than pre-authorizing it here. Broad application permissions are not part of PR-05.

The adapter resolves and verifies the user's default drive through `/me/drive`. It does not accept a SharePoint site ID or document-library selector. OneDrive for Business remains out of scope until separately accepted and tested.

### D2. OAuth credentials use a dedicated secure vault boundary

Raw client secrets, access tokens and refresh tokens are never stored in VALORA domain tables, API payloads, audit payloads or logs. A dedicated `M365CredentialVault` port owns encrypted-at-rest token material and refresh-token rotation. Domain persistence stores only an opaque credential reference and non-secret connection metadata. The first production adapter may store only authenticated ciphertext, nonce and key version in an infrastructure table; encryption keys remain outside the database in a deployment-supplied keyring.

The production vault implementation and its encryption/key-management contract must be accepted before a live connection can be activated. Token refresh replaces rotated token material atomically; a failed refresh cannot silently leave a connection marked healthy.

### D3. Canonical VALORA document identity is separate from legacy render output

PR-05 introduces a bounded `document_workspace` model rather than reinterpreting `GeneratedDocument` in place:

- `DocumentRecord` is the stable project document identity;
- `DocumentRevision` is append-only and records its Data Snapshot digest, content checksum, creation actor/time and optional lineage to a legacy generated output;
- `DocumentRevisionCurrentHead` holds the one current revision pointer and optimistic revision for a document.

The legacy generated output can be lineage input, but it does not become canonical merely because an M365 file is created from it. PR-05 does not migrate or reinterpret old render rows.

### D4. OneDrive connection identity and baseline binding are explicit

The `m365_integration` bounded context contains:

- one `OneDriveConnection` per organization and connected user for the first implementation;
- the organization ID, VALORA user ID, validated consumer issuer, Microsoft account subject, drive ID, opaque credential reference and connection status;
- one immutable `M365RevisionBinding` per Document Revision;
- the external identity tuple `connection_id + drive_id + drive_item_id`;
- the baseline observation captured at bind time: version ID when available, `eTag`, `cTag`, modified time, size, name and `webUrl`.

Path and filename are display metadata, not identity. A moved item with the same drive/item identity remains the same file. A replacement with the same filename is not rebound automatically. Short-lived download URLs are never persisted.

PR-06 may append revalidation observations and classifications later. It must not overwrite the baseline bound to an existing Document Revision.

### D5. Provider port and transaction boundary

Application services depend on an `M365GraphGateway` port and an `M365CredentialVault` port. The production Graph adapter uses Microsoft Graph v1.0 and delegated tokens; tests use deterministic fakes.

The external metadata read completes before the database transaction. The transaction then:

1. rechecks organization, user, project, document and expected current revision;
2. inserts the immutable revision binding from the observed Graph metadata;
3. appends an AuditEvent without secret or token data;
4. commits atomically.

An idempotency key plus server-derived request digest makes replay return the original binding. Conflicting reuse fails closed. Cross-tenant identifiers return the same hidden-not-found behavior as existing tenant-safe project services.

### D6. PR-05 remains a OneDrive foundation slice

PR-05 may complete consumer delegated authorization, verify the signed-in user's OneDrive Personal, create canonical document/revision records and bind one existing OneDrive file by stable ID. It does not implement:

- SharePoint sites, document libraries, `Sites.Selected` grants or site provisioning;
- OneDrive for Business or work/school-account authorization;
- application-only Graph access or tenant-wide file permissions;
- file upload, overwrite, move, delete, sharing or folder provisioning;
- delta queries, webhooks or change notifications;
- return/revalidation classification, Managed Region extraction or three-way comparison;
- sync writes, conflict resolution, case-state provider wiring or publishing;
- public document-workspace UI, file locking, Release Manifest or legal-artifact linking.

OneDrive for Business and SharePoint integration require their own tasks and architecture decisions after the Personal baseline is accepted. They must not reuse consumer-account assumptions without a fresh identity, permission and tenant-isolation review.

## Alternatives considered

### Reuse `GeneratedDocument` as Document Revision

This is smaller initially, but it conflates render output with business revision identity, inherits legacy PDF and package semantics and makes later sync lineage ambiguous. Rejected.

### SharePoint-first application access

Selected application permissions can support tightly scoped SharePoint resources, but that is not the Product Owner's first delivery target. Deferred to the later SharePoint integration slice.

### Broad delegated or application permissions

`Files.ReadWrite`, `Files.ReadWrite.All`, `Sites.ReadWrite.All` and equivalent write or tenant-wide access exceed the read-and-bind OneDrive use case. Rejected for PR-05; a later write slice must justify incremental consent independently.

## Adversarial review

- Delegated access introduces refresh-token custody. A production connection must remain blocked until the credential vault and rotation behavior are implemented and verified.
- A new canonical document model adds migration and lineage cost. The signal that this choice is wrong would be an existing accepted model that already satisfies revision identity, immutable snapshot binding and current-head concurrency; the survey found none.
- Persisting names, paths or `webUrl` as identity would guarantee silent misbinding after moves or replacements. Only drive/item IDs are authoritative.
- Six months from now, the likely failure is treating OneDrive Personal as an implicit OneDrive for Business or SharePoint abstraction. The explicit D6 boundary requires each to enter through a separate decision.

## Consequences

- PR-06 receives a trustworthy file/version baseline without inventing Document Revision semantics.
- Initial onboarding requires interactive personal Microsoft-account consent and secure refresh-token custody; it does not require organization admin consent.
- PR-05 does not require SharePoint site discovery, document-library selection, admin site grants or `Sites.Selected`.
- PR-05 adds new document and integration bounded contexts instead of extending legacy document endpoints.
- Runtime implementation first proceeded with fake-provider verification. The separately authorized live-account acceptance passed on 2026-09-12 with an owner-controlled OneDrive Personal account and temporary non-production vault configuration.

## Owner decision

Accepted on 2026-09-12: PR-05 targets OneDrive Personal; OneDrive for Business and SharePoint integration are deferred. The Product Owner authorized proceeding after fixing that scope. Acceptance authorizes only the bounded task in `VALORA_UIUX_V2_3_PR05_M365_INTEGRATION_FOUNDATION_TASK_BRIEF.md`.

## References

- [Microsoft Graph delegated access](https://learn.microsoft.com/en-us/graph/auth-v2-user)
- [Microsoft identity platform authorization-code flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow)
- [Microsoft identity platform account types](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app)
- [Personal-account `consumers` authority](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens)
- [Get a user's OneDrive](https://learn.microsoft.com/en-us/graph/api/drive-get?view=graph-rest-1.0)
- [Microsoft Graph permissions overview](https://learn.microsoft.com/en-us/graph/permissions-overview)
- [driveItem resource and identity metadata](https://learn.microsoft.com/en-us/graph/api/resources/driveitem?view=graph-rest-1.0)
- [Get driveItem and conditional eTag/cTag reads](https://learn.microsoft.com/en-us/graph/api/driveitem-get?view=graph-rest-1.0)
- [List driveItem versions](https://learn.microsoft.com/en-us/graph/api/driveitem-list-versions?view=graph-rest-1.0)
