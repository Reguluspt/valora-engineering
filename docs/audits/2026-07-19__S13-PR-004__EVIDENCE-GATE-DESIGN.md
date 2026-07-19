# S13-PR-004 Evidence-Gate Design — Column Mapping Memory Persistence and Application Services

**Date:** 2026-07-19
**Status:** FROZEN — design-first gate; runtime changes must conform or stop for an addendum
**Task:** S13-PR-004 — Column Mapping Memory Persistence and Application Services
**Owner assignment:** explicitly assigned in the 2026-07-19 project session
**Accepted runtime baseline:** `d09662c95edfd3515d405e468d215159b46fbf1f`
**Baseline tree:** `dd9bac3c366f910b5c1d7da78b3f11947d3c37a6`
**Implementation branch:** `s13-pr-004-column-mapping-memory`
**Contract versions:** `s13-pr-004-v1`, `s13-pr-004-fingerprint-v1`,
`s13-pr-004-similarity-v1`, `s13-pr-004-materialization-v1`

This document freezes the implementation choices that were still conceptual in ADR 0030. It is
binding for S13-PR-004. A coder must not silently choose different persistence, lifecycle,
concurrency, replay, audit, or staging behavior. A necessary change requires a design addendum,
independent review, and owner acceptance before runtime code changes.

## 1. Authority and conflict order

The implementation must follow, in order:

1. `CODEX.md` and `ENGINEERING_GUARDRAILS.md`;
2. `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md`;
3. `docs/VALORA_PROJECT_HANDOFF.md`;
4. Design Book v1.4 §§5.5–5.7, 6.1–6.4 and acceptance fixture §16;
5. accepted feature contracts and ADRs, specifically ADR 0030, ADR 0033, and ADR 0029 plus the
   Excel staging contract §§14–15;
6. `docs/remediation/S13_S16_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_REMEDIATION_PLAN.md`,
   S13-PR-004;
7. the accepted S13-PR-002 source-artifact and S13-PR-003 structure-snapshot code/evidence.

If this design conflicts with a higher authority, stop. Historical corrective reports are evidence,
not authority to expand this task.

## 2. Scope and completion boundary

S13-PR-004 closes G-03 and G-06 through backend persistence and application services only:

- persist versioned `ColumnMappingProfile`, `ColumnMappingField`, append-only
  `ColumnMappingDecision`, and append-only `ColumnMappingProfileUsage` records;
- define a versioned semantic role registry and deterministic proposal rules;
- derive a customer-scoped structural template fingerprint from a verified PR-003 snapshot;
- propose, confirm, reject, retrieve, and correct mappings;
- preserve the exact confirmed mapping snapshot used by each import generation;
- materialize only confirmed `asset` rows to the existing S12-compatible staging table;
- enforce tenant, actor, state, integrity, idempotency, lock, and audit invariants;
- prove PostgreSQL concurrency, migration, `.xls`/`.xlsx`, full-stream, rollback, and frozen Apply
  compatibility.

### 2.1 Explicit non-goals

This PR must not add or change:

- API routes, request/response schemas, OpenAPI, frontend, Astryx UI, or Vietnamese UX flows;
- `AITaskRun`, `DecisionEpisode`, `LearningFeedbackEvent`, `ExecutionPolicy`, provider calls, prompts,
  model selection, or any generic memory table;
- asset identity, taxonomy, pricing, quote, dossier, or canonical-asset decisions;
- `ProjectAssetLine` writes or the S12 `s12-pr-004-v1` Apply contract;
- automatic validation, automatic Apply, or any bypass of human mapping confirmation;
- cross-organization learning or an unapproved organization template;
- creation, approval, activation, correction, or supersession of an organization template; this PR
  persists/retrieves the authority shape but exposes no write command for that scope;
- unversioned/fuzzy similarity, silent selection of a similar/conflicting profile, or similarity
  based on unrestricted body-cell contents;
- source upload, structure analysis, adapter security limits, or PR-003 discovery heuristics except a
  narrow reusable verified-source/full-row replay helper;
- a major dependency, a new worker, or unrelated refactoring.

S13-PR-005 owns the confirmation API and UX. Later tasks own AI proposals and broader profile
retrieval policy.

## 3. Frozen domain decisions

