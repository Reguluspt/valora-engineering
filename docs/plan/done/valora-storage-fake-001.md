# VALORA-STORAGE-FAKE-001 — Provider-neutral immutable storage proof

**Status:** COMPLETE — LOCAL FAKE ACCEPTED; PRODUCTION PROVIDER UNSELECTED
**Date:** 2026-09-19
**Authority:** ADR 0043 and accepted Document Blob Storage contract

## Goal

Prove that an old execution, lost response, crash, replay or concurrent writer cannot overwrite a
newer VALORA document, create a duplicate authoritative revision or turn unknown storage state into
success.

## Accepted boundaries

- Implement only the four-operation provider-neutral `DocumentBlobStore` port.
- Use a deterministic in-memory fake with explicit fault injection.
- Reuse canonical `DocumentRecord`, `DocumentRevision` and `DocumentRevisionCurrentHead`.
- Persist the smallest intent/candidate/event/state/binding model required by T1–T14.
- Use exact SHA-256; provider eTag, timestamp, size or existence alone is never integrity proof.
- Keep all storage calls outside database transactions/locks.
- Finalize by database CurrentHead CAS; one intent finalizes at most one revision.
- Each execution intent has exactly one active state projection. Competing intents frozen from the
  same document head may coexist until CurrentHead CAS selects the only authoritative winner.
- Preserve Model A export-only and the accepted retention/deletion/encryption policy.

Explicitly excluded:

- AWS credentials, requests, account changes or S3 adapter;
- any other cloud/provider adapter or generic multi-cloud framework;
- real customer documents or valuation records;
- production rollout, historical backfill, bulk migration or provider/residency selection;
- OneDrive direct-write, Model B import, UI work, PR-08, deployment or release.

## Contract refinements grounded in the current code

`DocumentRevision` stores `content_checksum_sha256` but no byte length. Therefore:

- binding checksum must equal candidate checksum and revision checksum;
- binding byte length must equal candidate byte length;
- this task does not add a revision byte-length column or backfill historical revisions;
- the one-binding invariant applies to revisions finalized by the new app-owned flow.

The execution-state projection repeats tenant/project/document IDs for tenant-safe lookup. There is
exactly one state row per intent; lineage-wide uniqueness is intentionally not imposed because ADR
0043 D6 and T8 require competing intents from one frozen head. Append-only execution events remain
the history, and CurrentHead CAS is the sole authoritative winner selector.

## Implementation slices

### S1. Domain port and result types

Add a provider-neutral module containing exactly:

- `create_immutable`;
- `observe`;
- `verify_checksum`;
- `delete_uncommitted_or_expire`.

Use closed result/status types. No SDK, credential, signed URL, browser handoff or provider-specific
retry policy enters this module.

### S2. Persistence

Add normalized models and one Alembic migration for:

- `DocumentStorageExecutionIntent` — immutable frozen command/idempotency input;
- `DocumentStorageCandidate` — one deterministic key/checksum/size per intent;
- `DocumentStorageExecutionEvent` — append-only transitions;
- `DocumentStorageExecutionState` — one-per-intent current projection with optimistic version;
- `StorageObjectBinding` — immutable link from a newly finalized canonical revision to its exact
  object/candidate/intent plus retention snapshot.

Use tenant-scoped composite foreign keys and unique constraints. Store no document bytes, credential,
token, signed URL or query-critical JSON.

### S3. Application flow

Implement explicit commands for:

1. prepare intent in a short transaction;
2. record deterministic candidate/checksum in a short transaction;
3. create/observe/verify through the port with no database lock;
4. finalize revision/binding/head/event/audit in one short CAS transaction;
5. recover an uncertain create using the same intent/key;
6. clean only eligible unbound terminal candidates.

Same organization/idempotency key plus the same request digest returns the persisted execution.
Same key plus another digest fails. Illegal state transitions fail closed.

### S4. Deterministic fake

The test fake maintains committed objects independently from response outcomes and exposes bounded
faults at create-before-commit, create-after-commit-before-response, observe, streamed verification
and cleanup. Tests select faults explicitly; default behavior does not hide missing assertions.

### S5. Verification and review

Run targeted storage, document workspace, affected M365 and PostgreSQL suites, then the appropriate
backend suite. Run migration upgrade/downgrade/upgrade, `ruff`, compile/static checks and
`git diff --check`. Independent review receives only authority, exact diff and acceptance criteria.

