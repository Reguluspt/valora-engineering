# OS-G2 A13 — Supplier quotation runtime

This is the bounded backend/domain/provider/API candidate for [Issue #137](https://github.com/Reguluspt/valora-engineering/issues/137), based on main `4b8f227e304a3066b79d48c82ac3ebee723d5478`. Accepted authority is [A12](../plan/VALORA_OS_G2_SUPPLIER_QUOTES_AUTHORITY_PROPOSAL.md): D1–D5 and D7–D12 accepted as proposed; D6 accepted with the Product Owner's explicit human-click clarification. A13 certification, integration, and product UX closure remain Gate Owner decisions. The certified runtime boundary remains PRICE_EVIDENCE until integration is certified.

## Persistence and lifecycle

One additive Alembic head, `e8f9a0b1c2d3`, succeeds `d7e8f9a0b1c2`. It creates three dedicated tables with tenant/project composite foreign keys; no legacy promotion or backfill occurs.

| Table | Authority |
| --- | --- |
| `supplier_quote_receipts` | Global command UUID, scoped actor/session, canonical request digest, historical response |
| `supplier_quote_facts` | Append-only registration, revision, item-registration, confirmation, withdrawal and rejection journal; immutable source/Supplier/line/upstream bindings and audit identity |
| `supplier_quote_items` | Exact sealed ProjectAssetLine mapping, positive `Numeric(26,8)` quantity and unit price, resolved unit and safe item locator |

The logical quotation identity is the existing retained DocumentRecord ID. A document has one latest revision chain and a separately derived current confirmed revision. Unique predecessor and document/revision-number constraints prohibit branching. Items in a draft are updated by appended item-registration facts; confirmed items cannot be edited. Source DocumentRevision and StorageObjectBinding rows become pinned against UPDATE/DELETE once referenced. PostgreSQL triggers and ORM events prohibit overwriting or deleting the new authority journal.

A correction or replacement creates a complete successor item set and atomically withdraws any current confirmed predecessor. An explicit Supplier correction preserves the old issuer snapshot and requires fresh human confirmation of the corrected revision. A negotiation draft preserves a still-current confirmed predecessor; rejecting that draft preserves that existing authority. Confirming a successor supersedes the entire predecessor, including omitted lines. Withdrawal targets the exact contributing confirmed revision, even when a newer negotiation draft exists. Withdrawal, correction and supersession never reactivate an older revision.

Material identity/authenticity/integrity concerns recorded on withdrawal or rejection remain blocking across successors. A reasoned successor identifies the exact concern IDs and resolution evidence; only its explicit confirmation clears those concerns. This is correction history for an already recorded concern, not an additional professional checklist required for ordinary confirmation.

## Retained source admission and D6

Admission reads existing DocumentRevision, StorageObjectBinding and DocumentRevisionCurrentHead rows with exact organization/project/document/revision scope. EvidenceFile, EvidenceLink, generic ProjectFile, remote URLs and uploader organization are not admission authority. The existing document blob-store factory supplies the retained store; A13 invokes only observation and bounded verified byte reads. It never invokes ingestion, import, parsing, OCR, OAuth or remote fetching.

Admission requires the current retained revision/head generation, matching revision and binding SHA-256, exact positive byte length, existing provider profile/container, provider object version and creation identity. Before and after observations must match the binding; `read_verified` must hash the retained bytes successfully. Reads are bounded to 32,000,000 bytes. The existing local store is create-only and checks filesystem object generation; generation/creation changes and same-ID byte replacement invalidate quotation authority, even when restored bytes have the same checksum. No storage path/key or raw bytes are returned publicly. Unsupported or unavailable retained source fails admission rather than assuming safe ownership.

The authenticated human's `confirm: true` command is the professional attestation. Confirmation adds no scan, OCR, parser, extracted-text comparison, signature/stamp verifier, checklist, or second approver. Tests confirm quotations backed by deliberately non-DOCX retained bytes; no document-content processor is called. Cryptographic byte identity and availability checks are ordinary technical command safety and do not attest to document meaning.

## Commands and API

| Command | Contract | POST suffix |
| --- | --- | --- |
| RegisterSupplierQuote | `supplier-quote-registration-v1` | `/register` |
| RegisterSupplierQuoteLine | `supplier-quote-line-registration-v1` | `/register-line` |
| ReviseSupplierQuote | `supplier-quote-revision-v1` | `/revise` |
| ConfirmSupplierQuote | `supplier-quote-confirmation-v1` | `/confirm` |
| WithdrawSupplierQuote | `supplier-quote-withdrawal-v1` | `/withdraw` |
| RejectSupplierQuote | `supplier-quote-rejection-v1` | `/reject` |

All routes use `/api/v1/projects/{project_id}/supplier-quotes`. GET preparation returns server-derived invocation versions, exact line coverage, deficiencies, currentness, eligibility and command availability. GET the base path returns paged quotation revisions/items, scoped terms/prices, safe source metadata/locators, lineage and registrar/confirmer. Optional quote/revision filters enforce scoped 404. GET `/sources` and `/suppliers` return paged safe IDs and current versions. GET `/command-receipts/{command_id}` reconciles the original actor's command outcome with the current Case State token. Preparation and public Case State contain no bulk quotation prices or Supplier personal/legal data.

Reads require existing `project:read`. Writes require an active authenticated human, server-derived organization, existing `workbench:edit`, an owned active Workbench session and Project DRAFT. Session acquisition remains `workbench:open`. No new RBAC permission or grant is introduced. Strict typed contracts reject unknown fields, floats, unsupported values and invalid dates with static 400 responses; route bodies retain the existing 2 MB bound. Cross-tenant/project/source/line/Supplier references return safe 404 or version conflicts, without exposing foreign facts.

## Compute-on-read Case State

The read-only provider is `supplier_quotes_v1`; the shared registry/token successor is `global-case-state-v6-supplier-quotes-v1`. It joins the existing coherent Case State snapshot and canonical CAS calculation without a parallel stage algorithm or new result/action enum. Current PRICE_EVIDENCE COMPLETE makes `current_stage = SUPPLIER_QUOTES` reachable.

COMPLETE requires the exact non-empty inherited sealed line set, current PRICE_EVIDENCE COMPLETE, intact receipts/audits, no applicable blocking concern, and at least one current confirmed independently resolved Supplier on every exact line. Drafts, uploads and historical receipts count zero. One Supplier covering every line is sufficient. Additional quotations are optional; irrelevant drafts or stale optional quotes do not invalidate otherwise intact COMPLETE coverage. There is no zero-quote waiver, NOT_APPLICABLE bypass, three-quote rule or canonical-asset fan-out.

Supplier authority pins its tenant-scoped ID, version, status, merge state and identity snapshot. Merged/inactive identities do not count; unresolved duplicate normalized tax identities (or duplicate legal names without tax identity) block rather than pretending independence. Coverage uses a set of legal Supplier IDs, so multiple documents/revisions from one Supplier count once. Duplicate retained bytes cannot be assigned simultaneously to different active legal Suppliers through separate quotation documents. An explicit issuer correction does not rewrite historical snapshots.

Currentness includes seal/lineage, exact line description/specification/quantity/unit, upstream confirmation and currentness, Supplier and currency registry state, source head/generation/availability/checksum/object identity, quotation revision/items, effective/expiry/review deadlines, receipt/audit integrity and lifecycle. Dependency changes enter the shared Case State token, including changes to an already unavailable/corrupt source. Currentness is rechecked after locks and just before commit with server time.

The provider reuses NOT_AVAILABLE, BLOCKED, STALE, INCOMPLETE and COMPLETE. Its pending action is `supplier_quotes_prepare_required`, kind PENDING, stage SUPPLIER_QUOTES, context `supplier_quotes_preparation`, meaning “Tạo và hoàn thiện báo giá NCC”. Contexts contain safe IDs/versions/hashes and reason codes only. COMPLETE yields NO_AUTHORIZED_DOWNSTREAM_ACTION because SUPPLIER_SELECTION remains unauthorized. An intact COMPLETE remains readable outside DRAFT; new quotation writes and reversals are unavailable there.

## Warnings, transactions and reconciliation

Optional `same_working_unit_basis` records the human's comparable-basis declaration. With exact quantity/unit/currency compatibility and a positive working unit price, Decimal comparison emits `below_working_price` below that price and `difference_exceeds_15_percent` only for absolute deviation strictly greater than 15%. These codes are warnings, never blockers. NULL/zero working prices and unassessed/incompatible basis produce no fabricated percentage. No working price or appraised price is written.

Every command locks Project first, then resolves scoped access/session, the shared Case State and Supplier/source dependencies with compatible shared locks. CAS requires Project row version, Case State token, seal/set/membership, full exact line-version set, owned session, upstream confirmation, Supplier version, latest quotation revision/head version and source generation. There is no last-write-wins or silent rebind. A final outer-transaction hook flushes and rechecks active access/session, DRAFT, source bytes/dependencies, token and server deadline before committing.

Facts, exact items, Project version, receipt and success audit commit in the caller-owned outer transaction. Audit failure or final currentness failure rolls back all of them. Same UUID and canonical payload returns exactly the original historical result; changed payload conflicts. Historical replay still checks current actor/access and journal integrity, but does not create another success audit or claim current completion. After an unknown outcome, read the original UUID receipt; never retry blindly with a new UUID.

The audit allowlist contains command/receipt/record/Project/session/contract IDs, pre/post versions and content/request/record digests only. It excludes money, Supplier names/tax/contact, source bytes/text/paths/URLs, freeform reasons, credentials and full request bodies. The read-derived fold checks response/request/content/audit integrity, exact item set and lifecycle; mismatched or orphaned success audits make authority STALE.

## Verification and boundaries

The focused suite consists of `test_g2_supplier_quotes.py`, `test_g2_supplier_quotes_api.py`, `test_g2_supplier_quotes_postgresql.py` and `test_g2_supplier_quotes_storage.py`. The final four-file local PostgreSQL run passed **86 tests**, with **1 Linux-only filesystem test skipped on Windows** (492.90 seconds), including all **39 real PostgreSQL matrix cases**. This includes both valid negotiation-confirmation/current-withdrawal orderings and rollback when an item-registration deadline crosses immediately before commit. It covers Decimal extremes, one-click confirmation, exact minimum coverage, independence/deduplication, currentness/expiry/review, byte integrity/generation, source availability, legacy non-promotion, scoped negatives, replay/reconciliation, atomic rollback, warnings, provider/action and downstream hold. Full-suite and exact frozen-HEAD review/CI evidence are recorded in the Draft PR and Gate handoff after those checks finish.

The final complete local backend run passed **2,305 tests**, with **2 Linux/POSIX-only skips** on Windows (2,268.63 seconds). The skips are the existing local blob-store acceptance test and the A13 retained-source test. Both must run in repository Linux CI. Backend Ruff, security baseline scan and `git diff --check` passed. A fresh isolated PostgreSQL database passed the full migration-chain upgrade, A13 downgrade to `d7e8f9a0b1c2`, and re-upgrade to the single `e8f9a0b1c2d3` head. Prior failed/superseded runs remain historical evidence; they are not reclassified as passing verification.

The real PostgreSQL matrix observes actual blocking backend PIDs and both lock orderings for source replacement/loss/integrity, Supplier merge/deactivation, line description/quantity/unit changes, upstream withdrawal, competing successors/confirmations, withdrawal/rejection, replay versus successor/withdrawal and multiline corrections. It verifies deadline crossing after a lock wait and coherent repeatable-read Case State before/after official mutation. Assertions require no fork, complete atomic item sets, failed CAS with zero success audit and historical replay with exactly one success audit. Storage tests run the actual migration upgrade/downgrade/re-upgrade and SQL append-only/source-pin guards in an isolated schema.

The existing S13 prior-head historical-parity fixture removes the three A13 child tables before removing older parent tables. This preserves its existing schema-slice and parity assertions in the presence of the new foreign keys; production migration behavior is unchanged.

The production local-filesystem retained-source test is Linux-only and skips on Windows; repository CI must run it on Linux. Fake stores are test fixtures only. Unsupported provider bindings fail closed. No visual baseline or browser E2E product-closure claim is made.

PRICE_EVIDENCE remains prerequisite/context with its prior semantics: no conversion, price copy, source promotion or upstream confirmation rewrite. Existing QuoteBatch, QuoteLine, SupplierQuoteEvidence and generic knowledge quote routes are supporting inventory only. A13 does not call NCC Selection, create NccSelectionRevision, update NccSelectionCurrentHead, create AppraisedPriceDecision, write appraised_unit_price, advance APPRAISAL_RESULT or generate documents. Frontend quotation workspace, product UX closure, selection and appraisal authorization are separate tasks.
