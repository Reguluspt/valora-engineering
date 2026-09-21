# ADR 0043 — App-owned immutable document storage

**Status:** AMENDED — LOCAL VPS G6 ACCEPTED; G8 OFFLINE EXCHANGE COMPLETE
**Date:** 2026-09-20
**Task:** `VALORA-STORAGE-ARCH-001`

## Context

PR-05 and PR-06 implemented a OneDrive Personal read/bind/revalidation foundation. PR-07 then
investigated direct replacement of the bound OneDrive file. The bounded `C2_AUTO_V2` observation
preserved concurrent bytes but returned an undocumented `404 itemNotFound` at the stale final
fragment. It did not prove the final-commit compare-and-set guarantee required by ADR 0042/D6.

The Product Owner has approved a new direction: VALORA will own the authoritative DOCX bytes for
each document revision in immutable object storage. OneDrive remains an external integration for
import, read, revalidation, a user working copy and export. This direction does not turn the proposed
storage runtime into an implemented capability and does not reopen the original OneDrive write path.

The repository already contains these relevant capabilities:

- append-only `DocumentRevision` records and an explicit `DocumentRevisionCurrentHead`;
- immutable `M365RevisionBinding`, Managed Content/Region baselines and revalidation observations;
- checksum and tenant-safe lineage primitives.

At this ADR's initial acceptance, the repository did not yet contain `DocumentBlobStore`, storage
execution-intent persistence, `StorageObjectBinding`, a storage provider adapter or PR-07
write/conflict runtime. The current implementation/authority state is recorded in the gate record
and dated amendment below.

## Decision

The following decisions are the accepted architecture and policy baseline. Initial authority covered
only the bounded provider-neutral fake; the dated amendment below now opens local S3 adapter
preparation. Production runtime, migration of existing documents and live-provider activity remain
closed.

### D1. VALORA database owns current-version authority

`DocumentRecord`, append-only `DocumentRevision` and `DocumentRevisionCurrentHead` are the business
source of truth. An object-store listing, filename, modification time, provider version or OneDrive
state must never select the current VALORA revision.

### D2. One immutable object stores the exact bytes of each finalized revision

Every successfully finalized content change creates a new object. A finalized revision's object is
never overwritten in place. The object is verified against the expected full-content SHA-256 before
the database may publish the revision as current.

Object keys are opaque, server-owned identifiers derived from stable tenant/document/intent inputs.
They are not user-authored paths or mutable filenames. The exact physical key layout is an adapter
detail and must not become a business identifier.

### D3. Use one narrow `DocumentBlobStore` port

The first implementation exposes only the required primitives:

- `create_immutable`;
- `observe`;
- `verify_checksum`;
- `delete_uncommitted_or_expire`.

This is a domain port for the selected provider, not a generic bring-your-own-storage framework.
Provider-specific identity, checksum and conditional-create results remain explicit at the adapter
boundary.

### D4. Persist a durable execution intent before external I/O

An immutable intent freezes the tenant, document, expected current revision, idempotency key,
request/decision digests and actor. Deterministic DOCX generation records one candidate object key,
full checksum and byte length for that intent. State transitions are append-only events with a
queryable current-state projection.

One execution intent may finalize at most one `DocumentRevision`. Retrying recovery uses the same
intent and object key; it never invents a new write after an ambiguous response.

### D5. External object creation and database publication are separate phases

The target flow is:

```text
preview and validate
  -> persist intent
  -> generate deterministic DOCX and SHA-256
  -> create immutable object
  -> observe and verify the exact bytes
  -> short database compare-and-set transaction
  -> insert DocumentRevision N+1 and StorageObjectBinding
  -> move CurrentHead from N to N+1
  -> seal baseline and audit
  -> FINALIZED
```

No database lock is held during generation, upload, observation or checksum verification. The final
database transaction may hold a short row lock while it checks and changes the current-head pointer.

### D6. Current-head compare-and-set decides concurrency

Finalization requires the current head to equal the revision frozen by the intent. Two competing
executions may create different candidate objects, but only one can advance that pointer. A losing
transaction creates no published revision or binding; its candidate object is retained temporarily
as an uncommitted orphan and is then removed or expired under policy.

There is no silent conflict winner and no provider object becomes authoritative merely because it
was uploaded first.

