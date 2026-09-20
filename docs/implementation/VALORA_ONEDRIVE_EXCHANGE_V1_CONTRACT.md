# VALORA OneDrive Personal Exchange v1 implementation contract

**Status:** FROZEN FOR G8 OFFLINE IMPLEMENTATION
**Date:** 2026-09-20
**Task:** `VALORA-ONEDRIVE-EXCHANGE-001`
**Authority:** ADR 0044, ADR 0043, ADR 0029

## Boundary

G8 implements only offline/non-live behavior for delegated OneDrive Personal App Folder Exchange.
The authoritative system remains PostgreSQL plus app-owned immutable blobs. No Microsoft credential,
live Graph call, AWS call, customer file, deployment, release, PR readiness change or merge is
permitted.

## Bounded contracts

- OAuth profiles: `read_only` requests `Files.Read`; `exchange_write` requests exactly `Files.Read`
  and `Files.ReadWrite.AppFolder` and requires both in the returned normalized grant.
- Capabilities: `READ_AVAILABLE`, `APPFOLDER_WRITE_AVAILABLE`; connection status is not evidence.
- Roles: `inbox`, `working`, `export`; media: `docx`, `xlsx`.
- Namespace: resolved app-root item ID, then exact `VALORA/Exchange/{Inbox,Working,Exports}`.
- Provider writes: create-new-only, exact parent item ID, deterministic name, never overwrite.
- Operation states: `PREPARED`, `PROVIDER_UNKNOWN`, `PROVIDER_VERIFIED`, `FINALIZED`,
  `FAILED_ACTION_REQUIRED`.
- AppFolder escape, file/folder collision, ambiguous exact-name result and mismatched drive/parent
  identity are terminal fail-closed outcomes.

## Persistence shape

### OAuth ledger

Persist normalized granted scopes as one row per connection/scope and bounded capabilities as one
row per connection/capability with availability, evidence source and observation time. Reconsent
replaces ledger/token material only after the requested profile is fully satisfied. Migration legacy
provenance may add `files.read`/`READ_AVAILABLE` only; AppFolder is never backfilled.

### `M365ExchangeArtifact`

Required columns: tenant/project/connection IDs; role/media/state; drive/item IDs; logical namespace;
display name; eTag/cTag/provider version; observed SHA-256 and byte length; bounded source authority
type; explicit nullable Document/Revision and Excel batch/source-artifact foreign keys; created,
updated and observed timestamps. Provider identity is unique per connection. All authority FKs use
tenant-composite lineage. Delete is restricted and never cascades to authority.

### `M365ExchangeOperation`

Required columns: tenant/project/connection IDs; operation ID; organization-scoped idempotency key;
request digest; bounded kind/role/media/state; deterministic parent item ID and destination name;
expected item ID/eTag; pre/post checksum and byte length; provider request/result evidence; linked
artifact ID; prepared/updated/verified/finalized timestamps. Same key/different digest is conflict.

## Graph port

The port may expose only:

```text
get_app_root
ensure_child_folder
create_file
get_item_by_id
resolve_child_by_exact_name
get_bounded_content
```

Every returned item includes drive/item/parent identity, item kind, name, size and available tag/
version metadata. `create_file` accepts only a verified parent under the resolved App Folder Exchange
subtree. The fake records mutation counts and can inject before-send, lost-response, collision,
stale-precondition, throttling and unavailable outcomes.

## DOCX commands

### Initial import

```text
explicit Inbox command
-> metadata before
-> bounded content + exact length + full SHA-256
-> metadata after; identity/tag/size must still match
-> existing DOCX safety/template validation
-> INITIAL_REVISION storage intent and deterministic candidate
-> immutable app-owned object create/observe/verify
-> one transaction: revision 1 + CurrentHead + StorageObjectBinding + artifact link + audit
```

No DB lock spans Graph or blob-provider I/O. A failed transaction publishes none of the four
authoritative/linking rows. Replay uses the same command/intent.

### Working and explicit re-import

Working reads the current binding through the bounded blob-read port and validates exact SHA-256/
length before a create-new Graph operation. It creates no revision. Re-import repeats provider
metadata/content verification; equal current checksum returns no-change; otherwise it uses the G6
`NEXT_REVISION` flow and CurrentHead CAS.

## XLSX commands

Downloaded XLSX bytes are wrapped in a bounded upload/stream facade and passed into the existing
source-artifact and staging pipeline. No second parser is allowed. The command never creates a
DocumentRevision or invokes Apply. Re-import produces a new source generation subject to existing
version/concurrency checks.

## UI contract

Keep the current M365 workspace. Present one capability-aware state:

- `read-only`: existing read/revalidation remains usable; show “Cần cấp quyền Exchange”; write CTAs
  are unavailable.
- `exchange-write-ready`: expose applicable “Nhận tệp”, “Bản làm việc”, “Nhập thay đổi” and “Xuất
  sang OneDrive” actions.
- `reconsent-required`: explain the missing Exchange grant and provide only explicit reconsent.

Near every Working action persist:

> Lưu trong Word/Excel chưa cập nhật VALORA. Chỉ “Nhập thay đổi” mới bắt đầu kiểm tra và ghi nhận.

## Verification matrix

E2, E8, E10, E12, E28 and E29 require behavioral execution of the real Excel source-artifact and
staging pipeline with offline storage/provider fakes. Source-text inspection or replacement of both
intake facades with stubs is not acceptance evidence.

| ID | Required offline proof |
|---|---|
| E1 | explicit DOCX Inbox import |
| E2 | explicit XLSX Inbox through existing Excel intake |
| E3–E4 | full SHA-256 and exact length |
| E5 | duplicate import idempotency |
| E6–E8 | Working/Word/Excel Save leaves authority/Apply unchanged |
| E9 | explicit DOCX re-import creates one immutable N+1 revision |
| E10 | explicit XLSX re-import creates existing source/staging flow |
| E11–E12 | DOCX head and Excel source-generation conflicts fail safely |
| E13–E16 | Export/rename/move/delete leaves authority unchanged |
| E17–E18 | OAuth/Graph failure isolates Exchange |
| E19 | unknown create reconciles without duplicate mutation |
| E20 | no provider event mutates authority |
| E21–E22 | read-only cannot write; missing AppFolder grant fails closed |
| E23–E24 | target escape and file/folder collision fail |
| E25–E26 | digest conflict and restart recovery |
| E27–E30 | initial binding; XLSX no revision; no Apply bypass; artifact delete preserves blob |

Real PostgreSQL evidence must cover operation races/replay/recovery, DOCX CurrentHead CAS, Excel
source generation, migration up/down/up and tenant/project isolation. SQLite-only evidence is not
acceptance. T1–T14, L1–L17 and all affected backend/frontend suites remain regression gates.

## G9 prerequisites

G9 remains closed until G8 has two independent verdicts on one exact frozen snapshot, exact-head CI
succeeds, the Product Owner explicitly authorizes live reconsent, a synthetic-only Microsoft account
and cleanup boundary are frozen, AppFolder preview availability is confirmed, and no broader scope is
needed. Any need for `Files.ReadWrite` returns to the Product Owner with evidence.
