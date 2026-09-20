# ADR 0045 — Working-copy change observation and human-confirmed document revision

**Status:** ACCEPTED DESIGN / RUNTIME CONTRACT REQUIRED  
**Date:** 2026-09-21  
**Task:** `VALORA-DOCUMENT-CHANGE-OBSERVATION-001`

## Context

ADR 0043 made PostgreSQL, `DocumentRevision`, `DocumentRevisionCurrentHead` and app-owned immutable
blobs authoritative. ADR 0044 established OneDrive Personal Exchange v1 with non-authoritative
`Inbox`, `Working` and `Exports` roles and implemented explicit Working DOCX re-import in G8.

G8 is technically robust at the storage and provider boundary, but its explicit DOCX re-import can
currently move a changed Working DOCX directly toward `NEXT_REVISION` after provider/content
verification. The accepted UI/UX authority already requires Managed Region revalidation, three-way
`Old / VALORA / Word` semantics, explicit conflict decisions and no silent overwrite.

The Product Owner has approved a refined target model:

- VALORA should automatically observe and analyze Working-copy changes where technically possible;
- Word Save, provider notification and revalidation are never business commits;
- automatic processing may create a non-authoritative Change Candidate and recommendation;
- authoritative domain mutation and `DocumentRevision N+1` require an explicit human-confirmed
  business write boundary.

Microsoft Graph supports change notifications for OneDrive Personal folder hierarchies. A personal
OneDrive subscription may target the root or a subfolder, but not an individual file. Delta query can
then track driveItem changes over time using a delta link. On OneDrive consumer items, `cTag`
represents content while `eTag` represents the whole item. These signals are optimization/evidence
inputs only; they do not replace exact identity/content verification.

## Decision

### D1. DocumentRevision means accepted VALORA authority

A `DocumentRevision` represents an append-only document version that VALORA has officially
accepted. It is not equivalent to:

- a Word Save;
- a Microsoft 365 file version;
- a provider notification;
- a changed eTag/cTag;
- a changed checksum before review;
- a revalidation observation;
- a Change Candidate.

Only an authorized business commit may create `DocumentRevision N+1` and advance
`DocumentRevisionCurrentHead`.

### D2. Working change observation is non-authoritative

Provider notifications, delta results, focus-triggered refresh and explicit freshness checks may mark
a Working artifact as potentially changed/stale and may enqueue read-only analysis.

They cannot directly mutate business data, create a revision, advance CurrentHead, resolve a conflict
or publish a release.

Working Change Observation is an integration capability under the existing document stages. It does
not add a seventeenth Global Case State stage.

### D3. Use folder-level subscription only as a change signal

For OneDrive Personal, the preferred subscription scope is the resolved VALORA Working folder (or the
narrowest supported ancestor that contains it), never an individual file subscription.

The webhook endpoint must treat a notification as a wake-up signal only:

```text
Graph notification
→ validate notification/subscription
→ mark potentially changed
→ schedule reconciliation
```

No notification payload may be interpreted as accepted document content or business truth.

Subscription renewal, delivery gaps, duplicate notifications and out-of-order delivery must be
expected. Correctness must not depend on guaranteed webhook delivery.

### D4. Delta/exact-item revalidation establishes provider evidence

After a change signal, VALORA reconciles provider state using the persisted subscription/folder
identity and a delta cursor where appropriate, then revalidates the exact known Working driveItem by
stable provider ID.

Delta identifies potentially changed items and returns latest state, not every user Save. VALORA
therefore coalesces repeated Word saves naturally.

`cTag`/provider version metadata may avoid unnecessary content downloads, but a candidate that will
affect review/commit must be based on the existing bounded content verification rules: stable item
identity, exact size, full SHA-256 and Managed Region fingerprinting as required.

### D5. Automatic content analysis remains read-only to authority

Automatic revalidation may:

- read bounded verified DOCX bytes;
- compute whole-file and Managed Region fingerprints;
- compare against the accepted revision/snapshot baseline;
- derive `Old / V / W`;
- classify no-change, Word-only, VALORA-only or true conflict;
- create/update non-authoritative observation/candidate state;
- generate rule-based or AI-assisted recommendations.

It may not automatically apply a Word value to authoritative domain data or create a new revision.

### D6. Introduce a non-authoritative Change Candidate boundary

The target runtime must have a durable/recoverable representation of a document change candidate
before human review if background processing crosses process/session boundaries.

A Change Candidate must be explicitly linked to:

- organization/project/document;
- accepted baseline revision;
- Working Exchange artifact/provider item;
- observed provider evidence;
- affected Managed Regions/digests;
- the `Old / V / W` comparison;
- recommendation and review lineage.

Exact table names/columns/states are deferred to the implementation contract. Whatever representation
is chosen must be tenant-safe, non-authoritative and distinguishable from `DocumentRevision`.

If the Working item, authoritative VALORA data or baseline revision changes after candidate creation,
the candidate becomes stale/superseded and cannot be blindly committed.

### D7. Word-only Managed Region edits become proposals

When:

```text
Old = V
W != Old
```

the Word observation is not a three-way conflict. VALORA must preserve the observation and require
explicit handling before any operation that could overwrite it.

If the Managed Region represents authoritative business truth, the preferred flow is:

```text
Word value
→ typed proposal
→ human-confirmed domain command
→ authoritative business value
→ accepted document-version plan
```

