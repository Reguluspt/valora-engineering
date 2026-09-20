# ADR 0044 — OneDrive Personal Exchange v1

**Status:** ACCEPTED FOR OFFLINE IMPLEMENTATION
**Date:** 2026-09-20
**Task:** `VALORA-ONEDRIVE-EXCHANGE-001`

## Context

ADR 0040–0041 established delegated OneDrive Personal read, immutable provider identity bindings and
revalidation. ADR 0043 then made PostgreSQL, `DocumentRevision`, `DocumentRevisionCurrentHead` and
app-owned immutable blobs authoritative. The Product Owner has now authorized the offline foundation
for an explicit OneDrive App Folder Exchange workflow. No live Microsoft consent, Graph mutation,
AWS activity, deploy, release, PR readiness change or merge is part of this decision.

The approved Exchange namespace is logical and must be resolved from `/me/drive/special/approot`:

```text
approot
└── VALORA
    └── Exchange
        ├── Inbox
        ├── Working
        └── Exports
```

Provider item IDs are provider identity. Names and paths are display/reconciliation metadata only.

## Decision

### D1. Exchange roles are bounded and non-authoritative

`inbox` is an external source transport, `working` is a mutable user-editable copy, and `export` is
a derived VALORA output. OneDrive may disappear without changing any authoritative VALORA state.
Rename, move, save or delete on OneDrive never changes CurrentHead, an Excel current source, staging,
Apply state or an app-owned authoritative blob.

### D2. Exchange v1 media is DOCX and XLSX only

The bounded media enum is `docx | xlsx`. `.xls`, `.doc`, `.docm`, PDF and every other format are
rejected. Extension is only an early gate; the existing DOCX package safety rules or Excel intake
adapter must validate actual content. Existing `.xls` support in the Excel domain is not Exchange
authority for `.xls`.

### D3. App-root is resolved, never guessed

The Graph adapter resolves `/me/drive/special/approot`, then verifies/reuses the exact `VALORA`,
`Exchange`, `Inbox`, `Working` and `Exports` folder chain. An exact folder may be reused. A file where
a folder is expected, more than one exact match, a mismatched drive/parent identity, or any target
outside the resolved app-root subtree fails closed. There is no auto-rename or destructive repair.

### D4. Import and re-import are explicit commands

Inbox import and Working re-import begin only from an explicit VALORA command. Provider events,
revalidation, polling, Word Save and Excel Save cannot call an authoritative mutation. Revalidation
may observe provider change but cannot promote it.

Unchanged DOCX bytes return an idempotent no-change result and create no duplicate revision. XLSX
re-import creates a new source generation through the existing Excel intake and leaves Apply as a
separate explicit command.

### D5. Provider-unknown writes reconcile before any repeat

Create-new-only writes persist `PREPARED` before Graph I/O. The only successful path is:

```text
PREPARED -> Graph create -> exact identity/content verification
         -> PROVIDER_VERIFIED -> ExchangeArtifact persistence -> FINALIZED
```

A timeout, transport loss or eligible 5xx after a possible send becomes `PROVIDER_UNKNOWN`. Recovery
uses the persisted deterministic parent item ID and destination name, resolves the exact child, then
verifies type, drive/parent identity, name, size and full SHA-256 when required. It never blindly
creates again. Ambiguity becomes `FAILED_ACTION_REQUIRED`. `429` follows bounded `Retry-After` only
when no mutation may have been sent; `409` inspects state; `412` is a stale precondition.

Same organization-scoped idempotency key plus the same server-derived request digest returns or
reconciles the prior operation. Reuse with another digest returns conflict.

### D6. OAuth capabilities are evidence, not connection status

The requested delegated scopes are exact `Files.Read` plus preview
`Files.ReadWrite.AppFolder`. No `Files.ReadWrite`, `Files.ReadWrite.All`, application permission or
SharePoint scope is accepted as a fallback.

Normalized granted scopes and the bounded capability ledger are persisted separately from encrypted
token material. Capability codes are `READ_AVAILABLE` and `APPFOLDER_WRITE_AVAILABLE`; availability
comes only from exact normalized grant evidence. `status = active` is never capability evidence.

Existing PR-05 connections receive only a migration provenance entry for `READ_AVAILABLE`, based on
the frozen legacy `Files.Read` authorization contract. They receive no AppFolder capability. An
explicit Exchange reconsent must actually return both exact scopes before new token material and
write capability replace the prior read-only grant. A missing AppFolder grant fails closed and does
not destroy the still-usable read-only connection.

The business states are `read-only`, `exchange-write-ready` and `reconsent-required`. G8 prepares
the code and mock tests only; live consent is forbidden.

### D7. Exchange persistence records transport, not authority

`M365ExchangeArtifact` stores tenant/project/connection lineage; bounded role/media/state/source
kind; drive/item identity; logical namespace and display metadata; eTag/cTag/version; observed
SHA-256/length; optional Document Revision or Excel batch/source-artifact linkage; and observation
timestamps. Provider identity is unique within the owning connection. Deleting this row cannot
delete any authoritative blob or business record.

`M365ExchangeOperation` stores one provider mutation/reconciliation attempt: tenant/project/
connection, operation kind, role/media, idempotency key, request digest, deterministic parent/name,
expected provider identity/eTag, pre/post SHA-256 and length, state, provider evidence and timestamps.
The bounded states are `PREPARED`, `PROVIDER_UNKNOWN`, `PROVIDER_VERIFIED`, `FINALIZED` and
`FAILED_ACTION_REQUIRED`. The unique organization/idempotency constraint is the race arbiter.

