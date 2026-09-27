# VALORA UI/UX v2.3 — PR-03 NCC Selection Persistence Task Brief

**Task:** `VALORA-PR03-IMPL-001`
**Status:** HISTORICAL TASK BRIEF — IMPLEMENTATION COMPLETED / ENGINEERING GATE PASSED
**Date:** 2026-09-05
**Prerequisite:** PR-00 closed; ADR 0039 accepted by the Product Owner

> **2026-09-23 current disposition:** This brief records the original assignment/survey gate. PR-03 persistence was subsequently implemented and accepted; current implementation truth is `VALORA_UIUX_V2_3_PR03_NCC_SELECTION_PERSISTENCE_CONTRACT.md` plus its audit. Do not re-execute this task brief as an open assignment.

## Objective

Implement the persistence and internal application-service foundation for revisioned NCC Selection:
one project and one project asset line may have one current selection pointing to one eligible,
confirmed QuoteLine, while every prior selection revision remains immutable and queryable.

## Authority

- `CODEX.md`
- `ENGINEERING_GUARDRAILS.md`
- `docs/engineering/VALORA_MULTI_MODEL_DELIVERY_WORKFLOW.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.3.md` section 2.1
- `docs/design/VALORA_UIUX_HANDOFF_v2.3_NCC_SELECTION_BASELINE_ADDENDUM.md`
- accepted audit, tenant and human-commit conventions already present in the repository

## Survey gate

Before implementation, Kimi must inspect the current Project, ProjectAssetLine, Supplier,
QuoteBatch, QuoteLine, evidence and AuditEvent structures plus recent migration/application-service
patterns. The survey must answer:

1. Which existing facts can prove candidate eligibility and quote confirmation without inventing a
   new workflow meaning?
2. Which required selection snapshots can be copied deterministically from current records?
3. What schema shape preserves immutable revisions and exactly one current revision per project
   asset line on PostgreSQL and SQLite?
4. Which server-side concurrency, tenant and audit pattern should the command reuse?
5. Does any unresolved authority gap require an ADR or Product Owner decision before runtime work?

The survey is read-only. It must return a compact file map, proposed schema/service boundary,
risks and an explicit `READY` or `BLOCKED` recommendation.

## Planned implementation boundary

Subject to survey acceptance, PR-03 may add:

- one append-only NCC Selection revision model and migration;
- deterministic warning/snapshot value objects needed by persistence;
- an internal confirmation command/application service with tenant, permission, eligibility,
  optimistic revision and atomic audit checks;
- focused unit and PostgreSQL persistence/concurrency tests;
- PR-03 implementation contract and audit evidence.

## Accepted implementation allowlist

- `backend/alembic/versions/d4b7c9e2f1a6_create_ncc_selection_revisions.py`
- `backend/app/db/__init__.py`
- `backend/app/modules/project_master_data/models.py`
- `backend/app/modules/project_master_data/application/ncc_selection_service.py`
- `backend/tests/test_pr03_ncc_selection_service.py`
- `backend/tests/test_pr03_ncc_selection_postgresql.py`
- `backend/tests/test_quote_batch_line_persistence.py` only when required by the accepted tenant
  hardening
- `docs/adr/0039-tenant-safe-ncc-selection-revisions.md`
- `docs/implementation/VALORA_UIUX_V2_3_PR03_NCC_SELECTION_PERSISTENCE_TASK_BRIEF.md`
- `docs/implementation/VALORA_UIUX_V2_3_PR03_NCC_SELECTION_PERSISTENCE_CONTRACT.md`
- `docs/audits/2026-09-05__PR-03__NCC_SELECTION_PERSISTENCE_AUDIT.md`

The implementation must follow accepted ADR 0039 D1-D7 exactly. Any additional production or test
file requires coordinator review before it is edited.

## Forbidden scope

- no public NCC Selection API or frontend (PR-04);
- no case-state provider wiring, route key or PR-02 change;
- no AppraisedPriceDecision mutation or price-authority change;
- no selected flag on Supplier, QuoteBatch or QuoteLine;
- no automatic supplier selection, silent rebind or last-write-wins;
- no M365, publishing, resume-context or unrelated refactor;
- no commit, push or pull-request publication.

## Required verification after implementation

- focused model/service tests;
- PostgreSQL migration, uniqueness, concurrency and rollback evidence with zero skips;
- existing QuoteBatch/QuoteLine and design-contract tests;
- full relevant backend suite if the focused gate passes;
- Ruff, Python compilation, migration single-head check and `git diff --check`;
- independent Qwen review of the final bounded delta.

## Stop conditions

Stop before runtime edits if eligibility, confirmation authority, evidence lineage, current-revision
uniqueness or audit semantics cannot be derived from existing accepted facts without invention.

## Survey result

Kimi survey session `ses_f902d3f6fffephjsTan6cs9ICu` returned `BLOCKED` without editing files.
The Product Owner accepted ADR 0039 on 2026-09-05, closing the quote-confirmation, asset-line
matching, supplier/tenant identity, current-price and stale authority gaps. Runtime implementation
is authorized within the allowlist above.
