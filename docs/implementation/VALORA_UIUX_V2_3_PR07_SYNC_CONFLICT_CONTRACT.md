# VALORA UI/UX v2.3 — PR-07 Sync/Conflict Implementation Contract

**Task:** `VALORA-PR07-CONTRACT-001` **Status:** ACCEPTED BY PRODUCT OWNER **Date:** 2026-09-13 **Authority:** accepted ADR 0042, accepted ADRs 0040–0041, and UI/UX v2.3 Document Sync Version plus Bulk Sync Preview/Conflict/Confirm/Result addenda

## Authorization gate

The Product Owner explicitly accepted ADR 0042 and this contract on 2026-09-13. Bounded PR-07
runtime, migrations, UI and separate writer-consent work are authorized. PR-08 work remains gated
until PR-07 acceptance closes; push, merge, deployment and release remain unauthorized.

## Scope

After acceptance, implement the minimum OneDrive Personal sync/conflict slice that:

- enrolls immutable protected values only under historical-content proof;
- builds a bounded, persisted, zero-document-write three-way preview;
- records explicit conflict decisions;
- conditionally updates only selected Managed Regions in the exact bound DOCX;
- creates new immutable VALORA revision/binding/baseline lineage per successful document;
- recovers safely when Graph and database outcomes are uncertain;
- returns per-document bulk results without false all-or-nothing claims.

No release/publish implementation, generic template authoring UI, Word editor, SharePoint, OneDrive for
Business, application permission, file creation, rename, move, delete, share or restore is in scope.

## Required persistence

Names may follow repository conventions, but the implemented schema must preserve these aggregates
and invariants.

### Protected baseline values

`M365ProtectedRegionValue` is immutable and unique by organization + content baseline + region key.
It contains exact tenant/project/document/revision/binding/baseline lineage, ordered region identity,
semantic and normalization contracts, AEAD ciphertext/nonce/key version/AAD version, tenant-bound
HMAC value identity/key version, creator and creation time.

Database checks and composite foreign keys prevent cross-tenant lineage, blank contracts, malformed
key versions and duplicate regions. Product commands never update or delete a protected value.

### Server-owned sync mapping

`M365ManagedRegionSyncMapping` is immutable for one active Template Version and manifest digest. Each
entry binds one stable region key to one canonical Workbench snapshot selector and output formatter.
The mapping's ordered canonical digest participates in plans, idempotency and baselines. Unknown,
duplicate, client-supplied or incompatible mappings fail `SYNC_MAPPING_REQUIRED` before provider I/O.

### Sync plan aggregate

`M365SyncPlan` owns immutable `M365SyncPlanRevision` records and bounded document/region children. It
stores stable lineage/digests and encrypted comparison values, not unrestricted Word text.

Each plan revision includes:

- organization/project/actor and one canonical source Data Snapshot ID/digest;
- exact document/current revision/binding/baseline/template/mapping lineage;
- observed drive/item ID, eTag, content checksum and fingerprint contracts;
- ordered `O/V/W` protected identities and comparison outcome per region;
- selection, Warning/Blocking facts, explicit conflict decisions and expected output classification;
- row version, canonical plan digest, creation/expiry time and superseded/ready/consumed state.

Editing selection or conflict decisions appends a new plan revision. No revision number for a future
Document Revision is reserved by preview.

### Execution and result aggregates

`M365SyncBatchExecution` owns one `M365SyncDocumentExecution` per document. A document execution keeps
the idempotency/request digest, frozen plan revision, pre-write identity/eTag/checksum, deterministic
expected output checksum, provider observation, terminal result, recovery code and timestamps.

Allowed operational states are:

```text
PREPARED
PROVIDER_COMMITTING
PROVIDER_COMMITTED
FINALIZED
FAILED_NO_WRITE
RECONCILIATION_REQUIRED
```

State transitions are compare-and-set and auditable. At most one active execution exists per tenant
and document. `FINALIZED` requires a resulting Document Revision, immutable binding and sealed digest
plus protected-value baseline. `FAILED_NO_WRITE` requires proof that provider bytes remain the exact
pre-write bytes. Ambiguous state can only be `RECONCILIATION_REQUIRED`.

## Protected-value enrollment

New canonical revisions create protected values with their binding/baseline. For an existing PR-06
baseline, enrollment accepts only document ID, expected revision/binding/baseline and idempotency key.
The client cannot submit values or proof fields.

The service may enroll when either:

1. current exact provider bytes match the immutable baseline checksum and all fingerprints; or
2. a retained OneDrive version is read by stable version identity and its exact bytes match the
   baseline checksum and all fingerprints.

The parser extracts only declared Managed Regions, normalizes them under the baseline contracts and
encrypts the typed values. A current changed file without an exact historical proof is blocked. The
enrollment transaction rechecks all lineage and appends a sanitized audit event atomically.

## Preview contract

### Inputs

- project ID;
- bounded ordered document IDs or an authorized server-side group selector;
- source Data Snapshot reference/current authoritative project revision;
- explicit idempotency key.

No raw source values, Word values, locators, provider facts, classifications, decisions or readiness
facts are accepted from the client.

