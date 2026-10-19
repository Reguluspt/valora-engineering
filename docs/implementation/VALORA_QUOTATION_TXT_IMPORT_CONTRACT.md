# Human TXT quotation source custody

Authority: [Phase 2 release](https://github.com/Reguluspt/valora-engineering/issues/208#issuecomment-6251855643), [accepted technical contract and 34 cases](https://github.com/Reguluspt/valora-engineering/issues/208#issuecomment-6247275505), and [bounded design acceptance](https://github.com/Reguluspt/valora-engineering/issues/208#issuecomment-6247940075). Implementation baseline: `bced12a754c2ddf41655eb12d6688e523136f45d`, exact-main CI #671. This document describes the bounded implementation; it is not product certification or permission to operate #199, import #205, execute #203 UAT, merge or deploy.

An authenticated human with current `project:read` and `project:update` selects one original UTF-8 `.txt` in one existing same-tenant DRAFT Project. The dialog displays the server Project code/name, filename, exact byte count, SHA-256 and escaped plain-text preview limited to 4,096 Unicode scalar values. The human explicitly selects **Xác nhận nhập tài liệu**. Import capability is independent of professional quotation write permission and an owned Workbench session.

Files contain 1–1,048,576 original bytes. Optional BOM and newline bytes remain unchanged. The server bounds the complete multipart stream at 1,114,112 bytes, permits exactly one `metadata` part and one `file`, limits metadata to 8,192 UTF-8 bytes, rejects unknown command fields, unsafe filenames, unsupported media, invalid UTF-8, forbidden controls and binary signatures. Filenames are display metadata and never object keys. Neither preview nor raw content enters request/receipt/audit rows.

## HTTP contract

All paths are below `/api/v1/projects/{project_id}/quotation-documents` and retain existing session, cookie, CSRF and Origin enforcement.

| Method/path | Meaning |
| --- | --- |
| `GET /import-context` | Read current Project identity, coherent Case State token, Project row version, import capability and TXT limits. No document/storage mutation. |
| `POST /import` | Explicit initial admission using `ImportCommand` metadata and one file. |
| `GET /import-receipts/{command_id}` | Original-actor, same-tenant/Project historical receipt or durable pending state, plus separate current source proof. No recovery write. |
| `POST /import-receipts/{command_id}/recover` | Human-confirmed same-intent recovery after exact-file reselection, original CAS and current storage state version. No new intent/key or rebasing. |

Strict metadata uses `contract_version=quotation-txt-import-v1`, command UUID, `confirm=true`, original `expected_case_version`, `expected_project_row_version`, expected SHA-256 and byte count. Recovery adds `expected_storage_state_version`. Actor, tenant, Project identity, provider, policy, retention and document/revision/binding IDs are server-owned. Canonical source, plan, human decision and request digests follow the accepted domain-separated JSON manifests; the storage idempotency key is `txt-quote-import:{command_id}`.

`201` is the first confirmed commit, `200` a verified historical replay/read and `202` a durable pending outcome. Static safe validation/auth/scope/conflict responses do not expose filename/content/private provider diagnostics. A lost response, timeout or `5xx` never asserts rollback. The frontend disables mutation retry, retains only scoped command identity before dispatch and makes GET reconciliation the first recovery action. Historical success remains historical if current source proof later fails.

## Retention and immutable history

The static manifest is `quotation-txt-retention-policy-v1`, policy `quotation-txt-record-10y-v1`, version 1. Request and receipt store the canonical manifest and its digest. After external verification ends, a fresh PostgreSQL finalization transaction samples `transaction_timestamp()` once as business-effective `t`. On successful COMMIT, the custody audit timestamp/payload, receipt finalization/anchor and pending binding's `bound_at`/retention anchor equal `t`, including microseconds. This is not a physical WAL commit timestamp.

The minimum initial floor is ten calendar years in UTC, preserving month/day/time/microseconds with 29 February clamped to 28 February when necessary. The PostgreSQL migration also checks the exact UTC calendar floor. Callback/audit/flush/COMMIT failure leaves no committed import milestone, revision, head, binding, receipt or Project increment. Historical replay validates and returns the original timestamp, floor, policy manifest and receipt digest.

Request/receipt rows and custody audits are append-only. Original revisions and bindings are pinned by the scoped receipt. No historical DOCX backfill, policy change, new role/grant, retention extension, legal-hold writer or purge endpoint is introduced. Current disposition is `NO_PURGE_EXTENSION_UNCERTIFIED`: `purge_allowed=false`, `effective_minimum_retain_until=null`, with `release_extension_enforcement_not_certified`. Existing orphan cleanup rejects every finalized/bound object before provider deletion.

## Transaction boundaries and narrow seams

The coherent full Case State read uses the existing caller-owned repeatable-read snapshot before preparation/I/O. A short preparation transaction locks Project first and revalidates the human/session/tenant/permissions/DRAFT/original Project CAS. The optional `prepare_initial_storage_intent.preparation_callback` writes the immutable original request envelope and PREPARED audit after intent flush and before the helper-owned commit.

Candidate persistence and existing create/recover/observe/checksum helpers retain their transaction ownership. Every finalization attempt obtains fresh local pre-observation, bounded full-byte read and post-observation outside database locks, including recovery from an already OBJECT_VERIFIED state.

The optional `finalize_storage_revision.pre_finalization_guard` executes after its existing-binding early return and before candidate/state/head locking. It acquires Project first, then organization, original User, current login session, UserRole rows and supporting Role rows in stable UUID order, derives fresh permissions, checks DRAFT/original CAS and validates the scoped request/candidate/policy/proof. It performs database checks only. Lock/statement waits are bounded. No full Case State resolver or provider/file access runs under final locks.

The existing finalization callback checks the actual pending binding against the externally verified object identity, assigns `bound_at=t` before its INSERT, flushes revision/head/binding, performs exactly one conditional Project `v→v+1`, and inserts the receipt and explicit-timestamp `QUOTATION_DOCUMENT_IMPORTED` audit. The helper retains its single final commit, storage transition and storage success audit. The application wrapper rolls back every guard/callback/flush/commit exception and validates the immutable receipt/audit chain even when a storage replay/race branch bypasses the guard. Existing no-callback/no-guard callers retain their behavior. The audit helper's optional keyword-only timestamp preserves omitted-argument behavior and rejects naive explicit timestamps.

Concurrent same-command completion returns the original committed receipt. Different commands at the same original Project CAS serialize to one winner and a conflict. No initial-head conflict becomes revision 2. A revocation winning first denies publication; a writer arriving after the guard waits for its supporting authority locks. If revocation wins immediately after commit, the HTTP caller may lose read access despite a committed receipt; the client retains the original command and reconciles after authorized login instead of treating denial as rollback.

## Source availability and business boundary

After publication locks end, unchanged A13 `retained_source` verifies the current scoped revision/head/binding, `exchange-local`, local provider, exact object version/creation identity, positive length and pre/read/post full SHA/count proof. The historical receipt and live availability remain separate. A privileged replacement after the last external proof can fall in the filesystem/database gap; current A13 reads then report unavailable and professional source selection stays disabled. There is no filesystem/PostgreSQL two-phase claim or automatic repair/reupload.

Import creates no SupplierQuote fact/item/confirmation, PRICE_EVIDENCE, selection, appraisal, fabricated release or Case State completion. Existing A13 registration/mapping and A14 **Hoàn tất báo giá NCC này** remain separate explicit human operations with their existing authority. After a committed import, bounded source/preparation/Case State reads refresh; no source is automatically selected.

## Verification ownership

Focused parser/calendar/controller/adapter tests accompany the feature. Storage/A13/A14 regressions remain in their existing modules. The [task-only acceptance harness](../../tests/e2e/issue208/README.md) uses synthetic data, real PostgreSQL 16, the Linux immutable local store, actual API/auth and browser UI. It includes transaction rollback/commit failure, Project/identity/role/session races, no-I/O-under-lock proof, original-byte readback, same-command replay, current-source failure, multipart safety and migration round trips. Exact results and `TXT-01..TXT-34` statuses belong to the unchanged frozen review packet.

`TXT-06` future release-extension writers, `TXT-08` future legal-hold writers and `TXT-09` operator use of original #205 bytes are **DEFERRED**, never implemented/PASS by this change. Their current fail-closed no-purge disposition is tested separately. #199 and original #205 resources are never accessed by this developer harness; PO E2E/SQ execution remains a later gate.
