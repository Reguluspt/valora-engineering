# PR-05 OneDrive Personal Integration Foundation Audit

**Date:** 2026-09-12 **Task:** `VALORA-PR05-IMPL-001` **Status:** ENGINEERING AND LIVE ACCOUNT ACCEPTANCE PASSED **Authority:** Accepted ADR 0040 and the PR-05 implementation contract **Writer and final verifier:** Codex

## Outcome

The bounded OneDrive Personal foundation is implemented. The runtime contains canonical immutable document revisions, consumer delegated authorization, encrypted credential custody, verified personal-drive identity and immutable file metadata binding. It contains no SharePoint, OneDrive for Business, Graph write, sync or frontend implementation.

## AI provider workflow

- DeepSeek V4 Flash (`opencode-go/deepseek-v4-flash`) performed the initial repository survey and implementation-boundary analysis.
- Gemini 3.1 Pro High (`gemini-3.1-pro-high`) challenged the architecture/security decision from a supplied evidence bundle. Its recommendation led to the accepted production-grade encrypted database vault with an external versioned keyring.
- Qwen 3.7 Max (`opencode-go/qwen3.7-max`) independently reviewed the implementation delta. Its first review reported no P0 and four P1 test/parity/validation findings; Codex verified and fixed all four.
- Codex remained the sole file writer, adjudicator and final verifier.
- Claude and Kimi were not used.

## Qwen findings closed

- Added concurrent PostgreSQL proof that one OAuth state can be consumed only once.
- Added concurrent PostgreSQL proof that one semantic binding creates one fact and audit event.
- Moved active user/organization authorization ahead of vault/OAuth component construction.
- Aligned the named OAuth-state unique constraint between ORM and Alembic.
- Added account-switch rejection and vault replacement/rotation tests.
- Recorded that DriveItem version-history lookup belongs to PR-06; PR-05 stores a version ID only when an adapter can provide one.

## Verification evidence available

- Focused SQLite/fake-provider PR-05 suite: 10 passed, 0 failed, including callback access-log redaction.
- Focused live PostgreSQL PR-05 suite: 4 passed, 0 failed, including migration upgrade/downgrade/upgrade and three concurrency paths.
- Clean isolated regression selection: 16 passed after separating a stale authority marker; the marker was corrected and its contract test then passed independently.
- MinIO regressions implicated by the first environment run: all 9 passed after MinIO was started.
- Existing auth PostgreSQL concurrency test passed against the configured isolated database after its portable Alembic invocation was corrected.
- Security scanner: passed with no blocker regression.
- Ruff: passed on runtime, migrations and changed tests.
- Python compilation: passed.
- Alembic exposes one head: `f4c8d2a1b7e9`.
- `git diff --check`: passed; only Windows CRLF conversion notices were emitted.
- Final Qwen 3.7 Max exact-delta review: READY; all four prior P1 findings closed and no new actionable P0/P1/P2 findings.

## Full-suite diagnostic history

The first full backend run produced 1,345 passed and 14 failed. Every failure was classified:

- 9 were caused by stopped local MinIO and passed after the service became healthy;
- 1 was a stale authority-contract literal and passed after reconciliation;
- 3 PostgreSQL migration/FK failures passed on a new isolated database after the existing S13 parity fixture learned to remove PR-05 later-schema tables;
- 1 auth test used a non-portable executable and hard-coded database; it passed after using `python -m alembic` and `TEST_DATABASE_URL`.

The final full rerun used `CI=true`, isolated PostgreSQL and live local MinIO: 1,360 passed, 0 failed and 0 skipped in 260.07 seconds. It emitted 29 pre-existing deprecation, legacy API, collection and deliberate stream-finalizer warnings.

`alembic check` reports three pre-existing PR-03 ORM drift items: the migration-created `idx_quote_batches_organization`, `idx_quote_lines_organization` and `idx_quote_lines_supplier` indexes are not declared in the PR-03 ORM models. PR-05 neither created nor changed those indexes; its own named constraints and tables passed migration round-trip and final independent parity review. The legacy drift is recorded without expanding this PR into PR-03 runtime changes.

## Security and scope disposition

- No raw OAuth secret is persisted in domain rows, returned by the API or written to audit payloads.
- Credential ciphertext uses AES-256-GCM with owner/purpose-bound associated data and key versions.
- Consumer account issuer, account subject, drive type and drive ID are verified before activation.
- Tenant, active-user, permission and current-revision checks fail closed.
- File identity uses immutable Graph IDs; rename/move affects metadata, not identity.
- OneDrive for Business and SharePoint remain explicitly deferred.

## Live OneDrive Personal acceptance

Live delegated acceptance passed on 2026-09-12 with an owner-controlled Microsoft personal account, a personal-account-only app registration, delegated `Files.Read` and the configured localhost callback. The callback exchanged the authorization code, verified Microsoft Graph `/me/drive` as `driveType == personal` and persisted exactly one active connection with non-empty consumer issuer, account subject and immutable drive ID.

The MSAL token cache was persisted only as AES-256-GCM ciphertext under vault key version `v1`; no raw token, authorization code or client secret entered a domain row or audit payload. The successful state was consumed and its encrypted OAuth-flow credential reference cleared. A repeated callback was rejected with `onedrive_oauth_state_invalid`, confirming the single-use replay boundary. The temporary database and runtime secrets used for this acceptance are not production credentials.

The first live run also exposed that Uvicorn's default access log included the callback query string. The closeout added a narrow ASGI boundary that presents a redacted query to the server access logger while preserving the original query only for the callback application scope. A regression test proves both halves of that boundary; raw callback values are no longer emitted by the access log.
