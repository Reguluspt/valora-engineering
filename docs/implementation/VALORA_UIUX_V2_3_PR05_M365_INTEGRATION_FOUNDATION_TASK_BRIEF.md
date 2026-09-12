# VALORA UI/UX v2.3 — PR-05 M365 Integration Foundation Task Brief

**Task:** `VALORA-PR05-IMPL-001` **Status:** IMPLEMENTED — ENGINEERING AND LIVE ACCOUNT ACCEPTANCE PASSED **Date:** 2026-09-12 **Branch:** `integration/phase1c-pr05-m365-foundation` **Baseline:** `839debf84fca555447597eb0575cac5641d321d7`

## Objective

Create the smallest tenant-safe Microsoft 365 foundation that can bind a canonical VALORA Document Revision to one verified file in the signed-in user's OneDrive Personal and an immutable M365 version baseline. PR-06 must be able to revalidate that baseline without treating a new Microsoft 365 version as a new VALORA Document Revision.

## Goal chain

```text
Verified M365 connection and file binding
→ authoritative Return/Revalidation baseline for PR-06
→ conflict-safe sync foundation for PR-07
→ edit Word externally without silent overwrite or broken lineage
```

## Authority

- `CODEX.md`
- `ENGINEERING_GUARDRAILS.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.3.md` sections 1.4 and 5
- `docs/design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.3_M365_DOCUMENT_WORKSPACE_BASELINE_ADDENDUM.md`
- `docs/design/assets/VALORA_M365_DOCUMENT_WORKSPACE_BASELINE_v2.3.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.3_M365_RETURN_REVALIDATION_CONTRACT_ADDENDUM.md`
- proposed `docs/adr/0040-onedrive-delegated-integration-and-file-binding.md`

Repository authority outranks recall, provider suggestions and legacy endpoint behavior.

## Multi-provider execution plan

The Product Owner fixed the provider roster for PR-05 on 2026-09-12:

| Gate | Provider route | Mode | Required output |
| --- | --- | --- | --- |
| Independent repository survey | OpenCode Go `opencode-go/deepseek-v4-flash` | read-only | file map, risks and `READY` or `BLOCKED` |
| Architecture and security challenge | AGY `gemini-3.1-pro-high` | plan/read-only | ADR 0040 findings classified P0-P2 |
| Runtime implementation | Codex Sol at `xhigh` | sole writer | bounded diff inside the accepted allowlist |
| Database and tenant review | OpenCode Go `opencode-go/qwen3.7-max` | read-only | exact file/line findings classified P0-P2 |
| Final acceptance | Codex Sol at `xhigh` | gate | one `PASS`, `FAIL` or `BLOCKED` verdict |

No Claude model may be used for this task. Kimi is not a PR-05 survey or fallback provider. Gemini must run through AGY, not OpenRouter. A provider liveness or quota failure is reported as `BLOCKED`; it must not be hidden by silently substituting Claude or Kimi. External providers do not write repository files, approve their own output or replace command/test evidence.

## Survey result

The initial read-only survey returned `BLOCKED`. Owner acceptance plus the production encrypted vault decision cleared the runtime gate; live-account verification subsequently passed.

### Verified repository facts

1. No Microsoft Graph, OneDrive, SharePoint or M365 runtime exists.
2. No provider credential-encryption or token-store boundary exists.
3. `GeneratedDocument` is a legacy render output with template, snapshot hash and local storage metadata. It is not an accepted canonical Document Revision.
4. Legacy document APIs include PDF and package/QC semantics that the v2.3 M365 baseline must not expand.
5. No durable drive/item identity, file-version observation or revision binding exists.
6. The current Alembic head is `d4b7c9e2f1a6`; its PostgreSQL downgrade round trip is covered by the parent baseline.
7. Live `origin/main` remains `93f50f9ac81ab93e2361fffa8b71fc3bcfca57f6`.

### Authority gaps resolved by the proposal

- backend access mode: delegated authorization-code flow through the `consumers` authority;
- delivery scope: the signed-in user's OneDrive Personal; OneDrive for Business and SharePoint are deferred;
- least privilege: delegated `Files.Read`; write consent is deferred to the sync-write slice;
- secret boundary: dedicated encrypted credential vault, never domain persistence;
- canonical document identity: new Document/immutable Document Revision foundation;
- external identity: drive ID + drive-item ID, never filename/path;
- baseline observation: version ID when available plus eTag/cTag and immutable metadata;
- bounded PR split: PR-05 foundation, PR-06 revalidation, PR-07 sync/conflict.

## Planned implementation boundary after acceptance

PR-05 may add:

- canonical `DocumentRecord`, append-only `DocumentRevision` and current-head persistence;
- organization-and-user-scoped `OneDriveConnection` metadata with no secret/token columns;
- immutable `M365RevisionBinding` persistence;
- an `M365CredentialVault` port for encrypted token custody and atomic refresh rotation;
- an `M365GraphGateway` port and delegated Microsoft Graph v1.0 metadata adapter;
- internal authorization callback handling with state validation and secure token handoff;
- internal application services for connection verification, first revision creation and binding;
- atomic sanitized audit and idempotency behavior;
- focused unit and PostgreSQL migration/concurrency/downgrade tests;
- the final PR-05 implementation contract and audit evidence.