### Pre-provider gate

Before OAuth or Graph access, require active actor/organization, `project:read`, tenant-owned documents,
current canonical heads, immutable bindings/baselines/protected values, active templates and exact sync
mappings. Require read-capable actor-owned OneDrive Personal connections. Reject published/release
protection unknowns, in-flight executions and unsupported contracts without provider access.

### Provider phase

Without a database lock, read metadata and bounded DOCX bytes for each exact bound item. Reuse PR-06
package/parser safeguards. Verify identity, metadata/content consistency, current-head baseline and
outside/managed fingerprints. Freeze `W`; build `V` from the canonical server snapshot; load `O` only
through the protected-value service; normalize all three under one contract.

Provider, parser, mapping or decryption failure is Blocking. It cannot become no-change.

### Plan commit

In a short transaction, recheck permission, current heads, bindings/baselines, mapping and source
snapshot authority. Append the exact plan revision and `M365_SYNC_PLAN_CREATED` audit atomically.
Same key/same digest returns the same plan without another provider call. Conflicting key reuse is
`409 idempotency_key_reused`.

Preview writes only plan/audit persistence. It performs no Graph write, Document Revision creation,
current-head mutation or business-data mutation.

## Conflict decision contract

Conflict detail returns the three typed display values only to an authorized project user, with
`Cache-Control: no-store`; secrets and unrestricted document content remain absent.

Updating decisions requires `project:update`, exact plan revision/row version and one explicit choice
per addressed conflict:

- `USE_VALORA`: write normalized/formatted `V` into the region at execution;
- `KEEP_WORD`: leave `W` untouched and record an acknowledged divergence outcome;
- `SKIP_THIS_SYNC`: leave `W` untouched and keep the region marked for later review/update.

No choice is preselected by the server. Every required conflict must be resolved before a ready plan
can be confirmed. Decision changes append a new plan revision and audit stable IDs/digests only.

## Confirmation and execution contract

### Confirmation gate

Require `project:update`, exact ready plan revision/digest/row version and a batch idempotency key.
Before provider work, re-evaluate permissions, source snapshot, current heads, release protection,
connections, template/mapping contracts, Blocking count and conflict completion. Any mismatch returns
`SYNC_PLAN_STALE` or the narrower recovery code.

### Per-document pre-write phase

For each selected document, one at a time:

1. reread exact metadata and bytes;
2. require plan drive/item identity, eTag, checksum and `W` fingerprints;
3. deterministically patch only selected `USE_VALORA` or non-conflicting VALORA-change regions;
4. prove outside-managed digest preservation and untouched-region equality;
5. parse output and prove expected protected identities;
6. calculate deterministic output checksum;
7. persist `PREPARED` intent and sanitized audit in one short transaction.

If output equals input, return `UNCHANGED` and create no intent that can write, no revision and no M365
version claim.

### Provider commit

Execution requires server-verified delegated OneDrive Personal `Files.ReadWrite`. The adapter updates
only the exact bound item through a v1.0 upload session using `deferCommit: true`, conflict behavior
`fail`, and the frozen `If-Match` precondition. It rereads identity/eTag immediately before final
commit and applies the precondition again. `412`, identity drift or a content race produces stale-plan
behavior and no blind retry.

The exact write mechanism cannot ship until live provider conformance proves conditional final commit
for OneDrive Personal. Upload URLs and tokens remain inside the provider adapter and are never
persisted or logged.

### Verification and finalization

After commit, read exact current metadata and bytes. Require expected checksum, unchanged outside
digest, expected region values and the same stable item identity. Then one short transaction rechecks
tenant/permission/current-head/plan/execution protection and atomically creates:

```text
RenderJob / GeneratedDocument lineage
→ DocumentRevision N+1
→ current head N+1
→ immutable M365RevisionBinding
→ digest M365ManagedContentBaseline + region rows
→ protected Managed Region values + per-region outcomes
→ finalized execution/result + sanitized audit
```

The resulting Data Snapshot is the exact frozen authoritative snapshot used for `V`. The resulting
DOCX checksum is the exact provider-verified byte checksum. VALORA revision and Microsoft 365 version
remain separate lineage fields.

No database lock spans Graph I/O. Any finalization failure leaves the durable intent recoverable and
blocks a second writer.

## Uncertain-write recovery

Recovery always uses the original execution intent and exact item identity:

| Current provider proof | Recovery |
| --- | --- |
| checksum/fingerprints equal expected output | finalize once without another write |
| checksum/eTag equal exact pre-write state | regenerate deterministic output and retry same intent conditionally |
| missing access, parser failure or any third state | mark/retain `RECONCILIATION_REQUIRED`; block sync and release |

An operator can request re-observation but cannot mark success manually. Recovery uses no new
idempotency key, never creates duplicate revisions and does not infer success from a Graph version ID
or changed eTag alone.

## Bulk semantics

- Preflight blocks starting a batch when any selected item has known Blocking facts.
- Once execution starts, each document is its own provider/finalization unit.
- A later failure does not rewrite successful files back to old bytes.
- Batch result counts and lists `SYNCED`, `UNCHANGED`, `SKIPPED` and
  `FAILED_REQUIRES_ACTION` per document.
