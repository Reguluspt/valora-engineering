# OS-G2 A0 — Appraisal Core entry authority record

**Status:** ACCEPTED PRODUCT OWNER AUTHORITY for the decisions in the accepted-decision section below. Their runtime enforcement remains unimplemented. Other candidate predicates and route examples are not accepted authority. **Baseline:** `main` at `81b5366d580681a768daaee6b7cacb54d1a8cc5e`, exact-main CI #530 SUCCESS. **Scope:** Official Intake → first official `ProjectAssetLine` set → `ASSET_REVIEW`; later OS-G2 stages are outside this record.

## Accepted Product Owner decisions

Accepted in the Product Owner comment on PR #72 (2026-10-01):

1. Keep S12 `ApplyProjectAssetImportBatch` as the single authoritative staging → `ProjectAssetLine` promotion mutation. Do not create a second promotion command.
2. Apply is a separate explicit human-confirmed transaction strictly AFTER Official Intake. Intake/Result generation must never auto-Apply.
3. Before runtime, ratchet ADR 0029 so Apply atomically proves committed Result → current batch → source → confirmed mapping/current staging usage → exact staging set → exact version/currentness under server authority.
4. Post-Intake validation/re-validation is allowed only for the already-selected staging set needed for this entry boundary. Source upload, mapping mutation and new Pre-case lineage remain closed.
5. The initial Appraisal Core authoritative set is the exact non-empty one-to-one Apply lineage from the committed Result's selected staging rows.
6. `ASSET_REVIEW=COMPLETE` requires project-wide coverage of that authoritative set: every covered line is `review_status=accepted` AND `validation_status=valid`, with no blocking issue and no stale lineage. Screen visits, legacy Project status, workflow state and Official Intake alone do not complete it.
7. Pre-existing/unlinked manual official lines fail closed at Appraisal Core entry. They must not be silently included or silently ignored.
8. Case State remains `NO_AUTHORIZED_DOWNSTREAM_ACTION` until the successor ADR/Case State contract is accepted and the provider/runtime is implemented.

Additional accepted authority requirements: the successor contract must explicitly define later manual/additional-line behavior and how authoritative-set membership changes invalidate prior `ASSET_REVIEW` completion; tenant/RBAC/idempotency/audit/exact-version fail-closed rules remain binding; ADR 0028 Human Commit Gate remains binding for restricted Workbench fields.

These decisions authorize this authority record only. They do not authorize runtime implementation. The candidate states, routes and implementation details below remain proposals unless explicitly included above or accepted in the successor ADR/Case State contract.

## Verified facts and gap

- The [roadmap](../VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md) places `ASSET_REVIEW` first in OS-G2. The [PR-01 authority matrix](../implementation/VALORA_UIUX_V2_3_PR01_CASE_STATE_PROJECTION_CONTRACT.md) §§3–5 marks its completion predicate `UNMAPPED`; missing capability must be `NOT_AVAILABLE`, and blocking issues outrank ordinary actions. The [Orchestration Hub addendum](../design/VALORA_UIUX_HANDOFF_v2.3_CASE_OVERVIEW_ORCHESTRATION_BASELINE_ADDENDUM.md) requires one fact-derived primary Next Action and semantic route keys.
- `ProjectOfficialIntakeCommit` freezes the current Result identity/version/checksums, not asset lines. The [Intake service](../../backend/app/modules/project_master_data/application/official_intake_service.py) inserts no `ProjectAssetLine`; its [test](../../backend/tests/test_pr01_official_intake_service.py) asserts that Project status stays `DRAFT`. [G1.1K evidence](../implementation/G11K_PRECASE_PRODUCT_CLOSURE_E2E_EVIDENCE.md) ends with `NO_AUTHORIZED_DOWNSTREAM_ACTION`. The [current Case State provider](../../backend/app/modules/project_master_data/application/case_state_projection.py) leaves every downstream stage unavailable; this proposal does not claim otherwise.
- Confirmed mapping materialization owns S12-compatible staging but sets its batch to `parsed`; [staging validation](../../backend/app/modules/excel_import/application/validate_staging.py) must make it `ready_for_review`. [ADR 0029](../adr/0029-excel-staging-apply-command-and-lineage.md) and the [staging contract](../design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md) §15 make human-confirmed, `DRAFT`-only S12 Apply the existing staging → official-line command. It appends one line per valid staged row, with unique staging-row lineage, atomic audit and `applied` batch state. Its [current handler](../../backend/app/modules/excel_import/application/apply_staging.py) checks project/batch/row readiness but does **not** check Intake, committed Result or selected mapping lineage. Thus the existing endpoint alone cannot certify *which* Pre-case batch becomes the initial official set.
- [ADR 0028](../adr/0028-official-mutation-command-and-atomic-audit-gate.md) requires exact-version, human-confirmed draft commit for restricted Workbench fields. Apply may create `description`, but spreadsheet appraisal price and review/validation decisions are excluded; new lines start `pending` / `unvalidated`. The [line model](../../backend/app/modules/project_master_data/models.py) has those statuses and `row_version`.
- A separate [manual line creation route](../../backend/app/api/projects.py) can create official lines with `project:update` and without S12 staging lineage. The current authorities do not say how such lines join the *initial* Pre-case-derived set; the proposed entry guard therefore treats pre-existing lines as a conflict pending explicit policy.

## Implementation boundary — accepted authority, runtime pending

