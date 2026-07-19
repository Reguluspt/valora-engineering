# S13-PR-004 Sol High Coding Packet

**Date:** 2026-07-19
**Implementer:** Sol High AI Coder
**Task:** S13-PR-004 only
**Repository:** `Reguluspt/valora-engineering`
**Worktree:** `/workspace/scratch/c2fbd0b4f9ed/valora-engineering-pr004`
**Branch:** `s13-pr-004-column-mapping-memory`
**Required baseline:** `d09662c95edfd3515d405e468d215159b46fbf1f`
**Required baseline tree:** `dd9bac3c366f910b5c1d7da78b3f11947d3c37a6`
**Binding design:** `docs/audits/2026-07-19__S13-PR-004__EVIDENCE-GATE-DESIGN.md`

This packet delegates runtime implementation, not design authority. The first commit containing this
packet and the binding design is the design gate. Before editing runtime code, verify the worktree
baseline, read every authority below, and confirm the design audit is PASS. If any requirement cannot
be implemented inside the permitted scope, stop and report the exact conflict; do not improvise.

## 1. Mandatory read order

1. `CODEX.md`
2. `ENGINEERING_GUARDRAILS.md`
3. `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md`
4. `docs/VALORA_PROJECT_HANDOFF.md`
5. `docs/remediation/S13_S16_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_REMEDIATION_PLAN.md`, S13-PR-004
6. `docs/adr/0030-versioned-column-mapping-memory-and-adaptive-workbook-intake.md`
7. Design Book v1.4 §§5.5–5.7, 6.1–6.4 and §16
8. `docs/adr/0033-audited-ai-task-runs-decision-episodes-and-learning-evidence.md`
9. ADR 0029 + Excel staging contract §§14–15
10. the binding evidence-gate design above

Also inspect the accepted S13-PR-002/003 models, services, migrations, tests, and final corrective
evidence. Do not use historical report prose to expand scope.

## 2. Start gate

Before runtime edits, return this acknowledgment to the lead:

```text
baseline commit/tree verified
design-gate commit/tree verified
worktree and branch verified
binding documents read
scope/non-goals understood
no local residue or unexpected tracked changes
implementation file plan
open ambiguity: none | exact blocker
```

Do not start if the baseline differs, design audit is not PASS, or the worktree has unexplained
changes.

## 3. Deliverable

Implement backend-only, versioned Column Mapping Memory:

- migration and four conceptual persistence records;
- semantic role registry and canonical snapshot/fingerprint/digest helpers;
- authority-ordered exact/similar/approved-organization-template retrieval, human confirm/reject,
  correction/supersession;
- exact confirmed usage and full-source staging materialization;
- tenant/actor/current-generation/integrity/idempotency/concurrency/audit protection;
- complete focused SQLite development tests and PostgreSQL concurrency/migration evidence;
- no API/UI/AI/Apply/official-data changes.

Contract versions are exact:

```text
s13-pr-004-v1
s13-pr-004-fingerprint-v1
s13-pr-004-similarity-v1
s13-pr-004-materialization-v1
```

## 4. Implementation sequence

### Phase A — migration and models

1. Add the next Alembic revision with `down_revision = "a3b4c5d6e7f8"`.
2. Add enums/check constraints, composite tenant lineage, partial active-profile uniqueness, family
   version uniqueness, append-only decision/usage idempotency, and required indexes.
3. Add model declarations matching the migration exactly.
4. Do not backfill or mutate existing data.

### Phase B — pure domain contract

Create `domain/column_mapping.py` with:

- exact semantic role enum/registry and versioned synonyms;
- Unicode normalization shared with, or behaviorally identical to, PR-003;
- mapping cardinality and positional-bound validation;
- fingerprint v1 and canonical mapping snapshot/digest functions;
- deterministic role suggestions that fail closed for blank/ambiguous/duplicate roles;
- strict similar-template comparison/remapping that never reads body values or silently prefills;
- deterministic scalar/positional staging projection helpers;
- no SQLAlchemy, FastAPI, object storage, or provider calls.

Pure-domain tests must cover input ordering, duplicate/blank headers, Vietnamese accents, unknown
roles, digest stability, canonical JSON type rejection, and every role projection.

### Phase C — verified replay seam

Extract the PR-003 verified temporary-source context only if needed; preserve every PR-003 error,
cleanup, checksum, size, format, and close-failure behavior. Do not duplicate a weaker verifier.

Expose the smallest public PR-003 domain helper needed to classify every physical row inside a
frozen candidate region using stored v3 behavior. Do not re-run candidate discovery and do not use
the stored preview as data. One adapter open and one selected-sheet stream per materialization.
Write asset-row staging candidates to a bounded temporary spool before database locks; after locks
and fingerprint revalidation, stream that spool into bounded database insert batches. Own and unlink
the spool on every success and failure path. Never stream database writes before serialization locks.