### D7. Lost responses are reconciled without blind retry

After an unknown create outcome, VALORA observes the same immutable key:

| Observation | Required action |
|---|---|
| Object absent | A recovery command may repeat create with the same intent/key. |
| Object present with exact checksum and size | Continue verification/finalization idempotently. |
| Object present with different checksum or unverifiable identity | Fail closed as `RECONCILIATION_REQUIRED`. |
| Provider unavailable or observation ambiguous | Keep the intent recoverable; do not write again. |

An eTag is opaque metadata and is not full-content SHA-256 proof unless the selected provider
explicitly documents that equivalence for the exact upload mode.

### D8. OneDrive is an external integration, not the authoritative mutable store

The PR-05/PR-06 `Files.Read` foundation remains useful for import, read, baseline and revalidation.
The accepted interaction is **Model A — export-only**. An exported OneDrive file is a derived
artifact/external working copy. Edits to it do not automatically change VALORA CurrentHead, create a
`DocumentRevision` or start implicit bidirectional sync. Explicit import/revalidation of an external
edit is a future capability outside this task. Microsoft clarification may still be monitored, but
the storage roadmap does not depend on it.

ADR 0042/D6 remains unchanged. It continues to govern any future proposal to replace an existing
OneDrive item directly. This ADR succeeds the direct-write path as the primary PR-07 roadmap; it
does not reinterpret the inconclusive C2 observation as provider conformance.

### D9. Retention, deletion and legal hold are policy-driven

Finalized document revisions for valuation records have a minimum retention period of ten years from
the applicable record/release business milestone. The governing retention policy supplies that
milestone; object creation time does not invent it.

Finalized revisions have no ordinary hard-delete path. A physical purge after retention must be
explicit, authorized, audited and policy-driven, and an active legal hold prevents it. Temporary
staged or orphan candidate objects use a separate lifecycle policy because they were never
finalized. The architecture must not encode every object as “keep forever.”

### D10. Encryption and recovery targets are production requirements

Production storage uses server-side encryption with customer-managed keys under VALORA-controlled
key ownership. The AWS reference shape is SSE-KMS with a customer-managed KMS key. Production and
non-production use separate storage and key boundaries; per-tenant keys are not required by this
task.

The architecture targets `RPO <= 15 minutes` and `RTO <= 4 hours`. The local fake task must not claim
that these targets are operationally met; backup, replication and restore evidence belong to later
production-provider and operations gates.

Production provider and permitted residency region are not selected. No real customer document or
valuation record may be uploaded during local fake validation or an isolated technical spike.

### D11. Validate one provider before broad abstraction

The initial architecture comparison selects AWS S3 for an isolated spike because its official
contract explicitly supports create-only `If-None-Match: *` on both `PutObject` and
`CompleteMultipartUpload`, including defined concurrent outcomes and enforceable bucket policy.
This is a future technical-spike selection, not a production-provider or residency decision. The
spike remains closed until the provider-neutral T1–T14 matrix and independent review pass.

Azure Blob Storage remains the second candidate because `Put Block List` provides a staged final
commit, conditional headers and strong managed-identity integration. Production selection remains
blocked on residency, operations, account ownership, cost and spike evidence; the accepted
encryption and recovery targets constrain whichever provider is later selected.

### D12. Current-phase VPS storage and two independent OneDrive roles

For development, test, pilot and the current small single-user deployment phase, the Product Owner
selected app-owned local immutable blob storage on the VALORA VPS. PostgreSQL remains authoritative
for revisions, CurrentHead and storage execution/binding state; the local provider holds the exact
authoritative revision bytes behind the unchanged `DocumentBlobStore` port.

OneDrive Personal is never authoritative and is not a required dependency for verified local reads.
It has two independent, explicitly separated roles:

- **Exchange:** `VALORA/Exchange/Inbox`, `Working` and `Exports` hold mutable external files for
  explicit import, Word/Excel editing and export. A Save changes only the OneDrive file. Creating a
  new `DocumentRevision` requires an explicit VALORA import/re-import command that stores exact bytes
  in the app-owned blob store and wins the existing CurrentHead CAS.
- **Backup:** `VALORA/Backup/<deployment-id>` receives only encrypted repository data covering valid
  PostgreSQL dumps and authoritative blobs. Backup content is not browsed as working documents and
  Exchange content is not evidence of backup.

