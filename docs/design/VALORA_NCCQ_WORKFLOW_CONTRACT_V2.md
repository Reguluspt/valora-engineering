# VALORA — NCCQ Workflow Contract v2

**Status:** PO-accepted v2 target, 28/11/2026. [Successor v1.2](../plan/VALORA_252_SUCCESSOR_ADR_DRAFT_v1.2.md) records the six choices. Technical authority-file certification and physical proof remain pending. [A9–A14 v1](../../CODEX.md#price-evidence-and-supplier-quotes-certified-scope-vs-approved-design) retain the certified cap and behavior.

Read with the [Iteration 7 baseline](assets/VALORA_NCCQ_BASELINE_v2.3.md), [Editable Data Grid v1](VALORA_EDITABLE_DATA_GRID_CONTRACT_V1.md) and [Knowledge Reuse v1](VALORA_NCCQ_KNOWLEDGE_REUSE_CONTRACT_V1.md). The [PO clarification on NCC knowledge reuse](https://github.com/Reguluspt/valora-engineering/issues/252#issuecomment-7233544880) defines the KB surface.

## 1. Purpose and scope

NCC quotes (historical, proposed, sent, returned, confirmed) serve procedural quotations and report population only. Never classify NCC prices as valuation price evidence, accepted price basis, source suitability, or price determination. Preserve separate Internet survey → unit-price explanation → prior appraisal result (not old supplier quote). No machine commercial/signature appraisal, new reviewer, automatic pricing decision or false supplier document. This is PO business direction, not legal advice or evidence of compliance.

## 2. Gate and grouping

After Official Intake on the same Project, verify the structural proof for exact nonempty sealed S. One explicit human working confirmation binds the entire set, current A7/A8, eligible selected independent source revisions and confirmed appraisal unit prices before NCCQ preparation. Reuse existing source-phase knowledge matches. PRICE_WORK_CONFIRMED is the working proof; final source acceptance occurs in APPRAISAL_RESULT. [P252-01-T-A](../plan/VALORA_252_SUCCESSOR_ADR_DRAFT_v1.2.md#3-p252-01-t-a--working-pricesource-proof) owns the predicate. Readback and scoped recovery have separate capabilities.

One stable group G per set of asset lines, full S covered exactly once (partition proposal; ambiguous assignment HOLD). Group category follows quotation business purpose, not mechanically section names. Each group has exactly three distinct resolved supplier legal identities, stable ordered slots and one consolidated table. Each supplier's quote covers all lines of G to satisfy procedural coverage. For n groups, 3n active quote slots/documents per round, not 3×asset count, no fourth/fifth active supplier in a group. Revisions/history may exceed 3n files, not additional active suppliers. Use confirmed historical group trio where valid; do not silently choose arbitrary trio if ambiguity/missing data. Replacement is one slot, auditable, no inherited price from a different issuer.

## 3. Preparation cases

1. Same identified asset, same confirmed appraisal unit price, exact compatible specification/unit/currency/tax/terms and matching selected supplier IDs: reuse actual historical quotation values as **historical reference in a new draft**. Use current dossier quantity and STT; never count as current agreement. No repeated identity scan; retain exact match reference and lineage.
2. Previously appraised asset with a changed human-confirmed P: refresh the affected internal proposal cells for the same fixed trio. Sent and actual confirmed quotes and manual overrides retain their values and revision lineage.
3. New asset: classify the asset into an exact group and prepare draft proposals for that same trio. Missing or ambiguous group/identity/compatibility requires attention and a genuine manual request where applicable.

For new or price-changed assets, [P252-05-A](../plan/VALORA_252_SUCCESSOR_ADR_DRAFT_v1.2.md#5-p252-05-a--grouped-nccq-and-knowledge-reuse) defines internal defaults P, 105% of P and 110% of P. Use the uniquely compatible previous equal-price slot for P or visibly default to the first ordered slot. The operator may choose the anchor. With positive representable P and approved quantum q, floor each higher target to q and clamp within [P+q, floor(1.15P/q)q]. Values may coincide. If the interval is empty or inputs are unresolved, require attention/genuine manual request. B05 owns exact q, locale, precision and empty-cell behavior. Record genuine supplier responses faithfully, including values outside the draft cap.

Automatic mode fills eligible empty draft cells, preserves explicit manual overrides, shows provenance and reason. Updating a working appraisal price can require source reconfirmation and re-evaluation of proposal data; does not retrospectively rewrite sent/confirmed actual quotes. Manual mode allows direct editing and paste of actual incoming data or internal proposed values with explicit provenance; do not conflate the two. The same working grid is used; switching modes retains data. Invalid/ambiguous paste no partial commit.

## 4. Document and confirmation lifecycle

DRAFT proposed data → deterministic actual Word generation using verified template version and data snapshot → send/share under actual authorized method and record exact sent revision → receive actual supplier response/retained original signed return (where applicable under owning evidence contract) → user records actual price and explicitly confirms that exact quote revision. No mandatory auto-email. One-click agreement is the operator's attestation, not software impersonating supplier. One click may use unchanged sent data when supplier actually agreed; exceptions may paste changed actual data, keep sent value and return separately. No fabricated signatures, dates or actual offers. Missing required source custody/integrity holds confirmation. Receipt handling remains distinct from human agreement; no extra mandatory UI receipt-confirmation modal. Manual workflow must support genuine received quotes without requiring system-generated outbound Word if admitted by owning contract.

Preserve app-owned immutable retained bytes, exact template version, proposal snapshot, sent/returned revision, identity, mapping, actor/time, receipt and audit. `04_Báo giá nhà cung cấp` outbound working/sent documents and `05_Pháp lý` received signed evidence under existing document placement; never turn provider Working copy or metadata into accepted bytes. TM01/TM03/TM04 real `.docx` template mapping/fill/preview/READY, no mock render proof or PDF export scope. Returned PDF evidence only if separately authorized admission rules; PDF return is not PDF generation authority. Original source and historical revisions unchanged.

The dossier owns quotation dates, applicable expiry/currentness, source custody, actual confirmation and report binding. An authorized KB update reuses the exact confirmed supplier-price revision under existing knowledge review/activation. It requires neither date re-entry nor a duplicate source upload. Price history and minimal integrity lineage support subsequent preparation without a separate KB date/expiry or document workflow.

## 5. Coverage and report

Each exact line of every group needs a current actual item from all three fixed legal suppliers. Each slot needs one current confirmed quote revision whose unique mapped items cover the full group. The quotation head, retained DocumentRevision custody/head and actual item mapping must each pass their owning check. A true shared fault holds all dependent items; a genuine item-local change holds its affected item. Invocation CAS and working-source proof remain separate. Keep an intact current head during negotiation only while its exact quote and retained document proof hold. There is no cross-revision stitching or older-head fallback. [F03](../plan/VALORA_252_TECHNICAL_RECONCILIATION_AND_DOR_V1.md#f03--invocation-working-and-actual-currentness) and [P252-03](../plan/VALORA_252_SUCCESSOR_ADR_DRAFT_v1.2.md#4-p252-03-a--policy-and-currentness) define the separation.

The dossier needs exact partition, current work, every complete slot and no mandatory hold. [P252-04](../plan/VALORA_252_SUCCESSOR_ADR_DRAFT_v1.2.md#6-p252-04-a--derived-supplier_selection) derives SUPPLIER_SELECTION from the ordered group×line×slot binding. Group setup and actual confirmation provide user intent; v2 has no separate selection screen, click or ranking. Each group has one report table with STT, tên, ĐVT, SL, NCC1–NCC3 actual unit prices and independent Tổ TĐG unit/total columns. [P252-02](../plan/VALORA_252_SUCCESSOR_ADR_DRAFT_v1.2.md#7-p252-02-a--finalization) supplies the single final human action in APPRAISAL_RESULT. ADR 0051 remains PROPOSED.

## 6. Command/security contract (logical, proposed)

Server policy derives read and exact action-specific capabilities for draft setup/edit, replace slot, generate, record sent, admit/confirm actual, reject/withdraw and recovery. Preserve same-tenant/Project scope, active actor with owned session, DRAFT, policy/epoch after Project lock, exact target and CAS, retained-source proof and real outer-commit atomic fact/audit/receipt. [F01](../plan/VALORA_252_TECHNICAL_RECONCILIATION_AND_DOR_V1.md#f01--action-specific-recovery) applies to stale upstream: valid scoped withdraw/reject can stay available while register/confirm are held. [F02](../plan/VALORA_252_TECHNICAL_RECONCILIATION_AND_DOR_V1.md#f02--writer-compatibility-transactions-and-receipts) governs all writers, binary and cutover compatibility, and historical lookup separate from projection. The [proposed interfaces and DoR](../plan/VALORA_252_TECHNICAL_RECONCILIATION_AND_DOR_V1.md) retain open blockers and require future validation.

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
| W12 | Real Word mapping/fill, sent/return source, retained bytes and dossier lineage require separate #255 slices. KB price reuse references the confirmed revision without duplicating dossier document handling or currentness checks in the KB surface. |
