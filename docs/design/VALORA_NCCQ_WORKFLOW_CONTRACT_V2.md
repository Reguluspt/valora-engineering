# VALORA — NCCQ Workflow Contract v2

**Status:** PO-approved target direction + PM draft technical contract, 28/11/2026. Runtime v1 remains certified/current until separately superseded and implemented. See [#252 decision receipt](https://github.com/Reguluspt/valora-engineering/issues/252#issuecomment-7232992154). No production implementation permission.

Read with the [Iteration 7 baseline](assets/VALORA_NCCQ_BASELINE_v2.3.md), [Editable Data Grid v1](VALORA_EDITABLE_DATA_GRID_CONTRACT_V1.md) and [Knowledge Reuse v1](VALORA_NCCQ_KNOWLEDGE_REUSE_CONTRACT_V1.md).

## 1. Purpose and scope

NCC quotes (historical, proposed, sent, returned, confirmed) serve procedural quotations and report population only. Never classify NCC prices as valuation price evidence, accepted price basis, source suitability, or price determination. Preserve separate Internet survey → unit-price explanation → prior appraisal result (not old supplier quote). No machine commercial/signature appraisal, new reviewer, automatic pricing decision or false supplier document. This is PO business direction, not legal advice or evidence of compliance.

## 2. Gate and grouping

After official intake, verified structural asset/line membership and explicit completion of price-source working confirmation and appraisal unit-price confirmation for exact nonempty sealed set S, prepare NCCQ. Reuse the already matched knowledge references from source phase. No parallel preconfirmation preparation under target, no early final source acceptance. Define distinct `PRICE_WORK_CONFIRMED` vs final `FINAL_SOURCE_BASIS_ACCEPTED`; exact new A9/A10 proof in the [proposed successor ADR](../plan/VALORA_252_SUCCESSOR_ADR_DRAFT_v1.1.md), not pretend current v1 state has changed. Diagnostic read access may be available; writes require authorized server action.

One stable group G per set of asset lines, full S covered exactly once (partition proposal; ambiguous assignment HOLD). Group category follows quotation business purpose, not mechanically section names. Each group has exactly three distinct resolved supplier legal identities, stable ordered slots and one consolidated table. Each supplier's quote covers all lines of G to satisfy procedural coverage. For n groups, 3n active quote slots/documents per round, not 3×asset count, no fourth/fifth active supplier in a group. Revisions/history may exceed 3n files, not additional active suppliers. Use confirmed historical group trio where valid; do not silently choose arbitrary trio if ambiguity/missing data. Replacement is one slot, auditable, no inherited price from a different issuer.

## 3. Preparation cases

1. Same identified asset, same confirmed appraisal unit price, exact compatible specification/unit/currency/tax/terms and matching selected supplier IDs: reuse actual historical quotation values as **historical reference in a new draft**. Use current dossier quantity and STT; never count as current agreement. No repeated identity scan; retain exact match reference and lineage.
2. Previously appraised asset with human-confirmed changed appraisal unit price: refresh affected internal proposal cells for the same three slots under PO drafting rule. If one current proposal already equals P, it may be retained only if exact current context is valid and user did not override; no silent rewrite of signed/confirmed quote. One proposed value equals P; two proposed values are > P and <= 1.15P. This is solely proposal validation, not a requirement on actual supplier offers.
3. New asset: classify into group, prepare proposals for same three suppliers; no new supplier merely because asset is new. Same drafting-only constraint as case 2. If group/match/currency/rounding or exact policy cannot be determined, mark needs attention. No invented price values, false identity, or fabricated supplier confirmation. Detailed value selection/rounding and assignment of equal-price slot are OPEN, no production algorithm approved in this packet.

Automatic mode fills eligible empty draft cells, preserves explicit manual overrides, shows provenance and reason. Updating a working appraisal price can require source reconfirmation and re-evaluation of proposal data; does not retrospectively rewrite sent/confirmed actual quotes. Manual mode allows direct editing and paste of actual incoming data or internal proposed values with explicit provenance; do not conflate the two. The same working grid is used; switching modes retains data. Invalid/ambiguous paste no partial commit.

## 4. Document and confirmation lifecycle

DRAFT proposed data → deterministic actual Word generation using verified template version and data snapshot → send/share under actual authorized method and record exact sent revision → receive actual supplier response/retained original signed return (where applicable under owning evidence contract) → user records actual price and explicitly confirms that exact quote revision. No mandatory auto-email. One-click agreement is the operator's attestation, not software impersonating supplier. One click may use unchanged sent data when supplier actually agreed; exceptions may paste changed actual data, keep sent value and return separately. No fabricated signatures, dates or actual offers. Missing required source custody/integrity holds confirmation. Receipt handling remains distinct from human agreement; no extra mandatory UI receipt-confirmation modal. Manual workflow must support genuine received quotes without requiring system-generated outbound Word if admitted by owning contract.

Preserve app-owned immutable retained bytes, exact template version, proposal snapshot, sent/returned revision, identity, mapping, actor/time, receipt and audit. `04_Báo giá nhà cung cấp` outbound working/sent documents and `05_Pháp lý` received signed evidence under existing document placement; never turn provider Working copy or metadata into accepted bytes. TM01/TM03/TM04 real `.docx` template mapping/fill/preview/READY, no mock render proof or PDF export scope. Returned PDF evidence only if separately authorized admission rules; PDF return is not PDF generation authority. Original source and historical revisions unchanged.

## 5. Coverage and report

For every g in groups, trio T(g) has exactly 3 independent suppliers. For every l in g and s in T(g), a current human-confirmed actual quote revision of that supplier with exact current line mapping, retained evidence/terms/issuer integrity and no applicable blocking dependency must exist. A group COMPLETE only when its 3 slot revisions cover all exact lines; dossier procedural COMPLETE only when all groups are complete and the full S partition/proofs are valid. No file counting, extra slot, duplicate issuer or unconfirmed proposal. Report `NCC1–NCC3` by ordered group slots, selected confirmed exact revision items; one table per group preserving existing report column schema (STT, tên, ĐVT, SL, 3 NCC price columns, Tổ TĐG đánh giá đơn giá/thành tiền independently). Do not fill missing cells from history/proposals. Report format and business prose must not state valuation depends on NCC if it does not. Proposed elimination of per-line redundant NCC Selection remains OPEN; keep existing checkpoint/ADR0051 non-activated until authority settled. No downstream stage activation or official report acceptance in this task.

## 6. Command/security contract (logical, proposed)

Server policy derives read and action-specific capabilities: prepare/fill/save draft, manual paste, replace supplier, generate, sent receipt, returned intake, confirm, reject/withdraw and recover. Require existing authorized same tenant/project, active actor/session, correct DRAFT scope, versioned policy, full exact line/group/slot/target scope and CAS; commit rechecks and expiry. No new RBAC grant. Preserve actor-intent and idempotent receipt, atomic domain/audit, canonical decimals, exact digest, lock ordering, no provider writes without separate owning authority. Keep price facts read-only here. Recovery for stale upstream may permit narrowly authorized withdraw/reject based on intact target proof, not blanket writable. F255-02 remains static finding to reconcile. Explicit currentness and cutover in successor ADR. No fake COMPLETE from front end, no synthetic report acceptance.

## 7. Acceptance (future; not executed)

| ID | Scenario / expected result |
|---|---|
| W01 | Source confirmation incomplete or price unset: quote preparation denied, no write; view/recovery capability separately determined. |
| W02 | 2 groups with exact partition, 3 distinct suppliers each: 2 grids, 6 active slots; no arbitrary extra supplier or per-line trio; each group has coverage for all its lines. |
| W03 | Valid old identity + unchanged confirmed price: reuse only same issuer historical reference, current quantity/STT; no repeat identity lookup or auto agreement. |
| W04 | New/price-changed asset: same trio, drafting-only bound; missing/infeasible/ambiguous policy holds; no generated actual supplier quote, no automatic price write. |
| W05 | Auto fill blanks; manual overrides and confirmed revision immutable; replacement does not copy old issuer's values, exact group membership preserved. |
| W06 | Actual supplier agrees: one explicit click, exact revision, atomic receipt/audit and real source lineage; duplicate click exact replay; denied/stale/uncertain no false success. |
| W07 | Actual return differs (including outside proposal range): faithfully retain returned values; compare sent vs returned only for quote lineage; never alter appraisal price or label valuation invalid. |
| W08 | One line lacks one selected supplier or one duplicate identity: INCOMPLETE. All exact lines across 3/150-line full scope, all trios verified: procedural complete. |
| W09 | Three confirmed actual quotes cannot satisfy missing evidence; independent source acceptance remains distinct. |
| W10 | Report preview excludes unconfirmed prices; one table per group and stable slots, no fabricated third cell, no extra report columns. |
| W11 | Expiry, invalid retained file, supplier disabled, changed mapping, withdrawal, stale CAS, concurrent changes: fail closed where affected, retain unaffected history, no bulk rebind. |
| W12 | Real Word mapping and fill, sent/return source, retained bytes and lineage require separate #255 slices; no claim mock preview completes those. |