| Topic | Frozen S13-PR-004 decision |
| --- | --- |
| Source authority | Reuse the exact `ImportSourceArtifact` and `WorkbookStructureSnapshot`; never copy or replace them. |
| Proposal truth | A proposal is an append-only decision record and cannot materialize staging. |
| Human truth | Only an append-only human confirmation decision authorizes materialization. |
| Remember choice | Confirmation always persists a decision. PR-004 reusable memory is explicit: `memory_scope=none|customer`; default is `none`. |
| Profile prefill | One exact, active, same-organization + same-customer fingerprint match may prefill a proposal; it never counts as confirmation. |
| Retrieval hierarchy | Exact customer match → structurally similar customer candidates → approved exact organization template → new deterministic proposal. |
| Conflict | More than one exact candidate or a different active mapping fails closed for explicit review; no profile is silently chosen. |
| Similarity | Similar candidates are versioned, deterministically ranked, returned for review, and never prefilled automatically. |
| Correction | Correction cites the current active `supersedes_profile_id`; it creates a new positive version and atomically supersedes the cited version. |
| Prior usage | A correction never edits a prior decision, field set, usage, staging lineage snapshot, or audit event. |
| Replay | Materialization reopens and verifies the retained object and streams the complete frozen candidate region; it never consumes the 200-row preview as data. |
| Row eligibility | Only rows classified `asset` under the snapshot's supported rule become staging rows. |
| S12 boundary | Materialization writes only batch + staging + mapping usage + audit. It never validates, applies, or writes `ProjectAssetLine`. |
| Transaction split | Confirm/reject and materialize are separate commands and transactions. A durable confirmation remains evidence even if later materialization fails. |
| Scope | Confirmation may create/reuse only customer profiles. Retrieval recognizes an already active/approved tenant organization template, but PR-004 cannot create or mutate one. |

The `memory_scope` choice reconciles the v1.4 “Remember mapping” UX intent with ADR 0030: human
confirmation is always durable evidence, while reusable customer memory is an explicit human
choice. Organization-template publication requires a later owner-approved RBAC/write contract.

## 4. Semantic role registry v1

The exact role set is:

```text
row_number
raw_asset_name
raw_description
unit
quantity
customer_unit_price
customer_amount
reference_value
appraiser_proposed_price
evidence_note
ignore
```

Registry version is `s13-pr-004-v1`. Role values are persisted strings protected by database check
constraints and domain validation.

### 4.1 Cardinality

- exactly one source column must map to `raw_asset_name`;
- each other non-`ignore` role may occur at most once;
- `ignore` may occur any number of times;
- every column position in the confirmed candidate region must occur exactly once in the mapping;
- a position outside the frozen candidate bounds is invalid;
- source column indices are absolute, one-based workbook positions, never header-text keys;
- duplicate and blank headers remain distinct positions;
- no transformation is allowed in v1 beyond safe scalar-to-string staging projection.

### 4.2 Deterministic header suggestions

Proposal matching uses NFKC, whitespace collapse, case-folding, and Vietnamese accent-insensitive
search. It is position-based and versioned. Required exact synonym families include:

| Role | Required normalized suggestions |
| --- | --- |
| `row_number` | `stt`, `so thu tu` |
| `raw_asset_name` | `ten tai san`, `ten vat tu`, `ten hang hoa` |
| `raw_description` | `dac diem`, `quy cach`, `mo ta` |
| `unit` | `dvt`, `don vi tinh` |
| `quantity` | `so luong`, `khoi luong` |
| `customer_unit_price` | `don gia`, `don gia khach hang` |
| `customer_amount` | `thanh tien`, `gia tri khach hang` |
| `reference_value` | `gia tham khao`, `gia tri tham khao` |
| `appraiser_proposed_price` | `gia td`, `gia tham dinh` |
| `evidence_note` | `ghi chu`, `chu thich`, `note` |

Unknown, ambiguous, duplicate-role, and blank headers are suggested as `ignore` and force review.
A human may explicitly confirm a blank-header position as `evidence_note`. A rule may not infer that
choice merely because the position is blank.

## 5. Fingerprint contract

`s13-pr-004-fingerprint-v1` is SHA-256 over canonical UTF-8 JSON (`sort_keys=true`, compact
separators, no NaN). The canonical input is built only after verifying the PR-003 snapshot seal and
contains:

