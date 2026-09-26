# ADR 0042 — OneDrive Personal protected values and recoverable sync writes

**Status:** ACCEPTED HISTORICAL PR-07 AUTHORITY — COMPARISON/CONFLICT SEMANTICS RETAINED; DIRECT-WRITE EXECUTION RE-BASELINED BY ADR 0043–0045 **Date:** 2026-09-13 **Task:** `VALORA-PR07-CONTRACT-001`

## 2026-09-21 current-use note

Retain D1–D3 protected-value, server-owned mapping and deterministic `Old / V / W` comparison semantics plus explicit no-default conflict decisions. Do not use this ADR to reopen direct replacement of an existing OneDrive item. Current document runtime uses app-owned immutable revisions (ADR 0043), Exchange Working copies (ADR 0044) and Working Change Observation / Human Commit (ADR 0045).

## Context

PR-05 and PR-06 established delegated OneDrive Personal access, immutable revision bindings,
digest-only Managed Region baselines, append-only revalidation observations and five canonical
classifications. They deliberately did not retain the raw values needed to show `Old`, current
VALORA and current Word values, and they did not authorize a Graph write.

The accepted sync/conflict baselines require all of the following:

- preview and conflict resolution do not mutate Word or create a Document Revision;
- one semantic three-way comparison is available for each Managed Region;
- no party silently wins a conflict;
- only selected Managed Regions may change, while outside narrative remains byte-semantically
  preserved;
- stale plans, published/locked targets and unverifiable provider state fail closed;
- each updated document creates a new VALORA Document Revision and records the resulting Microsoft
  365 file/version separately;
- a bulk result remains truthful when only some documents succeed.

A database transaction cannot include a Microsoft Graph commit. Treating a successful HTTP response
as an atomic document revision would therefore leave an unrecoverable gap when Graph commits but the
response or subsequent database commit is lost.

## Decision

### D1. Persist protected, typed Managed Region values

PR-07 adds an immutable protected-value snapshot for each eligible content baseline and each region.
The protected payload is the typed normalized value, not unrestricted DOCX text. It distinguishes
missing, null, blank string, text, decimal, integer, boolean, date, datetime and bounded structured
values under an explicit normalization contract.

Each value row contains tenant/document/revision/baseline/region lineage, semantic type,
normalization-contract version, encrypted canonical payload, encryption key version, nonce,
authenticated-data contract, and a keyed value identity. Encryption uses an application-managed
AEAD key; value identity uses a separate tenant-bound HMAC key so low-entropy business values are not
exposed by an unsalted digest. Key versions are explicit. Values under different identity-key or
normalization versions are never compared as if their HMACs were equivalent; the service decrypts,
renormalizes and fails closed when it cannot establish one common contract.

Raw values are excluded from logs, audit payloads, idempotency digests and provider metadata. An
authorized conflict read may decrypt only the selected regions and returns `Cache-Control: no-store`.

For a new revision, protected values, digest baseline and binding are created atomically. An existing
PR-06 baseline can be enrolled only when exact current or retained-version bytes prove equality to
the sealed baseline. If the current Word content differs and no historical provider version exactly
matches the baseline checksum and manifest, `PROTECTED_VALUES_REQUIRED` blocks preview and sync.

### D2. Region identity and source mapping are server-owned

A region identity is the tuple:

```text
template_version_id
+ managed_region_manifest_digest
+ region_key
+ locator_contract_digest
+ semantic_type
+ normalization_contract
```

PR-07 never accepts a client-authored locator, value, classification or source selector. Each eligible
Template Version must have an immutable server-owned sync mapping that maps the stable region key to
a canonical Workbench Data Snapshot selector. The service builds both `Old` and current VALORA values
from authoritative lineage. A v1 manifest without an accepted sync mapping remains read-only.

### D3. Three-way comparison is deterministic

For every region in scope:

- `O` is the protected normalized value attached to the current revision's sealed baseline;
- `V` is the current normalized value from the frozen authoritative VALORA Data Snapshot;
- `W` is the normalized value parsed from the exact current OneDrive DOCX under the same manifest and
  parser/fingerprint contracts.

Equality is semantic equality under the normalization contract, never display-string equality.

| Comparison | Result before user decisions |
| --- | --- |
| `V = O` and `W = O` | no change |
| `V != O` and `W = O` | VALORA-only change; selectable update |
| `V = O` and `W != O` | Word-only change; preserve Word by default, no VALORA overwrite |
| `V != O`, `W != O` and `V = W` | converged; no conflict and no rewrite required |
| `V != O`, `W != O` and `V != W` | conflict; explicit decision required |

Structural drift that prevents a trustworthy value comparison is Blocking, not a guessed conflict.
An outside-managed change is preserved and is not a conflict by default.

