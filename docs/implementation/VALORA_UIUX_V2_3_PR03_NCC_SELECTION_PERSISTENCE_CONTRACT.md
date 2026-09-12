# VALORA UI/UX v2.3 — PR-03 NCC Selection Persistence Contract

**Task:** `VALORA-PR03-IMPL-001`
**Status:** IMPLEMENTED — ENGINEERING GATE PASSED
**Date:** 2026-09-05
**Authority:** ADR 0039, `docs/design/VALORA_UIUX_HANDOFF_v2.3.md` section 2.1, `docs/design/VALORA_UIUX_HANDOFF_v2.3_NCC_SELECTION_BASELINE_ADDENDUM.md`

## Scope

This contract records the bounded implementation of the PR-03 NCC Selection persistence
foundation: one immutable selection revision history and one current head per
organization + project + project asset line.

## Decisions implemented (ADR 0039 D1-D7)

- **D1 Eligible confirmed QuoteLine:** `QuoteLine.status == ACTIVE`, `QuoteBatch.status == ACTIVE`,
  `QuoteBatch.approved_by` and `approved_at` present, positive finite `quoted_unit_price`,
  non-blank `currency`, resolvable ACTIVE Supplier in the project organization,
  ACTIVE EvidenceFile owned by a user in the organization, and D2 identity match.
- **D2 Asset-line ownership:** Candidate match uses `ProjectAssetLine.approved_asset_variant_id`
  first, otherwise `approved_canonical_asset_id` with `QuoteBatch.asset_variant_id` null.
- **D3 Tenant hardening:** `organization_id` added to `quote_batches` and `quote_lines`;
  `supplier_id` added to `quote_lines`; composite tenant foreign keys on selection tables;
  existing rows backfilled where creator/batch organization is unambiguous.
- **D4 Current price and warnings:** `ProjectAssetLine.appraised_unit_price` is the comparison
  baseline; warnings `NCC_BELOW_CURRENT_PRICE` and `NCC_DIFFERENCE_OVER_15_PERCENT` are
  snapshotted using exact Decimal arithmetic.
- **D5 Immutable revision + current head:** `ncc_selection_revisions` is append-only;
  `ncc_selection_current_heads` holds one pointer per line; lock order Project →
  ProjectAssetLine → current head; expected `selection_revision` optimistic check;
  atomic audit event in the same transaction.
- **D6 Stale rule:** `is_ncc_selection_stale()` recomputes stale status from current facts
  without mutating the immutable revision or auto-rebinding.
- **D7 Authorization/idempotency:** Internal command uses `project:update` permission,
  requires `confirmed=True`, accepts `quote_line_id`, `expected_selection_revision`,
  `acknowledged_warning_codes` and `idempotency_key`; server resolves all monetary,
  supplier, evidence and warning values into a request digest.

## Files changed

- `backend/alembic/versions/d4b7c9e2f1a6_create_ncc_selection_revisions.py`
- `backend/app/db/__init__.py`
- `backend/app/modules/project_master_data/models.py`
- `backend/app/modules/project_master_data/application/ncc_selection_service.py`
- `backend/tests/test_pr03_ncc_selection_service.py`
- `backend/tests/test_pr03_ncc_selection_postgresql.py`

Coordinator gate stabilization also made the existing asset-line listing order deterministic in
`backend/app/api/projects.py`, because its unordered pagination made the full backend gate flaky.
This does not expose an NCC Selection API.

## Forbidden scope respected

- No public API or frontend.
- No case-state provider wiring or PR-02 change.
- No `AppraisedPriceDecision` mutation.
- No selected flag on `Supplier`, `QuoteBatch` or `QuoteLine`.
- No automatic supplier selection, silent rebind or last-write-wins.
- No M365, publishing, resume-context or unrelated refactor.

## Audit evidence

- `docs/audits/2026-09-05__PR-03__NCC_SELECTION_PERSISTENCE_AUDIT.md`
- Independent Qwen final-delta review: PASS, zero blocking findings.
- Full backend gate: 1,334 passed on PostgreSQL-backed CI settings.
