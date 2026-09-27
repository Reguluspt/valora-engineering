# VALORA-STORAGE-ARCH-001 — App-owned immutable document storage

**Status:** COMPLETE — POLICY BASELINE ACCEPTED; LOCAL FAKE VALIDATION AUTHORIZED
**Date:** 2026-09-19
**Runtime authority:** NONE

## Goal

Define and validate app-owned immutable document storage while preserving VALORA
`DocumentRevision` lineage and keeping OneDrive as an external import/read/revalidation/export
integration.

## Authority and constraints

The Product Owner approved the storage direction and policy baseline on 2026-09-19. ADR 0042/D6 and
G3 Option A remain unchanged: the OneDrive direct-write runtime is blocked and C2 research is closed.
This completed architecture task authorizes the next bounded local fake task. It does not authorize a
cloud adapter, provider account, credential, live invocation, production rollout/migration, PR-08,
deployment or release.

Required invariants:

- append-only `DocumentRevision` and immutable historical bytes;
- explicit database-controlled `DocumentRevisionCurrentHead`;
- exact full-object SHA-256 verification;
- no database lock across external I/O;
- no blind provider-write retry;
- no silent conflict winner;
- fail closed on an ambiguous third state;
- one execution intent to at most one finalized revision.

## Scope

1. Draft the successor ADR.
2. Define the narrow `DocumentBlobStore` contract.
3. Define the proposed `StorageObjectBinding` model.
4. Define durable execution-intent persistence and transitions.
5. Define database current-head CAS finalization.
6. Define a deterministic fake-provider model.
7. Define the T1–T14 recovery matrix.
8. Compare Azure Blob Storage and AWS S3.
9. Quantify storage economics and missing workload inputs.
10. Select exactly one provider for a later isolated spike.

## Explicit non-scope

- production or bulk migration;
- a generic multi-cloud/BYO provider framework;
- Dropbox implementation;
- another OneDrive write retry or live experiment;
- PR-07 protected-value/write runtime or migrations;
- PR-08 or later product work;
- deployment or release.

## Work packages and gates

| Work package | Deliverable | State |
|---|---|---|
| WP1 Authority reconciliation | Implemented/proposed inventory and ADR 0042 relationship | COMPLETE |
| WP2 Successor decision | ADR 0043 | COMPLETE — accepted policy baseline |
| WP3 Provider port | Four-operation `DocumentBlobStore` contract | COMPLETE — accepted for local fake |
| WP4 Persistence | Intent, candidate, event/state projection and binding proposal | COMPLETE — accepted for local fake |
| WP5 Finalization/recovery | DB CAS algorithm and T1–T14 matrix | COMPLETE — accepted for local fake |
| WP6 Provider comparison | Azure Blob versus AWS S3 | COMPLETE |
| WP7 Economics | Formula, volume scenarios and required inputs | COMPLETE — rates pending region |
| WP8 Spike selection | AWS S3 isolated spike | SELECTED — not authorized/run |
| G1 Product semantics | Model A export-only | ACCEPTED |
| G2 Retention/deletion | Minimum ten years, legal hold, no ordinary hard delete | ACCEPTED BASELINE |
| G3 Encryption/recovery | VALORA-controlled CMK; RPO <=15m; RTO <=4h | ACCEPTED TARGET |
| G4 Fake validation | Implement and independently review T1–T14 | OPEN AND AUTHORIZED |
| G5 Residency/provider | Production provider and permitted region | OPEN; not selected |
| G6 Provider spike | Separate S3 plan and action-time authority | CLOSED until fake/review pass |
| G7 Production selection | Provider and migration ADR acceptance | CLOSED until spike evidence |

## Accepted policy baseline

- Model A export-only: OneDrive exports are derived artifacts; edits do not change CurrentHead or
  create revisions automatically.
- Finalized valuation revisions retain for at least ten years from the applicable business milestone;
  legal hold blocks purge and there is no ordinary hard delete.
- Any post-retention physical purge is explicit, authorized, audited and policy-driven. Temporary
  candidates use a separate lifecycle policy.
- Production uses server-side encryption with VALORA-controlled customer-managed keys and separate
  production/non-production boundaries. AWS reference architecture uses SSE-KMS.
- Architecture targets `RPO <= 15 minutes` and `RTO <= 4 hours`.
- AWS S3 is the isolated-spike candidate only. Production provider and residency are not selected.

## Fake-provider acceptance matrix

| ID | Scenario | Pass condition |
|---|---|---|
| T1 | Normal create | One exact verified object and one finalized revision. |
| T2 | Duplicate, same checksum | Idempotent observation/finalization; no duplicate effect. |
| T3 | Duplicate, different checksum | Fail closed; no overwrite or revision. |
| T4 | Lost success response | Same-key observation recovers exact object without blind retry. |
| T5 | Crash before create | Intent resumes safely with no phantom provider success. |
| T6 | Crash after create | Existing object verifies and finalizes at most once. |
| T7 | Database finalization failure | No partial revision/head/binding; object remains candidate. |
| T8 | Competing execution | Only one execution advances the head. |
| T9 | Current-head CAS loss | Loser publishes no revision or binding. |
| T10 | Checksum mismatch | `RECONCILIATION_REQUIRED`; no replacement create. |
| T11 | Storage unavailable | Recoverable durable state; no automatic write retry. |
| T12 | Orphan cleanup | Only eligible unbound candidate expires/deletes. |
| T13 | Idempotent recovery | Repeated command returns the same durable outcome. |
| T14 | No duplicate revision | Database constraints and transaction prove one revision/intent. |

## Verification plan for a future implementation task

1. Add migration upgrade/downgrade/upgrade coverage and tenant-isolation constraints.
2. Test every state transition plus illegal transition rejection.
3. Run T1–T14 against a deterministic fake with crash/failure injection.
4. Test concurrent finalization against PostgreSQL, not only an in-memory database.
5. Prove audit/log redaction for credentials, URLs and DOCX content.
6. Run linters, focused backend suites and full affected regression suites.
7. Obtain independent review on exact file hashes before a provider-specific spike.

## Stop conditions

Stop the task and return to the Product Owner if:

- implementation would contradict Model A or the accepted retention/deletion/encryption baseline;
- production provider or residency must be chosen to proceed;
- the provider cannot enforce create-only final object creation;
- the exact checksum cannot settle an ambiguous response;
- the proposed schema cannot prove one intent to at most one revision;
- the requested work expands into migration, production credentials, live provider activity, PR-08,
  deployment or release.

## Completed artifacts

- [ADR 0043](../../adr/0043-app-owned-immutable-document-storage.md)
- [Document Blob Storage contract](../../implementation/VALORA_DOCUMENT_BLOB_STORAGE_CONTRACT.md)
- [Provider selection and economics](../../research/valora-storage-provider-selection.md)
- [PR-07 storage policy decision](../../research/pr07-storage-fallback-options-2.md)

## Next authorized action

Open bounded task `VALORA-STORAGE-FAKE-001` for the smallest local persistence model,
provider-neutral `DocumentBlobStore`, deterministic fake and T1–T14 tests. Use no AWS credential,
request or adapter, no real customer data and no production migration. Do not begin the S3 live spike.
