# VALORA Document Blob Storage contract

**Status:** AMENDED — LOCAL FAKE ACCEPTED; S3 G4 STATIC REVIEW READY; LIVE AWS CLOSED
**Date:** 2026-09-19
**Task:** `VALORA-STORAGE-ARCH-001`
**Authority:** ADR 0043 and accepted `VALORA-STORAGE-FAKE-001`; live provider activity closed

## 1. Purpose and boundary

This contract defines the smallest provider and persistence boundary needed to store one immutable
DOCX object per finalized `DocumentRevision`. It preserves the existing append-only revision model,
makes `DocumentRevisionCurrentHead` the only authority for the current version and incorporates the
accepted Model A and storage-governance baseline.

At the time of the initial draft, the names below were proposals. The current implementation state
is recorded in the table and §8.1; the isolated S3 plan does not make the runtime production-ready.

## 2. Implemented versus proposed

| Capability | State at 2026-09-19 |
|---|---|
| `DocumentRecord`, `DocumentRevision`, `DocumentRevisionCurrentHead` | Implemented |
| `M365RevisionBinding`, Managed Content/Region baselines, revalidation observations | Implemented |
| PR-05/PR-06 OneDrive read/bind/revalidation foundation | Implemented |
| `DocumentBlobStore` port and deterministic fake | Implemented and accepted locally |
| AWS S3 adapter | Implemented and independently reviewed for local preparation; not wired or live-proven |
| Durable document-storage execution intent/state/events | Implemented and accepted locally |
| Candidate object and `StorageObjectBinding` persistence | Implemented and accepted locally |
| PR-07 protected values, conflict/write runtime and migrations | Not implemented; blocked |

## 3. Domain invariants

1. `DocumentRevision` is append-only; finalized bytes never change.
2. `DocumentRevisionCurrentHead` is an explicit pointer changed only by a tenant-safe database CAS.
3. One execution intent finalizes at most one revision.
4. One revision finalized through the app-owned storage flow has exactly one authoritative storage
   binding. Historical PR-05/PR-06 revisions are not backfilled by this task.
5. A physical object is create-only and can bind to at most one finalized revision.
6. The full object SHA-256 and byte length must match before finalization.
7. No database lock spans deterministic generation or provider I/O.
8. No blind retry follows an ambiguous provider result.
9. A checksum mismatch or unexpected object identity fails closed.
10. A losing concurrent execution cannot publish a revision, even if its object exists.

## 4. Provider port

The application owns logical keys, expected checksums and recovery decisions. The adapter owns the
provider protocol and converts provider responses into the bounded result types below.

```python
class DocumentBlobStore(Protocol):
    async def create_immutable(
        self,
        *,
        object_key: str,
        content: AsyncIterable[bytes],
        byte_length: int,
        expected_sha256: str,
    ) -> CreateImmutableResult: ...

    async def observe(self, *, object_key: str) -> ObjectObservation: ...

    async def verify_checksum(
        self,
        *,
        object_key: str,
        expected_sha256: str,
        expected_byte_length: int,
    ) -> ChecksumVerification: ...

    async def delete_uncommitted_or_expire(
        self,
        *,
        object_key: str,
        expected_sha256: str,
    ) -> CleanupResult: ...
```

`content` is server-side only. The initial contract does not issue browser upload URLs, persist a
preauthenticated URL or expose provider credentials to a client.

### 4.1 Result types

`CreateImmutableResult.status` is one of:

- `CREATED`: create-only commit completed for the requested key;
- `ALREADY_EXISTS`: the key already has a committed object; caller must observe and verify it;
- `OUTCOME_UNKNOWN`: the request was dispatched but the commit outcome cannot be classified;
- `UNAVAILABLE`: no safe result is available and the caller must stop;
- `REJECTED`: provider refused a well-formed create-only request.

`ObjectObservation.status` is one of:

- `ABSENT`;
- `PRESENT` with provider object/version identity, byte length and any provider checksum metadata;
- `UNAVAILABLE`;
- `AMBIGUOUS` when identity or metadata cannot be trusted.

`ChecksumVerification.status` is one of:

- `MATCH` after explicit provider checksum proof or a full streamed read and local SHA-256;
- `MISMATCH`;
- `ABSENT`;
- `UNAVAILABLE`;
- `UNVERIFIABLE`.

The adapter must not translate opaque/multipart eTags into SHA-256. It may return the eTag for
diagnostics and conditional provider calls, but the domain accepts success only on `MATCH`.

### 4.2 Create-only behavior

The selected adapter must put the create-only condition on the provider's final object-creation
operation. Staging parts alone does not satisfy the contract. A duplicate-key response is not
automatically success: the caller observes the key and compares exact checksum and size.

