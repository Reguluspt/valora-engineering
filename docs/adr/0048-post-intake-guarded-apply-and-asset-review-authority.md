# ADR 0048: Post-Intake guarded Apply and Asset Review authority

## Status and authority

**PROPOSED / PRODUCT OWNER DECISION REQUIRED.** Task `VALORA-TASK-OS-G2-A1-ENTRY-GUARD-CASESTATE-AUTHORITY-RATCHET`, [Issue #73](https://github.com/Reguluspt/valora-engineering/issues/73). Baseline `main=a293395c53ab12aa27cac86d82046a6a9f59983b`, exact-main CI #533 SUCCESS; 2026-10-02. This ADR and the [candidate Case State contract](../implementation/VALORA_OS_G2_ASSET_REVIEW_CASE_STATE_CONTRACT.md) require the same Product Owner decision. Neither authorizes runtime implementation.

The [accepted A0 record](../plan/VALORA_OS_G2_APPRAISAL_CORE_ENTRY_AUTHORITY_PROPOSAL.md) is binding. [ADR 0029](0029-excel-staging-apply-command-and-lineage.md) and [staging contract §15](../design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md#15-s12-pr-004-excel-staging-apply-command--provenance-v1) remain frozen historical v1 authority. [ADR 0028](0028-official-mutation-command-and-atomic-audit-gate.md) remains binding for restricted Workbench edits. This is a proposed versioned successor, not an amendment to their historical bodies.

## Context verified at the baseline

[Apply](../../backend/app/modules/excel_import/application/apply_staging.py) already enforces confirmation, DRAFT-only, non-empty/all-valid staging, registered mapping, append-only lineage, atomic success audit and re-Apply conflict. It does not prove Official Intake, committed Result or selected mapping lineage. [Validation](../../backend/app/modules/excel_import/application/validate_staging.py) locks the batch, changes staging validation only and rejects applied batches. The [manual creation route](../../backend/app/api/projects.py) uses `project:update`, creates lines without staging lineage and does not serialize creation under a Project lock. These paths do not implement the successor controls below.

The current [Case State provider](../../backend/app/modules/project_master_data/application/case_state_projection.py) stops at the four-stage Pre-case prefix. An Intake commit proves the official boundary, not Apply or Asset Review completion.

## Proposed decision

### D1. One mutation, versioned guard, no legacy bypass

Keep `ApplyProjectAssetImportBatch` as the sole staging → `ProjectAssetLine` promotion command. Apply is synchronous, explicitly human-confirmed, a separate transaction strictly after Official Intake. Result generation and Intake never auto-Apply. No second promotion command, worker or direct SQL authority is introduced.

Proposed successor identifier: `contract_version=s12-post-intake-guarded-apply-v2`. On the existing Apply route, the successor request is exactly `contract_version`, `confirm=true`, and `expected_case_version` (opaque 64-character lowercase SHA-256 token from the candidate Case State contract). Actor, tenant, Project and batch scope are server-derived. Missing/unknown version or a v1 body is rejected before mutation once the successor runtime is activated. Every callable adapter to Apply, including the legacy endpoint/internal entry, must use the same guard; keeping a callable naked v1 path is forbidden. Until separately authorized runtime implements that activation, v1 remains current runtime and this ADR is only proposed.

Active human actor/organization and effective `workbench:edit` are required; no new permission or role grant. No active Workbench session is required for Apply. Recheck authorization server-side independently of CAS. Preserve safe 404 for inaccessible/cross-tenant/wrong-Project targets, explicit confirmation and `Project.status=DRAFT`.

### D2. Exact server-derived entry predicate

Under D4 locks, resolve one tenant/Project-scoped Intake commit and its immutable committed Result. Never select a Result/batch by client IDs, recency, legacy workflow state or screen visits. All conditions below must hold:

1. The Intake's Result identity, version, content checksum and source-snapshot digest equal the stored Result. Its typed canonical lineage manifest and the named immutable Analysis snapshot validate; recompute their canonical digests rather than trusting client digests. The committed Result remains the authoritative selected Result for this entry.
2. Result/Analysis lineage names the explicit Project current batch, its current source artifact ID/generation/checksum and available state, structure identity/digest, confirmed mapping decision/digest and profile usage/digest. The server's current mapping selection and `current_staging_usage_id` agree with that exact materialization. A historical retained usage is not current authority. Nullable historical Customer snapshots are not rewritten or compared to a newly bound Customer as an invented lineage condition.
3. The selected staging set is non-empty and equals the committed Result/Analysis selected source-row locator set one-to-one. Check tenant/Project/batch/staging-usage ownership, unique row identities and source locators, and typed canonical materialized-input equality/digest. Missing, extra, duplicate or changed rows fail closed. Validation output may change under D3; source, selected membership and mapped business inputs may not.
4. Only that batch is eligible: `ready_for_review`, every row `valid`, counters equal actual row states, no pending/invalid/warning row. Resolve registered fields and ACTIVE references with ADR 0029's exact lookup/Decimal/description rules. No partial Apply, wildcard copy or forbidden appraisal/review/validation spreadsheet fields.
5. No initial set seal or pre-existing official line exists. Any pre-existing/unlinked manual line is an entry conflict, never silently included, ignored, linked or deleted. An already applied batch is a re-Apply conflict, even if its lineage matches.
6. No open scoped `BLOCKING` issue; project targets and official-line targets must resolve to this tenant/Project. Open `WARNING` issues remain non-blocking. A staging row with warning status still blocks Apply under ADR 0029; issue severity is not converted.
7. Recompute the successor `case_version` from the same locked authority and require exact equality with `expected_case_version`. Missing, stale or future tokens cannot authorize a write. The token is a precondition, never a substitute for conditions 1–6 or current permission.

Invalid identity/scope or corrupt pointers fail closed without exposing inaccessible IDs. No guard failure repairs authority or modifies staging/official data.

### D3. Bounded validation after Intake

Allow validation/re-validation only on the already-selected, lineage-matching staging set, while the Project remains DRAFT and before Apply, in existing source states `parsed`, `validation_failed`, `ready_for_review`. Recheck Intake/Result/current source/mapping/usage/row identity and exact-version preconditions under the same Project-first serialization. Validation may change only validation outputs, counters and allowed batch state, with existing validation audit/failure protection. It never mutates official lines or rematerializes rows.

Source upload, mapping mutation, current-batch replacement and new Pre-case lineage remain closed after Intake. Applied staging remains immutable; validation of an applied batch is rejected. A lineage mismatch is not recoverable by re-validation. No automatic retry, new upload, new batch or mapping route is offered as recovery from this ADR.

### D4. Lock order, CAS and concurrency

Mutation lock order is: scoped **Project FOR UPDATE → selected batch FOR UPDATE → staging rows FOR UPDATE ordered by `(source_row_number, id)` → existing official lines FOR UPDATE ordered by `id` → inserts**. Project lock governs mutable current pointers, set membership and authority generations; immutable Intake/Result/Analysis/mapping facts are read and verified under it. Lock all existing Project lines for the no-pre-existing-lines check, not just linked rows.

All writers of authority used by the guard must first acquire the same scoped Project lock: validation and its failure recovery, Apply and its failure recovery, manual/membership mutations, official-line edits, Project status/pointer changes, and scoped ValidationIssue changes. Child locks follow the order above when needed; never acquire Project after a batch/line lock. Issue writes resolve their Project first; reference resolution must remain stable through mapping/commit. Project serialization prevents phantom line/issue insertion and closes the empty-set check race. Existing adapters that do not comply are implementation prerequisites, not proof that current runtime is safe.

Compute CAS after locks from a consistent authority view using the identical resolver/serialization as the read contract. All changes affecting its inputs must advance an authoritative version or alter the canonical input; validation attempts that commit a new validation generation invalidate prior tokens even if row verdicts are identical. Hold locks through the final outer commit. Re-resolve permission and reference eligibility before committing; successful Apply never changes Project workflow status.

| Race | Required outcome |
| --- | --- |
| Apply vs Apply | First winner creates one exact set; loser sees `applied`/seal and returns re-Apply 409, zero duplicates/success audit. |
| Validation vs Apply, both orders | Validation winner advances generation, so old Apply token conflicts; Apply winner makes validation reject applied staging. |
| Manual creation vs first Apply | Manual path is closed before seal; no race may insert an unlinked line or evade entry check. Pre-existing rows cause conflict. |
| Line edit vs Apply/projection CAS | Project-first serialization plus ADR 0028 exact line version; any winning edit invalidates the other stale token. |
| Project status/currentness vs Apply | Winner is re-read under Project lock; non-DRAFT, changed lineage or token mismatch denies Apply. |
| Issue mutation vs Apply | Winner is included in locked blocker/token checks; an open blocker cannot arrive between eligibility and commit. |
| Failure recovery vs newer mutation | Roll back first, reacquire locks in the same order; mismatch suppresses failure audit and any stale write. |

### D5. Atomic seal and authoritative-set lifecycle

Successful Apply creates one line per selected staging row in ADR 0029 stage order, with unique `source_staging_row_id` and exact batch lineage. New lines start `pending` / `unvalidated`, using the model's initial row version; appraised values are not imported. All lines, lineage, a durable versioned **initial-set seal**, batch `applied` and exactly one success audit commit together or all roll back.

The seal binds tenant/Project, Intake/Result identity and digests, selected batch/source/mapping/staging usage, exact ordered staging-row → line correspondence and initial membership version. It is a domain fact, not a UI selection, audit-only reconstruction or persisted Case State. Physical storage/schema design is deferred to a separately authorized implementation contract. Existing v1 applied batches cannot be retroactively declared guarded/sealed based on matching counters or a screen visit; they fail closed pending separately accepted remediation.

Before first guarded Apply completes, direct/manual official-line creation is closed for this entry lifecycle. After the initial set exists, additions/removals/replacements require a separately accepted explicit audited domain membership command/contract. Until that contract exists, such changes remain closed. Legacy naked manual creation must never silently create an excluded official line or alter membership. Non-membership line edits remain under existing permissions and ADR 0028 where restricted.

Any future accepted membership command must atomically update authoritative membership/version and invalidate the prior completion proof. The changed, non-empty set must again satisfy full accepted+valid coverage with no blocker/stale lineage. Missing, extra, unlinked or replaced rows without that command cause fail-closed divergence. This ADR defines no deletion/replacement mechanics, new permission, correction batch or second staging promotion path.

### D6. Replay, denial, audits and unknown responses

Preserve ADR 0029 state-based exact-once semantics: a successful Apply is not replayed as a new success receipt; every subsequent Apply on the applied batch returns 409 with zero writes/success audit. No new command-ID replay policy is proposed. Unique staging lineage and the atomic seal reinforce exact-once creation.

| Denial/failure | HTTP / safe class | Success / failure audit |
| --- | --- | --- |
| Missing/non-true confirmation | 400 `apply_confirmation_required` | 0 / 0 |
| Missing/unsupported successor contract or malformed/missing CAS | 400 `apply_contract_invalid` | 0 / 0 |
| Inactive/unauthorized actor | Established authentication/authorization denial | 0 / 0 |
| Inaccessible/wrong-scope target | Safe 404 | 0 / 0 |
| Project not DRAFT | 400 `apply_project_not_draft` | 0 / 0 |
| Intake absent, lineage/currentness mismatch, CAS mismatch | 409 `apply_intake_required`, `apply_lineage_conflict`, `apply_version_conflict` respectively | 0 / 0 |
| Pre-existing/manual lines, seal conflict, open blocker | 409 `apply_entry_conflict` | 0 / 0 |
| Wrong batch state/re-Apply or non-ready rows | 409 existing `apply_state_not_allowed` / `apply_rows_not_ready` | 0 / 0 |
| Mapping invalid after confirmed/scoped/eligible attempt | 400 `apply_mapping_invalid` | 0 / exactly 1 if extended fingerprint matches |
| Engine/flush/savepoint/audit/outer-commit failure | 500 `apply_engine_failed` | 0 / exactly 1 if fingerprint matches and failure audit persists |
| Stale failure fingerprint or failure-audit persistence failure | Safe failure; preserve newer authority | 0 / 0 |
| Successful Apply | Existing created-lines response | exactly 1 / 0 |

Preserve batch/staging/counters/pre-existing lines exactly on every Apply rejection/failure; no `apply_failed` state. Failure recovery uses ADR 0029's full generation fingerprint extended with locked Intake/Result/current source/mapping/usage, membership/seal, relevant issues and CAS inputs. Raw/mapped values may be hashed/compared internally, never logged. An unknown outer-commit outcome must be reconciled before emitting failure audit; a committed seal/applied state suppresses failure recording.

Keep command/event names `ApplyProjectAssetImportBatch`, `ProjectAssetImportBatchApplied`, `ProjectAssetImportBatchApplyFailed`. V2 audit payloads use the exact v2 contract identifier. Proposed success allowlist: v1 success keys plus `official_intake_commit_id`, `preliminary_result_artifact_id`, `entry_lineage_sha256`, `authoritative_set_sha256`, `membership_version`, `expected_case_version`. Proposed failure allowlist: v1 failure keys only, with the v2 identifier. No raw cells, proposed values, SQL, paths, stacks, secrets or bulk line-ID arrays. Audit failure rolls back all official effects.

After timeout/unknown response, read fresh scoped batch, exact seal/membership and success evidence. Exact applied/sealed lineage is the committed outcome; proceed to review without another Apply. If still eligible/unapplied with no committed seal, refresh Case State, obtain new explicit confirmation and submit its current token. Ambiguous/divergent outcome gives no Apply route until separately accepted recovery. The receipt read never infers success from a failure response or reopens applied staging.

### D7. Case State boundary

The companion contract proposes `ASSET_REVIEW` predicates, deterministic actions, version inputs and a five-stage current-stage bound using existing public wire enums. A0's COMPLETE condition is unchanged: full authoritative-set coverage, every line accepted and valid, no blocker or stale lineage. No appraised price or later-stage predicate is added.

Until this successor authority is accepted **and** its provider/runtime is implemented and authorized, retain current runtime: downstream `NOT_AVAILABLE`, four-stage `current_stage` bound, and `NO_AUTHORIZED_DOWNSTREAM_ACTION` after the completed prefix absent an existing higher-priority blocker. Acceptance of these documents alone does not switch capability or permit mutation.

## Rejected alternatives and required gates

Reject naked v1 Apply, promotion before Intake, auto-Apply, a second mutation, partial staging promotion, client-supplied lineage/membership, automatic manual-line inclusion/exclusion, audit-only set reconstruction and completion inferred from a screen/workflow/one accepted line. A new batch correction shortcut conflicts with the closed post-Intake lineage boundary; further membership/correction authority is separate.

**Product Owner acceptance is required for D1–D7 as one coherent successor**, especially the request/CAS identifier, lock participation, zero-audit guard denials, sealed membership lifecycle and companion state/action mapping. No accepted A0 point is reopened. Gate Owner must then assign a separate bounded runtime task.

Required future runtime evidence: PostgreSQL races in D4 both orders with exact audit/cardinality and zero skips; field/lineage/tenant/confirmation/permission/CAS mismatch matrix; rollback/audit/unknown-response faults; manual bypass closure; immutable applied staging; project-wide coverage/membership invalidation; deterministic snapshot hashing/actions and wire compatibility. Runtime tests are N/A for this docs-only task.