### D4. Preview persists an auditable plan but remains document-zero-write

PR-07 persists a bounded `M365SyncPlan` and immutable plan revisions so conflict decisions,
idempotency and stale checks refer to exact facts. This is operational plan persistence only: preview
and conflict resolution do not write OneDrive, mutate business data, create a Document Revision or
reserve a revision number.

The frozen plan binds exact project/document/current-revision/binding/baseline, template/mapping and
parser contracts, source Data Snapshot digest, observed Word checksum and eTag, ordered region inputs,
validation facts and plan digest. Each conflict decision records exactly one of:

`USE_VALORA | KEEP_WORD | SKIP_THIS_SYNC`.

There is no server default. Every required conflict must have an explicit actor/time-stamped decision.
Changing selection or a decision creates a new plan revision and invalidates prior confirmation.

### D5. Confirm is the sole write boundary

Confirmation requires `project:update`, an explicit idempotency key, the exact ready plan revision and
its row version/digest. Before any provider write, VALORA rechecks permission, tenant ownership,
current head, binding, baseline, protected values, source Data Snapshot, template/mapping contracts,
all Blocking facts, all decisions, active writer connection and document protection policy.

The command downloads the exact item again and requires the plan's stable drive/item identity,
checksum, eTag and semantic fingerprints. Any drift returns `SYNC_PLAN_STALE`; the user must preview
again. The patcher changes only selected Managed Regions, leaves `KEEP_WORD` and `SKIP_THIS_SYNC`
regions untouched, preserves outside-managed content, and verifies the output under the same bounded
DOCX safety contract. Unchanged documents are not written and receive no revision.

A current revision or provider artifact protected by a published/release lock returns
`PUBLISHED_REVISION_IMMUTABLE` before Graph I/O. PR-07 does not invent a copy-on-write release policy.

### D6. Write consent is explicit and narrow

Existing `Files.Read` connections remain read-only. Execution requires a separately and explicitly
consented OneDrive Personal delegated writer connection with least-privileged `Files.ReadWrite`.
VALORA does not request `Files.ReadWrite.All`, application permission, SharePoint or OneDrive for
Business scope. Connection status reports read/write capability from server-verified granted scopes;
the frontend cannot assert it.

The approved adapter may update only the exact bound `drive_id + drive_item_id`; it cannot create,
rename, move, delete, share, restore or bind by path. It uses a Microsoft Graph v1.0 upload session
for the exact item with `deferCommit: true`, `conflictBehavior: fail` and `If-Match` against the frozen
eTag. Immediately before final commit it rereads the item and again requires the same identity/eTag;
the final OneDrive Personal commit must also carry the precondition. A `412` is stale-plan failure.

Runtime implementation is blocked until provider conformance acceptance proves that the exact-item
OneDrive Personal final commit honors this precondition. A preauthenticated upload URL is secret,
memory-only and never persisted, logged or returned to the browser.

### D7. Provider commit uses a durable intent and recovery state machine

No database lock spans Graph or DOCX I/O. For each changed document, a short transaction first creates
one durable execution intent containing exact old lineage, plan/decision digest, expected eTag,
pre-write checksum, deterministic output checksum, actor and idempotency lineage. A tenant/document
unique active-intent constraint prevents concurrent writers.

The provider phase regenerates deterministic bytes, verifies the expected output checksum, and
performs the conditional Graph commit. It then rereads exact metadata and bytes. Only an exact output
checksum plus matching parsed values can become `PROVIDER_COMMITTED`.

The final short transaction rechecks authority and creates the new render/generated-document lineage,
Document Revision, current-head pointer, immutable binding, digest baseline, protected value snapshot,
region outcomes and success audit atomically. The old revision, binding and baseline remain immutable.

If the provider response or database finalization is uncertain, recovery rereads the exact item:

- exact expected output checksum and valid fingerprints: finalize the existing intent once;
- exact pre-write checksum and original eTag: the same intent may retry conditionally;
- anything else: `RECONCILIATION_REQUIRED`, block new sync/release, and require explicit recovery.

No blind retry is permitted. Same idempotency key plus same digest returns the persisted result;
different digest returns `409`. Recovery never creates a second revision for one provider commit.

### D8. Bulk execution is per-document atomic, not globally atomic

A batch has one frozen plan and per-document execution intents. Preflight must show `Blocking = 0`, but
provider or infrastructure failures can still occur after the batch starts. Successful documents are
not rolled back by rewriting OneDrive. Each document reports `SYNCED`, `UNCHANGED`, `SKIPPED` or
`FAILED_REQUIRES_ACTION` with its own lineage and recovery state. Batch success cannot hide partial
failure.