## Proposed implementation allowlist

- `backend/alembic/versions/<pr05_revision>_create_m365_integration_foundation.py`
- `backend/app/core/config.py`
- `backend/app/db/__init__.py`
- `backend/app/modules/document_workspace/**`
- `backend/app/modules/m365_integration/**`
- `backend/pyproject.toml` only for accepted Microsoft auth, HTTP and authenticated-encryption dependencies
- `.env.example` only for non-secret M365 setting names and safe empty placeholders
- `backend/tests/test_pr05_m365_foundation.py`
- `backend/tests/test_pr05_m365_postgresql.py`
- `backend/tests/test_s13_pr_004_column_mapping_postgresql.py` only to register PR-05 tables as later-schema artifacts in the existing isolated prior-migration parity test
- `backend/tests/test_auth_endpoints.py` only to make its PostgreSQL migration setup use the configured test database and portable `python -m alembic` invocation
- `docs/adr/0040-onedrive-delegated-integration-and-file-binding.md`
- `docs/implementation/VALORA_UIUX_V2_3_PR05_M365_INTEGRATION_FOUNDATION_TASK_BRIEF.md`
- `docs/implementation/VALORA_UIUX_V2_3_PR05_M365_INTEGRATION_FOUNDATION_CONTRACT.md`
- `docs/audits/2026-09-12__PR-05__M365_INTEGRATION_FOUNDATION_AUDIT.md`
- current-state authority files only when needed to record the exact PR-05 gate disposition

Any other production or test file requires coordinator review before edit.

## Required implementation semantics

- Tenant resolution and permission checks happen before external provider calls.
- Missing or foreign identifiers fail closed without leaking existence.
- Authorization binds the authenticated VALORA user and organization to the validated consumer issuer and Microsoft account subject; connection activation verifies `/me/drive` and records its drive ID.
- The callback validates state, PKCE, nonce, token signature, audience and consumer issuer before creating or updating a connection.
- Raw credentials and tokens never enter persisted rows, API responses, logs or audit payloads.
- OAuth state is single-use and bound to the initiating user/organization; token refresh rotation updates the credential vault atomically.
- File identity is `connection + drive + drive item`; filename/path are metadata only.
- The initial Graph observation completes before the database transaction.
- Expected current-revision concurrency, idempotency digest, revision binding and AuditEvent commit atomically.
- A new M365 version never creates or mutates a Document Revision automatically.
- Existing revisions and bindings are append-only; currentness uses an explicit head row.

## Forbidden scope

- no public business/document API or frontend; only the internal OAuth start/callback bridge is exposed for the delegated sign-in round trip;
- no file upload, overwrite, move, delete, sharing or folder provisioning;
- no SharePoint site, document-library, `Sites.Selected` or site-provisioning integration;
- no OneDrive for Business or work/school-account authorization;
- no application-only Graph access or tenant-wide file permissions;
- no OneDrive write permission or operation; later sync write requires incremental consent;
- no raw or reversibly exposed refresh tokens in domain persistence;
- no delta query, webhook or change-notification processing;
- no Return/Revalidation classification or UI;
- no Managed Region extraction, fingerprint, diff or three-way comparison;
- no sync write, conflict resolution, case-state provider, resume context or publishing;
- no Release Manifest, file-locking or legal-artifact linking;
- no rewrite or expansion of legacy document endpoints;
- no commit, push, pull request publication, merge, deploy, tag or release without separate authorization.

## Required verification after implementation

- focused service tests for tenant isolation, exact file identity, missing metadata, idempotent replay, conflicting replay and sanitized audit;
- fake-gateway tests for provider timeout, access denied, missing item and moved/renamed item;
- PostgreSQL migration upgrade/downgrade/upgrade with zero skips;
- uniqueness and concurrency tests for document current heads and revision bindings;
- authorization tests for state replay/mismatch, PKCE/nonce failure, non-consumer issuer, Microsoft-account mismatch and sanitized failures;
- credential-vault tests for token non-disclosure and atomic refresh rotation;
- dependency audit plus tests proving credentials/tokens cannot serialize into persistence/audit;
- full relevant backend suite, Ruff, Python compilation, Alembic single-head check and `git diff --check`;
- independent backend/security review of the exact final delta;
- no live tenant write test until a dedicated non-production OneDrive Personal account and credential-vault configuration are explicitly supplied.

## Stop conditions

Stop runtime edits when any of these becomes unresolved:

- implementation departs from accepted ADR 0040;
- the target is not a supported personal Microsoft account or returns a non-consumer issuer;
- a secure credential-vault implementation cannot be provisioned;
- canonical document/revision identity would need to reuse ambiguous legacy rows;
- secret handling would require raw credentials or refresh tokens in domain persistence;
- a required Graph behavior cannot be verified without broadening into PR-06 or PR-07.

## Survey disposition

`COMPLETE`. DeepSeek's survey, Gemini 3.1 Pro High's architecture/security challenge, implementation, 1,360-test full backend gate, final Qwen 3.7 Max review and live delegated OneDrive Personal verification completed on 2026-09-12. The live gate verified a personal default drive, encrypted token-cache persistence and single-use callback replay rejection without expanding into OneDrive for Business or SharePoint.