```json
{
  "contract_version": "s13-pr-004-fingerprint-v1",
  "structure_rule_version": "s13-pr-003-v3",
  "sheet_name_normalized": "...",
  "header_start_row": 5,
  "header_end_row": 5,
  "data_start_row": 6,
  "min_column": 1,
  "max_column": 9,
  "header_labels_normalized_by_position": ["stt", "ten vat tu", null]
}
```

The fingerprint deliberately excludes filename, artifact UUID, generation, row count, `max_row`,
raw body values, and unrestricted cell samples. Organization and customer are enforced as retrieval
scope and stored beside the digest; they are not secret inputs to the hash. The access-controlled
profile/decision retains the exact mapping snapshot and safe positional header evidence required for
replay. General audit payloads retain only digest/IDs/versions/counts.

Only PR-003 `s13-pr-003-v3` snapshots are accepted by v1. Older snapshots remain readable evidence
but must be re-analyzed under v3 before mapping/materialization.

### 5.1 Similar-template contract v1

`s13-pr-004-similarity-v1` is a deterministic structural comparison, not fuzzy content learning.
Profiles are similar only when all of these hold:

- same organization and same customer, both active and integrity-verified;
- exact fingerprint differs;
- equal candidate width and equal header-span height;
- the multiset of non-null normalized header labels is equal;
- every non-null label used for positional remapping is unique on both sides.

Qualifying candidates are ordered by most recent confirmed time, then profile UUID for a stable tie
break. They are returned as review candidates with safe IDs/versions/digests. A mapping may be
derived positionally only through the unique normalized labels; blank, duplicate, added, or removed
labels remain `ignore`/unresolved and force review. Similar candidates never become an automatic
prefill and never bypass confirmation. No body values, filenames, or row counts enter similarity.

After customer exact/similar lookup, one active, approved organization-template profile with the
exact fingerprint may prefill a review-required proposal. Multiple matches fail closed. A non-exact
organization template is not selected in v1.

## 6. Persistence contract

All new tables are owned by `excel_import`, use UUID primary keys, PostgreSQL JSONB with the existing
SQLite JSON variant for unit tests, tenant-scoped foreign keys where a suitable parent uniqueness
exists, `RESTRICT` for evidence lineage, timezone-aware timestamps, and named indexes/constraints.

### 6.1 `ColumnMappingProfile`

Minimum persisted facts:

```text
id, organization_id, customer_id (retrieval scope; nullable only for organization template)
source_customer_id (non-null project/source lineage)
scope_type: customer | organization_template
profile_family_id, profile_version
status: candidate | active | superseded | rejected
template_fingerprint_sha256, fingerprint_contract_version
mapping_contract_version, mapping_digest_sha256
source_artifact_id, structure_snapshot_id
sheet_name, header_start_row, header_end_row, data_start_row
min_column, max_column
supersedes_profile_id
confirmed_by_user_id, confirmed_at
approved_by_user_id, approved_at (required only for organization template)
created_at
```

Invariants:

- `profile_version > 0`; first version in a family is 1 and later versions are contiguous under a
  locked family;
- an active profile is immutable except the single `active → superseded` transition performed in
  the same correction transaction that inserts its successor;
- the successor cites the immediately active profile; no stale or skipped correction is accepted;
- one active customer profile may exist for a given organization, customer, and exact fingerprint;
- one active organization-template profile may exist for a given organization and exact fingerprint;
- the two scope-aware partial unique indexes are required on PostgreSQL and mirrored for SQLite
  tests;
- customer scope requires `customer_id=source_customer_id` and null approval fields;
- organization-template scope requires null `customer_id`, a non-null `source_customer_id` equal to
  the customer on its source project/snapshot, plus non-null approver/time;
- profile source, structure snapshot, `source_customer_id`, project-derived customer, organization,
  and actor must agree; `customer_id` is additionally equal for customer scope and intentionally
  null for organization-template retrieval scope;
- S13-PR-004 has no application service that inserts or transitions an organization-template row;
  tests may seed an integrity-valid approved row to prove retrieval hierarchy only;
- `candidate`/`rejected` are reserved status values for reviewable persisted versions; v1 proposal
  alone does not create a profile;
- rows are never hard-deleted by application services.