Provider `409`, `412`, timeout, disconnect and cancelled response paths remain distinct adapter
observations. Domain recovery depends on object state, not on guessing from an HTTP code.

### 4.3 Cleanup behavior

This primitive is for staged or orphan candidates that never finalized. Cleanup is legal only when
all of these conditions hold:

- no `StorageObjectBinding` refers to the candidate;
- the intent is terminal `SUPERSEDED`, `ABANDONED` or `RECONCILIATION_REQUIRED` under an accepted
  retention rule;
- the object identity and checksum still match the recorded candidate;
- the lifecycle policy permits deletion and no applicable legal hold blocks it;
- the cleanup command is authorized and produces an audit fact.

`delete_uncommitted_or_expire` may schedule provider lifecycle expiry instead of immediate deletion.
It must never delete a finalized revision's object. Finalized objects have no ordinary hard-delete
path; after the minimum retention period, physical purge remains an explicit, authorized, audited and
policy-driven production operation outside this four-primitive fake contract.

## 5. Persistence model

All query-critical values are typed columns. Provider secrets, access tokens, upload URLs and raw
DOCX bytes are forbidden in these tables and in audit/event payloads.

### 5.1 `DocumentStorageExecutionIntent`

Immutable command input recorded before external I/O:

| Column group | Required fields |
|---|---|
| Identity | `id`, `organization_id`, `project_id`, `document_id` |
| Frozen head | `expected_revision_id`, `expected_document_revision`, `expected_content_sha256` |
| Request identity | `idempotency_key`, `request_digest_sha256`, `plan_digest_sha256`, `decision_digest_sha256` |
| Actor | `requested_by_user_id`, `requested_at`, `correlation_id` |

Required constraints:

- unique `(organization_id, idempotency_key)`;
- composite tenant/document foreign key;
- the frozen revision belongs to the same tenant/project/document;
- all SHA-256 values are lowercase 64-character hexadecimal strings.

### 5.2 `DocumentStorageCandidate`

One deterministic output and physical key per intent:

| Column group | Required fields |
|---|---|
| Linkage | `id`, `organization_id`, `execution_intent_id` |
| Provider target | `storage_profile_id`, `provider_kind`, `container_name`, `object_key` |
| Exact output | `content_sha256`, `byte_length`, `media_type` |
| Generation | `generated_at`, `generator_version` |

Required constraints:

- unique `execution_intent_id`;
- unique `(storage_profile_id, container_name, object_key)`;
- immutable after insertion;
- provider kind is a closed value for the selected adapter, not a generic provider registry.

The candidate records no revision ID because the revision does not exist until finalization.

### 5.3 `DocumentStorageExecutionEvent`

Append-only facts provide the durable recovery and audit history:

| Field | Meaning |
|---|---|
| `sequence` | Monotonic per-intent sequence, unique with `execution_intent_id` |
| `event_code` | Closed transition/event value |
| `reason_code` | Typed failure/recovery reason when applicable |
| `provider_request_id` | Optional non-secret provider correlation value |
| `observed_object_version` | Optional opaque provider version identity |
| `observed_content_sha256`, `observed_byte_length` | Verification evidence when known |
| `recorded_at`, `recorded_by_user_id` | Audit actor and time |

Events are never updated or deleted by normal application commands.

### 5.4 `DocumentStorageExecutionState`

This one-row-per-intent projection supports efficient command checks:

- `execution_intent_id` primary key;
- `current_state`;
- `state_version` for optimistic transitions;
- `last_event_sequence`;
- `updated_at`.

Every state update and its corresponding append-only event occur in one database transaction. The
projection can be rebuilt from events. No state is inferred from an absent event.

### 5.5 `StorageObjectBinding`

Inserted only in the successful current-head finalization transaction:

| Column group | Required fields |
|---|---|
| Tenant lineage | `id`, `organization_id`, `project_id`, `document_id`, `document_revision_id` |
| Execution lineage | `execution_intent_id`, `storage_candidate_id` |
| Provider identity | `storage_profile_id`, `provider_kind`, `container_name`, `object_key`, `provider_object_version` |
| Integrity | `checksum_algorithm`, `content_sha256`, `byte_length`, `observed_etag` |
| Proof | `object_created_at`, `verified_at`, `bound_at` |
| Retention snapshot | `retention_policy_code`, `retention_anchor_at`, `minimum_retain_until` |

Required constraints:

