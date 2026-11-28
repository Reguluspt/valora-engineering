# Successor ADR #252 — Price work confirmation and grouped supplier-quotation authority

**Status:** PROPOSED technical ADR v1.1; PO business/UI decisions accepted, technical consistency review/acceptance pending. Do not assign an ADR number until live index and owning task checked. Task `VALORA-NCCQ-DESIGN-RECONCILIATION-01` (docs-only). Prior v1.0 issue drafts [I](https://github.com/Reguluspt/valora-engineering/issues/252#issuecomment-7196135718) and [II](https://github.com/Reguluspt/valora-engineering/issues/252#issuecomment-7196164881) remain historical. New decisions supersede their conflicting target assumptions only, not current certified A9/A10/A12/A13/A14 contracts.

## 1. Authority and exact baseline

Verified 2026-11-28 execution baseline `main=cbe99790fd6017166df5b0cedb19d882b5366fe1`, CODEX blob `a670270d0573edbeb3b7014dbebbe807b93408dc`, [CI #715/45835988845](https://github.com/Reguluspt/valora-engineering/actions/runs/45835988845), push/main, exact SHA, completed SUCCESS 5/5. #258 S1 and #259 governance certified. #255 [accepted audit](https://github.com/Reguluspt/valora-engineering/issues/255#issuecomment-7196026314) at same SHA remains historical static source inventory. [PO receipt 28 Nov](https://github.com/Reguluspt/valora-engineering/issues/252#issuecomment-7232992154), [purpose](https://github.com/Reguluspt/valora-engineering/issues/252#issuecomment-7220012630), [three per asset](https://github.com/Reguluspt/valora-engineering/issues/252#issuecomment-7220082565), [#222 final acceptance](https://github.com/Reguluspt/valora-engineering/issues/222#issuecomment-6527664352), [Option A](https://github.com/Reguluspt/valora-engineering/issues/252#issuecomment-6771617305), [D1](https://github.com/Reguluspt/valora-engineering/issues/252#issuecomment-6771778640), [D2–D4](https://github.com/Reguluspt/valora-engineering/issues/252#issuecomment-6772074151). Preserve prior decisions except explicit scoped refinements. No runtime changes. #203/#199 protected; OS-G2 PARTIAL, current cap SUPPLIER_QUOTES, `NO_AUTHORIZED_DOWNSTREAM_ACTION`. Supplier Selection/Appraisal Result/document acceptance/release not activated; ADR0051 is PROPOSED.

## 2. Context and decision

The [PO clarification on NCC knowledge reuse](https://github.com/Reguluspt/valora-engineering/issues/252#issuecomment-7233544880) and [PM follow-up receipt](https://github.com/Reguluspt/valora-engineering/pull/263#issuecomment-7234404160) narrow the KB target described in §§4–5. The clarification applies to design scope only.

A9/A10 currently bind qualifying_basis and a set confirmation; A13 relies on upstream COMPLETE and confirmation ID/hash. F255-01 whole-set staleness may affect unrelated quote; F255-02 frontend globally gates recovery by `snapshot.writable` despite backend action-specific exceptions; F255-03 outbound real Word lifecycle gap. A7/A8 validation/input digest includes appraisal price; changing price may stale upstream proof. Never change only a frontend predicate or remove server gate to implement target.

Target: after structural readiness, complete human confirmation of working sources and appraisal unit price for exact S; then prepare grouped NCCQ. This supersedes draft P252-01 proposal to allow quote collection/confirmation before price-source work completes. Earlier Option A distinguishes working readiness from final source acceptance; new direction requires an explicit **working confirmation** before quote preparation, not earlier final `Chấp nhận làm cơ sở`. D1 single operator. D2 quote confirmation attests actual supplier agreement only. D3 dependency-specific currentness, D4 per-dossier reconciliation. Three distinct fixed suppliers per quotation group, each line covered by all three. Source priority remains Internet survey / unit-price explanation / prior appraisal RESULT (not NCC). NCC data procedure/report only; cannot determine or validate appraisal price. Internal proposal constraints are not constraints on genuine offers. No automatic price setting, no NCC-based suitability rule, no `below_working_price` or `difference_exceeds_15_percent` as target valuation warning. Keep historical v1 behavior/tests until successor activation; proposed target warning rule reconciliation is limited to new semantic design, not a change to runtime.

## 3. Proposed versioned predicates and stages

Logical names, no existing schema/API implied. S = full nonempty exact sealed official line set. Structural readiness = current admitted membership, exact identity/lineage, valid description/spec/unit/quantity, applicable existing A7/A8 proof, no structural/integrity hold. Source work readiness = meaningful retained independent candidate relationships for each l in S, valid provenance/type/line mapping, no applicable unresolved hard hold. Mere URL or AI note, proposal or NCC value, local draft or corrupted source is insufficient.

Proposed `PRICE_WORK_CONFIRMED`: current coherent server snapshot of S, structural proof, per-line eligible working source selection and user-confirmed positive appraisal unit price with existing permitted unit/currency/scale and actor/receipt/audit, no outstanding mandatory source issue; human confirms completed work. It is not final acceptance. Preserve original A9/A10 historical facts under v1. Exact form of working confirmation (set event versus derived line decisions with explicit completion command), granularity of dependencies and eligibility taxonomy remain technical review/PO decision. No auto-generating final acceptance. For target, PRICE_EVIDENCE COMPLETE must represent the agreed working-confirmation gate, not final source basis. If evidence is incomplete, source stage/Next Action remains truthful; NCCQ preparation held. Read diagnostics or limited authorized withdrawal/rejection may remain available with proven scope.

NCCQ groups partition exact S, each ordered trio T(g) has exactly three distinct resolved supplier identities. For each l in g and s in T(g), require current human-confirmed actual quote revision with exact line mapping, retained source, issuer/terms and applicable currentness. Procedural coverage iff all pairs covered. SUPPLIER_QUOTES stage COMPLETE only with current upstream working proof + complete group coverage + integrity. Server derives all counts independent of pagination. No independent per-line trio, no file-count substitution, no unconfirmed/draft/history-as-current. For two groups, six active slots, two report tables. No automatic fourth supplier; replacement explicitly changes one slot and triggers exact dependent handling.

After SUPPLIER_QUOTES COMPLETE retain current downstream hold. No approval of checkpoint deletion. Since the fixed group trio makes per-line selection potentially redundant, recommend a future whole-group exact revision binding/report readiness projection instead of choosing again per line; retain current routing and ADR0051 proposed status until PO decision and separate owning contract. No stage addition/deletion/activation by this docs PR.

## 4. Commands / security / currentness

See [Workflow v2](../design/VALORA_NCCQ_WORKFLOW_CONTRACT_V2.md) and [Editable Data Grid v1](../design/VALORA_EDITABLE_DATA_GRID_CONTRACT_V1.md). One server versioned policy resolver must govern stage/provider/Case State, action-specific capabilities, prepare, commands and commit. Preserve project read, workbench edit/session and #208 TXT admission where applicable; no new permission/grant or provider scope. Require same tenant/project, active actor, DRAFT, exact policy epoch and relevant versions; fresh authorization, project-first deterministic lock, canonical request/decimal digest, atomic append facts/receipt/audit, no ambiguous replay or unsafe retry. Source/price work confirmation required before target quote preparation; narrow recovery (withdraw/reject) may be allowed despite upstream stale if exact target/scope/integrity remain proved. F255-02 reconciliation must distinguish capability of recovery from ordinary writes. No UI-only override.

D3 separates invocation CAS (refresh/reject on changed snapshot) from semantic currentness. Proposal reference binds exact working appraisal decision/line/group/trio; if user changes working price, new draft proposal needs refresh after source reconfirmation, no rewrite of sent/confirmed actual quote. Historical actual quote reuse is a new draft reference only. Adding unrelated evidence may change CAS or working proof; does not automatically invalidate actual quote. Quote semantic proof binds exact mapped asset/spec/quantity/unit/terms, issuer/identity, retained source revision/bytes, confirmation, deadlines and true explicit dependencies, not unrelated source-set hash. Source withdrawal affects only actual dependencies; membership/group change affects exact mappings/slot and requires owning contract. Quote-wide identity/bytes/terms failure holds all affected items, no partial re-sign or silent rebind. If A7/A8 current proof changes due price edit, hold affected writes/stage until valid proof recovered; do not demand reconfirmation of unchanged real quote solely due price. Integrity uncertainty fails closed. UTC expiry equal boundary, no clock-based churn hash. Preserve revision history, no older fallback. Reconcile v1 correction/negotiation semantics without silent behavior change. Item-local derived eligibility vs whole revision policy remains proposed and requires proof and test, not approval here.

D3 currentness for actual quotations belongs to the owning dossier. Keep A13 source custody, applicable quotation dates/expiry, retained bytes, exact sent/returned revisions, explicit confirmation and report binding. A KB version carries the identity, revision/audit metadata and minimum referential lineage needed for integrity. Existing records and current eligibility checks remain in force.

## 5. Proposal generation and knowledge

See the [Knowledge Reuse contract](../design/VALORA_NCCQ_KNOWLEDGE_REUSE_CONTRACT_V1.md). Reuse source-phase matching; fixed trio per group. Historical unchanged-price branch uses compatible actual historical values by exact supplier ID, never a current attestation. New/changed-price branch prepares only internal draft request values constrained by confirmed P: one equals P; other two > P and <= 1.15 P. Exact algorithm/rounding, slot choice, mixed history and infeasible/missing data handling are open; no production generator until accepted. Any actual supplier response is recorded exactly, even outside that range; no valuation warning or automatic appraisal change. No fabrication of quotes, signatures, dates or supporting evidence. Manual data grid uses same exact targets and actual vs draft provenance.

Keep appraisal-result candidates and NCC confirmed-price candidates distinct under existing review/activation. For authorized supplier-price updates, reuse the exact confirmed dossier revision without asking the user to re-enter the quotation date or upload the source again. Keep asset/variant, group/trio, supplier identity, compatible specification/unit/currency/terms and append-only price versions. The KB surface has no separate quotation-date or expiry workflow and no source-document management or lookup. Internal proposals remain draft data. Independent valuation evidence continues under its own authority.

## 6. Future finalization (P252-02 still proposed)

Recommend one authorized human action within existing APPRAISAL_RESULT after current result tables, separately authorized selection/result/administrative checks and before official report/certificate revision acceptance/sign/issue. No new stage/S17 whole-case dashboard, second approver or extra professional receipt step. Exact placement and administrative completion prerequisite not explicitly approved; keep hold. Final accepted source pairs are independent eligible valuation sources only, NOT NCC quote data. All selected exact line×source revisions, suitability, current appraisal decision, actor/time, result proof and version snapshot committed atomically with receipt/audit under CAS; no partial accept, no blanket accept or automated price change. True professional final acceptance only at explicit `Xác nhận hoàn thành hồ sơ`; report must reflect actual independent valuation methodology. Postfinal amendments separately authorized, no mutation of accepted snapshots/DocumentRevision/ReleaseManifest.

## 7. D4 cutover (P252-03 details still proposed)

One durable versioned server policy per dossier, existing v1 preserved until explicit eligible reconciliation. No global toggle, bulk conversion, implicit read promotion or mixed mutation. Preview exact line/group/trio/mode/version, source history, confirmed quote revisions, missing proof and actual historical/working candidates. Eligible DRAFT/unfinalized/nonreleased and exact scope/history integrity; unclear/invalid holds; #199 excluded. Old A10 confirmation is v1 historical fact only, not final v2 acceptance. Preserve existing actual quotes as historical; operator explicitly adopts exact still-current proven revisions/slots under separately approved reconciliation, no new signature solely for policy change. Old one-supplier coverage cannot certify v2 three slots. Missing selected supplier stays incomplete, no artificial third quote. Preview nonmutating, fresh project/line/quote/version/CAS and atomic policy/epoch/journal/receipt/audit commit. Failed transaction leaves v1; rollback after v2 writes must preserve history/fail closed/forward repair under approved procedure, no deletion or silent reverse conversion. Exact schema, migration and adoption/currentness policy require independent review and approval. New dossier default v2 only after separate activation.

## 8. Acceptance matrix — future runtime, NOT RUN

| ID | Required evidence |
|---|---|
| AC01 | v1 unchanged before cutover, exact current A9/A10/A13 facts and one-NCC stage semantics preserved. |
| AC02 | source work not confirmed / missing line or price: no target quote preparation, no artificial COMPLETE; diagnostics and scoped recovery separate. |
| AC03 | independent eligible sources + explicit human working confirmation distinct from final acceptance; NCC-only input never sufficient. |
| AC04 | multiple candidate/shared source and transitive dependency, exclusion vs material hold; exact scope. |
| AC05 | #222 preliminary carry, 3/150 lines, exact mapping/provenance/receipt, no name matching or auto acceptance (separate scope). |
| AC06 | group preparation only after current work proof, same 3 slots, draft/returned-but-unconfirmed zero procedural coverage. |
| AC07 | 2 groups 6 slots, each line all 3 selected supplier IDs; duplicate/partial/extra/missing membership and filtered page cannot COMPLETE. |
| AC08 | unrelated evidence change: CAS refresh/proof as applicable, no blanket actual-quote invalidation. |
| AC09 | user updated price: affected proposals refresh, upstream revalidation as needed; actual signed quote stays immutable; no appraisal suitability warning from real price. |
| AC10 | spec/quantity/unit/group/slot changed: only actual dependencies held; no auto-rebind or history overwrite. |
| AC11 | expiry boundary, withdrawal/issuer disabled/bytes missing/concern: fail closed, no older fallback. |
| AC12 | F255-02 valid recovery while upstream held, no broad writable bypass. |
| AC13 | cross-tenant/project/role/session, denied revision/media/payload; no unauthorized mutation or source disclosure. |
| AC14 | CAS/races/revocation at commit, replay/lost response, exact receipt, atomic audit. |
| AC15 | per-dossier preview and explicit cutover, historical v1 intact, exactly 3 target slots, no invented missing quotes. |
| AC16 | cutover concurrency/rollback/crash/finalized/unknown state, no partial v2 facts or mass conversion. |
| AC17 | #255 actual Word/template/sent/return, confirmed quote data only, one-click agreement, actual price outside draft range kept (separate scope). |
| AC18 | future finalization selected independent evidence only, actual required procedure separately verified, no early acceptance. |
| AC19 | future reopen/amend preserves snapshots and release history. |
| AC20 | 3/150-line grid/paste/keyboard/focus, full-set counts and error/stale/denied/unknown recovery (future product scope). |
| AC21 | Authorized KB price update/reuse from exact confirmed supplier revision without duplicate quotation date or source upload. Price history, identity, minimal lineage, audit and review/activation retained. Dossier currentness, document custody and report binding stay in their owning flow. |

Use real migrated isolated PostgreSQL/storage and synthetic fixtures when runtime authorized; no #199/#203 mutation. Exact T0–T4 and High/Product A/B on frozen HEAD; no claim new runtime evidence from prototype or #715.

## 9. Remaining decision table / DoR

| ID | Disposition / recommended next decision |
|---|---|
| P252-01 | OLD A/B superseded in part by PO sequential direction. New technical working-confirmation fact and exact eligibility/currentness needs review. Do not revive parallel preconfirmation quote workflow. |
| P252-02 | OPEN: location and predicate of whole-case finalization; recommend APPRAISAL_RESULT action, not a new stage. |
| P252-03 | OPEN: exact v1/v2 cutover, adoption and item-local vs whole-revision eligibility; D4 per-dossier direction binding. |
| P252-04 | OPEN: retire/reconcile per-line NCC Selection checkpoint vs whole-group slot binding; ADR0051 remains proposed, #147/#149 affected. |
| P252-05 | OPEN: grouping/identity/trio choice and fallback when historical match missing, mixed groups, exact value-selection/rounding rules, selected slot assignment. No automatic fabrication. |
| P252-06 | OPEN: ordering vs #203 business UAT and narrow OS-G3 Document Runtime prerequisite authority for #255. |

### Accepted #255 inventory and target gaps

The [accepted static audit](https://github.com/Reguluspt/valora-engineering/issues/255#issuecomment-7196026314) keeps its classifications at the pinned baseline. The [target overlay](https://github.com/Reguluspt/valora-engineering/issues/255#issuecomment-7233060782) adds design dependencies and future evidence.

| Audit IDs | Accepted source classification | Iteration 7 overlay |
|---|---|---|
| G01 | IMPLEMENTED (bounded A13/A14) | v1 coverage remains certified. The three-slot requirement is successor work. |
| G02 | NOT_FOUND_IN_INSPECTED_SCOPE | Grouped preparation after confirmed source work and price. |
| G03 | PARTIAL | Fixed trio and exact group membership, source-phase knowledge reuse and manual rectangular grid. |
| G04–G05 | PARTIAL | Actual Word template and mapping authority. |
| G06 | NOT_FOUND_IN_INSPECTED_SCOPE | Actual test fill and template READY proof. |
| G07–G08 | NOT_FOUND_IN_INSPECTED_SCOPE | Actual Word output and exact sent snapshot. |
| G09 | PARTIAL | Actual return admission and retained evidence linked to the exact offer. |
| G10 | IMPLEMENTED (bounded A13/A14) | v1 confirmation remains certified. Target one-click confirmation requires exact current group-slot revision and actual agreement. |
| G11 | NOT_FOUND_IN_INSPECTED_SCOPE | Sent-versus-returned comparison for document lineage. |
| G12 | PARTIAL / high-risk integration gap | Keep exact source → generated/sent Word → signed return → confirmed quote, line mapping, audit and report binding in the dossier. KB retains price versions and the reference needed to identify the confirmed revision. |
| G13 | PARTIAL M365 plumbing / business child flow unverified | Keep outbound working/sent documents in `04_Báo giá nhà cung cấp` and signed returns in `05_Pháp lý` under the owning contract. KB price reuse requires no duplicate upload or document lookup. |
| G14 | NOT_FOUND_IN_INSPECTED_SCOPE | Distinct source-work confirmation and independent final source acceptance. |

### Future acceptance trace

| Requirement | Workflow v2 | Grid v1 | Knowledge v1 | ADR acceptance |
|---|---|---|---|---|
| Certified v1, compatibility, currentness and command safety | W11 | DG04 | KB05 | AC01, AC08–AC16, AC19 |
| Prequote human confirmation and independent source authority | W01, W09 | — | KB01, KB03 | AC02–AC05, AC18 |
| Exact group coverage, slot binding and report structure | W02, W08, W10 | DG01–DG03 | KB01 | AC06–AC07, AC17, AC20 |
| Reuse, new/changed price proposals, manual entry and replacement | W03–W05 | DG01–DG05 | KB01–KB03, KB05 | AC06, AC09–AC10, AC20 |
| Actual confirmation, real Word, return/lineage and knowledge review | W06–W07, W12 | DG04–DG05 | KB04–KB05 | AC11–AC14, AC17, AC20 |
| PO NCC KB overlay, separate dossier custody/currentness and #255 G12/G13 | W11–W12 | — | KB04–KB06 | AC11, AC13–AC14, AC17, AC21 |

DoR for docs reconciliation: authorized scope + certified baseline + accepted PO target; unresolved engineering points explicitly PROPOSED/HOLD. Runtime DoR NOT READY. No model/runtime task opened. No blanket business approval inferred from this draft or CI. Future logical slices: (A) source work gate/versioned action/currentness, (B) per-dossier reconciliation and compatibility, (C) grouped grid/KB handoff/manual UX, (D) minimum real template/fill/generation under #255 and OS-G3 authority, (E) sent/return/confirm/knowledge, (F) selection/report/finalization under later stage authority. Design coherent vertical outcome, do not activate partial v2. WIP 1 implementation + 1 authority/design + 1 read-only discovery. Preserve #251 limited design/DoR. No code, migration, provider, RBAC, merge, deploy.