Exchange or Backup authentication/transport failure must not break authoritative reads or unrelated
VALORA business transactions.

This phase does not satisfy or replace D10's future production encryption/recovery requirements. A
single VPS is one failure domain and local filesystem immutability is not hardware WORM. The AWS
adapter and G1-G4 static evidence remain future references, but AWS G5/G6 are deferred and provide no
live provider or production-selection claim.

## Exchange policy

The Product Owner retains Model A authority semantics while authorizing a separately gated Exchange
workflow. Inbox import and Working re-import are explicit VALORA mutations; Export and Word/Excel
Save are not. OneDrive rename, move, edit or deletion cannot mutate authoritative bytes or
CurrentHead. No automatic sync or save-triggered revision is authorized.

## Required architecture validation

The fake provider and service model must pass all fourteen scenarios before provider selection can
advance:

`T1` normal create; `T2` duplicate/same checksum; `T3` duplicate/different checksum; `T4` lost
success response; `T5` crash before create; `T6` crash after create; `T7` database finalization
failure; `T8` competing execution; `T9` current-head CAS loss; `T10` checksum mismatch; `T11`
temporary storage outage; `T12` orphan cleanup; `T13` idempotent recovery; `T14` no duplicate
`DocumentRevision`.

Passing the fake does not authorize a live provider spike. The spike requires a separate bounded
plan, credentials/account boundary, cleanup plan and action-time approval.

## Safe degraded mode

While this ADR remains at draft/detail-gate status, VALORA may retain OneDrive `Files.Read` and the
implemented import/read/baseline/revalidation capabilities. A manual download-and-replace workflow
may be researched, but it must not be described as implemented until its UI/runtime exists.

## Consequences

- Authoritative concurrency moves from undocumented OneDrive final-commit behavior to a VALORA
  database compare-and-set.
- The application assumes custody obligations for official DOCX bytes, retention and recovery.
- Storage can accumulate uncommitted candidates; lifecycle and audit make that state explicit.
- Export preserves Microsoft ecosystem interoperability without making a mutable copy authoritative.
- Existing OneDrive research and ADR 0042 remain valid historical evidence.

## Rejected alternatives

### Continue searching for OneDrive Personal write workarounds

Rejected as the roadmap. It does not provide the contractual production invariant and would keep the
core release path dependent on unresolved provider behavior.

### Treat the observed `404 itemNotFound` as equivalent to `412`

Rejected by G3 Option A. The tested run was safe, but the response has no documented stale-commit
meaning for the exact flow.

### Build a generic multi-cloud or BYO storage framework now

Rejected for this task. It multiplies credential, recovery and conformance surfaces before one
adapter has proved the domain contract.

### Hold a database transaction open during upload

Rejected. It cannot roll back an external object and creates unnecessary lock contention.

## Gate record

| Gate | Owner | Current state |
|---|---|---|
| Exchange semantics | Product Owner | ACCEPTED — Inbox/Working/Exports are non-authoritative; import/re-import is explicit |
| Retention and legal hold | Product Owner | ACCEPTED — minimum ten years plus legal hold |
| Finalized-revision deletion | Product Owner | ACCEPTED — no ordinary hard delete; audited policy purge only |
| Encryption/key ownership | Product Owner | ACCEPTED TARGET — server-side, VALORA-controlled customer-managed key |
| Recovery objectives | Product Owner | ACCEPTED TARGET — RPO <= 15 minutes; RTO <= 4 hours |
| Provider-neutral fake T1–T14 | Engineering | ACCEPTED — local proof and independent review passed |
| Production residency and provider | Architecture/Product Owner | OPEN; not selected |
| S3 isolated-spike plan and account boundary | Product Owner/Engineering | G1-G4 complete/static evidence retained; G5 live AWS NOT RUN; closed/deferred by Product Owner before invocation |
| Current pilot provider | Product Owner/Engineering | LOCAL FILESYSTEM selected; G6 accepted on exact reviewed Linux/PostgreSQL snapshot |
| OneDrive Exchange | Product Owner/Engineering | G8 offline implementation complete; OneDrive remains non-authoritative; live AppFolder conformance/reconsent is separately gated |
| Off-site backup transport | Product Owner/Engineering | Separate encrypted Backup namespace selected; implementation/live OAuth not yet accepted |
| Production provider selection | Architecture/Product Owner | NOT RUN; no AWS production-provider claim |