Run all S13-PR-002/003 focused tests immediately after this seam change.

### Phase D — application services

Implement, in this order:

1. scoped source/snapshot/profile integrity helpers;
2. hierarchical profile retrieval (exact customer → similar customer → approved exact organization
   template);
3. `ProposeColumnMapping`;
4. `ConfirmColumnMapping` and correction/supersession;
5. `RejectColumnMapping`;
6. `MaterializeConfirmedMappingToStaging`;
7. idempotent retry and failure recovery.

Use project → batch lock order. Keep object I/O outside lock windows. Use `populate_existing` when
re-reading locked authority rows. Never compare stale aliases of one SQLAlchemy identity-map object.

### Phase E — focused proof

Build tests from the evidence matrix in the binding design. Add PostgreSQL-only concurrency probes
instead of accepting SQLite serialization as proof. Inject failures at adapter/read/close, flush,
savepoint/release, and outer commit boundaries. Assert prior staging state and audit cardinality after
each failure.

## 5. Non-negotiable implementation rules

- Proposal cannot create staging or usage.
- Proposal requires an explicit verified `candidate_index`; never silently choose candidate zero.
- Confirmation/rejection actor is human; AI/system cannot impersonate the actor.
- Active profile prefill still requires a new human confirmation for the batch.
- `memory_scope=none` persists a decision and later nullable-profile usage, not reusable memory.
- `memory_scope` is durably stored on the append-only decision and participates in idempotency.
- PR-004 confirmation accepts only `none|customer`. It may retrieve an already active/approved
  organization template, but cannot create, approve, activate, correct, or supersede one.
- A changed active mapping requires explicit `supersedes_profile_id` and a new profile version.
- Similar/conflicting profiles are returned for review and never silently selected.
- Every confirmed candidate column position occurs exactly once.
- Exactly one `raw_asset_name`; at most one of every other non-ignore role.
- Blank-header I may be explicitly confirmed as `evidence_note`.
- Only full-replay v3 `asset` rows become staging rows.
- `raw_values` remains positional and value-preserving through deterministic JSON-safe scalar
  encoding inside the candidate rectangle.
- No `ProjectAssetLine`, validation, or Apply call.
- No unrestricted raw headers/cells, filenames, object paths, exception text, or reason text in audit
  payloads.
- No skipped tests may support PASS.

## 6. Permitted files

```text
backend/alembic/versions/<new>_create_column_mapping_memory.py
backend/app/modules/excel_import/models.py
backend/app/modules/excel_import/domain/column_mapping.py
backend/app/modules/excel_import/application/column_mapping_service.py
backend/app/modules/excel_import/application/verified_source.py
backend/app/modules/excel_import/application/workbook_structure_service.py
backend/app/modules/excel_import/domain/workbook_structure.py
backend/app/modules/project_master_data/models.py  # only if a required composite lineage constraint is proven
backend/tests/test_s13_pr_004_column_mapping.py
backend/tests/test_s13_pr_004_column_mapping_postgresql.py
required package __init__.py exports only
```

Do not change API/schema/frontend/worker/CI/dependencies, Apply, live-gate docs, or unrelated tests.
If another file is required, stop and request a scope decision before editing it.

## 7. Required test order

Run from `backend/` with the repository's approved environment:

1. new pure-domain and application tests during implementation;
2. all S13-PR-002/003 focused tests after verifier/replay changes;
3. all S12 upload/validation/Apply focused regressions;
4. Alembic model/migration and upgrade/downgrade/upgrade checks;
5. complete backend suite locally as development evidence;
6. exact-head CI with PostgreSQL service, zero failures, zero skips.

Do not claim PostgreSQL concurrency from SQLite. Do not install or edit dependencies without owner
approval.

## 8. Commit discipline

Keep commits reviewable:

```text
1. migration + models
2. domain contract + unit tests
3. application services + replay seam + focused tests
4. corrective tests only if review finds a defect
```

Do not amend the frozen design commit. Do not commit cache, coverage, database, temporary workbook,
environment, or secret files. Use `git diff --check` before every handoff.

Only the lead publishes through GitHub App unless separately authorized. Do not use `gh`, push,
create/Ready/merge a PR, or modify remote state.

## 9. Handoff report required from AI Coder

Return:

```text
Task ID
baseline commit/tree and design-gate commit/tree
files changed (exact)
design/ADR sources followed
implementation invariants
tests run with raw pass/fail/skip counts
PostgreSQL-specific evidence
migration upgrade/downgrade evidence
adversarial/failure-injection evidence
known limitations
scope respected: yes/no
ADR/addendum needed: yes/no + exact reason
local commit SHA/tree
worktree status
```

The coding report is not an independent audit PASS. Internal independent review, Codex Lead review,
and exact-head CI remain separate gates. The owner removed the Antigravity gate on 2026-07-19.