- Only `SYNCED` creates a new revision and provider-version observation.
- Retry creates a fresh preview unless uncertain-write recovery can settle the original intent.
- A batch with any failure is never labeled wholly successful.

## API boundary

After acceptance, the bounded API may expose:

```text
POST /api/v1/m365/onedrive/projects/{project_id}/sync-plans
GET  /api/v1/m365/onedrive/projects/{project_id}/sync-plans/{plan_id}
PUT  /api/v1/m365/onedrive/projects/{project_id}/sync-plans/{plan_id}/decisions
POST /api/v1/m365/onedrive/projects/{project_id}/sync-plans/{plan_id}/confirm
GET  /api/v1/m365/onedrive/projects/{project_id}/sync-executions/{execution_id}
POST /api/v1/m365/onedrive/projects/{project_id}/sync-executions/{execution_id}/recover
POST /api/v1/m365/onedrive/projects/{project_id}/documents/{document_id}/protected-values/enroll
```

Create/read preview requires `project:read`; decisions, confirm and enrollment require
`project:update`; recovery requires `project:update` and the same tenant authority. Mutation bodies
are strict, CSRF-protected and idempotent. Foreign identifiers use hidden-not-found behavior. The
frontend renders server comparison/classification/readiness facts and never recomputes them.

## Security, privacy and audit

- Separate versioned encryption and HMAC keys; AEAD AAD binds tenant and exact lineage.
- Never return encryption material, HMAC key version internals, token/cache, upload URL or provider
  response body.
- Never log raw `O/V/W`, DOCX bytes, extracted narrative, authorization codes or credentials.
- Conflict value responses are least-data, permission checked and `no-store`.
- Audit contains IDs, digests, counts, decisions, outcomes, reason codes and correlation only.
- All provider URLs are fixed Microsoft endpoints or validated preauthenticated upload URLs consumed
  only by the adapter; no caller-controlled SSRF target.
- DOCX parser limits, XML hardening and relationship restrictions from PR-06 remain mandatory.
- Writer consent is explicit `Files.ReadWrite`; read-only users/connections are never silently
  upgraded.

## Published/release protection

Execution queries a fail-closed document write-policy port before provider I/O and again before
finalization. A locked/published current revision, protected provider artifact, unknown protection
state or unresolved execution returns a blocking code. PR-07 does not mutate or branch a released
artifact. PR-08/PR-09 must provide the durable lock facts consumed by this port before publishing can
exist.

## Required tests and evidence

### Unit and property tests

- typed normalization, missing/null/blank distinctions and cross-contract rejection;
- AEAD AAD/key rotation failure behavior and HMAC non-disclosure;
- full three-way comparison matrix and structural Blocking;
- decision completion and no-default behavior;
- deterministic patch output, outside preservation and untouched-region equality;
- state-machine transition and recovery matrix;
- same-key replay/different-digest rejection.

### API and PostgreSQL tests

- strict input, CSRF, permission and tenant-hiding cases;
- composite tenant foreign keys and append-only protected/plan facts;
- concurrent plan updates, confirmations and one active document execution;
- current-head/source/mapping/eTag stale rejection before write;
- atomic finalization of revision/head/binding/baselines/result/audit;
- injected rollback at every finalization edge;
- published/unknown protection denial before Graph access;
- mixed bulk outcomes without false success.

No skipped PostgreSQL test may be claimed as PASS.

### Fake-provider and live OneDrive Personal acceptance

- `If-Match` stale response produces no write lineage;
- response-lost cases recover from exact old/output/third-state bytes;
- write changes only declared selected regions and preserves outside narrative;
- a real Personal account separately consents to `Files.ReadWrite`;
- exact-item conditional final commit is proven before runtime is accepted;
- post-write bytes, new VALORA revision and observed M365 version lineage agree;
- credentials, upload URLs and values are absent from logs/audit/API snapshots.

### Browser acceptance

- preview is clearly not execution;
- all three values and every explicit choice are understandable;
- stale plan, Blocking, partial result and reconciliation-required states have one truthful recovery
  action;
- no fake Word editor and no Export PDF;
- desktop/laptop layouts and zero console errors.

## Stop conditions

Stop runtime implementation if any of these is unresolved:

- ADR 0042 or this contract lacks explicit Product Owner acceptance;
- no authoritative server-owned region-to-Workbench mapping exists;
- protected `Old` values cannot be proven from the baseline;
- exact-item OneDrive Personal final commit cannot enforce optimistic concurrency;
- write recovery would require blind retry or manual success assertion;
- output preservation cannot be proven at Managed Region and outside-content boundaries;
- release protection cannot fail closed;
- raw values, DOCX bytes, credentials or upload URLs would enter logs/audit/public API;
- implementation requires a provider/account/scope outside delegated OneDrive Personal
  `Files.ReadWrite`.

## Acceptance gate

Closed by explicit Product Owner acceptance on 2026-09-13. The authorization remains bounded to the
PR-07 implementation and migrations described here; it does not authorize push, pull request
publication, merge, deployment, release publishing, PR-08 work or widened Microsoft 365 scope.