## Owner decision record

On 2026-09-19, the Product Owner approved the app-owned immutable-storage direction. The Product
Owner then accepted Model A, the retention/deletion/encryption baseline and the RPO/RTO targets, and
authorized `VALORA-STORAGE-FAKE-001`. This authority covers only the smallest local persistence,
provider-neutral fake and T1–T14 validation needed to prove the contract. It does not authorize AWS
credentials or requests, a production provider or residency decision, real customer data, a
production rollout/migration, PR-08, deployment or release.

On 2026-09-20, the Product Owner selected the current VPS pilot path: local authoritative immutable
blobs plus two separate non-authoritative OneDrive Personal roles, Exchange and encrypted Backup.
The decision closed/deferred AWS before G5, retained all G1-G4 evidence and opened
`VALORA-STORAGE-LOCAL-001`; Exchange and Backup remain later independent gates. It does not authorize
live OneDrive OAuth, deployment or production claims.

## Amendments

- 2026-09-19 · D11 / Gate record: the provider-neutral fake, PostgreSQL CAS tests, T1–T14 and
  independent review passed. The Product Owner then opened the separate bounded
  `VALORA-STORAGE-S3-SPIKE-001` plan. Local adapter preparation is authorized; credentials,
  AWS resources/requests/cost, real customer data and production-provider or residency selection
  remain closed. A live invocation requires the exact reviewed commit, a frozen non-production
  account/bucket/identity boundary, a cleanup manifest and separate action-time approval.
- 2026-09-19 · D3/D7/D11 / Gate record: the AWS S3 adapter is locally prepared behind the unchanged
  four-operation port. Deterministic boto3/botocore request-shape and failure tests prove
  conditional single/multipart final creation, one-attempt SDK behavior, streamed SHA-256/length
  verification and bounded cleanup. DeepSeek and Gemini returned `READY` on the exact code hashes.
  Commit `5f3ab7f6e159aec9cc84aaa24ed04445cbb1215f` was pushed and GitHub CI run `35448475149`
  passed on attempt 2. G4 later froze an intended boundary and action-time checks without contacting
  AWS; this remains non-live evidence and does not authorize G5.
- 2026-09-20 · D10-D12 / Gate record: the Product Owner changed the current deployment path before
  any live AWS invocation. G1-G4 static/provider preparation evidence is retained; G5 and G6 were
  not run, no live AWS conformance or provider-selection claim exists, and AWS remains a future
  adapter/reference. The current pilot path is app-owned local immutable blobs on the VPS, with
  separately gated OneDrive Exchange and encrypted Backup roles. Neither role is authoritative and
  neither may be confused with the other. The single VPS is not HA/WORM and the long-term RPO/RTO
  targets remain unproven.

### 2026-09-21 gate reconciliation

- `VALORA-STORAGE-LOCAL-001` G6 is accepted. Exact reviewed snapshot:
  `d71a42e575f96d7cd8d9aac6c8aab2c60627c32f`; durable closeout manifest is retained in
  `docs/implementation/VALORA_STORAGE_LOCAL_G6_CLOSEOUT_MANIFEST.json`.
- `VALORA-ONEDRIVE-EXCHANGE-001` G8 is complete offline at code milestone `f896f15…`.
- ADR 0045 governs the newer Working-copy observation/review/human-confirmed revision boundary.
  Nothing in G6/G8 authorizes Word Save/provider notification to create a revision automatically.
- Production residency/provider, long-term RPO/RTO, encrypted off-site Backup and live AppFolder
  conformance remain separate/open gates.

## References

- [ADR 0040](0040-onedrive-delegated-integration-and-file-binding.md)
- [ADR 0041](0041-onedrive-personal-return-revalidation-observations.md)
- [ADR 0042](0042-onedrive-personal-protected-values-and-sync-write-transactions.md)
- [Storage contract](../implementation/VALORA_DOCUMENT_BLOB_STORAGE_CONTRACT.md)
- [Provider comparison](../research/valora-storage-provider-selection.md)
- [Completed architecture task](../plan/done/valora-storage-arch-001.md)
- [PR-07 storage policy decision](../research/pr07-storage-fallback-options-2.md)
