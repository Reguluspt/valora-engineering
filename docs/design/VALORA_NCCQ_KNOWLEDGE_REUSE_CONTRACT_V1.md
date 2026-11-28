# VALORA — NCCQ Knowledge Reuse Contract v1

**Status:** PO-approved reuse purpose, PM-proposed technical model, 28/11/2026. Applies to target only. Existing v1.4 / Knowledge Management and lineage/review/activation authority remains in force. No new DB/API/provider or AI invocation authorized.

See [Workflow v2](VALORA_NCCQ_WORKFLOW_CONTRACT_V2.md) for the price-work gate and [the Knowledge Management addendum](VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_MANAGEMENT_BASELINE_ADDENDUM.md) for review and activation.

## 1. Separate facts and provenance

| Data family | Required lineage | Permitted use |
|---|---|---|
| Valuation result/evidence | accepted identity/version, exact historical dossier/result line and independent retained evidence; actor/date/review | suggest source and appraisal price under existing price-source authority; never automatic acceptance |
| Actual supplier quotation | resolved legal supplier ID, exact item/spec/unit/currency/terms, dossier and quote revision, date/source retained bytes, explicit human confirmation | historical reference for preparing future proposals and current confirmed report facts; never valuation price evidence |
| Internal proposal | group/trio/slot, current asset mapping, referenced appraisal decision, historical match if used, generation policy/version and draft provenance | current quote preparation/request; never actual supplier offer, report confirmation or valuation evidence |

No silent promotion, rewriting old data, overwriting source bytes, auto-learning active official knowledge or routing around existing `Cần rà soát` and human approval. Preserve canonical asset and version registry, tenant/project scope, source custody, identity resolution, audit and explicit activation. Historical documents remain historical, not proof of today's price/agreement. Import paired historical reports via current review/admission authority, not raw examples from chat. No customer report files included in this package.

## 2. Reuse handoff from source-price phase

Capture a stable result of the already executed KB scan when user confirms price/source: exact project/asset line, canonical asset or explicitly unresolved candidate, spec/version/unit/currency/tax/conditions, chosen independent source references, historical appraisal result ID/value/date, current user-confirmed unit price and proof, relevant historical group/trio and issuer-item references where admissible. This is a proposed read-model/logical handoff; no existing implementation implied. Reuse this identity/proof at NCCQ; validate currentness (no duplicate scan or hidden second decision). Existing identity and knowledge review gates remain. No name-only joins, slot-index-only reuse or inference from report layout.

## 3. Branches

- Unchanged historical appraisal price and exact compatible identity + same supplier: use historical quote value as a labeled draft reference. If one supplier history absent or incompatible, mark missing/needs attention for that slot; do not attach another issuer's price or invent fallback. Group selection is fixed trio, not per-line list.
- User updated appraisal price: keep old actual confirmed quote history intact, record new appraisal decision under existing authorized workflow; mark affected new proposal as needing refresh; use confirmed new price as proposal reference only. Never retroactively modify real supplier offers.
- New identity: use approved classification/assignment; proposal generation uses current confirmed price, requires settled policy (see workflow and ADR). Ambiguous classification/manual review rather than a new supplier for every item. Track no-match vs ambiguous vs missing proof distinctly.

## 4. Update lifecycle

A newly confirmed appraisal price may produce a versioned appraisal-result candidate/knowledge update according to owning workflow (working confirmation is not necessarily an accepted historical result). A newly confirmed actual supplier quote may produce a source-backed actual-quote candidate/version; active reuse requires existing review/activation. Internal proposal may be stored separately as draft lineage only; it is excluded from actual historical-price lookup and valuation sources. No requirement to re-enter the same facts; explicit human command can drive downstream deterministic candidate creation only when contract authorizes it. No separate second professional appraiser. Append-only history; dedup/idempotency based on exact source/version/actor and canonical identity, not just value. Changes affect only exact dependent proposals/currentness, not blanket invalidation.

## 5. Acceptance (future)

| ID | Test |
|---|---|
| KB01 | same asset exact match and same 3 issuers: handoff reuses prior lookup; lineage per issuer preserved even when report column order differs. |
| KB02 | new price for old asset: only proposal dependency stale; new appraisal decision/version; old actual quote history unchanged. |
| KB03 | ambiguous identity, mismatched unit/terms, missing issuer, stale match, cross-tenant: HOLD, no unrelated price copy or silent match. |
| KB04 | confirmed real quote creates eligible source-backed candidate under existing review/activation; internal proposal never contributes to actual quote history or valuation evidence. |
| KB05 | retry/race/supersession/withdrawal, old and new sources, 150-line grouping: exact reference and atomic audit, no duplicate or unapproved activation. |