Bounded check constraints and tenant-composite foreign keys are mandatory. Source linkage cannot
claim both Document and Excel authority. Inbox transport may begin with no authoritative linkage;
successful import finalization adds exactly the domain linkage it created.

### D8. OneDrive failure is isolated

OAuth/Graph failure may yield `EXCHANGE_DEGRADED`, but cannot block authoritative local document
reads, unrelated PostgreSQL operations, Excel workflows, or other VALORA commands. Provider access
and database locks never overlap.

### D9. DOCX authority mapping uses the G6 storage transaction

The G6 storage execution contract gains one bounded `intent_kind`:

| Kind | Frozen predecessor | Finalization |
|---|---|---|
| `INITIAL_REVISION` | document shell with no head, expected revision `0` | atomically create revision 1, CurrentHead, StorageObjectBinding, ExchangeArtifact link and audit |
| `NEXT_REVISION` | exact existing CurrentHead | preserve existing N+1 CAS finalization |

This avoids an unbound seed revision and preserves the existing prepare/candidate/create/observe/
verify/finalize protocol. A `DocumentRecord` shell is not authoritative content; it becomes readable
only after the revision/head/binding transaction succeeds. Every initial imported DOCX therefore has
an app-owned immutable blob and binding. CAS loss or finalization failure publishes no loser revision.

Working creation reads bytes by `StorageObjectBinding` through a bounded `DocumentBlobStore` read
operation that validates full SHA-256 and exact length and never exposes a backing filesystem path.
It creates no revision. Explicit re-import uses `NEXT_REVISION`; equal CurrentHead checksum is a
no-change result.

### D10. XLSX authority mapping reuses Excel intake

Inbox and explicit Working re-import download bounded bytes, verify exact size/full SHA-256, then
invoke a byte/stream facade over the existing `upload_source_artifact` and workbook staging pipeline.
They create or advance `ImportSourceArtifact` generations and existing structure/mapping/staging/
validation state. They never create `DocumentRevision`, never add another workbook parser, and never
call Apply. Excel source-generation concurrency remains governed by the existing batch/source locks
and constraints.

### D11. Working is create-new-only

Every Working command creates a deterministic new filename and fails on collision; it never replaces
an existing item. Saving the file in Word/Excel changes only OneDrive. The UI must persistently state:
“Lưu trong Word/Excel chưa cập nhật VALORA. Chỉ ‘Nhập thay đổi’ mới bắt đầu kiểm tra và ghi nhận.”

### D12. Export is side-effect isolated

Export creates a new item beneath `Exports` from authoritative VALORA output. It cannot change
CurrentHead, Excel current source, staging, Apply or any business state. Its operation/artifact rows
are transport evidence only.

## Schema invariants

1. Capability and granted-scope rows are tenant/connection-owned; tokens remain only in the encrypted
   credential vault.
2. Artifact `role`, `media`, `state`, `source_authority_type` and operation `kind/state` use bounded
   database checks matching code enums.
3. Provider identity uses `drive_id + drive_item_id`; path/name are never foreign identity.
4. Operation request identity is immutable; same key/different digest cannot update the row.
5. `PROVIDER_UNKNOWN` retains enough parent/name/request/checksum evidence for process-restart recovery.
6. Artifact linkage is one bounded domain lineage, not an unvalidated polymorphic pointer.
7. Storage initial intent constraints couple `INITIAL_REVISION` to expected revision 0/no predecessor
   and `NEXT_REVISION` to a non-null predecessor/revision greater than 0.
8. No cascade from Exchange persistence reaches revisions, source artifacts, staging, official data
   or storage bindings.

## Adversarial review

- A broader `Files.ReadWrite` scope would simplify provider APIs, but violates the approved least-
  privilege boundary and is rejected. If AppFolder preview is unusable in live G9, implementation
  stops and returns evidence to the Product Owner.
- A generic OneDrive filesystem abstraction would reduce adapter methods, but increases escape and
  overwrite surface. Only named app-root primitives are allowed.
- Creating a revision before blob finalization would simplify initial import, but can publish authority
  without durable bytes. The initial-intent finalization shape is required instead.
- Automatically importing provider saves would feel convenient, but makes a mutable external system
  authoritative and bypasses review/Apply. Explicit commands remain mandatory friction.
- Persisting only a path would make folder recovery easy to read but fails after rename/move. Stable
  provider IDs plus verified parent relationships remain the recovery identity.

## Acceptance and stop conditions

Codex inspected this decision against ADR 0029, ADR 0040–0043, the PR-05/PR-06 contracts and the
Document Blob Storage contract. It is internally consistent and accepted as the G8-A implementation
authority. Mechanical work may begin only against this frozen decision and its implementation
contract.

Stop if mocked/contract evidence requires broader delegated permission, a live provider, OneDrive
authority, an Excel bypass, an unbound DOCX revision, blind create retry, or an unreconcilable
provider-unknown result.

## Provider limitation

`Files.ReadWrite.AppFolder` is a Microsoft preview delegated permission. G8 proves only the offline
contract with fakes and HTTP mocks. Live availability, consent behavior and Graph conformance are G9
prerequisites and cannot be claimed from G8.

## References

- [ADR 0029](0029-excel-staging-apply-command-and-lineage.md)
- [ADR 0040](0040-onedrive-delegated-integration-and-file-binding.md)
- [ADR 0041](0041-onedrive-personal-return-revalidation-observations.md)
- [ADR 0043](0043-app-owned-immutable-document-storage.md)
- [Exchange v1 implementation contract](../implementation/VALORA_ONEDRIVE_EXCHANGE_V1_CONTRACT.md)
- [Document Blob Storage contract](../implementation/VALORA_DOCUMENT_BLOB_STORAGE_CONTRACT.md)