- unique `document_revision_id`;
- unique `execution_intent_id` and `storage_candidate_id`;
- unique `(storage_profile_id, container_name, object_key)`;
- composite tenant/document/revision and tenant/intent foreign keys;
- `checksum_algorithm = 'SHA256'` in the first implementation;
- binding checksum equals both the candidate and `DocumentRevision.content_checksum_sha256`;
- binding byte length equals the candidate byte length. Existing `DocumentRevision` has no byte-length
  column, and this task does not add one or backfill historical revisions.

The binding is append-only. Provider identity fields are never edited to point at a replacement
object. For valuation records, `minimum_retain_until` is at least ten years after the applicable
record/release business milestone. Legal hold and later purge actions require their own append-only
policy/audit facts; they do not mutate or erase the binding.

## 6. Execution state machine

Happy-path states are:

```text
PREPARED
  -> CANDIDATE_GENERATED
  -> CREATE_DISPATCHED
  -> OBJECT_OBSERVED
  -> OBJECT_VERIFIED
  -> FINALIZING
  -> FINALIZED
```

Recovery/terminal states are:

| State | Meaning |
|---|---|
| `CREATE_OUTCOME_UNKNOWN` | Create was dispatched; object state must be observed before any repeat. |
| `STORAGE_UNAVAILABLE` | Provider cannot currently be observed; no write is permitted. |
| `RECONCILIATION_REQUIRED` | Present object identity/checksum is a third state or evidence is contradictory. |
| `SUPERSEDED` | Expected current head was lost; candidate cannot be published. |
| `ABANDONED` | Explicit authorized cancellation before publication. |
| `FINALIZED` | Exactly one revision/binding/current-head change committed. |

`CREATE_OUTCOME_UNKNOWN` may transition to `OBJECT_OBSERVED` only after observation. If the exact
object is absent, an explicit recovery command may append a new `CREATE_DISPATCHED` event for the same
intent/key. That is reconciled idempotent recovery, not an unbounded automatic retry.

## 7. Database CAS finalization

All provider I/O has completed before this short transaction begins:

```sql
BEGIN;

-- Short database lock only; no provider call follows inside this transaction.
SELECT current_revision_id, document_revision
FROM document_revision_current_heads
WHERE organization_id = :organization_id
  AND project_id = :project_id
  AND document_id = :document_id
FOR UPDATE;

-- Application verifies exact equality with the intent's frozen head.
-- On mismatch: ROLLBACK, append SUPERSEDED in a separate transition.

INSERT INTO document_revisions (..., document_revision, content_checksum_sha256, ...)
VALUES (..., :expected_document_revision + 1, :candidate_sha256, ...);

INSERT INTO storage_object_bindings (..., document_revision_id, execution_intent_id, ...)
VALUES (..., :new_revision_id, :intent_id, ...);

UPDATE document_revision_current_heads
SET current_revision_id = :new_revision_id,
    document_revision = :expected_document_revision + 1
WHERE organization_id = :organization_id
  AND project_id = :project_id
  AND document_id = :document_id
  AND current_revision_id = :expected_revision_id
  AND document_revision = :expected_document_revision;

-- Require exactly one updated row. Unique conflicts or zero rows mean CAS loss.
-- Insert baselines, audit and FINALIZED event/state in the same transaction.

COMMIT;
```

Any error rolls back the new revision, binding, pointer and finalized event together. The already
created object remains an uncommitted candidate and is reconciled by the intent workflow.

## 8. Recovery matrix and required fake-provider scenarios

| Test | Stimulus | Required durable result |
|---|---|---|
| T1 | Normal create | Exact object verified; one revision/binding published. |
| T2 | Duplicate request, same checksum | Existing exact object reused; still one revision. |
| T3 | Duplicate request, different checksum | `RECONCILIATION_REQUIRED`; no revision. |
| T4 | Lost success response | Observe same key; matching object continues without a blind write. |
| T5 | Crash before create | Resume from intent/candidate; no object and no revision. |
| T6 | Crash after create | Observe/verify existing object, then finalize once. |
| T7 | Database finalization failure | No partial revision/head/binding; candidate remains recoverable. |
| T8 | Two executions from one head | At most one finalizes; loser is `SUPERSEDED`. |
| T9 | Current-head CAS loss | Entire finalize transaction rolls back; no published loser revision. |
| T10 | Checksum mismatch | Fail closed; no finalization or replacement upload. |
| T11 | Storage unavailable | Durable recoverable state; no provider write retry. |
| T12 | Orphan cleanup | Only unbound exact candidate expires/deletes under policy. |
| T13 | Repeated recovery command | Same terminal result and identifiers; no duplicate effects. |
| T14 | Replayed finalize | Unique intent/revision constraints prove no duplicate revision. |