The accepted sequence is: selected mapping materializes staging → Analysis/Result → **Official Intake commits** → allowed validation/re-validation of only the already-selected staging set → human explicitly confirms **Apply** → official-line review. Apply remains a separate transaction strictly *after* Intake; Intake/Result generation never auto-Applies. Source upload, mapping mutation and new Pre-case lineage remain closed. ADR 0029 must be ratcheted before runtime to enforce the accepted lineage and exact-version conditions atomically. ADR 0028 remains binding for restricted Workbench fields.

The following accepted entry condition is not implemented in the current Apply handler: it must prove committed Result → current batch → source → confirmed mapping/current staging usage → exact staging set → exact version/currentness under server authority, atomically, and fail closed. The initial authoritative set is the exact non-empty one-to-one Apply lineage from the committed Result's selected staging rows. Pre-existing/unlinked manual official lines fail closed at entry.

The successor ADR 0029 ratchet and accepted Case State contract are prerequisites to runtime. They must preserve existing ADR 0029 and ADR 0028 controls and spell out how the accepted lineage, currentness, later manual/additional-line behavior, set-membership invalidation and Case State behavior are enforced. This record does not define extra command semantics or change the existing Apply v1 contract.

## Candidate `ASSET_REVIEW` predicate

**Accepted COMPLETE predicate:** project-wide coverage of the accepted initial authoritative set; every covered line has `review_status=accepted` AND `validation_status=valid`, with no blocking issue and no stale lineage. Screen visits, legacy Project status, workflow state and Official Intake alone do not complete it. Initial membership is the exact non-empty one-to-one Apply lineage from the committed Result's selected staging rows. Pre-existing/unlinked manual official lines fail closed at entry. The successor contract must define later manual/additional-line behavior and how membership changes invalidate prior completion.

The remaining candidate state details below are not accepted Product Owner authority. The successor Case State contract must accept, replace or omit them before runtime; only the `COMPLETE` predicate and Case State hold in the accepted-decision section above are binding here.

| Candidate state | Proposed predicate (evaluate in this precedence) |
| --- | --- |
| `NOT_AVAILABLE` | Candidate only; successor Case State contract must define. Accepted current behavior remains `NO_AUTHORIZED_DOWNSTREAM_ACTION` until successor contract acceptance and provider/runtime implementation. |
| `BLOCKED` | Candidate only; successor Case State contract must define from accepted lineage/set authority. |
| `STALE` | Candidate only; successor Case State contract must define from accepted lineage/set authority. |
| `IN_PROGRESS` | Candidate only; successor Case State contract must define from accepted lineage/set authority. |
| `COMPLETE` | Accepted as stated above: project-wide coverage of the initial authoritative set; every covered line accepted and valid, with no blocking issue or stale lineage. |

An open blocker outranks stale and ordinary pending actions; authoritative stale outranks otherwise valid progress. Unknown issue targets fail closed at the tenant/project boundary. `Project.status`, workflow enum, page visits, preliminary Analysis confirmations and Official Intake alone never make `ASSET_REVIEW` complete.

## Case State and one Next Action after Intake

Accepted Case State rule: remain `NO_AUTHORIZED_DOWNSTREAM_ACTION` until the successor ADR/Case State contract is accepted and the provider/runtime is implemented. The route keys and stage transitions that follow are unaccepted examples from the prior proposal; the successor Case State contract must decide them before runtime.

| Fresh authoritative state | Proposed primary Next Action / typed context |
| --- | --- |
| Before successor Case State contract and provider/runtime | Accepted `NO_AUTHORIZED_DOWNSTREAM_ACTION`; no OS-G2 route is authorized. |
| After provider/runtime | Not defined by this accepted decision; successor Case State contract must specify states and semantic actions. |

The accepted decision requires the successor Case State contract before implementation. It must preserve tenant/RBAC/idempotency/audit/exact-version fail-closed rules. Wire enums, `case_version` inputs, precedence beyond the accepted COMPLETE blockers/staleness, typed contexts and semantic route keys remain for that successor contract; this record does not settle them.

## Controls, rejected alternatives and decision gate

- **Tenant/RBAC:** resolve Project, Intake, Result, batch, usage, staging, line and issue in one server-derived organization/Project scope; inaccessible cross-tenant objects return safe `404`. Keep Apply and restricted line commits behind `workbench:edit`; frontend visibility grants nothing. [G1.1K evidence](../implementation/G11K_PRECASE_PRODUCT_CLOSURE_E2E_EVIDENCE.md) records standard owner/appraiser grants, not a new role policy.
- **Concurrency/idempotency/audit:** preserve ADR 0029 Project → batch → staging locks, generation fingerprint, unique `source_staging_row_id`, all-or-nothing lines/lineage/batch/success audit, stale-failure suppression and safe failure payloads. Preserve ADR 0028 exact line `row_version`, human confirmation and atomic audit for restricted edits. The successor ADR must define atomic expected-version checks, new guard-denial audit cardinality and races with validation, another Apply, official-line creation/edit and Project status change; no raw cells or client secrets in audit.
- **Reject** Apply before Intake (official rows precede the official boundary), Intake auto-Apply or direct Result→line copy (bypasses human S12 mapping/validation/Apply), a second promotion command or direct SQL (duplicate mutation authority), naked v1 Apply on any ready batch (no committed-lineage gate), and completion from any single line, screen visit or `DRAFT` status (false project-wide completion).

**OS-G2 A0 Product Owner decision required: NO — accepted in the PR #72 comment. Successor ADR 0029 ratchet and Case State contract required before runtime: YES.** Runtime guard/provider, API/UI routing and acceptance remain unimplemented and unauthorized by this task. The successor authority must define later manual/additional-line behavior and completion invalidation before separate implementation tasks are authorized.
