# PR-03 NCC Selection Persistence Implementation Audit

**Date:** 2026-09-05
**Task:** `VALORA-PR03-IMPL-001`
**Implementer:** Kimi (OpenCode)
**Authority:** ADR 0039, `VALORA_UIUX_HANDOFF_v2.3.md` section 2.1, NCC Selection Baseline Addendum

## Summary

Implemented the append-only NCC Selection revision persistence and internal confirmation
command. The final delta passed focused SQLite model/service checks, live PostgreSQL migration
and concurrency checks, a clean parent-to-head rollback cycle, the full backend suite, and the
independent Qwen gate.

## Files changed

- `backend/alembic/versions/d4b7c9e2f1a6_create_ncc_selection_revisions.py`
- `backend/app/db/__init__.py`
- `backend/app/modules/project_master_data/models.py`
- `backend/app/modules/project_master_data/application/ncc_selection_service.py`
- `backend/tests/test_pr03_ncc_selection_service.py`
- `backend/tests/test_pr03_ncc_selection_postgresql.py`
- `docs/implementation/VALORA_UIUX_V2_3_PR03_NCC_SELECTION_PERSISTENCE_CONTRACT.md`

Coordinator gate stabilization also added deterministic ordering to the existing asset-line
pagination in `backend/app/api/projects.py`; this is not an NCC Selection API surface.

## Test results

- `backend/tests/test_pr03_ncc_selection_service.py`: 25 passed, 0 failed, 0 skipped
- `backend/tests/test_quote_batch_line_persistence.py`: 5 passed, 0 failed, 0 skipped
- `backend/tests/design_contract/test_uiux_v23_contract.py`: 6 passed, 0 failed, 0 skipped
- Combined focused SQLite gate above: 36 passed, 0 failed, 0 skipped
- `backend/tests/test_pr03_ncc_selection_postgresql.py`: 2 passed, 0 failed, 0 skipped
- Existing project API pagination suite: 8 passed, 0 failed, 0 skipped
- Full `backend/tests` with `CI=true` and live PostgreSQL: 1,334 passed, 0 failed,
  0 skipped; 28 pre-existing deprecation/collection warnings

## Gates

- Ruff: passed on all final PR-03 and coordinator-stabilization files
- Python compilation: passed
- Migration single-head: `d4b7c9e2f1a6` is the single head
- Isolated PostgreSQL cycle: parent `c159fab13c3a` → `d4b7c9e2f1a6` → parent →
  head passed; NCC tables, tenant columns and `fk_ncc_rev_current_currency` verified
- Shared PostgreSQL repair environment restored to `d4b7c9e2f1a6`; PR-03 concurrency tests passed
- `git diff --check`: no whitespace errors; only existing CRLF conversion notices
- Independent Qwen initial review: PASS, zero blocking findings
- Independent Qwen final-delta review, session `ses_f8f8d0a50ffeWZ0ZLNVUrinJwQ`:
  PASS, zero blocking and zero non-blocking findings

## Correction round 1 findings addressed

- F1 ORM/migration mismatch: removed `UUIDMixin` from `NccSelectionCurrentHead`; mapped columns now exactly match migration composite PK.
- F2 supplier name fallback: `_find_eligible_quote` now fails closed when `QuoteLine.supplier_id` is `None`; removed `_resolve_supplier_id`.
- F3 idempotency key constraint: added `(organization_id, idempotency_key)` unique constraint to model and migration.
- F3 request digest: expanded `_request_digest` to cover quote batch id/revision, supplier name/id, quoted/current price and currency, quantity/unit/date, evidence id, differences, warning codes, acknowledgements, and correlation id.
- Fixed Vietnamese typo `đồng thời` → `đồng thời`.
- Added tests covering current-head mapped columns, null supplier_id rejection, changed acknowledgement idempotency rejection, and model unique-constraint metadata.

### Correction round 2 and coordinator fixture repair

- Made `TaxonomyNode.code` and `AssetFamily.code` unique per fixture run.
- Changed PostgreSQL cleanup to delete exact seeded IDs in foreign-key order, including
  EvidenceFile, rather than querying non-existent ownership fields.
- Confirmed both same-key replay and different-key conflict behavior on PostgreSQL with zero skips.

### Final Qwen follow-up hardening

- Removed `correlation_id` from the semantic request digest so tracing changes do not break a
  legitimate idempotent replay; added a regression test.
- Validated warning-code types before normalization and sorting.
- Persisted `Decimal` monetary/difference values directly and preserved zero versus null current
  prices in the digest and snapshot.
- Aligned model composite foreign-key declarations with the migration and added the current-price
  currency foreign key to both.
- Added approved-variant and cross-tenant QuoteLine/evidence tests.
- Stabilized existing asset-line pagination with a deterministic name-plus-ID order after the full
  suite exposed its unordered result set.

## Scope respected

No public NCC Selection API, no frontend, no case-state wiring, no AppraisedPriceDecision mutation,
no selected flag on Supplier/QuoteBatch/QuoteLine, no silent rebind, no M365/publishing/resume
refactor.

## Notes

- `organization_id` on `quote_batches`/`quote_lines` is nullable to retain existing rows
  whose creator organization cannot be resolved unambiguously; new eligible rows require
  organization_id in the selection command.
- Existing Knowledge API endpoints remain unchanged; tenant leakage is recorded as existing
  debt per ADR 0039 D3.
