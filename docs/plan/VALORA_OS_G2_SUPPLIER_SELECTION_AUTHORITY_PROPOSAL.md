# OS-G2 A15 — SUPPLIER_SELECTION authority proposal

**Status: PROPOSAL ONLY. D1–D12 PO status: PENDING. SUPPLIER_SELECTION runtime: UNAUTHORIZED. APPRAISAL_RESULT: UNAUTHORIZED.**

**Task:** `VALORA-TASK-OS-G2-A15-SUPPLIER-SELECTION-AUTHORITY-PROPOSAL`, [Issue #145](https://github.com/Reguluspt/valora-engineering/issues/145), read in full. **Date:** 2026-10-08. The only A15 repository output is this document. Recommendations below describe a future separately authorized implementation; they create no schema, migration, service, API, provider, frontend or RBAC change. Gate Owner owns proposal integration; Product Owner owns explicit D1–D12 acceptance. Merge, review PASS and CI SUCCESS do not accept these decisions or authorize runtime.

**Verified execution baseline:** live `main = 579d68a2122eac017615320a7f79c18184678183`; [exact-main CI #630 / run 37717959755](https://github.com/Reguluspt/valora-engineering/actions/runs/37717959755), COMPLETED / SUCCESS on that SHA. [UIUX-GOV-001 / #142 certification](https://github.com/Reguluspt/valora-engineering/issues/142#issuecomment-6051301155) is CERTIFIED / CLOSED. [A12 PO acceptance](https://github.com/Reguluspt/valora-engineering/issues/135#issuecomment-6030394940) accepts D1–D5 and D7–D12 as proposed and D6 with the human-click clarification; [PR #136](https://github.com/Reguluspt/valora-engineering/pull/136) is merged. [A13 certification](https://github.com/Reguluspt/valora-engineering/issues/137#issuecomment-6036528188), [PR #138](https://github.com/Reguluspt/valora-engineering/pull/138), certifies backend/domain/provider/API at `6e9c60f9bad6117f90fcdd85d636903f91097df5`, CI #622. [A14 certification](https://github.com/Reguluspt/valora-engineering/issues/139#issuecomment-6041091878), [PR #140](https://github.com/Reguluspt/valora-engineering/pull/140), certifies Product UX / browser E2E at `dbcc4f5ca39803dffa360e4eddba064156335dd3`, CI #625. Current certified product/runtime boundary is **SUPPLIER_QUOTES**; after its COMPLETE, **NO_AUTHORIZED_DOWNSTREAM_ACTION** remains actual product truth. Full OS-G2 is **PARTIAL / INCOMPLETE**.

CODEX and A12/A13/A14 reports retain dated earlier candidate/status wording. The later explicit certifications and current #145 contract resolve those status differences within their named scope; they do not weaken the documents' business/security invariants. No historical document is rewritten here. LIVE REPOSITORY WINS: fetch and compare live main/current authority again before freeze; material drift stops the candidate.

## 1. Authority and exact-baseline inventory

The assigned task requires reconciliation across current quotation authority and historical selection. These reads are evidence for recommendations, never automatic promotion of old runtime.

| Source | Applicable meaning |
| --- | --- |
| [CODEX §§1, 8.1, 10](../../CODEX.md), [Engineering Guardrails §§4–6, 8, 11](../../ENGINEERING_GUARDRAILS.md), [Operating Protocol v2](VALORA_AGENT_OPERATING_PROTOCOL_V2.md) | Human authority, tenant/RBAC/session, immutable facts, shared CAS, atomic audit, Local Saturation and exact-SHA review/CI. |
| [Unified Roadmap §§3, 10–11, OS-G2](../VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md), [UIUX master §§1.1–1.3, 2.1, 3](../design/VALORA_UIUX_HANDOFF_v2.3.md), [authority index](../design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md) | Separate ordered stages, server-owned truth, Fluent 2 light, Vietnamese-first, desktop/table-first. |
| [A12 authority](VALORA_OS_G2_SUPPLIER_QUOTES_AUTHORITY_PROPOSAL.md), [A13 runtime](../implementation/VALORA_OS_G2_SUPPLIER_QUOTES_RUNTIME.md), [A14 product](../implementation/VALORA_OS_G2_SUPPLIER_QUOTES_PRODUCT.md), certifications above | Current confirmed exact-line A13 items, explicit human click, retained source byte identity, minimum one Supplier per sealed line, currentness, receipts and warnings. No extra source-content verification/checklist or second approver. |
| [NCC Selection baseline](../design/VALORA_UIUX_HANDOFF_v2.3_NCC_SELECTION_BASELINE_ADDENDUM.md), [warning addendum](../design/VALORA_UIUX_HANDOFF_v2.3_NCC_PRICE_WARNING_RULE_ADDENDUM.md), [final-result baseline](../design/VALORA_UIUX_HANDOFF_v2.3_FINAL_RESULT_BASELINE_ADDENDUM.md) | Preserve per-line explicit selection/history and non-blocking comparison warnings. Replace legacy candidate identifiers through D10; final-result layout/routing is a later dependency, not authority to generate it. No post-quotation NCCQ aggregate screen. |
| [ADR 0039](../adr/0039-tenant-safe-ncc-selection-revisions.md), [PR-03 contract](../implementation/VALORA_UIUX_V2_3_PR03_NCC_SELECTION_PERSISTENCE_CONTRACT.md), [PR-04 contract](../implementation/VALORA_UIUX_V2_3_PR04_NCC_SELECTION_API_UI_CONTRACT.md), [PR-03 audit](../audits/2026-09-05__PR-03__NCC_SELECTION_PERSISTENCE_AUDIT.md), [PR-04 audit](../audits/2026-09-05__PR-04__NCC_SELECTION_API_UI_AUDIT.md) | Accepted historical foundation: revisions/head, human commit, CAS, warning snapshots and no rebind. Legacy catalogue matching, uploader-derived source ownership, permission and payload do not meet current A13 authority. Historical test results do not prove future selection. |
| [Frontend Architecture Rule](../architecture/VALORA_FRONTEND_ARCHITECTURE_RULE.md), [G6 plan](VALORA_OS_G6_PRODUCT_COMPLETION_AND_VISUAL_CONVERGENCE_PLAN_V1.md) | Tokens → Fluent primitives → shared components → feature → screen; Continuous Visual Integrity now, Final Visual Convergence in G6. Current server/domain semantics outrank obsolete mockup semantics. |

At the verified baseline:

| Exact code evidence | Observed fact / compatibility gap |
| --- | --- |
| [Legacy models](../../backend/app/modules/project_master_data/models.py), `NccSelectionRevision` / `NccSelectionCurrentHead` | Revision requires non-null `quote_batch_id`, `quote_line_id`, `evidence_file_id`; head points to that legacy revision. Price uses Numeric(15,2), quantity Numeric(15,4), with float annotations. Those required FKs and scales cannot represent A13 losslessly. |
| [Legacy service](../../backend/app/modules/project_master_data/application/ncc_selection_service.py) | `project:update`; ACTIVE batch/line + batch approval + canonical/variant match; EvidenceFile ownership through uploader; independent legacy warning calculation and no A13 Workbench/shared-token contract. |
| [Legacy API](../../backend/app/api/projects.py), [legacy schemas](../../backend/app/modules/project_master_data/schemas.py) | GET `/api/v1/projects/{project_id}/ncc-selections` uses `project:read`; POST `/api/v1/projects/{project_id}/asset-lines/{line_id}/ncc-selection` uses `project:update`, `quote_line_id`, head revision, string idempotency key and `confirmed`. No A13 item/revision/source/seal invocation proof. |
| [NccSelectionPage](../../frontend/src/components/ncc-selection/NccSelectionPage.tsx), [controller](../../frontend/src/components/ncc-selection/useNccSelection.ts), [adapter](../../frontend/src/api/nccSelection.ts) | Useful table/drawer/current/history shape and explicit action; monetary JSON fields are JavaScript numbers, and legacy command recovery lacks A14's durable original-UUID receipt protocol. |
| [A13 models](../../backend/app/modules/project_master_data/supplier_quote_models.py), [schemas](../../backend/app/modules/project_master_data/supplier_quote_schemas.py) | Append-only Fact/Item/Receipt journal. Item price/quantity Numeric(26,8). `quote_id` is the retained DocumentRecord ID. Registration/revision facts own quote revision identities; line-registration facts can own the effective items. |
| [A13 authority](../../backend/app/modules/project_master_data/application/supplier_quote_authority.py), [commands](../../backend/app/modules/project_master_data/application/supplier_quote_commands.py), [source admission](../../backend/app/modules/project_master_data/application/supplier_quote_source.py), [provider](../../backend/app/modules/project_master_data/application/supplier_quote_provider.py) | Fold determines latest and contributing confirmed heads separately, exact effective item set, currentness, concerns, warnings and coverage. Source authority is DocumentRevision/CurrentHead/StorageObjectBinding with bounded verified bytes, not EvidenceFile. |
| [Case State registry](../../backend/app/modules/project_master_data/application/case_state_projection.py), [shared authority/CAS](../../backend/app/modules/project_master_data/application/asset_review_authority.py), [Workbench requests](../../backend/app/modules/project_master_data/asset_workbench_schemas.py), [session/access checks](../../backend/app/modules/project_master_data/application/asset_review_line_commands.py) | Current registry is `global-case-state-v6-supplier-quotes-v1`; all stages from SUPPLIER_SELECTION onward unavailable. Shared snapshot/token and Project-first commands already exist. No second selection-only workflow/token is needed. |

## 2. D1 — Business meaning and COMPLETE

Recommend **one explicit current valid human-confirmed selection of an A13 quotation item for each exact sealed ProjectAssetLine**. Scope is organization + Project + exact line, with one logical selection history/head. Selection records which offer the professional chooses for later comparison/presentation. Supplier-global state, quotation confirmation and final appraisal price are separate authorities. Selecting the same Supplier on many lines is allowed, with a distinct eligible item for each exact line.

Let `M` be the exact non-empty current sealed set inherited from SUPPLIER_QUOTES. Let `H(l)` be the uniquely resolved latest selection revision for exact line `l`, and `Eligible(item, snapshot, now)` be current A13 authority, not a duplicated predicate. Recommend:

```text
future selection capability separately accepted, implemented and certified
AND current SUPPLIER_QUOTES = COMPLETE, including its upstream closure
AND tenant/Project/Intake/seal/membership correspondence exact and non-empty
AND no applicable accepted Blocking concern or unprovable required integrity
AND for every l in M:
    exactly one H(l), kind confirmed-selection rather than withdrawal
    AND intact immutable fact + command receipt + atomic audit
    AND explicit authenticated human confirmation recorded
    AND exact selected item is Eligible for this tenant/Project/l now
    AND selection dependency bindings are current with no retained invalidation
```

This is compute-on-read from authoritative facts. No persisted stage-done Boolean, page visit, radio state, Supplier ID, legacy `selected` label or head pointer alone establishes COMPLETE. An empty set does not complete vacuously. Head uniqueness without valid lineage does not count.

Recommend **no separate whole-stage confirmation**. Per-line commits already attest the substantive choice; a second button repeats coverage and would add a stale whole-set fact without a distinct business decision. A stage-wide attestation is an alternative only if PO defines a separate professional obligation. Ordinary selection does not require a checklist, mandatory warning acknowledgement or second approver.

## 3. D2 — Exact membership

Inherit A13's current sealed Project membership, seal ID, membership version, authoritative set digest, immutable original STT/order, exact line IDs and line bindings. Every member requires one selection. No NOT_APPLICABLE, zero-selection waiver, added/removed line, reorder, re-Apply or membership repair is proposed. An asset that needs exclusion returns to separately authorized membership authority; selection cannot grant it.

Multiple similar lines do not share an item by canonical/variant match. One A13 item maps to one exact ProjectAssetLine and its quoted quantity/unit. Selecting one Supplier for several lines requires each line's own A13 item; it does not fan out an item or allocate it twice. Optional additional eligible quotations remain available for deliberate comparison without creating a mandatory-three rule.

## 4. D3 — Eligible candidates and exact A13 binding

Recommend using the **same coherent A13 authority fold** used by SUPPLIER_QUOTES. A selectable candidate is an exact `SupplierQuoteItem` in the effective item set of that logical quote's **current contributing confirmed revision**, with A13 `eligible` true and no applicable hold. Require same organization, Project and exact line, current resolved active/unmerged/unambiguous Supplier, exact current retained source identity/verified-byte proof, effective/unexpired quotation authority and intact journals. Stage prerequisite remains current SUPPLIER_QUOTES COMPLETE.

Do not assume `SupplierQuoteItem.fact_id` identifies the confirmation or the quote revision. It identifies the fact that wrote that item: registration/revision or line-registration. Persist and verify the tuple:

```text
DocumentRecord quote_id
+ registration/revision SupplierQuoteFact ID and revision_number
+ exact contributing confirmation SupplierQuoteFact ID
+ effective SupplierQuoteItem ID and its owning fact_id
+ current A13 quote journal/head version
+ exact DocumentRevision source_revision_id and retained binding proof
```

Resolve that tuple through A13's fold, including the confirmation's `confirmed_items`; never select an obsolete item left behind by draft line-registration. The selected revision is the contributing confirmed head, which can differ from latest draft head. A negotiation draft alone does not invalidate the still-current confirmed predecessor. Correction/replacement withdraws it; confirming a successor supersedes the complete predecessor item set, including omitted lines. Rejecting an optional negotiation draft can leave the predecessor current. There is no older-revision fallback after withdrawal/correction/supersession, even if another quote keeps overall stage coverage COMPLETE.

Expose all current eligible offers for the exact line, with paging and server-owned stable presentation order. Additional valid quotes do not require selection; exactly one item is selected. Historical/unconfirmed/stale offers may be inspected with server reasons and disabled choice, never quietly included as candidates. No lowest-price default, algorithmic Supplier choice, fuzzy/alias identity confirmation, historical fallback, legacy QuoteLine authority or generic knowledge-route admission. Warning codes never remove an otherwise eligible item.

## 5. D4 — Immutable selection facts and precision

Recommend a successor selection journal, one head per organization/Project/exact line and durable command receipts. Names in this section are conceptual requirements, not implemented models or APIs. A head is a mutable index of immutable history, with CAS; it is never business truth by itself.

| Immutable fact group | Required successor facts |
| --- | --- |
| Scope/revision | Organization, Project, exact line ID; selection fact ID, positive monotonically increasing selection revision, predecessor ID, kind; exact seal ID, membership/set digest and upstream binding references. |
| A13 quotation tuple | All identities from D3, quote revision/content digest, effective item-set digest, item owning fact ID, confirmation receipt/audit references, quote journal version at commit. Keep latest-draft invocation context distinct from selected confirmed authority. |
| Supplier | Exact Supplier ID and tenant; pinned A13 Supplier version/material identity binding, active/merge/ambiguity proof; minimized safe display-name snapshot. No tax/contact data in public context or audit. |
| Terms | Quote number or explicit not-issued context, quote date, effective timestamp, nullable supplier expiry, mandatory A13 review deadline, comparison-basis declaration; immutable quoted terms/content reference. |
| Item values | Exact positive Decimal unit price and quantity, resolved currency code/registry identity/version, unit identity/code/binding, safe source item locator and exact line description/specification/quantity/unit binding digest. |
| Retained source | DocumentRecord ID, exact DocumentRevision ID/generation/checksum, CurrentHead reference/generation, StorageObjectBinding ID, byte length, provider generation/version/creation identity, minimized source-proof digest and availability/integrity observation reference. Do not expose storage key/path/URL or bytes. |
| Comparison | Nullable current working-price snapshot, its currency/unit/quantity/reference binding, comparable flag/reason, Decimal difference amount/percent when meaningful; canonical warning codes/calculation version and optional acknowledged-code subset. Working price is context only. |
| Professional history | Authenticated human actor ID, owned session ID, server UTC commit time, explicit confirm fact, predecessor/reason for change/reconfirm/withdrawal; bounded protected reason text in domain history, never bulk audit. |
| Command/integrity | Stable UUID, command contract, canonical request digest, receipt ID and historical result, audit ID/content digest, pre/post Project version, pre/post head revision, expected shared case token and exact invocation bindings. |

Unit price and quantity must preserve **at least A13 Numeric(26,8)** precision and range end-to-end: Python Decimal, adequate database Numeric, JSON decimal strings and string-safe frontend display. Do not funnel them through legacy Numeric(15,2)/(15,4), float annotations, JSON numbers or JavaScript arithmetic. Currency display rounding does not round stored authority. Threshold decisions use full precision; displayed percentages may be rounded only after the decision. Differences require adequate precision for subtraction; percent is a derived Decimal with explicit scale/rounding metadata, not an input authority.

Existing working price is legacy comparative data and A13 currently converts its stored value with `Decimal(line.appraised_unit_price)`. Preserve that canonical interpretation and disclose its provenance; selection cannot reconstruct an exact original value by casting a float, nor silently change A13 comparison semantics. No working-price precision migration is included here. A later shared-comparison change, if needed, must be explicit and cover A13 and selection together.

## 6. D5 — Lifecycle, withdrawal and invalidation history

| Operation | Recommended durable effect |
| --- | --- |
| First confirmation | Immutable revision 1, confirmed-selection kind; expected empty successor head and revision 0; exact A13 tuple and snapshots. |
| Change to different eligible item | New revision `n+1`, predecessor `n`, bounded reason, changed event; never UPDATE old fact. Different item from the same Supplier is still a change. |
| Reconfirm after stale | New explicit revision `n+1`, predecessor/reason, fresh candidate and all proofs. May use the same exact item only if A13 proves it currently eligible; otherwise professional chooses its eligible successor or another offer. Never copy old confirmation across IDs. |
| Same item on already-current head with new UUID | Reject as redundant/conflict; it is neither a change nor a stale reconfirm. True same-UUID replay returns the original receipt. |
| Withdraw / clear | Append revision `n+1` with withdrawal/tombstone kind, exact predecessor target and reason; retain head pointing to tombstone and all earlier history. No physical deletion or fallback to earlier selection. |
| Confirm after withdrawal | Append `n+1` with an explicit eligible item and reason, against the tombstone revision. Revision count never resets to 1. |
| Quote/source successor or external invalidation | No selection rebind, new selection, head repair or final-price write. Compute diagnostics and retain invalidation provenance. |

Recommend **REUSE WITH COMPATIBILITY WRAP** for the semantic `NCC_SELECTION_MARKED_STALE` diagnostic, replacing its legacy evaluator with D8. It may append a minimized once-per-head/dependency-generation observation with atomic audit; it cannot rewrite selection facts, move the selected head or attest a choice. Selection remains read-derived; diagnostic reconciliation is not professional confirmation.

A known invalidation must remain traceable after a transient source fault clears. The later runtime contract must retain an append-only invalidation observation/generation keyed to the exact selection revision and dependency fingerprint, through authorized dependency writers or bounded diagnostic reconciliation. Pure GET/Case State reads do not write facts. A newly detected fault suppresses validity immediately; recovery cannot restore that same head merely by refreshing or repairing bytes. Only a fresh explicit selection revision against proved current dependencies clears the hold for the successor. Recording observations grants no AI/system/job/worker selection or confirmation authority. This durable diagnostic requirement is a successor-schema/read-model implication, not an implemented A15 mechanism.

## 7. D6 — Human and Workbench authority

Recommend primary CTA **“Xác nhận NCC đã chọn”**, contextualized to one exact line. The authenticated professional deliberately chooses an item and clicks that action; selection of a radio row alone is local preparation. One click commits the choice subject to normal command safety. No additional approval modal, professional checklist or mandatory acknowledgement is justified.

Reuse existing **`workbench:edit` + active owned Workbench session + same tenant + Project DRAFT + exact expected versions/CAS**. Session acquisition retains `workbench:open`; reads use `project:read`. Server reloads active human account/org, grants and session ownership; no spoofed actor/tenant in payload. Existing owner/appraiser grants remain sufficient; no new RBAC is proposed. Legacy `project:update` is not retained as current selection authority: it lacks the professional Workbench gate required by A13 and current official line commands. PO would need an explicit separate decision for new segregation/grants.

Non-DRAFT allows authorized read of intact historical/current facts and valid COMPLETE; it closes new confirm/change/reconfirm/withdrawal. Missing permission/session suppresses mutation actions, not durable business COMPLETE. All first and successor writes require explicit `confirm: true`; the professional cannot delegate it to AI, system, job, worker, price rule, provider or frontend auto-action. Retained source availability/byte integrity is technical safety; no OCR/parser/extraction/semantic comparison/signature-stamp checker or second Supplier confirmation is added to A12 D6.

## 8. D7 — One canonical server warning calculation

Recommend **reuse A13's `comparison_warnings` through one shared canonical server comparison result at selection commit**, resolving the current working reference after locks. Persist the result/snapshot/calculation identity, and use that same result for preparation and read presentation. Do not reuse legacy `_compute_warnings`, which rounds percent before threshold comparison, or calculate thresholds in React. Future extraction of a shared function must keep A13's accepted behavior and tests intact.

For comparable current working price `C > 0` and quoted Decimal price `S`:

```text
difference_amount = S - C
difference_percent = (S - C) / C * 100
below_working_price when S < C
difference_exceeds_15_percent when abs(S - C) * 100 > C * 15
```

Exactly 15% is not the difference warning. Below-working-price still warns at any smaller deviation; both codes survive when both apply. They are **WARNING, never Blocking**, and cannot disable a server-permitted commit or create another checkpoint.

Comparability follows A13's explicit `same_working_unit_basis` declaration and exact quantity/unit/currency compatibility; no currency/unit conversion is inferred. Missing working price or incomparable basis: both differences NULL and no percentage/threshold assertion. Comparable zero working price may retain arithmetic difference `S`, but percent is NULL and no percentage/below-positive-reference warning is fabricated; zero remains distinct from missing. Preparation/history returns the reason when comparison is unavailable. Optional acknowledgements are a validated subset of canonical visible codes; they cannot remove warning truth or become a required completion fact.

## 9. D8 — Currentness and stale

Use one coherent server snapshot and A13's currentness fold, then selection dependency/receipt/audit checks. Pin content/identity/invalidation generations, not merely mutable row versions. Project/head/token increments created by this selection or another independent line's selection do not themselves stale otherwise unchanged selections. CAS protects invocation; it is not a durable business-staleness rule.

| Event / condition | Selection effect and professional recovery |
| --- | --- |
| Selected confirmed quote/item superseded, corrected or replaced | Selected tuple loses currentness even if SUPPLIER_QUOTES remains COMPLETE via another offer. STALE selection with exact historical provenance; explicitly choose/confirm an eligible tuple. No silent rebind. |
| Negotiation successor only | Latest-draft CAS changes, but contributing confirmed head remains eligible under A13. Existing selection stays current if its material dependencies remain intact; old prepared mutation conflicts. |
| Selected quote withdrawal/rejection | Cannot contribute. Previously selected authority becomes STALE; explicit clear/replace required. Rejecting a separate optional draft does not stale a still-current selected predecessor. No reactivation of older quote/selection. |
| Expiry, review deadline or future effectiveness | Require `effective_at <= server_now < min(review_due_at, expires_at if present)`. At the cutoff selected authority loses validity; history stays readable. Reconfirm cannot waive deadline; current eligible authority required. |
| Source replacement/head change, unavailable bytes, checksum/integrity or provider generation/creation mismatch | STALE; suppress selection eligibility immediately and retain observed fault lineage. Restore proved source through its owning authority, then explicitly reconfirm/select; no same-ID byte swap, remote fallback or inferred provenance. |
| Supplier merge, deactivation, material identity/version change or ambiguity | Selected binding non-current; preserve original Supplier snapshot, never follow merge target automatically. Resolve through Supplier/A13 authority then explicitly select again. A13 currently pins its full Supplier binding, so A15 does not exempt cosmetic edits that A13 considers stale. |
| Description/specification/approved identity, quantity/unit, currency/reference or comparison basis changes | Material exact line/quotation/working-reference bindings non-current, including their upstream effect. Restore owning upstream facts/confirmation first; then new explicit selection. No rewriting item values or price. |
| Seal/set/membership change or tenant/Project/line divergence | No valid selection against the old set. Known contradiction/negative hold BLOCKED; unprovable/corrupt required lineage STALE; no add/remove/reorder/tenant repair here. |
| PRICE_EVIDENCE stale or SUPPLIER_QUOTES no longer current COMPLETE | Selection COMPLETE impossible; actual aggregate returns the earliest upstream action/result. Selection dependencies remain traceable, with local invalidation where material facts changed. Do not relabel upstream ordinary INCOMPLETE as selection STALE. |
| Selection successor / withdrawal | Only new head considered. Prior selection immutable/historical; tombstone means ordinary missing selection INCOMPLETE with no fallback. |
| Receipt/audit/content/head integrity failure or orphan success audit | STALE/unprovable authority; known integrity contradiction/active concern may be BLOCKED. Disable writes that would conceal broken history. New successor cannot waive a corrupt predecessor or repair receipts. |
| Permission/session or Project CAS-only change | Reload/deny invocation as appropriate; unchanged business facts do not become stale solely because page/session/token changed. Intact COMPLETE may remain readable outside DRAFT. |

If optional unselected offers become stale, selection need not become stale when its selected closure and A13 stage prerequisite remain intact. A13's applicable global unresolved concerns still block; another valid offer cannot conceal them. A13 currently pins the whole quote's line-binding closure, so a mutation of another item in that same confirmed revision can invalidate the selected quote; selection must respect that actual A13 scope rather than weaken it to a local-row check.

After lock waits and immediately before the caller-owned outer transaction commits, re-resolve actor/session/state, exact versions, A13 tuple, retained byte generation/integrity/availability, Supplier/line/upstream bindings and server deadline. Flush first, recheck with current UTC rather than transaction-start time, perform no later long-running work. Roll back selection/head/Project/receipt/audit if the cutoff or a required dependency fails. This final check is the proposed linearization boundary; a later expiry makes the next read stale while the receipt remains a truthful historical commit. Hash deadline/freshness classifications in shared CAS, never wall-clock ticks. PostgreSQL tests must prove both sides of the boundary.

## 10. D9 — Command, security, CAS and transaction proposal

Recommend three explicit conceptual contracts: **`ConfirmSupplierSelection`** (first selection, change and re-establish after withdrawal), **`ReconfirmSupplierSelection`** (deliberate response to stale) and **`WithdrawSupplierSelection`**. A separate `ChangeSupplierSelection` endpoint is unnecessary; successor-aware Confirm expresses a new choice while operation/predecessor/reason preserve its meaning. These commands are proposals only.

### Shared invocation and receipt contract

For every new mutation, actor/permission/session are D6; Project DRAFT is mandatory. Inputs are strict typed IDs and expected proofs, never client monetary/Supplier/source snapshots: command UUID, versioned command contract, `confirm: true`, exact Project/line, expected Project row version/shared Case State token, seal ID/set digest/membership version, full exact sealed line-version set, owned session ID, current PRICE_EVIDENCE confirmation reference and upstream binding digest, expected selection head ID/revision (NULL/0 only when never selected), predecessor/target and bounded reason where required. Positive commands additionally include the exact D3 A13 tuple, expected latest quote head ID/version and selected confirmed head/confirmation/item digests, Supplier version, source revision/generation/proof and comparison-reference digest. Preparation supplies these authoritative invocation proofs.

| Command | Operation-specific input / currentness | CAS, receipt and audit |
| --- | --- | --- |
| ConfirmSupplierSelection | Explicit eligible item tuple; current SUPPLIER_QUOTES COMPLETE; `operation=first` with empty head, or `operation=change` with exact predecessor and reason. After tombstone, change uses its revision/reason. All snapshots server-resolved. A stale predecessor uses Reconfirm instead. | Shared exact CAS + empty/existing head guard; UUID canonical invocation digest; immutable revision/receipt; CONFIRMED on first or CHANGED on successor, atomic minimized audit. |
| ReconfirmSupplierSelection | Exact stale predecessor and reason plus freshly reviewed eligible tuple. Same item allowed only if now eligible; different item/revision explicitly identified. Require current SUPPLIER_QUOTES COMPLETE; it cannot resurrect unavailable/unconfirmed authority. | Same shared CAS, expected stale head and invalidation generation; new UUID/revision; RECONFIRMED audit preserving old/new tuple references, not old confirmation reuse. |
| WithdrawSupplierSelection | Exact existing positive head, including stale, and reason. No candidate required. May clear despite non-COMPLETE upstream/source loss/Supplier inactivity, because withdrawal grants no positive authority. Must still prove tenant/Project/exact retained seal/line correspondence and intact selection history/receipt/audit; unresolved membership or history corruption denies it. | Current observable shared CAS, exact head target and invalidation context; no requirement for failed quote to regain eligibility; append tombstone/revision/receipt + WITHDRAWN audit. Final check verifies actor/DRAFT/session/CAS/target integrity, not positive quote currentness or expiry. |

Proposed events preserve `NCC_SELECTION_CONFIRMED`, `NCC_SELECTION_CHANGED`, `NCC_SELECTION_RECONFIRMED`, add `NCC_SELECTION_WITHDRAWN`, and wrap `NCC_SELECTION_MARKED_STALE` for minimized diagnostics. Final physical event/contract names require the later runtime contract; no existing audit is rewritten.

Use one stable globally unique command UUID, retained before transport and scoped to actor/tenant/Project/line/session/contract. Canonical request digest covers the strict semantic invocation and expected proofs; tracing correlation alone does not alter semantics. Same UUID + same invocation returns **the original historical result**, after current access and receipt/journal integrity checks, with current Case State token separately. Replay never advances head/Project, generates another success audit or claims current COMPLETE. Changed payload or foreign actor/scope conflicts safely; no foreign receipt disclosure. A replay does not require old CAS or candidate to remain eligible. For replay via mutation route, reuse A13's active owned-session/access checks; fresh DRAFT/currentness gates apply only to new writes. Receipt GET uses current `project:read` and original actor scope and remains useful without an active Workbench session or outside DRAFT.

Unknown transport/500 outcome blocks new selection commands. Reconcile the original UUID receipt, then refresh coherent preparation/history/Case State; never generate a new UUID just to retry uncertainty. Missing receipt is not proof of failure and must not unlock a blind retry. 409 refreshes authority and requires deliberate review/new attempt, never last-write-wins. 401/403/404 clears protected data/denies mutations; automatic client auth replay must not resubmit an official command.

### Project-first atomicity and PostgreSQL proof

Lock Project first using the existing same-tenant guard, then active actor/org/grants/session and shared sealed-line authority in A13-compatible order. Reuse the shared authority resolver's deterministic line/Supplier/currency/source lock order before locking the exact selection head/receipt; order multiple child IDs consistently. Never acquire a child then request Project. Head-empty creation is serialized by Project plus scoped uniqueness; one revision predecessor has at most one successor.

In one caller-owned outer transaction: resolve/revalidate authority; append revision (or tombstone), advance index head, increment Project version once, append immutable receipt and required audit; flush and final recheck under locks; commit together. Audit failure, CAS/currentness failure or uniqueness conflict rolls everything back, including receipt and Project/head. No success audit survives a failed selection. Do not separately commit a child or audit. Shared v7 token is computed through the existing single registry/snapshot algorithm with selection facts, heads, invalidation/dependency state and unchanged A13/upstream contributors.

Audit allowlist: command/contract/receipt/fact/Project/line/session IDs, actor/tenant, predecessor/head versions, pre/post Project versions, request/content/proof/record digests and bounded reason/warning **codes**. Exclude prices/quantity, Supplier names/tax/contact, source bytes/text/path/object key/URLs, freeform reasons, credentials and full payloads. Protected domain history can retain the necessary D4 snapshots with scoped reads. Integrity verifies exact receipt response/request/content/audit references and head/revision closure, not audit existence alone.

The future runtime must review every participating legacy/direct writer. A15 does not claim generic non-restricted line PATCH, Supplier master changes, document-head writers or out-of-band storage operations already use Project-first selection CAS. Coordinate/lock compatible writer paths only within the later authorized runtime contract, and retain dependency/final-commit validation for external storage faults that PostgreSQL cannot lock. Do not retrofit them here or claim database locking prevents physical byte loss after commit.

| Required real PostgreSQL interleaving | Required observable outcome |
| --- | --- |
| Selection vs quote correction | Correction first → old tuple fails; selection first → historical commit then stale on next read. No rebind. |
| Selection vs replacement/successor confirmation | Exact current confirmed item set wins; old prepared selection conflicts, no omitted-line fallback. Negotiation-only successor preserves existing selection but changes invocation CAS. |
| Selection vs quote withdrawal/rejection | Withdrawal first → candidate fails; selection first → traceable then stale. Rejected optional draft does not invalidate retained confirmed head. |
| Selection vs expiry/review cutoff | Post-wait and final-boundary clock tests: expired commit rolls back all effects; valid commit just before cutoff becomes stale on later read. |
| Selection vs source replacement/loss/integrity failure | Source-head/byte generation and bounded verification catch old or invalid proof; no source substitution, orphan receipt or surviving success audit on failure. Fault after commit suppresses currentness. |
| Selection vs Supplier merge/deactivation/ambiguity | Post-lock identity revalidation; either old selection commits before change then invalidates, or new selection fails. Never follow merged Supplier automatically. |
| Selection vs exact line mutation/upstream stale/seal change | Exact content and shared CAS reject stale preparation; upstream restoration does not silently re-attest selection. No mutation/order of members by selection. |
| Two competing first/change selections on one line | One accepted successor per expected head; other 409, zero official partial effects. No fork/last-write-wins. |
| Reconfirm vs competing change | Same head/invalidations and shared CAS serialize; one successor, losing attempt must refresh and be reviewed. |
| Withdraw vs change/reconfirm | One successor from target; tombstone never restores earlier head. Both winner orderings tested. |
| Replay/unknown outcome vs successor/withdrawal | Original receipt stays historical with one success audit; replay never overwrites later head, even when old candidate is no longer eligible. Changed payload conflicts. |
| Audit failure, revoked actor/grant/session or Project status during wait | Required access/final checks fail and atomically roll back; no detached receipt/head. |

Prove both supported lock orderings with separate real PostgreSQL connections, observed blocking/wait synchronization, exact winner/loser revisions and zero partial effects. SQLite is not serialization evidence. Repeatable-read Case State must show coherent before/after facts and the same CAS consumed by commands. These are later implementation acceptance requirements, not tests executed in A15.

## 11. D10 — Legacy disposition and field compatibility

Recommend **additive successor persistence**, keeping legacy tables/history intact and introducing official A13-bound selection revisions/head/receipts plus necessary invalidation provenance under a later authorized migration. Do not overload old non-null legacy FKs with unrelated A13 UUIDs, truncate prices, drop history or mass-backfill current selections. Official new stage reads count legacy heads as zero until an explicit human commit creates a proved A13 selection; a compatibility history view labels their namespace/source and historical status. No guessed equivalence between QuoteBatch, DocumentRecord, QuoteLine and SupplierQuoteItem.

| Concept | Classification | Recommended treatment |
| --- | --- | --- |
| NccSelectionRevision | **MIGRATE** | Preserve existing immutable rows as legacy history. Successor journal required for A13 identities, precision, withdrawal, receipts/CAS/session and provenance. No automatic semantic row conversion. |
| NccSelectionCurrentHead | **MIGRATE** | Preserve one-head concept; official successor index refers only to successor facts/tombstones. Legacy pointer remains historical and contributes zero. |
| ncc_selection_service.py | **REPLACE** | New A13-bound command/read service; reuse safe revision/CAS/audit ideas, remove legacy candidate/warning/replay/access logic from official path. |
| Existing GET NCC Selection API | **REUSE WITH COMPATIBILITY WRAP** | Canonical project/line route shape may remain, with explicit versioned official preparation/current/history and isolated labeled legacy history. Must never merge legacy candidates into official eligible set. |
| Existing POST NCC Selection API | **REPLACE** | Explicit current contract/item tuple, workbench/session/shared CAS/UUID receipt; legacy body cannot be silently translated. Later contract must gate/retire legacy writes for the official slice without expanding unrelated knowledge hardening. |
| NccSelectionPage / table / drawer | **REUSE WITH COMPATIBILITY WRAP** | Retain approved presentation/line drawer/history pattern and route mapping after binding to official server result/preparation. Legacy access cannot count as stage authority. |
| frontend/src/api/nccSelection.ts / controller | **REPLACE** | Versioned typed adapter, decimal strings, current invocation proofs, original UUID receipt recovery and read/command security semantics. No number conversion for monetary authority. |
| ADR 0039 | **REUSE WITH COMPATIBILITY WRAP** | Retain per-line immutable history/head, explicit human commit, CAS, warning snapshots and no rebind. D1/D2 legacy candidates, D4 precision/calculation, D6 stale dependencies and D7 permission/idempotency need a scoped successor ADR/runtime contract after PO acceptance. Do not edit accepted historical ADR in A15. |
| PR-03 / PR-04 contracts and audit results | **HISTORICAL ONLY** | Preserve as dated implementation evidence; useful acceptance patterns, not current A13 compatibility or stage certification. |
| PR-03 / PR-04 executable tests | **MIGRATE** | Preserve historical regression coverage where legacy code remains; add official A13 fixtures/CAS/session/Decimal/receipt/currentness proofs later. Old passing tests never certify new stage. |
| QuoteBatch | **HISTORICAL ONLY** | Catalogue-oriented candidate/batch authority is not selection authority; no auto-promotion or invented DocumentRecord mapping. |
| QuoteLine | **HISTORICAL ONLY** | Not an official selectable item; price/source/asset matching cannot prove A13 exact-line confirmation. |
| EvidenceFile | **HISTORICAL ONLY** | Preserve legacy source reference in history; uploader tenant/ACTIVE file is insufficient A13 provenance. |
| SupplierQuoteFact | **REUSE AS-IS** | Official A13 revision/confirmation/lifecycle journal via canonical fold; selection reads/references and never modifies it. |
| SupplierQuoteItem | **REUSE AS-IS** | Exact effective item ID and owning fact, line/Decimal values; selected only through its current confirmed revision. |
| Retained DocumentRecord / DocumentRevision authority | **REUSE AS-IS** | Existing scoped immutable revision/head/storage admission, verified-byte generation and safe locator. Selection creates no source or revision. |
| Supplier / SupplierAlias | **REUSE WITH COMPATIBILITY WRAP** / **OUT OF STAGE** | Supplier identity via A13's current binding; alias is suggestion-only and contributes no confirmed selection identity. No master-data mutation. |
| AppraisedPriceDecision / final-result forms | **OUT OF STAGE** | No command, read-model activation, price write or generation here. |

### Required old-field → A13 compatibility matrix

| Old PR-03/04 field/concept | Safe reusable concept | Unsafe dependency | Required successor field / runtime implication | Historical evidence retained |
| --- | --- | --- | --- | --- |
| organization_id / project_id / project_asset_line_id | Exact tenant/Project/line scope | Nullable ownership inferred through legacy creator/uploader or canonical match | Non-null proved scope plus seal/set/membership and line bindings; enforce scoped FKs/command checks in later migration | Original legacy scope, never inferred anew. |
| selection_revision / current_revision_id | Immutable revision chain + one head + expected revision | Pointer alone treated as current/COMPLETE | Successor fact/head namespaces, predecessor/kind/tombstone, head CAS and integrity proof; no pointer retarget to legacy fact | Old chain/head and actor/time. |
| quote_batch_id / quote_batch_revision_number_snapshot | Logical quotation + exact revision | QuoteBatch is not DocumentRecord or A13 registration/revision fact | quote_id DocumentRecord, A13 revision fact/number, confirmed fact and quote journal version; no ID cast/backfill | Legacy batch ID/revision explicitly labeled. |
| quote_line_id | Exact selected offer item | Catalogue line reused across matching assets | A13 effective item ID + item.fact_id + exact sealed line + confirming item-set digest; fresh human commit | Original QuoteLine reference. |
| supplier_id / supplier_name_snapshot | Exact Supplier + safe historical label | Alias/text/merge-target inference or legacy ACTIVE-only test | Current A13 pinned identity/version/ambiguity/merge binding; snapshot safe name | Original Supplier snapshot unchanged. |
| evidence_file_id / evidence metadata | Traceable source locator | EvidenceFile/uploader is not retained revision proof | DocumentRecord/DocumentRevision/StorageObjectBinding/CurrentHead generation/checksum/availability proof; no generic evidence fallback | Original file ID/metadata and legacy limitations. |
| quoted_unit_price_snapshot / quantity_snapshot / currency / unit | Immutable quoted values and unit basis | Float/number conversion, two/four-decimal truncation, values detached from item | Numeric at least (26,8), Decimal strings, exact A13 item values and currency/unit registry binding; no recovery of lost original precision | Stored legacy rounded values marked historical. |
| quote_date_snapshot | Issued-date context | Missing validity/review/number means quote looks timeless | A13 terms incl. number/not-issued, effective/expiry/review cutoff and comparison_basis | Original date unchanged. |
| current_unit_price_snapshot / difference_amount / difference_percent | Comparative snapshot, never final price | Different warning engine or invented comparable basis | Canonical current A13/shared comparison, nullable Decimal differences, reference digest and calculation version | Original reference/difference snapshots; no recompute as new history. |
| warning_codes / acknowledged_warning_codes | Non-blocking reasons; ack does not erase warning | Legacy uppercase codes/rounded threshold treated as current | Canonical `below_working_price` / `difference_exceeds_15_percent`; explicit presentation-only old-code mapping; no authority rewrite | Original codes and acknowledgements. |
| confirmed_by_user_id / confirmed_at / confirmed | Explicit authenticated professional commit | `project:update` alone without session/DRAFT/current CAS | workbench:edit, owned session, server-derived human/org, confirm:true and UTC commit/proofs | Original confirmer/time. |
| idempotency_key / request_digest_sha256 | Stable attempt identity and canonical digest | String key and re-resolved mutable candidates without historical receipt | Global command UUID, scoped immutable receipt/result, invocation digest, shared CAS and original-UUID recovery; legacy attempts never reissued as new commands | Original key/digest/history. |
| state=selected/stale / KPIs | Server-derived per-line diagnostics and display totals | Local counter/head/legacy selection used as stage truth | Five stage results, canonical eligible set/currentness, compute-on-read per exact sealed membership | Legacy labels clearly historical, zero official completion credit. |

Successor migration requires its own authorized schema/runtime contract, tenant-safe constraints, append-only enforcement, precision proof, upgrade/downgrade/re-upgrade and historical parity. It must prevent competing legacy POST/head writers from supplying official truth and retain authorized legacy reads without widening disclosure. No schema SQL, migration, field backfill, endpoint replacement or UI switch is performed in A15.

The strongest alternative is an additive extension of the existing tables: it reduces parallel history surfaces, but required old FKs/scales and audit/idempotency semantics would need an explicit discriminated schema with constraints preventing mixed identities and loss. A compatibility wrapper alone cannot satisfy that. Recommend successor tables because legacy data stays intact and official identity/precision cannot be confused; assess actual names/ADR in the later contract. Cost is dual labeled history, not dual official authority.

## 12. D11 — Case State, Next Action and product proposal

Explicitly recommend the proposed names **`supplier_selection_v1`**, **`global-case-state-v7-supplier-selection-v1`**, **`supplier_selection_prepare_required`**, stage **`SUPPLIER_SELECTION`**, context **`supplier_selection_preparation`**, Vietnamese **“Chọn NCC đã xác nhận giá”**. They are reserved recommendations, not current registry entries. Actual registry remains v6; actual boundary remains SUPPLIER_QUOTES. Do not add a parallel token/provider or new public enum.

After separate acceptance/implementation/certification, extend the existing coherent projection/registry/CAS through selection. Current SUPPLIER_QUOTES COMPLETE is prerequisite; when upstream loses completeness, preserve the earliest upstream result/action. Global accepted blocker precedence remains unchanged. Mutations and preparation consume the same v7 case token that public Case State returns, with selection dependencies included.

| Proposed selection result | Meaning and existing Next Action kind |
| --- | --- |
| NOT_AVAILABLE | Capability not authorized/available or upstream quotation prerequisite not COMPLETE. UNAVAILABLE locally; global action remains owning upstream action. |
| BLOCKED | Applicable known negative/integrity hold, proven scope contradiction, or unfinished mutation-required work outside DRAFT. BLOCKER only when an existing authorized recovery exists; otherwise UNAVAILABLE. No invented repair action. |
| STALE | Previously positive selection no longer current or required journal proof unprovable; diagnostics/history retained. UNAVAILABLE with safe inspection/reload context; a coherent authorized preparation may expose explicit reconfirm/change/withdraw after resolving prerequisites. Corrupt history exposes no repair/commit. |
| INCOMPLETE | Valid sealed membership with at least one unselected or withdrawn line, no higher blocker/stale. PENDING `supplier_selection_prepare_required` when DRAFT and actor/session permit; otherwise UNAVAILABLE. |
| COMPLETE | D1 predicate true for every member. NO_AUTHORIZED_DOWNSTREAM_ACTION until separate appraisal acceptance/implementation/certification, absent higher-priority authorized blocker. |

Within the available stage, inspect applicable blockers, then stale positive heads, then ordinary missing/tombstone heads, then COMPLETE; required integrity failures suppress COMPLETE regardless of pointer/count. Viewer access or lack of Workbench session does not change a business result. Missing candidate because upstream coverage is incomplete returns upstream responsibility, never a selection waiver.

Pending context contains kind, Project UUID, case token/Project version, seal/set digest/membership version, bounded reason code (`selection_required`), first deficient exact line ID/version in inherited STT order, optional scoped selection head/revision and command-contract reference. Preparation supplies the full invocation and server-owned eligible item tuple; Next Action contains no money, bulk Supplier names, source path/URL/key, freeform reason or full asset manifest. STALE inspection context uses bounded `supplier_selection_diagnostic`, reason codes, Project/case reference and reload-required; it cannot submit a command. Route keys map to URLs in the frontend contract, never business authority in React.

Recommend keeping the approved dedicated **selection** table/drawer shape and canonical existing project route `/workbench/projects/{projectRef}/ncc-selection`, entered from the server's Workbench/Case Overview Next Action with Project/line/return context. The Workbench remains the main workspace. Route/page availability alone grants no candidate or downstream authority. This is the selection checkpoint itself, not a post-SUPPLIER_QUOTES NCCQ aggregate. A14 quotation management remains distinct and its four Asset Context tabs remain `Tổng quan | Thông số kỹ thuật | Nguồn giá & Chứng cứ | Lịch sử`.

The future server read model returns exact ordered sealed lines, current/historical selection, selectable A13 candidates and safe source/actor/version metadata, canonical warnings/differences, currentness reasons, stage result/KPIs and allowed per-line actions. UI displays them; it never derives eligibility/stale/COMPLETE, selects cheapest, interprets Supplier identity as selection, or unlocks downstream from counts. History and current snapshots remain visually distinct. Show the chosen item's Supplier, quoted price/date/validity/source and current warning context before the single primary commit; no candidate is preselected automatically. Change/reconfirm uses the same explicit professional action with the relevant reason/context; withdrawal is a deliberate secondary action.

Fluent 2 light, Vietnamese-first, desktop-first, table-first. Preserve approved table hierarchy/density and per-line drawer tabs for eligible quotes/current/history, readable safe labels rather than typed UUIDs, exact decimal text, immutable STT, source/decision/history entry points and return focus. Follow shared architecture/components, no feature-local visual system. Continuous Visual Integrity applies: explicit loading/empty/no-results/error/stale/conflict/denied/offline/uncertain states, keyboard row/candidate actions, accessible labels/focus, no broken layout. Source failure is not empty; background unverified data locks writes; auth failure clears protected data; conflict refreshes without retry; uncertain outcomes require original receipt recovery. G6 owns full visual convergence, not deferral of serious usability/IA/architecture defects.

No external visual/design skill or Taste dependency is used in this proposal. The certified advisory policy remains binding for later use, including exact revision pinning and Valora/server/Fluent precedence. A15 makes no screenshot/mockup/visual acceptance claim.

## 13. D12 — Hard APPRAISAL_RESULT boundary

Selection establishes only one current selected quote-item authority per exact line. It must not write `appraised_unit_price`, create/change `AppraisedPriceDecision`, choose/finalize appraisal price, mutate PRICE_EVIDENCE/SUPPLIER_QUOTES, generate final-result tables/documents or activate APPRAISAL_RESULT. Reading comparative working price for warnings grants no write authority. No quote price is copied into working/final price.

Canonical order remains `ASSET_REVIEW → ASSET_WORKBENCH → PRICE_EVIDENCE → SUPPLIER_QUOTES → SUPPLIER_SELECTION → APPRAISAL_RESULT`. Future selection COMPLETE caps at selection with **NO_AUTHORIZED_DOWNSTREAM_ACTION** until APPRAISAL_RESULT is separately accepted, implemented and certified; null downstream route/stage/context, no stage skip or disguised generation button. Final-result company forms and the retained result-price comparison rule are later-stage authority to reconcile; A15 does not implement that rule, assign its quote set/severity or turn it into a selection blocker. Price-evidence priority remains Internet survey → unit-price explanation → prior appraisal result; Supplier quote is not primary final-price authority.

## 14. Future acceptance requirements and A15 delivery limit

This matrix is a Definition-of-Ready input for a later assigned runtime/product task, not A15 execution evidence.

| Future acceptance area | Required proof |
| --- | --- |
| Business/membership | Non-empty exact set; one line with many valid candidates; all lines complete only with one valid explicit selection each; same Supplier/distinct items on several lines; missing/tombstone/stale line prevents COMPLETE; no waiver/reorder/canonical fan-out or automatic choice. |
| A13 compatibility | Correct item.fact_id/revision/confirmation tuple; line-registration replaces draft item; negotiation vs correction/replacement; omitted-line successor, withdrawal/rejection and optional offers; legacy heads/ACTIVE lines contribute zero. |
| Precision/warnings | A13 maximum/8-decimal values survive API/database/UI; NULL/zero/incomparable reference, below-price, exact ±15% and strict beyond; no float/number authority, frontend threshold engine or warning blocker; acknowledgements preserve codes. |
| Lifecycle/currentness | First/change/reconfirm/withdraw/re-establish with immutable history and no fork/rebind; all D8 conditions; retained transient invalidation and explicit reconfirm; no token-only staleness, successor action cannot waive broken predecessor. |
| Security/transactions | Active same-tenant human/session/RBAC/DRAFT, foreign/unknown IDs safe denial, actor/grant/session revocation, immutable facts/receipts/audits, no audit payload leakage, complete rollback and all D9 real PostgreSQL interleavings. |
| Receipt recovery | Same UUID historical replay vs successor, changed payload, cross-actor/tenant, revoked access, uncertain response after actual commit, no receipt yet, 409 refresh/no blind retry, no duplicate success audit/head write. |
| Case State/downstream | Shared public/command v7 token; five public results/four action kinds/precedence; safe exact action context; upstream regression and non-DRAFT complete read; no APPRAISAL_RESULT action, price write, result table or generation. |
| Product/browser/visual | Real authenticated server/PostgreSQL commands and retained source authority; exact lines/candidates, keyboard/drawer focus, full state matrix and unknown-outcome receipt recovery; reference-based Fluent evidence/Continuous Visual Integrity on frozen product HEAD. Mockup cannot resurrect legacy candidate semantics. |
| Migration/history | Additive successor upgrade/downgrade/re-upgrade and append-only/FK guards, lossless decimals, legacy history parity/labels, no mass promotion or dual competing official writer. |

A15 local checks cover only this proposal: scope/authority reconciliation, exact relative paths and anchors, D1–D12 table/compatibility/command/concurrency completeness, no unintended files or sensitive material, and `git diff --check`. Runtime, migration and browser tests are N/A for this document; current CI remains mandatory and does not prove unimplemented selection behavior.

Apply PM-OPS-002 Local Saturation before first push: complete proposal/T0/T1/T2 document checks, justify runtime T3 N/A, inspect final diff, commit only this reviewed path and freeze a clean HEAD after live-baseline recheck. HIGH risk requires independent read-only `opencode-go/deepseek-v4.1-flash` through OpenCode Go and `gemini-3.1-pro-high` through Antigravity on that same frozen HEAD, with changed-file/hash manifest/scoped authority. Adjudicate every finding VALID / INVALID / DUPLICATE / OUT_OF_SCOPE / ADVISORY; unresolved P0/P1/P2 blocks readiness. Changed HEAD requires renewed reviews/CI. Require exact-head repository CI SUCCESS, Draft PR with `Refs #145`; no Ready/merge/issue closure/certification/PO acceptance or runtime handoff by this task. Evidence belongs in the immutable reviewer packet and Draft PR closeout, not a self-referential frozen source commit.

No schema/migration/backend/API/Case State/frontend/RBAC implementation, legacy promotion, automatic selection, APPRAISAL_RESULT/final-price/result generation, OS-G3, Windows, AI/provider runtime, workflow YAML or deployment/distribution. Later selection Definition of Ready remains unsatisfied until explicit PO acceptance plus an assigned scoped runtime contract. Gate Owner integrates this proposal; Product Owner accepts decisions separately.

## 15. Product Owner decision table

Every recommendation is **PENDING**. Integration/merge certifies only proposal preparation/reconciliation; it does not accept a row or open runtime.

| Decision | Strong recommendation | Alternatives | Trade-off | PO status |
| --- | --- | --- | --- | --- |
| D1 — Meaning / COMPLETE | One current valid explicitly human-confirmed A13 item per exact sealed line, compute-on-read; no whole-stage confirmation. | Separate whole-stage professional attestation if PO defines its distinct obligation. | Per-line facts suffice; a second whole-set confirmation adds a new stale fact and click without current business need. | PENDING |
| D2 — Membership | Inherit all exact current A13 sealed lines/order; no waiver, mutation or reorder; same Supplier permitted with distinct exact-line items. | Separately authorized membership/exclusion policy outside selection. | Strict truthful coverage may leave specialist assets unfinished; avoids hidden exemptions and item fan-out. | PENDING |
| D3 — Candidate | Only current A13 effective item + contributing confirmed revision/confirmation tuple and current Supplier/source/line/upstream closure. | Re-register legacy offers through A13 human quotation authority; never direct compatibility by ID. | Re-entry costs work but proves exact lineage; catalogue identity/ACTIVE flags cannot replace it. | PENDING |
| D4 — Durable facts | Successor immutable scope/item/revision/source/Supplier/terms/Decimal/warning/actor/predecessor/receipt/CAS snapshots, one guarded head. | Explicit discriminated additive extension with equivalent constraints/precision. | More facts/storage preserve precision and traceability; old required FKs/scales cannot be reused losslessly. | PENDING |
| D5 — Lifecycle | First/change/stale reconfirm append successors; clear is tombstone; retain invalidation/history, no deletion/fallback/rebind. | Omit clear initially; retain change/reconfirm only. | Withdrawal honestly records no current choice and needs extra contract/proof; omission forces a replacement even when none is justified. | PENDING |
| D6 — Human authority | Existing workbench:edit + active owned session + active same-tenant human + DRAFT + exact CAS; one explicit CTA, no new RBAC. | New segregation permission only through explicit separately justified PO decision. | Reuses certified professional gate; legacy project:update is insufficient, additional roles would add governance burden. | PENDING |
| D7 — Warnings | One canonical A13/shared server comparison at commit; below C and strict absolute >15% warn, never block; NULL/zero/incomparable stays truthful. | Snapshot already-resolved A13 warnings only if current reference/proof is identical. | Commit-time shared result avoids obsolete warning snapshots; requires preserving A13 exact comparison and legacy working-price provenance. | PENDING |
| D8 — Currentness | Respect current A13 confirmed closure, retained invalidations and selection proofs; no silent rebind/recovery; new explicit revision to restore selection. | Broader conservative invalidation on every quote draft, or permit automatic validity recovery. | Material currentness preserves valid negotiations; blanket draft invalidation adds unnecessary work, automatic recovery loses explicit professional reassessment. | PENDING |
| D9 — Safety/concurrency | Project-first compatible locks, shared v7 CAS, exact head/version, UUID receipt reconciliation, minimized atomic audit/rollback, real PostgreSQL matrix. | Retain legacy local-head/string-key protocol. | Shared safety may conflict more broadly; legacy protocol lacks current upstream/session/receipt guarantees and is not recommended. | PENDING |
| D10 — Legacy/migration | Additive A13-bound successor schema/service/adapter; explicit versioned read/UI compatibility, historical-only legacy quotes/files, no auto-backfill. | Discriminated extension of existing schema with equal constraints and lossless precision. | Successor isolates domain identities and preserves history; costs dual labeled history, while extension risks mixed references/rounding. | PENDING |
| D11 — Case State/product | supplier_selection_v1 / global-case-state-v7-supplier-selection-v1; supplier_selection_prepare_required / supplier_selection_preparation; existing results/actions and approved Workbench selection table/drawer/route. | Different explicit versioned names or a Workbench-embedded selection region under a later approved UX decision. | Named successor prevents parallel truth; route-shape reuse still requires official contracts, server authority and Continuous Visual Integrity. | PENDING |
| D12 — Downstream | No price/upstream/result/document mutation; future COMPLETE holds NO_AUTHORIZED_DOWNSTREAM_ACTION until appraisal separately accepted/implemented/certified. | None within A15; APPRAISAL_RESULT needs its own assigned authority/runtime/product gates. | Bounded selection becomes useful input without falsely certifying final professional value or the full OS-G2 journey. | PENDING |
