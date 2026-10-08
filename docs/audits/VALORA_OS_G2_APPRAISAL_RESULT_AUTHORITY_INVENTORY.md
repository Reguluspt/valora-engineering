# VALORA OS-G2 APPRAISAL_RESULT Authority Inventory

**Task:** `VALORA-TASK-OS-G2-A16-APPRAISAL-RESULT-READONLY-AUTHORITY-INVENTORY` (Issue [#146](https://github.com/Reguluspt/valora-engineering/issues/146))
**Inventory date:** 2026-10-08
**Repository baseline:** `579d68a2122eac017615320a7f79c18184678183` (`main`; exact-main CI #630 / run `37717959755`, SUCCESS)
**Scope:** factual, read-only discovery. This document does not authorize APPRAISAL_RESULT, answer D1–D12, or grant implementation authority.

`docs/discovery/` does not exist in this repository. Existing read-only audit records are kept in `docs/audits/`, so this inventory uses that closest established location. No product, runtime, schema, API, frontend, workflow, or authority file was changed.

## 1. Authority snapshot

- Current certified OS-G2 product/runtime boundary: `SUPPLIER_QUOTES`; OS-G2 remains PARTIAL / INCOMPLETE. The current roadmap records this boundary in [`VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md`](../VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md).
- A15 / Issue [#145](https://github.com/Reguluspt/valora-engineering/issues/145) is open as the `SUPPLIER_SELECTION` authority proposal task. The issue says its future D1–D12 require Product Owner acceptance. No accepted A15 decision was assumed in this inventory.
- `SUPPLIER_SELECTION` runtime and `APPRAISAL_RESULT` remain UNAUTHORIZED. APPRAISAL_RESULT cannot proceed until its A15 dependency is resolved and its own authority is separately accepted.
- Current product route in design authority: `SUPPLIER_SELECTION → APPRAISAL_RESULT → Document`. This is a future design sequence, not current runtime activation.

### 1.1 Design authority and supersession

| Authority | Current use | Supersession / boundary |
|---|---|---|
| [`design/assets/VALORA_FINAL_RESULT_BASELINE_v2.3.md`](../design/assets/VALORA_FINAL_RESULT_BASELINE_v2.3.md) | Approved immutable layout and flow for the three company forms. | Supersedes earlier final-result mockups where they split technical facts into columns, add supplier totals/analytics, change the result schema, or restyle the company forms. |
| [`design/VALORA_UIUX_HANDOFF_v2.3_FINAL_RESULT_BASELINE_ADDENDUM.md`](../design/VALORA_UIUX_HANDOFF_v2.3_FINAL_RESULT_BASELINE_ADDENDUM.md) | Routes from completed individual quotes, through confirmed-supplier selection, directly to the final-result step and three forms. | Explicitly supersedes a post-selection NCCQ aggregate screen and a separate S17 whole-case readiness screen inserted before the result. |
| [`design/VALORA_UIUX_HANDOFF_v2.3_PRICE_EVIDENCE_AUTHORITY_ADDENDUM.md`](../design/VALORA_UIUX_HANDOFF_v2.3_PRICE_EVIDENCE_AUTHORITY_ADDENDUM.md) | Price-source priority, human price decision, quote comparison rule, and supplier-quote role. | Supersedes earlier equal-priority treatment of price evidence or supplier quotes as the primary final-price source. |
| [`design/VALORA_UIUX_HANDOFF_v2.3_NCC_PRICE_WARNING_RULE_ADDENDUM.md`](../design/VALORA_UIUX_HANDOFF_v2.3_NCC_PRICE_WARNING_RULE_ADDENDUM.md) | Supporting current NCC price comparison semantics. | Does not authorize final-price selection or APPRAISAL_RESULT completion semantics. |
| [`design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md`](../design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md) and [`design/VALORA_DESIGN_AUTHORITY_INDEX.md`](../design/VALORA_DESIGN_AUTHORITY_INDEX.md) | Authority entrypoints and visual/product precedence. | Fluent 2 governs the application surface; the approved company-form layout remains immutable. |
| [`design/VALORA_USER_FLOW_MINDMAP_v2.3.md`](../design/VALORA_USER_FLOW_MINDMAP_v2.3.md) | Supporting workflow map. | Older sections are subordinate to the later final-result and price/evidence addenda where they conflict. |

The final-result baseline establishes presentation layout and route. It does **not** define a backend result identity, sealed-line COMPLETE predicate, result revision policy, lifecycle, or a document-generation authorization.

### 1.2 Locked company-form schemas

The three schemas below are transcribed from the approved final-result baseline and addendum. They must not be redesigned as part of any later authority or runtime task.

1. **Bảng Đặc điểm kinh tế - kỹ thuật**

   `STT | Tên tài sản | Đặc điểm kinh tế - kỹ thuật | ĐVT | SL`

   All technical characteristics for one asset remain in one `Đặc điểm kinh tế - kỹ thuật` cell. Preserve section/category rows from the source form.

2. **Bảng Tổng hợp giá các nhà cung cấp**

   `STT | Tên tài sản | ĐVT | SL | Đơn giá tham khảo: NCC 1 | NCC 2 | NCC 3 | Tổ TĐG đánh giá: Đơn giá | Thành tiền`

   Each supplier has one unit-price column only. The form has no supplier amount columns or lowest/highest/difference analytics. It retains the company `Tổng cộng` pattern.

3. **Bảng Kết quả thẩm định giá**

   `STT | Tên tài sản | ĐVT | SL | Đơn giá | Thành tiền`

   Preserve `Tổng cộng`, `Làm tròn`, the total in digits, and the amount in words where the company form requires it.

`STT` retains the source asset-catalog order/lineage across all three forms; supplier choice, table reconstruction, and report output must not renumber it. Supplier-price lineage in the comparison form is `NCC → báo giá → dòng thiết bị → đơn giá NCC đã xác nhận → file ký/đóng dấu`.

Fluent 2 light applies to the shell and surrounding controls, context, warnings, evidence, lineage, and history. It does not change the three forms' headings, columns, grouping, totals, border/header structure, or layout.

## 2. Accepted price and evidence facts

The price/evidence addendum fixes this priority for appraisal-price evidence:

1. Internet survey;
2. unit-price explanation;
3. prior appraisal-result source.

`Tổng hợp căn cứ` is a surface, not another evidence type. Knowledge is a candidate/reference mechanism, not a fourth peer price source. A prior result remains historical evidence with source lineage and does not copy itself into the current price.

Supplier quotations are not the primary source for the final appraisal price. A selected NCC and its quote are comparison context and do not automatically set the final price. `appraised_unit_price` is existing working/legacy data, not certified APPRAISAL_RESULT authority. Final price remains a human decision; AI, knowledge, rules, and external sources do not overwrite it.

## 3. Pending SUPPLIER_SELECTION dependency

Issue #145 remains OPEN as an authority-proposal task. Treat each item here as **PENDING DEPENDENCY** until A15 authority is accepted and the relevant current facts are available:

- the exact selected quote item for each sealed asset line;
- Supplier identity and supplier lineage;
- quote identity/revision and quote-item identity;
- exact line identity and line-to-quote lineage;
- retained source document/revision lineage;
- eligibility and currentness, including stale detection;
- explicit change/reconfirmation behavior; no silent rebind to a quote, item, source, or successor;
- the selected quote set available for APPRAISAL_RESULT comparison.

Current A13 supplier-quote authority and runtime facts can provide quotation records; they do not themselves establish which exact item is selected for each line. The legacy NCC-selection routes and PR-03/PR-04 concepts are not evidence that A15 has accepted their semantics. No A15 D1–D12, exact comparison set, or completion rule is presumed here.

## 4. Backend inventory

Classifications describe present repository artifacts only and do not promote them to official result authority.

| Artifact | Classification | Present behavior and boundary |
|---|---|---|
| `ProjectAssetLine.id`, `project_id`, `asset_name`, `description`, `quantity`, `unit_id` in `backend/app/modules/project_master_data/models.py` | `CURRENT FIELD` | Current per-project line data. `project_id` scopes the line through its project; there is no appraisal-result identity or immutable result revision on the line. Unit is nullable. Quantity is stored as `Numeric(15,4)` and exposed through float-typed API schemas. |
| `ProjectAssetLine.appraised_unit_price` and `appraised_currency_id` | `UNSAFE FOR OFFICIAL RESULT WITHOUT NEW AUTHORITY` | Nullable working values on the asset line, stored as `Numeric(15,2)` and a nullable currency FK, while ORM/API types expose price as `float`. The Workbench authority map explicitly labels the value `optional-working-data`. The value may be initialized when creating a line and edited through the guarded asset-line draft flow. It has no result revision, decision-source binding, or final-result confirmation identity. |
| `ProjectAssetLine.source_import_batch_id` / `source_staging_row_id` and staging `source_row_number` | `CANDIDATE FOUNDATION` | Import lineage can connect an imported line to a source staging row and source row number. These fields are nullable; manually created lines have no such import lineage. `ProjectAssetLine` has no canonical `STT` field, so preservation of original order/number is only partial and must be reconciled with the source catalog. |
| `AppraisedPriceDecision` and `AppraisedPriceDecisionStatus` | `UNSAFE FOR OFFICIAL RESULT WITHOUT NEW AUTHORITY` | Legacy catalog decision keyed optionally by canonical asset, asset variant, or quote batch—not by organization/project/asset line/result revision. Statuses are `draft`, `candidate`, `active`, `superseded`, `rejected`. It is not a per-project final result. |
| Generic `/api/v1/knowledge/appraised-price-decisions` API and schemas | `UNSAFE FOR OFFICIAL RESULT WITHOUT NEW AUTHORITY` | `GET` list, `GET /{decision_id}`, and `PATCH /{decision_id}` exist; no create route exists. `AppraisedPriceDecisionUpdate` accepts optional `status`, `final_unit_price` (`float`), `currency`, and `rationale`, plus required `expected_row_version`. The response exposes the decision ID, optional canonical-asset/variant/quote-batch IDs, amount/currency/rationale/status, creator/approver/approval time, row version, and timestamps. Reads query by ID/list without an organization filter in the route. Patch checks `row_version` and blocks `active`/`superseded`, but the model has no tenant/project lineage. The update commits before it calls audit logging. These are material scope, tenant-isolation, lifecycle, and audit-atomicity questions for any reuse. |
| `AppraisedPriceDecision.final_unit_price` storage | `LEGACY/SUPPORTING` | ORM/migration use floating-point storage (`sa.Float` in `a87a9b6da99d_create_appraised_price_decisions.py`), with API schema `float`; it is not a Decimal-safe final-result store. `row_version` is optimistic concurrency metadata, not an append-only result revision chain. `created_by`/`approved_by`/`approved_at` record users/approval metadata but do not create a tenant/project-bound audit history. |
| Asset-line creation and update surfaces in `backend/app/api/projects.py`; `commands/commit_asset_line_draft.py` | `UNSAFE FOR OFFICIAL RESULT WITHOUT NEW AUTHORITY` | Creation accepts `appraised_unit_price` and currency fields. Direct line PATCH forbids `description` and `appraised_unit_price`; the existing Workbench draft/commit path can write the price with field validation and row-version checks. This is working-data mutation authority only, not APPRAISAL_RESULT authority. |
| Project asset-line precision and validation | `CURRENT FIELD` | Database precision is `Numeric(15,2)` for prices and `Numeric(15,4)` for quantity. The commit validator uses `Decimal`, rejects negatives and more than two decimal places, and does not silently round. Float annotations/schemas and existing consumers remain a precision boundary to resolve before official monetary snapshots. |
| Supplier quote comparison in `supplier_quote_authority.py` / `ncc_selection_service.py` | `LEGACY/SUPPORTING` | Comparison code reads `appraised_unit_price` as a current working/comparative price. This use does not turn that price into certified final result. Current A13 quote facts are distinct from legacy `QuoteBatch`/`QuoteLine` models and are the future A15 dependency source. |
| `DossierExtractionSnapshot`, extracted table role `word_final_result_table`, and `DossierRowAlignment.final_result_row_id` | `HISTORICAL` | Dossier extraction retains source-backed historical document/table/row facts and alignment candidates. A final-result table role or row ID in an old dossier is not a current APPRAISAL_RESULT decision. No code creating current `AppraisedPriceDecision` from dossier extraction was found. |
| APPRAISAL_RESULT-specific result model/API/output model | `UNSAFE FOR OFFICIAL RESULT WITHOUT NEW AUTHORITY` | No current result aggregate, result revision/head, final-result command/API, or canonical final-result backend completion model was found. Design mockups are not runtime models. |

### 4.1 Tenant, audit, status, and precision observations

- `ProjectAssetLine` is project-linked and the Project carries organization scope; line safety depends on using the project-scoped paths. The generic `AppraisedPriceDecision` record has no `organization_id`, `project_id`, or line ID and therefore cannot directly prove tenant/project/result scope.
- Project-line `row_version` and generic decision `row_version` are single-row concurrency controls. They do not alone supply cross-aggregate Case State CAS, idempotent command receipts, append-only result revisions, or unknown-outcome reconciliation.
- The generic decision PATCH logs an audit event after committing the mutation. Its audit is not part of an atomic result append.
- The legacy catalog model stores `final_unit_price` as float. The project-line price uses numeric database storage but float-typed ORM/API surfaces. Decimal-safe identity, comparison, rounding, and snapshot semantics remain open.
- No current result lifecycle, revision semantics, withdrawal behavior, or final-price audit event is accepted by this inventory.

## 5. Frontend inventory

| Surface | Evidence | Authority risk / boundary |
|---|---|---|
| Workbench `AssetGrid` | `frontend/src/components/workbench/AssetGrid.tsx`, `AssetGridTypes.ts`, `hooks/useProjectAssetLines.ts`, and `session/useWorkbenchDraftSync.ts` display/edit `appraised_unit_price` as `appraised_price`; the grid labels it `Giá TĐ` and has an “Áp dụng nháp” command. | A prominent appraisal-price label and an official-data commit can look like final result authority. The field remains working data under current authority. |
| Legacy NCC Selection page/table/drawer | `frontend/src/components/ncc-selection/NccSelectionPage.tsx`, `NccSelectionTable.tsx`, `NccSelectionDrawer.tsx`, and `frontend/src/api/nccSelection.ts` display the line's current `appraised_unit_price` beside selected quote price, difference, warnings, and selection state. | The “Đơn giá hiện hành” label plus selected supplier comparison may imply an accepted result baseline or selection authority. Issue #145 remains open; this older surface is not proof of accepted A15/current supplier-item binding. App routing also gates the page on the supplier-selection availability flag. |
| `AppraisedPriceDecision` frontend shape | `frontend/src/components/workbench/panels/ContextPanelTypes.ts` declares a typed `appraised_price_decision` panel field. Search found no frontend rendering/use of that field or a decision editor. | A type alone does not establish an active user surface or an authoritative project result. |
| Case Overview future-stage timeline | `frontend/src/components/case-overview/CaseOverviewPage.tsx` groups `APPRAISAL_RESULT` under “Kết quả thẩm định”; `caseOverviewPresentation.ts` supplies its stage label/result label. The overview renders projection stages and shows “Chưa có nguồn trạng thái được xác nhận” when a stage lacks an available capability. | This is a generic Case State progress surface, not a result editor or result model. Its future-stage entry still needs to remain clearly unavailable until the server exposes accepted authority; stage vocabulary does not grant completion or output authority. |
| Final-result mockups/assets | `docs/design/assets/VALORA_FINAL_RESULT_BASELINE_v2.3.md` and `docs/design/visual-reference/v2.3/` contain approved design/reference material. | These govern the visual/form contract, not server state, final-price confirmation, completeness, or revision history. No active final-result frontend route/component was found in `frontend/src`. |
| Report/document preview | Existing document workspace and dossier extraction code serve document workflows and historical extraction. Search found no preview consuming a current APPRAISAL_RESULT aggregate or producing these three forms from an accepted result. | An existing document preview/workspace must not be treated as an APPRAISAL_RESULT output pipeline. |
| Legacy AssetGrid supplier quote columns | `AssetGrid.tsx` includes working `supplier_quote_1..3` columns in its grid shape. | These are not the A15-selected quote-item lineage or authority for the fixed final company comparison form. |

No UI was changed.

## 6. Company-form field/data map

Availability is evaluated against current repository data and accepted authority at this baseline. `DEPENDS ON A15` denotes a future selected-supplier fact, not a statement that the A15 decision has been made.

| Form field / cell | Required fact | Status | Repository evidence / gap |
|---|---|---|---|
| All forms — `STT` | Original asset catalog order/number preserved unchanged | `PARTIAL` | Imported staging has `source_row_number` and imported lines retain staging lineage, but `ProjectAssetLine` has no universal STT/order field; manual lines are not covered by source-row lineage. |
| All forms — `Tên tài sản` | Exact current asset-line name | `AVAILABLE` | `ProjectAssetLine.asset_name`; source/import lineage can support provenance where present. |
| Form 1 — `Đặc điểm kinh tế - kỹ thuật` | Complete company-form text for one asset in one cell | `PARTIAL` | `description`, brand/manufacturer references, taxonomy/canonical/technical-specification foundations exist; no guarantee that all form-required technical attributes are present as one approved line snapshot. |
| Forms 1–3 — `ĐVT` | Unit label tied to the exact line/unit | `PARTIAL` | `unit_id` and unit reference exist but are nullable; historical/future unit display snapshot and normalization are not frozen for result output. |
| Forms 1–3 — `SL` | Quantity tied to the exact line | `AVAILABLE` | `ProjectAssetLine.quantity` exists; result snapshot/rounding semantics are not defined. |
| Form 2 — `NCC 1`, `NCC 2`, `NCC 3` unit prices | Exact selected eligible confirmed quote item(s), price/currency, Supplier, quote/line/source lineage, and currentness | `DEPENDS ON A15` | A13 supplies quote facts; A15 selection of exact current quote items per sealed line and its lineage/currentness semantics are still pending. |
| Form 2 — `Tổ TĐG đánh giá / Đơn giá` | Human appraisal-team comparison amount, with authority/source context | `LEGACY` | `appraised_unit_price` is optional working data. Price-source priority is accepted, but no APPRAISAL_RESULT result identity or confirmation command exists. |
| Form 2 — `Tổ TĐG đánh giá / Thành tiền` | Result unit price × exact quantity, under accepted unit/currency and rounding rules | `MISSING AUTHORITY` | No result snapshot, arithmetic/precision authority, or output rounding contract was found. |
| Form 3 — `Đơn giá` | Human-confirmed final appraisal unit price | `MISSING AUTHORITY` | No APPRAISAL_RESULT authority or current result model/API exists. The working line field cannot be silently promoted. |
| Form 3 — `Thành tiền` | Final unit price × result quantity in a durable result snapshot | `MISSING AUTHORITY` | No result snapshot or accepted arithmetic/precision/rounding rule exists. |
| Form 2/3 — `Tổng cộng` | Company-form total from authorized row values | `MISSING AUTHORITY` | Layout is accepted; total inclusion, calculation, precision, and revision binding are not backend-authorized. |
| Form 3 — `Làm tròn`, total in digits, total in words | Company-form rounding and number-text representation | `MISSING AUTHORITY` | Presentation requirement is fixed; rounding mode, currency wording, and authoritative source values are unresolved. |

## 7. Comparison-rule gap

Accepted design statement:

```text
Đơn giá Kết quả định giá <= Đơn giá trong báo giá NCC dùng để đối chiếu
→ Phù hợp
```

If result price is greater than a quote in the mandatory comparison set, UI validation is required at the appropriate dependency. The system does not auto-correct the price. The exact dependency location and behavior are not frozen.

Product Owner decision gaps:

- Which exact supplier quotation set is mandatory for each line? **PENDING DEPENDENCY on A15.**
- Is the validation Warning or Blocking?
- Does an above-quote result affect APPRAISAL_RESULT `COMPLETE`?
- How are multi-currency prices compared?
- How are unit differences normalized?
- How are tax, delivery, warranty, and commercial terms normalized?
- What happens when no comparable selected quote exists?

No comparison outcome or severity is decided here.

## 8. APPRAISAL_RESULT D1–D12 question skeleton

All rows have Product Owner status **NOT YET PROPOSED**. “Accepted facts” below are only current repository/design facts; they are not proposed decisions for D1–D12.

| Decision | Accepted facts | Unresolved decisions | Repository evidence | Risk if decided incorrectly | PO status |
|---|---|---|---|---|---|
| **D1 — business meaning / COMPLETE** | Final-result forms follow supplier selection in design; current certified runtime ends at SUPPLIER_QUOTES. | What business event/result does APPRAISAL_RESULT represent, and what exact predicate means `COMPLETE`? | Final-result baseline; unified roadmap; no result aggregate/model. | False completion could authorize document output with missing, stale, or unconfirmed lines. | NOT YET PROPOSED |
| **D2 — sealed-line coverage** | `STT` preserves source catalog order; each form is line-oriented. Asset review/Workbench has a sealed membership foundation. | Which exact sealed lines must have results; how do manual/imported lines map to original numbering; how do membership corrections affect prior results? | `ProjectAssetLine`, import staging lineage, asset review seal code and authority. | Omitted or duplicated assets, incorrect order, or a result bound to a changed line set. | NOT YET PROPOSED |
| **D3 — final-price input / authority** | Price-source priority is Internet survey → unit-price explanation → prior appraisal-result source. Supplier quotes are comparison context; final price is human-only. | What command/record stores the decision and its evidence/rationale; precision and accepted price snapshot? | Price/evidence addendum; `ProjectAssetLine.appraised_unit_price`; `AppraisedPriceDecision`. | Working or supplier price could be mistaken for the official final appraisal value. | NOT YET PROPOSED |
| **D4 — durable result identity / revisions** | Current line rows have IDs and row versions; no APPRAISAL_RESULT identity/head was found. | Is result identity per project, line, sealed set, or another aggregate; how are revisions and predecessor links represented? | `ProjectAssetLine`; absence of an APPRAISAL_RESULT model/API. | Overwrites could destroy what was reviewed or make documents point at mutable values. | NOT YET PROPOSED |
| **D5 — lifecycle / correction / withdrawal** | Legacy decision statuses exist for catalog records only; final-result design does not specify lifecycle. | Draft/confirm/correct/reconfirm/withdraw states, append-only history, and effects on output/currentness. | `AppraisedPriceDecisionStatus`; no result lifecycle implementation. | Corrections may rewrite history, retain invalid current values, or silently change an issued output. | NOT YET PROPOSED |
| **D6 — human final-price confirmation** | Human decides current/final price; automated systems may not overwrite it. | Actor/permission/session, explicit confirmation, line/result scope, acknowledgements, and change confirmation. | Price/evidence authority addendum; guarded Workbench price draft is not a final-result confirmation. | AI, automation, or a generic edit could acquire professional decision authority. | NOT YET PROPOSED |
| **D7 — PRICE_EVIDENCE relation** | Three source classes and their priority are accepted; old result is historical evidence and does not copy its value into current price. | Whether evidence links are live or snapshotted; required evidence, provenance retention, staleness, and citation granularity. | `price_evidence_authority.py`, price-evidence models/schemas/commands, addendum. | Evidence could be detached from the value or a historical value could be silently reused. | NOT YET PROPOSED |
| **D8 — SUPPLIER_SELECTION / comparison relation** | Selected NCC quote is comparison context, not automatic final price; comparison inequality is accepted. | Mandatory comparison set, quote/item identity, currency/unit/terms normalization, validation location/severity, and no-comparable behavior. | Price/evidence addendum; A13 quote authority; A15 Issue #145 remains OPEN. | A non-selected, stale, incomparable, or wrong-line quotation could validate/invalidate a professional result. | NOT YET PROPOSED |
| **D9 — currentness / stale** | A15-derived quote/source currentness and no-silent-rebind requirements remain pending; result must not assume them. | Which changes stale a result/evidence set, how stale is surfaced, and whether output is blocked pending explicit reconfirmation. | A13 currentness mechanisms; A15 Issue #145; no result currentness provider. | Changed source facts could be presented as current without professional review. | NOT YET PROPOSED |
| **D10 — security / CAS / idempotency / audit** | Existing code has project/line row versions, Workbench sessions/drafts, permissions, audit, and quote command patterns; those patterns have different scopes. | Actor/tenant rules, Project DRAFT, lock ordering, aggregate CAS, UUID receipts/replay, atomic audit, unknown outcomes, concurrency matrix. | `projects.py`, Workbench draft command, `supplier_quote_authority.py`, generic knowledge routes. | Cross-tenant mutation, lost updates, duplicate commits, or an unaudited official result. | NOT YET PROPOSED |
| **D11 — Case State / Next Action / product surface** | Final-result design is the next step after supplier selection and uses Fluent 2 around the forms; current runtime boundary is earlier. | Provider/stage/context/state/action semantics, route/feature gate, source-of-truth ownership, and exact operator surface. | Final-result baseline/addendum; Case State API/provider registry; no APPRAISAL_RESULT provider found. | UI may display a future/mock screen as enabled or imply completion that server truth does not authorize. | NOT YET PROPOSED |
| **D12 — output / document boundary** | The forms are output-facing company layouts; routing continues from final result to report/certificate document work. | Whether output is preview-only or generated; immutable snapshot identity; document versions, correction/reissue, and downstream handoff. | Final-result baseline; document workspace; dossier extraction models; no current result-to-document output pipeline found. | A document could contain mutable, unconfirmed, stale, or unsupported values. | NOT YET PROPOSED |

## 9. Legacy disposition questions (not recommendations)

The later APPRAISAL_RESULT proposal must resolve these compatibility questions; this inventory does not select an implementation:

- **`ProjectAssetLine.appraised_unit_price`:** Is it retained solely as working/comparison data, mapped into a new result record, or treated as a legacy value requiring review? It currently has no final-result identity, revision, evidence binding, or confirmation fact.
- **`ProjectAssetLine.appraised_currency_id`:** How is a working currency reconciled with evidence currency and the final form's monetary output? It is nullable and attached to the mutable line.
- **`AppraisedPriceDecision`:** Does its catalog-wide canonical-asset/variant/quote-batch rationale have any supporting role, or must it remain separate from per-project results? It lacks project-line and organization scope and uses float storage.
- **Generic knowledge API:** Can these generic permissions/routes remain catalog-only, or do they require future tenant-scope/audit/lifecycle remediation before any relationship to APPRAISAL_RESULT? Existing list/get/patch semantics are not a safe final-result contract.
- **Historical dossier final prices:** How are extracted `word_final_result_table` rows and row alignments exposed as cited prior-result evidence without becoming current results or auto-populating a new result?
- **Three immutable output tables:** What read model/snapshot binds their cells to exact line, selected quote, evidence, and human result revisions while preserving original `STT` and immutable layout?
- **Report/certificate pipeline:** Which later task owns generation, preview, immutable document snapshot, correction/reissue, and publication boundaries? Existing document workspaces and historical extraction do not answer this.

## 10. Security and concurrency inventory

Patterns for a later authority proposal to reconcile—not decisions made for APPRAISAL_RESULT:

- Human actor, tenant, project, and active Workbench session checks exist in project/workbench flows; generic AppraisedPriceDecision routes instead use generic knowledge permissions and lack record-level organization scoping.
- Project/line locking and `row_version` CAS exist in asset-line update paths; Workbench draft commit has its own field/session/version contract. Neither is automatically a result-level aggregate CAS.
- Current A13 supplier-quote authority (`docs/plan/VALORA_OS_G2_SUPPLIER_QUOTES_AUTHORITY_PROPOSAL.md`, `backend/app/modules/project_master_data/application/supplier_quote_authority.py`) specifies active human/session checks, Project DRAFT gating, Project-first lock ordering, expected shared Case State token, tenant/project/actor-bound UUID receipts, replay reconciliation, and transactionally bound minimized audit. These contracts govern supplier quotes; they are evidence to reconcile, not automatically APPRAISAL_RESULT rules.
- Current PRICE_EVIDENCE command patterns (`backend/app/modules/project_master_data/application/price_evidence_commands.py`) scope receipts/facts to organization, project, actor, and session and bind receipt/audit IDs. They are a relevant evidence dependency, not a final-result command contract.
- The later proposal must explicitly decide how Project DRAFT rules, Project-first lock ordering, Case State CAS, command UUID/receipt replay, unknown-outcome reconciliation, atomic append/audit, and cross-tenant isolation apply to result mutations.
- Numeric storage and conversion paths span Decimal validators, SQL `Numeric`, and float-typed model/schema/UI fields. No binary-float monetary snapshot should be assumed safe for official output.
- Human-only final-price authority is accepted. AI, provider, background job, or system-generated confirmation is outside the boundary.

## 11. Explicit risks

1. `appraised_unit_price` is working/legacy data and cannot be silently promoted to official APPRAISAL_RESULT.
2. Generic `AppraisedPriceDecision` knowledge routes may carry catalog/legacy semantics; they need scope, tenant, numeric, status, and audit review before any official-result use.
3. The approved three-table final-result design fixes presentation layout; it does not define backend `COMPLETE` semantics.
4. Selected NCC price is comparison context, not an automatic final appraisal price.
5. Severity and completion impact when result price exceeds the selected quote comparison set remain unresolved.
6. APPRAISAL_RESULT authority cannot be finalized until the A15 `SUPPLIER_SELECTION` dependency is resolved.
7. The existing Workbench and legacy NCC-selection UI can present working price and quote comparison in ways that look more authoritative than the currently certified business truth.
8. Historical extracted final-result rows and generic decision records are supporting/historical artifacts, not current project result authority.

## 12. Boundary and next gate

This inventory prepares later authority work only. It does not answer or accept D1–D12, request Product Owner acceptance, implement runtime, create an APPRAISAL_RESULT authority proposal, or authorize a stage advance. Recheck live main and A15 before using this snapshot; changes to A15-derived facts require rebaselining the dependency section.
