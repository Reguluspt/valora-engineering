# OS-G2 Asset Review Case State contract

**Status:** CANDIDATE AUTHORITY — PRODUCT OWNER DECISION REQUIRED with [ADR 0048](../adr/0048-post-intake-guarded-apply-and-asset-review-authority.md). **Task:** OS-G2 A1 / [Issue #73](https://github.com/Reguluspt/valora-engineering/issues/73). **Baseline:** `a293395c53ab12aa27cac86d82046a6a9f59983b`, exact-main CI #533 SUCCESS; 2026-10-02. Runtime remains unimplemented and unauthorized by this task.

## 1. Authority and capability gate

The [accepted A0 decisions](../plan/VALORA_OS_G2_APPRAISAL_CORE_ENTRY_AUTHORITY_PROPOSAL.md) bind initial-set lineage, post-Intake Apply, project-wide COMPLETE and the current downstream hold. This candidate extends [PR-01 projection §§2–6](VALORA_UIUX_V2_3_PR01_CASE_STATE_PROJECTION_CONTRACT.md) and [provider current-stage/Next Action rules](VALORA_UIUX_V2_3_PR01_CASE_STATE_PROVIDER_IMPLEMENTATION_CONTRACT.md#6-aggregator--next-action) only through `ASSET_REVIEW`. Historical broader design vocabulary does not add public enums: the [current schema](../../backend/app/modules/project_master_data/schemas.py) supports stage results `COMPLETE | INCOMPLETE | BLOCKED | STALE | NOT_AVAILABLE` and action kinds `BLOCKER | PENDING | UNAVAILABLE | NO_AUTHORIZED_DOWNSTREAM_ACTION`. Use those values only; business progress maps to `INCOMPLETE`.

Proposed provider identity `asset_review_v1`; capability available only after PO accepts this contract/ADR and separately authorized runtime is implemented and wired. Until then retain current [provider](../../backend/app/modules/project_master_data/application/case_state_projection.py): `ASSET_REVIEW=NOT_AVAILABLE`, four-stage bound, no authorized downstream action after the completed prefix (existing scoped blockers still take global priority). Merely merging authority does not activate a provider.

Compute on read in one caller-owned consistent database snapshot, without `FOR UPDATE`, writes, flush/commit/rollback or audit by the provider. Future runtime must provide snapshot consistency across all fact reads; mixing generations across statements is forbidden. The mutation guard independently re-reads and checks CAS under ADR 0048 locks. No Case State/completion persistence or cache is introduced.

## 2. Authoritative set and deterministic states

Before Apply, use only the committed Result's exact non-empty selected staging set. After Apply, use its exact guarded seal and one-to-one staging → official-line correspondence. Current membership is the sealed initial set until a separately accepted membership command exists. Such a command must version membership and invalidate prior completion; no legacy/unlinked line is silently included or ignored. The provider verifies all Project official lines against authorized membership, not only a page of covered lines.

Evaluate capability/prerequisite availability first, then `BLOCKER → STALE → valid unfinished work → COMPLETE`. Within an available post-Intake provider, the following table is exhaustive in that order:

| Result | Exact predicate / safe reason |
| --- | --- |
| `NOT_AVAILABLE` | Provider not accepted/wired (`provider_unwired`), or Intake absent (`official_intake_prerequisite`). Missing indispensable provider support is capability absence, not completion. Unexpected failures/corrupt cross-tenant pointers raise a typed safe projection/integrity error rather than fabricate a business state. |
| `BLOCKED` | A known scoped open `BLOCKING` issue; pre-existing/unlinked/unauthorized official line or unauthorized membership divergence; known zero selected rows; `ready_for_review` rows/counters not all valid and consistent; covered line `flagged`, `rejected` or `invalid`; or unfinished work requiring mutation while Project is not DRAFT. These are explicit independent domain impediments. Ordinary open `WARNING` issues never block. |
| `STALE` | With no independent blocker, the authoritative read proves committed Result/current batch/source/mapping/current staging usage/row identity or immutable input digest mismatch; missing/extra/duplicate staging selection; unexpected batch state; or applied state lacking the exact guarded seal/correspondence. Mismatched current authority must not be treated as an ordinary pending step. No stale verdict comes from frontend memory or an old client token alone. |
| `INCOMPLETE` | Intake and lineage are current, no blocker/stale: (a) before seal, selected batch is `parsed` or `validation_failed`, requiring validation; (b) batch is `ready_for_review`, all rows valid/counters consistent, requiring explicit guarded Apply; or (c) exact applied/sealed current set exists but at least one covered line is not both accepted and valid, without a negative status classified as BLOCKED above. |
| `COMPLETE` | Exact current non-empty authoritative membership is proved, every covered line is `review_status=accepted` AND `validation_status=valid`, no scoped blocker and no stale lineage. Recompute from full set and current line versions. No price requirement. Intake, workflow/Project status, visits or one accepted line are insufficient. |

`parsed`/`validation_failed` rows need validation rather than premature row-verdict blocking; `ready_for_review` invalid/pending/warning rows block Apply. Validation retry is allowed only while ADR 0048 D3 lineage is current. For blocker-plus-stale cases publish both diagnostics but choose BLOCKED/one blocker action; checks using an unproved selection cannot manufacture row readiness blockers. A pure row-selection mismatch is STALE. Membership violations explicitly classified BLOCKED remain blockers even if they also invalidate the seal.

Resolve accepted ValidationIssue target spellings `project`/`Project` and `project_asset_line`/`ProjectAssetLine` through this tenant/Project. Include known Project-line blockers even if the line is an entry conflict. Ignore resolved/ignored issues as open blockers; retain their authoritative versions for token invalidation. Unknown/unresolvable targets do not contribute or leak data; known cross-scope integrity faults fail closed. Warnings are separately visible and versioned, never severity-converted.

Lineage mismatch stops progress but never automatically alters the committed Result, mapping, staging, membership or issues. A refreshed read that matches authority clears STALE; unresolved mismatch remains explicit without a new source/mapping/manual mutation shortcut.

## 3. current_stage and exactly one Next Action

Preserve the earliest non-COMPLETE stage among the four Pre-case stages; later facts cannot complete or skip it. Extend the bound only when all four are COMPLETE and `asset_review_v1` is accepted/implemented/wired: `current_stage=ASSET_REVIEW`, including its BLOCKED/STALE/INCOMPLETE/COMPLETE results. A successful Intake then enters ASSET_REVIEW before Apply; Apply is its unfinished entry work. Missing capability keeps `current_stage=OFFICIAL_INTAKE`. Completion is capped at ASSET_REVIEW; it neither advances to a later stage nor claims publishing.

Global existing scoped blockers retain first priority, then authoritative stale, then the nearest valid unfinished work. Before four-prefix completion preserve existing prefix action behavior; no Asset Review mutation route is offered. After entry use the table below. `next_action.stage` can differ from `current_stage` for a global blocker.

All action contexts have typed `project_id:UUID`, `case_version:SHA256` and a safe `reason_code` enum, plus only the branch-specific fields below. Semantic keys are domain routing identifiers, not frontend URLs or commands; provider output never executes a mutation. These are proposed descriptors, not claims that today's public response exposes typed target context. The current action schema has only kind/stage/key/issue ID; a separately authorized API task must expose the proposed discriminated contexts without changing the existing enums.

| Condition | Kind / semantic key | Typed context |
| --- | --- | --- |
| Current selected batch `parsed` / `validation_failed` | `PENDING` / `asset_import_validate_pending` | `official_intake_commit_id:UUID`, `result_id:UUID`, `batch_id:UUID`, `staging_usage_id:UUID`, reason `validation_required` / `validation_retry`; expected version is the common case token. |
| Current all-valid `ready_for_review` batch | `PENDING` / `asset_import_apply_confirm` | Same identities, `contract_version:s12-post-intake-guarded-apply-v2`, `confirmation_required:true`; never auto-Apply. |
| Applied/sealed set with ordinary unfinished line | `PENDING` / `asset_review_line_pending` | `membership_version:positive integer`, `line_id:UUID`, `line_row_version:positive integer`; first eligible line by initial staging `(source_row_number,id)`, then line ID tie-break. Future membership commands must define stable order for added lines before activation. |
| Open scoped issue | `BLOCKER` / `asset_review_issue_blocker` after Asset Review entry | Lowest issue UUID in canonical ascending order; `validation_issue_id:UUID`, `issue_row_version:positive integer`, typed target kind/UUID resolved to this Project. Before entry keep existing prefix blocker action. |
| Covered line has negative review/validation status | `BLOCKER` / `asset_review_line_blocked` | First affected line in the same stable order; membership/line versions and reason `review_flagged`, `review_rejected` or `validation_invalid`; only existing human review authority may resolve it. |
| Entry/membership, staging readiness or non-DRAFT impediment | `BLOCKER` / `asset_review_entry_blocked` | Reason `manual_line_conflict`, `membership_conflict`, `empty_selection`, `rows_not_ready`, `counter_conflict` or `project_not_draft`; scoped batch/line IDs only if proved. Diagnostic navigation only; no repair command is authorized. |
| Authoritative stale/recovery condition | `UNAVAILABLE` / `asset_review_stale_recovery` | Reason `lineage_mismatch`, `selection_mismatch`, `batch_state_conflict` or `seal_mismatch`; scoped Intake/Result/batch/usage IDs only if proved; `reload_required:true`. Read/reload diagnostic route only, never closed Pre-case mutations. No STALE action enum is added. |
| ASSET_REVIEW COMPLETE | `NO_AUTHORIZED_DOWNSTREAM_ACTION` / key null, stage null | No mutation target; completion remains in stage results and versioned facts. No later-stage route. |
| Provider missing / unmet Intake prerequisite | Preserve current prefix behavior / no Asset Review key | Safe availability reason; no Asset Review target. |

Deterministic blocker selection: open scoped issues by UUID first; then membership/manual/empty-set conflicts, staging readiness/counters, negative lines, non-DRAFT unfinished-work constraint. Within each class use stable scoped ID order; select one primary action and retain all diagnostics separately. STALE reasons use table order as tie-break. Warnings never displace the primary action.

Projection truth is account-independent for an authorized `project:read` caller. Before emitting any mutation-capable pending or line-review route, independently check the actor's effective permission and applicable existing command prerequisites. If unauthorized, keep the stage result, use `UNAVAILABLE`, null route/target and safe `permission_required` reason. Read-only blocker/stale diagnostics may remain navigable. Backend command authorization remains authoritative and is rechecked at invocation; no role grant/new permission is proposed.

## 4. case_version and invalidation

Propose versioned envelope `contract=global-case-state-v2-asset-review-v1`; do not silently alter v1. Preserve organization/Project UUID scope and all current prefix fact inputs, add the facts below, sort entries lexicographically and serialize typed canonical JSON with UTF-8, sorted keys, compact separators, lowercase canonical UUID/SHA strings and explicit nulls. SHA-256 produces the opaque 64-character lowercase hex token. Use digests for composite data, never database object representations or lossy stringification. The same resolver builds mutation CAS from locked authority.

| Added authority inputs | Required token content |
| --- | --- |
| Intake / committed Result / Analysis | IDs, immutable versions and canonical checksums/manifests/source-snapshot lineage; include absence/conflict tokens rather than dropping missing facts. |
| Project | `row_version`, workflow status, explicit current-batch pointer. |
| Source / structure / mapping | Current artifact ID/generation/checksum/availability, structure digest, selected confirmed mapping ID/digest, selection version, profile usage ID/digest, `current_staging_usage_id`. |
| Batch / staging | Batch ID, status, counters; validation/apply authoritative generation (including committed validation-success generation); ordered row identities/source locators/ownership, canonical registered inputs and validation output digests. Include absence/conflict identity. |
| Membership | Exact seal identity/digest, membership version and sorted member-line/lineage correspondence; detect all Project official IDs, including extra/unlinked lines, so phantom membership invalidates the token. |
| Covered official lines | Every member ID, `row_version`, review/validation state and immutable lineage; all members, never current page/filter. |
| ValidationIssue | Every relevant accepted-target issue ID, row version, target identity, severity/status, including open warnings and transitions to resolved/ignored; changes in target membership/absence affect the token. |
| Future membership command | Its authoritative committed version/outcome and new membership generation; forbidden until its separate accepted contract defines representation. |

Physical version fields/storage for currently unversioned inputs are implementation design, not existing schema claims. Every committed authority-changing write must alter this canonical input; a new validation generation cannot reuse the same CAS just because verdicts match. No display labels/text, frontend state, pagination, route URLs, user secrets, actor permissions or unordered data. Static capability is outside business facts, but the new envelope/provider contract version changes the token at successor activation. A stale client token returns conflict/reload; it does not make a fresh authoritative projection permanently STALE.

Membership/line/issue changes invalidate the old completion token. COMPLETE is a fresh computed proof only when the new full set again qualifies; no previous receipt, cached state or stage visit can reuse that proof.

## 5. PO decision and future acceptance

Accept this candidate with ADR 0048 as one bounded authority decision: five-state mapping, blocker/stale precedence, capped current-stage extension, six semantic action branches, discriminated safe contexts and versioned token inputs. The accepted A0 COMPLETE predicate stays fixed. Later membership mutation mechanics/recovery and later-stage semantics require separate authority.

Future runtime gates must prove consistent read snapshots, exact token invalidation for every input family, key/query order stability, tenant/unknown-target safety, warning separation, deterministic full-set line coverage, blocker-plus-stale precedence, permission-gated actions, no capability activation from documents alone, no new public enums and no unauthorized downstream route. Runtime tests are N/A for this three-file authority proposal.