The fake must allow deterministic injection before/after create, during observation, during streamed
verification and before/after database commit. It must model `ABSENT`, exact `PRESENT`, mismatched
`PRESENT`, unavailable and lost-response outcomes independently.

### 8.1 Local fake acceptance evidence

`VALORA-STORAGE-FAKE-001` completed on 2026-09-19 at commit
`2641e41939a04c4278709f6dc072e06bf52a68dc`. GitHub CI run `293` passed all jobs with `1542`
backend tests. The deterministic fake suite passed `19/19`; PostgreSQL passed `4/4`, covering T8,
T9, T14 and the migration roundtrip. DeepSeek v4.1 Flash and Gemini 3.1 Pro High independently
reviewed the corrected PostgreSQL harness as `STATIC READY`.

This evidence accepts only the provider-neutral local fake and persistence/CAS model. Production
provider, residency, encryption operations, backup/restore and recovery objectives remain
unverified future gates.

### 8.2 Local AWS S3 adapter evidence

`VALORA-STORAGE-S3-SPIKE-001` G2/G3 prepared one isolated adapter without changing the database
schema, `provider_kind` constraint or production service wiring. The adapter:

- sends `IfNoneMatch="*"` on `PutObject` and `CompleteMultipartUpload`;
- constructs botocore with `total_max_attempts = 1` and has no caller write retry;
- maps `412` to existing-object observation and maps `409` or unreadable/lost responses to an
  unknown outcome;
- treats ETag as opaque and verifies both upload modes by streamed `GetObject`, local SHA-256 and
  exact byte length;
- rejects out-of-prefix or checksum-mismatched cleanup and relies on the application service's
  existing finalized-binding guard.

Local evidence used Python `3.14.7`, boto3 `1.43.89` and botocore `1.43.89`. Adapter plus T1–T14
passed `42/42`; the affected storage/document/M365 selection passed `145` with `11` PostgreSQL-only
local skips. DeepSeek v4.1 Flash and Gemini 3.1 Pro High both returned `READY` with no P0–P2 finding
on the corrected exact code hashes. Pushed commit `5f3ab7f6e159aec9cc84aaa24ed04445cbb1215f`
passed GitHub CI run `35448475149` on attempt 2; backend passed `1565` tests with PostgreSQL and
MinIO available. No AWS credential, endpoint or live request was used. Production provider,
residency and production encryption operations remain unselected. The G4 packet freezes only the
isolated spike's intended non-production boundary; every actual AWS value still requires the
documented action-time verification and G5 approval.

## 9. Security and operational constraints

- Provider calls run server-side with a workload identity or secret-manager-held credential.
- Permissions are scoped to the chosen container/bucket and required object operations.
- Logs/audit store only opaque key, checksum, size, provider request ID and classified outcome.
- DOCX bytes, access tokens, account keys and preauthenticated URLs are never logged.
- Encryption at rest and in transit is mandatory. Production uses server-side encryption with a
  VALORA-controlled customer-managed key; the AWS reference is SSE-KMS with a customer-managed KMS
  key.
- Production and non-production have separate storage and key boundaries. Per-tenant keys are not
  required by this task.
- Object download authorization must pass the same tenant/project/document checks as revision reads.
- Finalized valuation revisions are retained for at least ten years; active legal hold overrides
  expiry, and ordinary hard delete is forbidden.
- Production recovery targets are `RPO <= 15 minutes` and `RTO <= 4 hours`. The fake implementation
  proves no operational backup or restore claim.
- Production provider and residency remain unselected release gates. Fake tests use no cloud
  credential, request or real customer data.

## 10. Stop conditions

Stop and return to architecture review if:

- the provider cannot enforce create-only semantics at final object commit;
- exact full-object checksum cannot be proved after an ambiguous response;
- a provider-specific limitation requires mutable replacement of a finalized revision object;
- the persistence model cannot prove one intent to at most one finalized revision;
- cleanup could delete a finalized or legally retained object;
- the implementation would introduce a live provider, production migration or real customer data;
- production-provider or residency selection is required before those decisions are accepted;
- any flow treats an exported Model A OneDrive copy as authoritative or automatically re-imports it.

## 11. References

- [ADR 0043](../adr/0043-app-owned-immutable-document-storage.md)
- [Provider comparison](../research/valora-storage-provider-selection.md)
- [Completed architecture plan](../plan/done/valora-storage-arch-001.md)
- [Completed local fake plan](../plan/done/valora-storage-fake-001.md)
- [Existing document models](../../backend/app/modules/document_workspace/models.py)
- [Existing M365 models](../../backend/app/modules/m365_integration/models.py)