### 6.2 `ColumnMappingField`

One immutable row per profile/source-column position:

```text
id, organization_id, profile_id
source_column_index, source_column_letter
original_header (nullable), normalized_header (nullable)
semantic_role, required_flag
proposal_source_kind, proposal_source_version, proposal_confidence (nullable)
created_at
```

`(profile_id, source_column_index)` is unique. `source_column_letter` is derived evidence, never an
identity key. No raw body cell is stored.

### 6.3 `ColumnMappingDecision`

Every proposal, confirmation, and rejection is an immutable append-only record:

```text
id, organization_id, customer_id, project_id, import_batch_id
source_artifact_id, structure_snapshot_id
decision_kind: proposal | confirmation | rejection
outcome: proposed | accepted | corrected | rejected
memory_scope: none | customer
proposal_decision_id (nullable self-reference)
profile_id (nullable), supersedes_profile_id (nullable)
actor_user_id, command_id, correlation_id
proposal_source_kind: human | deterministic_rule | ai_task
proposal_source_version, proposal_source_ref (nullable)
mapping_contract_version, template_fingerprint_sha256
mapping_snapshot, mapping_digest_sha256
before_summary, after_summary
reason_code, reason_text (bounded/nullable)
created_at
```

Rules:

- confirmation/rejection must cite a same-scope proposal;
- `memory_scope` is part of the immutable decision and canonical idempotency input; proposal and
  rejection store `none`, while confirmation stores the explicit caller choice;
- only `human` actor confirmation/rejection is accepted in S13-PR-004;
- a confirmation stores the full exact final mapping; rejection stores the rejected proposal
  digest/safe summary and cannot authorize usage;
- `before_summary`/`after_summary` are safe role/count/digest summaries, not unrestricted raw cells;
- `(organization_id, command_id, decision_kind)` is unique for idempotency;
- retrying the same command with identical canonical input returns the existing result without a
  second audit; reuse with different input returns `409/idempotency_key_reused`;
- no update/delete application method exists.

These fields are ADR 0033-compatible domain provenance. This PR does not create generic ADR 0033
tables. `proposal_source_ref` remains nullable and untrusted until a future registered task contract
can verify it.

### 6.4 `ColumnMappingProfileUsage`

One immutable successful materialization record for an exact source/snapshot generation:

```text
id, organization_id, customer_id, project_id, import_batch_id
source_artifact_id, structure_snapshot_id
confirmation_decision_id, profile_id (nullable), profile_version (nullable)
command_id, materialization_contract_version
mapping_contract_version, template_fingerprint_sha256
mapping_snapshot, mapping_digest_sha256
source_checksum_sha256, structure_digest_sha256
materialized_asset_row_count, created_by_user_id, created_at
```

The exact mapping snapshot is stored even when a remembered profile exists. `profile_id` is nullable
for confirmed mappings with `memory_scope=none`. The unique generation key is
`(organization_id, project_id, import_batch_id, source_artifact_id, structure_snapshot_id)`.
An identical retry returns the existing usage; a different decision/mapping for an already-used
generation returns `409/mapping_usage_conflict` and never replaces staging.

## 7. Canonical mapping snapshot

The exact mapping snapshot is canonical JSON with:

```text
contract_version
source_artifact_id + generation + checksum
structure_snapshot_id + version + rule_version + digest
template_fingerprint_sha256
selected candidate index and frozen bounds
ordered fields: source index, column letter, original header, semantic role
```

The mapping digest is SHA-256 of this canonical JSON. Input field order cannot affect it. The
service rejects unknown keys, duplicate indices, missing positions, unknown roles, non-canonical
scalar types, or any mismatch with the verified snapshot.

## 8. Application-service contracts

No route is added. Services accept an authenticated current user, explicit tenant/project/batch/
artifact/snapshot IDs, and a caller-supplied UUID `command_id`. They fail closed through scoped
queries; a cross-tenant identifier is indistinguishable from not found.

Future S13-PR-005 routes must require `workbench:edit` for proposal/confirm/reject/materialize and
`project:read` for retrieval. No PR-004 command publishes an organization template; that future
write path requires a separately approved RBAC/design contract. S13-PR-004 tests call the services
directly and prove tenant scope and actor organization consistency.

### 8.1 `ProposeColumnMapping`

