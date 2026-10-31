# OS-G1 vNext — Authority reconciliation and implementation gates

**Purpose:** Identify existing accepted authorities affected by new PO UX choices. **Design changes here do not amend runtime contracts automatically.** This document records required independent review/gate decisions before any Codex task.

## Precedence to preserve

1. Live repository/CODEX/ENGINEERING_GUARDRAILS and current accepted domain/ADR/API contracts remain operational truth.
2. Canonical [UI/UX v2.3 master](../VALORA_UIUX_HANDOFF_v2.3.md), [authority index](../VALORA_UIUX_V2_3_AUTHORITY_INDEX.md), applicable addenda and the [frontend architecture](../../architecture/VALORA_FRONTEND_ARCHITECTURE_RULE.md) govern design and implementation boundaries.
3. Later explicit PO UX decisions may change **their specified OS-G1 future design**, but do not retrospectively rewrite accepted APIs, certified evidence, app permissions or protected UAT scope.
4. [Issue #222](https://github.com/Reguluspt/valora-engineering/issues/222) preserves the 2026-10-26 approved HTML mockup on an archived branch. Do not overwrite that snapshot. New OS-G1 vNext v02 may supersede earlier UI behavior **after** documented adjudication.
5. [Issue #203](https://github.com/Reguluspt/valora-engineering/issues/203) UAT remains separately controlled. This docs PR does not open UAT, code changes, CI, merge or deployment.

## 1. Explicit conflict register

| ID | Existing authority / implemented shape | New decision | Required adjudication |
|---|---|---|---|
| AR-01 | [2026-10-26 Issue #222 mockup](https://github.com/Reguluspt/valora-engineering/issues/222) requires per-line confirmation with price, explanation and evidence. | UX-G1.10 uses view-progress on navigation; one overall confirmation, may export incomplete prices/evidence with warning. | PO UX scope supersession is recorded; **formal G1 analysis/finalize contract and tests must be redesigned and approved separately**. |
| AR-02 | Current [preliminary analysis snapshot contract](../../implementation/VALORA_UIUX_V2_3_PR01_PRELIMINARY_ANALYSIS_SNAPSHOT_CONTRACT.md) historically specifies strict nine-field line manifest, `human_line_confirmed=true`, `has_unresolved_blocking_line=false`, confirmed price fields. Newer G1 successor contracts preserve lineage/integrity and versioning. | Allow warning-only incomplete preliminary asset lines while still creating a versioned result. | Domain schema/API/generator agreement, snapshots and currentness, migration/test, numerical and audit handling. **Do not claim current API already supports it.** |
| AR-03 | [Preliminary result generation contract](../../implementation/VALORA_UIUX_V2_3_PR01_PRELIMINARY_RESULT_GENERATION_CONTRACT.md) writes price/amount into sourced workbook at mapped row positions with strict amount; ADR 0046 supports bounded immutable versions. | One results table with URLs and embedded multiple evidence images, partial-price outputs, independently retained versions. | New artifact contract, image safety, row geometry, formula/count integrity, lineage and storage verification. |
| AR-04 | The [Price & Evidence authority addendum](../VALORA_UIUX_HANDOFF_v2.3_PRICE_EVIDENCE_AUTHORITY_ADDENDUM.md) ranks Internet survey, unit-price explanation, historical appraisal result; Knowledge is retrieval, not an independent price source. | Enrichment from Knowledge for preliminary prices, with auto-fill when strong basis and human-overridable price. | Preserve actual source type/authority; enforce source conditions and human proposal vs final appraisal distinction. |
| AR-05 | [Knowledge review baseline](../VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_REVIEW_BASELINE_ADDENDUM.md) is **single-user**; domain-local `Cần rà soát` candidate queue; not global reviewer workflow. | UX-G1.14 B chooses staff proposal, **authorized approver** activation. | Clarify permissions and whether the approver can be the same authorized user or is a distinct person. Separate PO decision + ADR/RBAC review before introducing multi-user assignment/inbox. Retain domain-local queue. |
| AR-06 | [Knowledge management baseline](../VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_MANAGEMENT_BASELINE_ADDENDUM.md) has canonical/variant/alias, structured KTKT, explicit human activation. | Auto-generated proposals on case edit, duplicate resolution, versions. | Reuse existing identity/candidate/decision/lineage primitives; no parallel knowledge service without architecture approval. |
| AR-07 | [S12/S13 approved visuals](../visual-reference/v2.3/README.md) are exact baselines for their own surfaces; S05 is only visual-grammar reference in the bundled PDF. | OS-G1 vNext new Workbench based on Fluent UI React v9 with right panel; 26-Oct S05 archived HTML remains original design evidence. | Use grammar and approved shell, don't claim pixel approval; new mockup v02 needs explicit PO visual review and diff. |
| AR-08 | Frontend architecture establishes tokens → Fluent primitives → Valora shared components → features → screens, with OS-G6 visual-convergence sequencing. | Standardize Fluent theme/component use for v02. | Documentation and design can proceed now; implementation and CI follow bounded frontend task, not a covert full product rewrite. |

### Important nuance on scope

UX-G1.13 warning behavior applies to **unusual spread between preliminary price sources** during sequential review; it does **not** repeal OS-G2 final price evidence/provider quotation comparison rules or supplier-selected semantics.

New preliminary “source auto-fill” is a working suggestion for the human and must never bypass explicit knowledge candidate activation, identity review, source-lineage or final OS-G2 price authority.

## 2. ADR/API changes that MUST NOT be silently assumed

Potential future changes include:
- Relaxing or supplementing line-manifest `human_line_confirmed` and no-unresolved-line requirements; precise meaning of 'viewed' vs 'confirmed'.
- Extending API with evidence-card rich content and clipboard image upload, including object security and source/evidence linkage.
- Batch materialization/matching idempotency, eventual consistency, stale-data/retry/partial failure semantics.
- Controlled canonical/variant/alias approval lifecycle, RBAC and historical versioned facts.
- Partial-price XLSX generator that does not represent unknown price as zero; multi-image layout, formula/total safety and snapshot immutability.
- Replacement/supersession of older UI wording and mockups with explicit semantic mapping, without changing OS-G2 certified boundaries.

**These are design dependencies, not approved migrations or Codex implementation instructions.**

## 3. Delivery and gate sequence

1. PO review this decision bundle and **approve specific semantic supersession items**.
2. Architecture/domain/RBAC/privacy/evidence security review for affected contracts, authority and ADR impacts.
3. Align UX-G1.15 v02 Microsoft Fluent 2 React mockup with accepted design and architecture (visual-only prototype).
4. Break implementation into small standalone micro-tasks with separate tests/review for source matching, asset review, evidence, result generation, Knowledge candidate reviews and UI composition.
5. Implementation only after authorized task contract, appropriate tests and environment recheck; UAT #203 and CI production scope remain outside this docs-only PR.

## 4. Current disposition

- **Approved by PO in conversation:** individual business/UX choices in Decision Register.
- **Proposed / not approved as completed artifact:** consolidated UI/UX spec, new matching thresholds, implementation schema, v02 mockup.
- **Unchanged:** existing GitHub canonical and archived files; current server and CI/runtime/UAT status.
- **PR intent:** documentation traceability and review, not merging code or validating production behavior.