Only `SYNCED` documents create a new Document Revision and Microsoft 365 observation. `UNCHANGED` and
fully skipped documents create neither. A mixed document may create a revision for the regions that
were updated while retaining explicit per-region `KEEP_WORD`/`SKIP_THIS_SYNC` outcomes; skipped
regions are not represented as synchronized.

### D9. Audit and publication safety are fail-closed

Audit records plan creation, conflict decisions, confirmation, provider outcome, finalization and
recovery using stable IDs, digests, classifications, counts, actor, time and correlation ID. It never
contains raw values, DOCX bytes, upload URLs, tokens or provider response bodies.

Any unresolved active intent or reconciliation-required document blocks release readiness. A future
release lock is an input to the PR-07 write policy; unknown or unavailable lock state blocks execution.
PR-08/PR-09 may consume these facts but may not reinterpret an unresolved write as success.

## Alternatives considered

### Keep only SHA-256 value digests

Rejected. Conflict UX must show three values, and unkeyed digests of low-entropy business values are
guessable. Digest-only PR-06 rows remain valid integrity facts but are not sufficient for PR-07.

### Reconstruct `Old` from today's file

Rejected unless bytes and fingerprints prove exact equality to the sealed baseline. Otherwise this
would erase the very edit that conflict detection is meant to preserve.

### Write Graph first and create the revision afterward without an intent

Rejected. A lost response or failed database commit would leave an untraceable provider mutation and
unsafe automatic retry.

### Wrap the whole bulk operation in one database transaction

Rejected. A database transaction cannot roll back OneDrive, and holding locks across provider I/O
would increase contention without producing atomicity.

### Automatically prefer VALORA on conflict

Rejected by design authority. Every true conflict requires an explicit, auditable user decision.

## Consequences

- PR-07 adds protected business-value persistence and a more sensitive key-management boundary.
- Existing digest-only baselines may remain ineligible until proof-based protected-value enrollment.
- Preview/conflict screens can be deterministic and auditable without mutating documents.
- Sync execution is recoverable across provider/database split-brain scenarios, but a genuinely
  ambiguous provider state intentionally requires operator action.
- Bulk sync can truthfully report partial success without attempting destructive rollback.
- OneDrive write permission is a separate explicit consent event and remains Personal-only.

## Owner decision

Accepted explicitly by the Product Owner on 2026-09-13. Acceptance authorizes the bounded PR-07
schema/runtime/UI work and separate delegated OneDrive Personal writer-consent path described here.
It does not authorize scope beyond PR-07, push, pull request publication, merge, deployment or release.

### G3 provider-conformance closeout — 2026-09-19

The Product Owner approved G3 Option A after the bounded `C2_AUTO_V2` observation returned a safe
but undocumented HTTP `404 itemNotFound` stale-session result. D6 remains unchanged. The research
candidate is closed and is not an accepted production write mechanism; PR-07 provider-write runtime,
migrations, G4 and PR-08 remain blocked. Only read-only provider clarification may continue. Reopen
this decision only on a documented Microsoft guarantee or a separately reviewed supported mechanism.

### App-owned storage successor direction — 2026-09-19

The Product Owner subsequently approved app-owned immutable document storage as the primary roadmap
for authoritative DOCX bytes and revision history. [ADR 0043](0043-app-owned-immutable-document-storage.md)
records the accepted Model A and storage policy baseline. This note does not amend D6: any future
proposal to replace an existing OneDrive item directly must still satisfy D6 independently. The
original OneDrive provider-write runtime remains blocked. ADR 0043 authorizes only provider-neutral
local fake validation; it authorizes no cloud adapter, production migration, live provider call,
PR-08, deployment or release.

## References

- `docs/adr/0040-onedrive-delegated-integration-and-file-binding.md`
- `docs/adr/0041-onedrive-personal-return-revalidation-observations.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.3_DOCUMENT_SYNC_VERSION_BASELINE_ADDENDUM.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.3_BULK_DATA_SYNC_BASELINE_ADDENDUM.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.3_BULK_SYNC_PREVIEW_BASELINE_ADDENDUM.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.3_SYNC_CONFLICT_RESOLUTION_BASELINE_ADDENDUM.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.3_BULK_SYNC_CONFIRM_EXECUTE_BASELINE_ADDENDUM.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.3_BULK_SYNC_RESULT_BASELINE_ADDENDUM.md`
- [Microsoft Graph: upload or replace driveItem content](https://learn.microsoft.com/en-us/graph/api/driveitem-put-content?view=graph-rest-1.0)
- [Microsoft Graph: create an upload session](https://learn.microsoft.com/en-us/graph/api/driveitem-createuploadsession?view=graph-rest-1.0)
- [Microsoft Graph: list driveItem versions](https://learn.microsoft.com/en-us/graph/api/driveitem-list-versions?view=graph-rest-1.0)