## T1–T14 acceptance matrix

Every automated scenario asserts initial state, selected fault/event, provider object state,
execution state, revision count, CurrentHead and recovery behavior.

| ID | Scenario | Required outcome |
|---|---|---|
| T1 | Normal create | Exact object verified; one N+1 revision/binding/head advancement. |
| T2 | Duplicate, same checksum | Existing exact object reused; still one finalized revision. |
| T3 | Duplicate, different checksum | `RECONCILIATION_REQUIRED`; no overwrite/revision. |
| T4 | Lost success response | Same-key observation and verification recover without blind create. |
| T5 | Crash before create | Intent/candidate remain; explicit same-key recovery can create. |
| T6 | Crash after create | Existing exact object verifies and finalizes once. |
| T7 | DB finalization failure | Revision/head/binding roll back; candidate remains recoverable. |
| T8 | Competing executions | Only one active execution/finalizer may win; no silent writer. |
| T9 | Current-head CAS loss | Loser is `SUPERSEDED`; no loser revision/binding. |
| T10 | Checksum mismatch | Fail closed; no finalization or replacement upload. |
| T11 | Temporary storage outage | Durable recoverable state; no automatic provider write retry. |
| T12 | Orphan cleanup | Only eligible unbound terminal candidate can expire/delete. |
| T13 | Idempotent recovery | Repeated recovery returns the same durable result and IDs. |
| T14 | Finalize replay | Database constraints/service return exactly one revision per intent. |

The PostgreSQL concurrency test uses independent sessions and a barrier. Both candidates start from
the same head; winner advances `N -> N+1`; loser cannot create another authoritative `N+1`, change the
winner or bind its candidate.

## Stop conditions

Stop rather than weaken the invariant if:

- the accepted contract conflicts with a canonical model in a way this plan does not resolve;
- CurrentHead CAS or one-intent/one-revision cannot be proven;
- any T1–T14 scenario remains red;
- implementation requires a new accepted ADR semantic, cloud credential/request, real customer data,
  production migration/provider selection, OneDrive write, PR-08, deployment or release.

## Deliverables

- provider-neutral port and result types;
- normalized local persistence/migration;
- deterministic fake and bounded application service;
- automated T1–T14 plus PostgreSQL CAS evidence;
- synchronized contract/recovery matrix and acceptance state;
- independent review record and verification report;
- next-gate recommendation without opening the S3 spike.

## Closeout evidence

- Implementation commits: `e9d87ad` (port, persistence, migration and service) and `101e60e`
  (T1–T14 tests).
- CI compatibility correction: `2641e41` updates the older prior-head parity fixture to drop the
  new storage tables before their document parents.
- GitHub CI run `293` on `2641e41939a04c4278709f6dc072e06bf52a68dc`: all jobs passed.
- Backend evidence: `1542 passed`; the deterministic fake suite passed `19/19` and the PostgreSQL
  suite passed `4/4`, including concurrent T8, CAS-loss T9, finalize replay T14 and Alembic
  upgrade/downgrade/upgrade.
- Static and operational gates passed: Ruff, committed-whitespace, Alembic upgrade, single migration
  head, dependency vulnerability scan, security policy scan, worker and frontend jobs.
- Independent review: DeepSeek v4.1 Flash and Gemini 3.1 Pro High both returned `STATIC READY` on
  the corrected scalar-ID PostgreSQL test harness; DeepSeek also returned `READY` on the parity
  drop-order correction.

The proof is deliberately local/provider-neutral. It does not select a production provider or
residency region, validate SSE-KMS/customer-managed keys, prove `RPO <= 15 minutes` or `RTO <= 4
hours`, authorize production rollout, or open the isolated S3 spike.

## Next gate

Await an explicit Product Owner decision before opening any provider-specific spike. The next gate,
if authorized, is the isolated AWS S3 create-only/checksum experiment already bounded by ADR 0043;
it remains separate from production-provider and residency selection.

## References

- [ADR 0043](../../adr/0043-app-owned-immutable-document-storage.md)
- [Storage contract](../../implementation/VALORA_DOCUMENT_BLOB_STORAGE_CONTRACT.md)
- [Storage policy decision](../../research/pr07-storage-fallback-options-2.md)
- [Completed architecture task](valora-storage-arch-001.md)
