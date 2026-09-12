# ADR 0039 — Tenant-safe NCC Selection revisions

**Status:** ACCEPTED — PRODUCT OWNER APPROVED
**Date:** 2026-09-05
**Task:** `VALORA-PR03-IMPL-001`

## Context

UI/UX v2.3 requires one current NCC Selection for each ProjectAssetLine, backed by one confirmed
QuoteLine. A change creates a new immutable selection revision; source revision changes make the
current selection stale and never silently rebind it. The selection is an explicit human commit,
warnings remain non-blocking and the command must not mutate AppraisedPriceDecision.

The current foundation does not fully encode that boundary:

- QuoteLine stores supplier text but no Supplier foreign key;
- QuoteBatch and QuoteLine have no organization_id, so a database-level tenant-safe reference is
  unavailable;
- the accepted UI authority does not name the exact existing status predicate for a confirmed
  quote;
- QuoteBatch revision creation preserves the old batch and creates a new draft child;
- ProjectAssetLine has both raw_price and appraised_unit_price.

PR-03 must settle these facts before adding runtime persistence.

## Proposed decision

### D1. Eligible confirmed QuoteLine

A QuoteLine is eligible only when all conditions hold:

- QuoteLine.status is ACTIVE;
- its QuoteBatch.status is ACTIVE, approved_by is present and approved_at is present;
- quoted_unit_price is a positive finite decimal and currency is non-blank;
- supplier_id resolves to an ACTIVE Supplier in the Project organization;
- evidence_file_id resolves to an ACTIVE EvidenceFile owned by a user in the Project organization;
- the QuoteBatch identity matches the ProjectAssetLine rule in D2.

Missing or ambiguous facts fail closed. Warning codes never make an otherwise eligible candidate
ineligible.

### D2. Quote ownership by ProjectAssetLine

Candidate matching uses approved asset identity only:

- when approved_asset_variant_id is present, QuoteBatch.asset_variant_id must match exactly;
- otherwise approved_canonical_asset_id must be present, QuoteBatch.canonical_asset_id must match
  exactly and QuoteBatch.asset_variant_id must be null;
- a line with no approved identity has no eligible candidates.

The same eligible QuoteLine may be selected independently for two project lines with the same
approved identity. Selection currentness remains scoped to organization + project + asset line.

### D3. Tenant and supplier hardening

PR-03 adds organization_id to QuoteBatch and QuoteLine and a nullable supplier_id to QuoteLine.
Existing rows are backfilled deterministically from QuoteBatch.created_by and retained as nullable
or rejected by the migration if creator organization cannot be resolved unambiguously. The
application requires new or eligible rows to have organization_id and supplier_id.

Composite tenant foreign keys prevent an NCC Selection from referencing a Project,
ProjectAssetLine, Supplier, QuoteBatch or QuoteLine outside its organization. Existing knowledge
API tenant leakage is recorded as debt and must be corrected in the smallest prerequisite slice if
the new constraints expose it; PR-03 does not otherwise redesign Knowledge APIs.

### D4. Current unit price and warnings

`ProjectAssetLine.appraised_unit_price` and its appraised currency are the user-controlled current
price authority for NCC comparison. raw_price remains intake/source data.

- If current price is null, difference_amount and difference_percent are null.
- If current price is zero, difference_amount is quoted price, difference_percent is null.
- Otherwise difference_amount and difference_percent use exact Decimal arithmetic.
- `NCC_BELOW_CURRENT_PRICE` applies when S < C.
- `NCC_DIFFERENCE_OVER_15_PERCENT` applies when abs(S - C) / C > 0.15.

Warnings and acknowledged warning codes are snapshotted, but acknowledgement never suppresses the
stored warning fact.

### D5. Immutable revision and current head

Use an append-only `ncc_selection_revisions` table plus one
`ncc_selection_current_heads` row per organization + project + asset line. The head holds the
current revision pointer and concurrency revision. The command locks Project then ProjectAssetLine
then current head, checks expected_selection_revision, inserts a new immutable revision, advances
the head and appends the required AuditEvent in one transaction.

The first commit emits NCC_SELECTION_CONFIRMED; a different source selection emits
NCC_SELECTION_CHANGED; explicit confirmation of a stale selection emits
NCC_SELECTION_RECONFIRMED. No historical row is updated or deleted.

### D6. Stale rule

The current head is stale when any of these facts holds:

- a later QuoteBatch revision names the selected batch, directly or through its revision chain;
- selected QuoteBatch or QuoteLine is no longer ACTIVE;
- selected Supplier is no longer ACTIVE;
- selected evidence is missing or no longer ACTIVE;
- the ProjectAssetLine approved identity no longer matches D2.

Stale is computed from current facts for reads. A bounded reconciliation command may append
NCC_SELECTION_MARKED_STALE once per current head for audit, but it cannot modify the immutable
selection revision or auto-select/rebind another QuoteLine.

### D7. Command authorization and idempotency

The internal command uses the existing project:update permission until PR-04 defines a public API
permission contract. It accepts quote_line_id, expected_selection_revision, acknowledged warning
codes and an idempotency key. Monetary, supplier, evidence, eligibility and warning values are
resolved again on the server and included in a request digest.

## Consequences

- PR-03 can enforce one current selection per project line with immutable history and deterministic
  concurrency on PostgreSQL and SQLite.
- Tenant safety requires a bounded hardening of existing quote persistence before selection rows
  can reference it.
- Existing quote rows without deterministic organization or supplier identity remain ineligible;
  no guessed mapping or cross-tenant fallback is allowed.
- PR-04 may expose read/confirm APIs and UI only after this persistence contract passes.

## Owner decision

The Product Owner accepted ADR 0039 on 2026-09-05 and authorized Kimi to implement the bounded
persistence/service task described by
`VALORA_UIUX_V2_3_PR03_NCC_SELECTION_PERSISTENCE_TASK_BRIEF.md`.
