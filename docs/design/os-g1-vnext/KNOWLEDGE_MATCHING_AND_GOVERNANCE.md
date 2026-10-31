# OS-G1 vNext — Knowledge matching, source ranking and proposal governance

**Status:** Design specification / not production logic. UX-G1.08, UX-G1.12–UX-G1.14 PO decisions.

## 1. Distinct business identities

- **CaseAsset:** asset line in a particular preliminary/official case, with raw Excel observation, working description, quantity, price decisions and history.
- **Canonical / model / variant Knowledge asset:** shared description of a equipment model/configuration; not the same physical asset as a customer machine.
- **Price observation/source:** a dated, typed offer, survey or historical appraisal-result observation with condition data, distinct from a user's proposed appraisal price.
- **Evidence:** links, snapshots and documents with provenance and associated price/source.
- **Review candidate/proposal:** not activated into shared knowledge until explicit authorized decision.

Two customers can have separate case assets linked to the same canonical model while retaining different age/condition and independently determined prices.

## 2. Two independent suitability gates

**Gate 1 — Asset identity suitability.** Normalize Vietnamese/English names, brand, model, type, unit, key performance attributes and variant; compare **category-specific critical attributes** (for generator: kVA; for crane: load; for CNC: model/configuration). Do not use display name alone. Missing model/critical data is not proof of equivalence.

**Gate 2 — Price/source/evidence suitability.** Check verifiable origin, timestamp, item condition, unit/package scope, VAT/transport facts and evidence/source link validity. Correct model with poor source still **must not auto-fill surveyed price**.

| Class | Meaning | Auto-fill? |
|---|---|---|
| M1 | Same model and materially equivalent configuration; no critical conflict | May proceed to Gate 2 |
| M2 | Different variant (power/configuration/age/etc.) | Similar-only suggestion |
| M3 | Comparable equipment with different identity | Similar-only suggestion |
| M4 | Insufficient identification attributes | Request completion or show candidates |
| M5 | Material mismatch or conflict | Reject as auto-fill source |

Confidence scores may help ranking/explanation but do not override hard contradictions. No arbitrary 85%/90% similarity threshold has been approved; tune with labeled realistic UAT data and error budgets before implementation.

## 3. Source priorities and multiple valid sources

The authoritative **price-evidence types and precedence** remain as the v2.3 addendum:
1. Internet survey price.
2. Unit-price explanation.
3. Price from the **appraisal result** in a historical dossier (not historical supplier quotation by default).

Knowledge Base is the **retrieval mechanism**, not a fourth price-source type. Supplier quotation prices also do not automatically become final appraised unit prices.

UX-G1.12 B decision:

- Rank only candidates that pass mandatory identification/source gates.
- Compare provenance/traceability, technical suitability, item condition, date, tax/transport, unit scope, contradictions and price-source type priority.
- **If one source has a clearly explainable business preference**, select it as the auto-fill working reference; preserve other candidates as reviewable context.
- **If valid sources are indistinguishable or not comparable**, show them for human choice, do not pick a numerical top score arbitrarily.
- Source selection may suggest surveyed reference and derived proposed unit price. Human may override proposed price; no silent later overwrite.

For example, 100M VND excluding VAT/transport and 108M including VAT cannot be ranked solely by raw prices. No VAT or transport amount should be invented to force comparability.

## 4. Price spread behavior (UX-G1.13 PO correction)

- Detect notable deviations among comparable normalized sources and display a side-by-side warning during **existing sequential asset review**.
- Do not create a separate approval screen or require extra per-source approval solely for abnormal spread.
- A clearly preferred and otherwise eligible source may still support automatic working-value suggestion; warning is visible.
- Employee determines proposed price and whether to retain/change sources and evidence. Overall preliminary export confirmation is separate from final OS-G2 appraisal-basis acceptance.
- Spread thresholds are not yet specified; tune by equipment segment and condition. **Do not fabricate a global percentage** or assume warning itself proves a source invalid.

## 5. Identity edit classification and effects

On save of a materially changed identity field, ask **inline in the right panel**, not while each character is typed:

| Operator choice | Case data | Shared Knowledge | Price/source handling |
|---|---|---|---|
| Correct existing canonical knowledge | Save case working value | Emit proposed before/after change + lineage | Reassess source; keep human proposed price |
| New asset or variant | Save case value | De-duplicate first; propose new canonical/variant candidate | Mark old variant source for recheck; never copy blindly |
| Case-only correction | Save case value | No shared-KB change | Reassess affected source; keep proposed price |