The command requires an explicit `candidate_index`; there is no implicit fallback to candidate zero.
The index must identify a retained candidate in the verified snapshot. A later API may initialize
the UI from `proposed_candidate_index`, but the persisted proposal always records the explicit index.

1. Resolve the project, its customer, batch, current source artifact, requested snapshot, and
   explicit candidate index in one tenant scope.
2. Verify source state/current pointer/checksum and the complete snapshot digest/finalization seal.
3. Require rule version v3, resolve the selected candidate, and compute fingerprint v1.
4. Apply the authority hierarchy in order: exact customer profile, similar customer candidates
   under `s13-pr-004-similarity-v1`, approved exact organization template, deterministic registry.
5. If exactly one profile exists and its field set/digest verifies, use it as a prefill source and
   still mark the proposal `review_required=true`. This automatic prefill is permitted only for an
   exact customer match or one exact approved organization template.
6. Similar customer profiles are returned as ordered candidate provenance and may yield a partial
   positional suggestion, but they are never silently selected and always force review.
7. If no exact prefill exists, apply semantic registry v1 to unresolved positional headers.
   Unknown/ambiguous/blank/
   duplicate-role results force review.
8. More than one exact candidate, a corrupt profile, or a conflicting active mapping fails closed;
   no profile is chosen.
9. Insert one proposal decision and one `ColumnMappingProposed` audit atomically.

No proposal changes the batch or staging.

### 8.2 `ConfirmColumnMapping`

1. Scope and verify the cited proposal, current source/snapshot, actor, mapping snapshot, and digest.
2. Reject stale source pointer, changed project customer, changed snapshot seal, applied batch, or
   non-human actor.
3. Lock project, then batch. If `memory_scope != none`, also lock the cited active profile/family in
   deterministic UUID order.
4. Insert a confirmation decision. Outcome is `accepted` when mapping digest equals the proposal and
   `corrected` otherwise.
5. For `memory_scope=none`, leave `profile_id=null`.
6. For `memory_scope=customer`:
   - reuse the single exact active profile when its mapping digest is identical;
   - create family version 1 when no active conflict exists;
   - for a changed mapping or moved-column fingerprint, require the caller to cite the current
     active `supersedes_profile_id`, create the next family version, and atomically mark the cited
     profile superseded;
   - on a stale/missing/duplicate conflict, return review-required conflict with no partial writes.
7. Reject every other memory scope. In particular, confirmation cannot create, approve, activate,
   correct, or supersede an organization-template profile.
8. Insert one `ColumnMappingConfirmed` audit atomically.

Confirmation does not create usage, staging, validation, or official rows.

### 8.3 `RejectColumnMapping`

Verify the same scope/current-generation/actor conditions, insert one rejection decision citing the
proposal, and insert one `ColumnMappingRejected` audit atomically. It changes no profile, batch,
staging, or official row.

### 8.4 Hierarchical profile retrieval

Retrieval accepts verified current snapshot scope, computes fingerprint/similarity v1, and returns a
typed result with at most one exact customer profile, ordered similar customer candidates, and at
most one exact approved organization template. It never crosses organizations or customers for the
first two tiers. Multiple exact rows, invalid lineage, wrong scope, missing organization-template
approval, non-active status, field/digest mismatch, or an unverified snapshot fails closed. The
proposal service alone applies the ordered hierarchy; a repository query must not silently choose.

### 8.5 `MaterializeConfirmedMappingToStaging`

Preflight before object I/O:

1. scope project/customer/batch/current artifact/snapshot/confirmation;
2. require a human `accepted|corrected` confirmation, exact digest agreement, supported versions,
   current source pointer, available artifact, unapplied batch, and no conflicting usage;
3. freeze primitive source and structure fingerprints.

Object I/O occurs without database row locks:

4. use/refactor the PR-003 verified temporary-source context; stream in bounded chunks, verify size,
   checksum and detected format, and always unlink the temporary file;
5. open the approved `.xls` or `.xlsx` adapter and iterate the selected sheet once;
6. replay all rows within the frozen candidate bounds, reclassifying each row with the stored v3
   rule semantics; do not reopen per row and do not use preview;
