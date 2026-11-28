# VALORA — NCCQ Knowledge Reuse Contract v1

**Status:** PO-approved reuse purpose, PM-proposed technical model, 28/11/2026. Applies to target only. Existing v1.4 / Knowledge Management and lineage/review/activation authority remains in force. No new DB/API/provider or AI invocation authorized.

The [PO clarification on NCC knowledge reuse](https://github.com/Reguluspt/valora-engineering/issues/252#issuecomment-7233544880) applies to this target. See [Workflow v2](VALORA_NCCQ_WORKFLOW_CONTRACT_V2.md) for the price-work gate and dossier records, and [the Knowledge Management addendum](VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_MANAGEMENT_BASELINE_ADDENDUM.md) for review and activation.

## 1. Separate facts and provenance

| Data family | Required lineage | Permitted use |
|---|---|---|
| Valuation result/evidence | accepted identity/version, exact historical dossier/result line and independent retained evidence; actor/date/review | suggest source and appraisal price under existing price-source authority; never automatic acceptance |
| Actual supplier quotation | KB price history references the resolved legal supplier, exact asset/variant and item/spec/unit/currency/terms, and the exact confirmed dossier quote revision. The owning dossier retains quotation dates, source bytes, sent and returned revisions, and explicit human confirmation. | KB provides historical prices for preparing future proposals. Current report data comes from eligible confirmed dossier revisions. Neither use establishes valuation price evidence. |
| Internal proposal | group/trio/slot, current asset mapping, referenced appraisal decision, historical match if used, generation policy/version and draft provenance | current quote preparation/request; never actual supplier offer, report confirmation or valuation evidence |

No silent promotion, rewriting old data, overwriting source bytes, auto-learning active official knowledge or routing around existing `Cần rà soát` and human approval. Preserve canonical asset and version registry, tenant/project scope, source custody, identity resolution, audit and explicit activation. Historical documents remain historical, not proof of today's price/agreement. Import paired historical reports via current review/admission authority, not raw examples from chat. No customer report files included in this package.

## 2. Reuse handoff from source-price phase

Capture a stable result of the already executed KB scan when the user confirms price/source: exact project/asset line, canonical asset or explicitly unresolved candidate, spec/version/unit/currency/tax/conditions, chosen independent source references, historical appraisal result ID/value/date, current user-confirmed unit price and proof, relevant quotation group and preferred trio, and admissible supplier-specific confirmed price versions. Preserve supplier identity and the supplier information needed for reuse. This is a proposed logical handoff. Reuse the resolved identity and proof at NCCQ and validate currentness under the owning contract. Existing identity and knowledge review gates remain. No duplicate scan, name-only joins, slot-index-only reuse or inference from report layout.

The NCC KB surface supports supplier and confirmed-price reuse for a subsequent dossier. Separate quotation-date tracking, expiry monitoring and source-document entry, attachment, lookup or management are outside this KB scope. The owning dossier continues to manage quotation documents, dates and applicable expiry/currentness and custody checks.

## 3. Branches

- Unchanged historical appraisal price and exact compatible identity + same supplier: use historical quote value as a labeled draft reference. If one supplier history absent or incompatible, mark missing/needs attention for that slot; do not attach another issuer's price or invent fallback. Group selection is fixed trio, not per-line list.
- User updated appraisal price: keep old actual confirmed quote history intact, record new appraisal decision under existing authorized workflow; mark affected new proposal as needing refresh; use confirmed new price as proposal reference only. Never retroactively modify real supplier offers.
- New identity: use approved classification/assignment; proposal generation uses current confirmed price, requires settled policy (see workflow and ADR). Ambiguous classification/manual review rather than a new supplier for every item. Track no-match vs ambiguous vs missing proof distinctly.

## 4. Update lifecycle

A newly confirmed appraisal price may produce a versioned appraisal-result candidate under its owning workflow. Historical-result acceptance remains a separate decision. An authorized update from an actual supplier quote uses the already confirmed dossier revision to create a supplier-price candidate. The user can update and reuse the price without re-entering the quotation date or uploading the source document again. Active reuse still requires existing review and activation. Store internal proposals separately as draft lineage and exclude them from actual supplier price history and valuation sources.

Keep append-only price versions, revision identity, audit metadata and the minimum reference to the owning confirmed revision needed for integrity. Deduplication and idempotency bind the exact source/version/actor and canonical identity. Preserve existing dates, evidence and historical records in their owning storage. A13 source custody, expiry/currentness and integrity still govern current-case eligibility and report binding. Changes affect exact dependencies only.

## 5. Acceptance (future)

| ID | Test |
|---|---|
| KB01 | same asset exact match and same 3 issuers: handoff reuses prior lookup; lineage per issuer preserved even when report column order differs. |
| KB02 | new price for old asset: only proposal dependency stale; new appraisal decision/version; old actual quote history unchanged. |
| KB03 | ambiguous identity, mismatched unit/terms, missing issuer, stale match, cross-tenant: HOLD, no unrelated price copy or silent match. |
| KB04 | An authorized update uses an exact confirmed actual dossier revision to create a candidate, without date re-entry or source re-upload. Existing review/activation applies. Internal proposals stay out of actual price history and valuation evidence. |
| KB05 | Retry, race, supersession and withdrawal across old and new revisions and 150-line grouping preserve price history, identity, minimal revision lineage and atomic audit, without duplication or unapproved activation. |
| KB06 | KB exposes reusable supplier prices and version history without a quotation-date/expiry workflow or source-document management and lookup. Existing dossier documents, dates, custody/currentness checks and report binding stay under their owning contracts. |