Word is a proposal source, not a source of truth.

### D8. True three-way conflict remains explicit and zero-write until commit

When:

```text
V != Old
W != Old
V != W
```

the existing conflict authority applies. The user must explicitly decide the affected regions.
Conflict review/decision updates a review/sync plan only; it does not itself create a
`DocumentRevision`.

A final revision can be created only after all required decisions are complete and the final plan is
revalidated as fresh.

### D9. Human-confirmed revision command is the only promotion path

The target DOCX Working flow becomes:

```text
provider change / return
→ observe
→ revalidate
→ verified content read
→ Change Candidate
→ Old / V / W
→ recommendation/review/conflict
→ explicit human confirmation
→ approved revision command
→ G8 NEXT_REVISION storage intent
→ immutable blob verification
→ CurrentHead CAS
→ Revision N+1
```

G8's storage transaction, CAS, idempotency and recovery machinery remain authoritative below this
new business decision gate.

### D10. Automatic observation has three reliability layers

```text
PRIMARY
Graph notification
→ near-real-time stale signal

FALLBACK
focus/open/explicit "Kiểm tra thay đổi"
→ delta/exact revalidation

SAFETY GATE
before Revision / Sync / Publishing
→ mandatory exact freshness revalidation
```

Webhook loss therefore degrades timeliness, not correctness.

### D11. UI wording must reflect review, not immediate import

Preferred user-facing flow:

```text
Đã phát hiện thay đổi từ Word
→ Xem & xác nhận thay đổi
```

Fallback:

```text
Kiểm tra thay đổi
```

If `Nhập thay đổi` remains as a label, it means "start/import into the review pipeline", not
"immediately accept this file as Revision N+1".

The backend stage `DOCUMENT_SYNC_REVIEW` may remain for compatibility. Preferred user-facing meaning
is `Rà soát thay đổi tài liệu` / `Xem lại thay đổi & tạo phiên bản mới`.

### D12. AI remains advisory

AI may explain diffs, summarize changes and recommend a resolution. It cannot:

- confirm authoritative business values;
- resolve conflicts;
- create a revision;
- advance CurrentHead;
- publish;
- impersonate human approval.

All AI outputs remain typed proposals with provenance.

## Persistence and runtime constraints

1. Subscription/cursor/observation/candidate persistence must be organization/connection/project safe.
2. Provider item ID is identity; path/name are not identity.
3. Webhook validation secrets/tokens must not be stored in plaintext business rows.
4. Duplicate/out-of-order notifications must be idempotent.
5. Delta cursor advancement must be recoverable; a cursor cannot be advanced in a way that silently
   loses unprocessed change evidence.
6. Provider/network I/O must not hold long database locks.
7. Background processing uses durable idempotent jobs if it survives request/session boundaries.
8. Candidate review must re-check baseline revision, authoritative domain facts and provider freshness
   before commit.
9. The final revision command reuses G8 storage CAS and cannot bypass immutable-blob verification.
10. Published revisions/releases remain immutable.

## Authority relationship

This ADR supersedes ADR 0044 only in the narrow semantics of **DOCX Working re-import promotion**:
an explicit re-import action is no longer sufficient by itself to authorize immediate
`NEXT_REVISION` when changed content requires review.

It does not supersede ADR 0044's:
- non-authoritative Exchange roles;
- AppFolder least-privilege model;
- create-new Working/Export;
- provider-unknown reconciliation;
- XLSX source/staging isolation;
- storage/provider safety rules.

The accepted UI/UX authority is:
`VALORA_UIUX_HANDOFF_v2.3_WORKING_CHANGE_OBSERVATION_REVIEW_CONTRACT_ADDENDUM.md`.

## Implementation gate

No runtime webhook/subscription/delta watcher or automatic revision promotion is authorized by this
ADR alone.

Before runtime implementation, freeze a task-specific contract covering:

- subscription lifecycle and validation;
- delta cursor/reconciliation;
- durable job/idempotency boundary;
- Change Candidate schema/read model;
- Managed Region diff inputs;
- stale/superseded rules;
- review/confirmation command;
- exact API/UI states;
- PostgreSQL concurrency/failure acceptance;
- notification loss/duplicate/out-of-order acceptance;
- provider conformance boundary.

Live Microsoft activity remains separately gated.

## References

- ADR 0041 — OneDrive Personal return/revalidation observations
- ADR 0043 — App-owned immutable document storage
- ADR 0044 — OneDrive Personal Exchange v1
- UI/UX v2.3 M365 Return / Revalidation Contract
- UI/UX v2.3 Document Sync & Version baseline
- UI/UX v2.3 Sync Conflict Resolution baseline
- Microsoft Graph change notifications overview:
  https://learn.microsoft.com/en-us/graph/api/resources/change-notifications-api-overview?view=graph-rest-1.0
- Microsoft Graph OneDrive subscription limitations:
  https://learn.microsoft.com/en-us/graph/api/subscription-update?view=graph-rest-1.0
- Microsoft Graph driveItem delta:
  https://learn.microsoft.com/en-us/graph/api/driveitem-delta?view=graph-rest-1.0
- Microsoft Graph driveItem resource:
  https://learn.microsoft.com/en-us/graph/api/resources/driveitem?view=graph-rest-1.0