7. write canonical, JSON-safe staging candidates for `asset` rows to a caller-owned temporary spool
   in bounded chunks while computing row count and spool digest. Do not write the database before
   serialization locks. The spool must be unlinked after open/read/adapter/spool/lock/insert/commit
   failure and after success.

Serializable finalization:

8. lock `Project FOR UPDATE`, then `ProjectAssetImportBatch FOR UPDATE`; refresh both;
9. lock the source artifact and confirmation decision in deterministic order; re-read and verify the
   snapshot seal and compare all frozen fingerprints;
10. re-check no usage/conflict and batch is not `applied`;
11. inside one transaction, replace this batch's staging rows and stream the verified temporary
    spool into bounded database insert batches; then insert one usage and set:
    - `source_filename` to the verified artifact filename,
    - `source_sheet_name` to the confirmed sheet,
    - `status=parsed`,
    - `total_rows=materialized_asset_row_count`,
    - `valid_rows=invalid_rows=warning_rows=0`;
12. insert exactly one `ConfirmedMappingMaterialized` success audit and commit;
13. on any parse/classification/spool/flush/commit failure, roll back. Existing staging/batch
    counters and status remain unchanged. S13-PR-004 writes no failure audit; stale state therefore
    cannot overwrite or append failure evidence to a newer generation.

Materialization never calls the S12 upload parser, validation, or Apply service.

### 8.6 Role-to-staging projection

| Semantic role | Existing staging destination |
| --- | --- |
| `raw_asset_name` | `proposed_asset_name` |
| `raw_description` | `proposed_description` |
| `unit` | `proposed_unit` |
| `quantity` | `proposed_quantity` |
| `customer_unit_price` | `proposed_raw_price` |
| `appraiser_proposed_price` | `proposed_appraised_unit_price` |
| `row_number`, `customer_amount`, `reference_value`, `evidence_note` | exact `mapped_values` only |
| `ignore` | positional `raw_values` only |

`raw_values` preserves every candidate-region position using stable positional keys, including
blank and duplicate headers, with deterministic JSON-safe scalar encoding. `mapped_values` uses
semantic role keys only. `proposed_currency`,
`proposed_review_status`, and `proposed_validation_status` remain null. Apply v1 continues to exclude
`proposed_appraised_unit_price`; this PR does not change that rule.

Scalar conversion must be deterministic and safe for JSON/date/decimal values. Formula text,
macros, links, or code are never evaluated.

## 9. Audit and privacy cardinality

| Outcome | Domain writes | Success audit | Failure audit |
| --- | ---: | ---: | ---: |
| not found, unauthorized, invalid input, stale state, conflict | 0 | 0 | 0 |
| idempotent identical retry | existing only | existing only | 0 |
| proposal success | 1 decision | exactly 1 | 0 |
| confirm/reject success | 1 decision + optional profile/version | exactly 1 | 0 |
| materialize success | staging replacement + 1 usage | exactly 1 | 0 |
| engine/spool/flush/commit failure | rollback | 0 | 0 |
| stale fingerprint after failure | 0 | 0 | 0 |

S13-PR-004 emits no failure audit. Success audit payload keys are command-specific and allowlisted.
They may include only organization,
project/batch/artifact/snapshot/decision/profile/usage IDs, contract/rule/profile versions, digests,
source generation, outcome, role counts, and materialized asset-row count. They must not include
filenames, original/normalized headers, cell values, mapping field values, business names, reason
free text, exception text, paths, object keys, or secrets.

## 10. Stable failure contract

Application services use structured errors with Vietnamese diacritics. Minimum stable codes:

```text
mapping_source_not_current
mapping_source_not_available
mapping_structure_not_found
mapping_structure_integrity_failure
unsupported_structure_rule_version
mapping_candidate_invalid
mapping_role_invalid
mapping_role_cardinality_invalid
mapping_proposal_not_current
mapping_confirmation_required
mapping_profile_conflict
mapping_profile_stale
mapping_profile_integrity_failure
mapping_usage_conflict
mapping_materialization_stale
mapping_batch_already_applied
idempotency_key_reused
```

Cross-tenant/nonexistent resources remain 404-compatible and do not reveal foreign existence.
Conflicts/stale state are 409-compatible. Integrity failures are fail-closed 500-compatible unless a
documented client mismatch makes 409 appropriate. No raw parser/SQL/storage exception is returned.

## 11. Migration and compatibility