Price-only/narrative-only edit never triggers identity classification.

## 6. Governance UX-G1.14 B — proposal then authorized approval

Operator edits once in case Workbench; VALORA derives candidate from the saved change, exact source, evidence and relevant attributes. Operator can continue the case while the **domain-local Knowledge Management → Cần rà soát** candidate waits. Do not invent a global Review Queue, multi-stage inbox or SLA.

Proposed lifecycle:
- Draft / pending validation.
- Duplicate and conflict check.
- Needs evidence / awaiting decision.
- Human approved and version published **atomically**, or rejected/deferred/merged/withdrawn.
- A failed publication must NOT be shown as successfully activated knowledge.

**Important authority gap:** UX-G1.14 B says authorized reviewer approves; existing v2.3 Knowledge Review baseline is **single-user human confirmation** with no multi-person workflow. Product roles and RBAC must be reconciled and approved as a separate domain task. Until then, describe a logical approval permission, **not** an implemented two-user assignment workflow. See [authority reconciliation](AUTHORITY_RECONCILIATION.md).

## 7. Duplicate and concurrency checks

Before creation, compare both activated canonical/variant/alias records and pending candidates:
- same standardized model + same critical configuration = possible duplicate;
- same model with new meaningful configuration = proposed variant;
- same device with alternate name = alias proposal;
- similar function but different model = comparable, not same identity;
- conflicting pending proposals = present comparison for human;
- canonical record updated while candidate pending = revalidate base version before activation.

Retries, double-click, refresh and timeout recovery must not generate duplicate proposals/source/evidence (idempotency). Never silently merge hard conflicts. Do not overwrite raw observations when normalizing.

## 8. Knowledge history and audit

Minimum lineage record on proposed activation:
- CaseAsset identity and original Excel cell/row source;
- canonical asset ID and version, model/variant aliases used;
- attribute before/after, proposed type, actor and time;
- price-source category, raw surveyed price, timestamp and condition;
- source URL/document/image and traceability;
- decision, reviewer authority, rationale, approved value, version published;
- change notifications to consuming cases without silent source/price overwrite.

Case XLSX snapshots already exported retain the exact source, evidence and Knowledge version used then; a later Knowledge version never edits historical artifacts. Rejected candidate remains auditable without affecting case-authored text.

New market observation is an **additional dated PriceSource**; it must not erase previous market observations merely because it was submitted through the same model record. A staff-edited proposed unit price is **not** automatically a new market observation.

## 9. Acceptance tests

| ID | Condition | Expected behavior |
|---|---|---|
| K-01 | Same model/technical configuration and valid evidence | Eligible source used for working suggestion |
| K-02 | Same name, materially different power or model | Variant/similar, no automatic copy |
| K-03 | Missing key model attribute | Suggest only; request clarification |
| K-04 | Correct model but missing/invalid source basis | No auto-surveyed price |
| K-05 | Two valid sources equally credible | Human choice |
| K-06 | Two credible sources with explainable preference and large price spread | Auto-suggestion possible; spread warning visible in sequential review |
| K-07 | Changed identity field | Inline classification; recheck source; preserve human price |
| K-08 | Case-only correction | No shared-Knowledge proposal |
| K-09 | Correct existing Knowledge | Proposal only; does not activate on case save |
| K-10 | New model with matching pending candidate | Duplicate warning; link/merge rather than duplicate |
| K-11 | Reviewer declines proposal | Case facts preserved, candidate auditable |
| K-12 | Other user updates canonical before approval | Version/conflict recheck |
| K-13 | Approval publication fails | No false activated/success state |
| K-14 | Fresh price observation | New dated source with original historical source retained |
| K-15 | Re-run enrich/proposal with same intent | No duplicate source/candidate/evidence |
| K-16 | Historical XLSX v01 after Knowledge v02 activation | v01 unchanged |
| K-17 | Reviewer deferred candidate | No active Knowledge mutation; case work continues |
| K-18 | Human manually changes proposed price | Knowledge refresh does not override it |

## 10. Open implementation questions

- Per-category critical identity fields and blocking conflicts.
- Confidence/calibration and matched-source aging requirements.
- Exact derived-price rules for VAT, transport and missing information.
- Permission model for approver (single-user vs distinct user).
- Existing schema/ADR compatibility for source-card rich evidence, proposal/version lineage and case snapshots.

Do not treat this file as approval for schema changes, new inference providers or multi-user workflow.