- New Alembic revision must descend from `a3b4c5d6e7f8`.
- No backfill may fabricate mapping decisions/usages/profiles for historical batches.
- Existing batches simply have no PR-004 usage until a confirmed v2 mapping is materialized.
- Upgrade must create all constraints/indexes/FKs deterministically; model and migration schemas
  must match.
- Downgrade removes only PR-004 tables/indexes/constraints. It is destructive only to PR-004 data
  and must not change source artifacts, snapshots, staging, or official lines.
- Prove PostgreSQL upgrade → downgrade → upgrade on an isolated database and regular upgrade from
  the current head.

## 12. Required evidence matrix

The implementation is not complete without tests for:

1. semantic mappings for `TÊN VẬT TƯ`, `KHỐI LƯỢNG`, `GIÁ TĐ`;
2. explicit human confirmation of blank-header I as `evidence_note`;
3. same organization/customer/exact template retrieves the one active profile;
4. deterministic similar-template retrieval returns review candidates without automatic prefill;
5. an integrity-valid exact approved organization template is retrieved only after customer
   exact/similar tiers and still requires confirmation; missing approval fails closed, and PR-004
   exposes no template write command;
6. no cross-customer or cross-organization retrieval;
7. moved columns require review and create the correct new snapshot/profile version when explicitly
   superseding;
8. duplicate/conflicting/stale active profiles fail closed under PostgreSQL concurrency;
9. correction never rewrites prior decisions, fields, usages, audits, or staging lineage snapshot;
10. proposal and rejection cannot materialize;
11. idempotent command retry and idempotency-key input mismatch;
12. `.xls`/`.xlsx` parity for identical value-only content;
13. more than 200 physical rows proves full replay and no preview truncation;
14. section/subtotal/total/note/empty/unresolved rows do not become staging assets;
15. source checksum/object change, source pointer drift, snapshot payload/seal tamper, project customer
    drift, and applied batch all fail closed;
16. staging replacement/counters/status/usage/audit commit atomically;
17. injected adapter, spool, flush, savepoint/release, outer commit, and stream-close failures preserve prior
    staging and leave no false success evidence;
18. lock order and concurrent materializations on PostgreSQL produce at most one usage;
19. audit payload exact-key/privacy assertions and event cardinality;
20. zero `ProjectAssetLine` writes and zero Validate/Apply invocation;
21. all S12 Apply regression tests remain unchanged and pass;
22. Alembic upgrade/downgrade/upgrade and model/migration parity;
23. no skipped tests in the exact-head CI claim.

Local SQLite is development evidence only. PostgreSQL CI and exact-head independent audit are
required before Ready/merge.

## 13. Runtime file boundary

Allowed runtime change set:

```text
backend/alembic/versions/<new>_create_column_mapping_memory.py
backend/app/modules/excel_import/models.py
backend/app/modules/excel_import/domain/column_mapping.py
backend/app/modules/excel_import/application/column_mapping_service.py
backend/app/modules/excel_import/application/verified_source.py        # optional extraction only
backend/app/modules/excel_import/application/workbook_structure_service.py  # narrow helper use only
backend/app/modules/excel_import/domain/workbook_structure.py          # public full-row replay helper only
backend/app/modules/project_master_data/models.py                       # only if composite lineage constraint is required
backend/tests/test_s13_pr_004_column_mapping.py
backend/tests/test_s13_pr_004_column_mapping_postgresql.py              # optional focused PG split
```

The coder may add `__init__.py` exports only when required. Any API/schema/frontend/worker/CI,
dependency, Apply, general project model, or unrelated test change is a stop condition. Generated
cache/coverage/environment files are forbidden.

## 14. Evidence gate and handoff

Required order:

```text
frozen design commit
→ independent Sol Max design audit PASS
→ publish exact design tree on Draft PR
→ Sol High coding packet acknowledged at exact baseline/design commit
→ runtime implementation + focused tests
→ independent code review / adversarial probes
→ exact-head PostgreSQL CI with zero skips
→ Codex Lead final evidence review
→ owner authorization for Ready/merge
```

The implementer may not issue the independent PASS verdict. On 2026-07-19 the owner removed the
Antigravity gate; internal independent review, exact-head CI, and Codex Lead evidence review remain
mandatory.
