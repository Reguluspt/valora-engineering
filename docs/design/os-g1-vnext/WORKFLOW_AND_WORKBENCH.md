# OS-G1 vNext — Operator workflow and Workbench UX contract (design proposal)

**Status:** Scope-specific UX requirements derived from approved PO choices, **not an implemented contract**. Requires domain/API authority reconciliation before coding.

## 1. North-star preliminary flow

1. **Create preliminary request** without mandatory customer.
2. **Upload XLSX and confirm mapping**: show source structure, mapped unit/quantity/name/specification/customer price, preserve raw workbook facts and explicit human mapping confirmation.
3. **Automatic Knowledge enrichment** immediately after successful mapping: background/progressive source lookups; only high-confidence matched identity **and** valid source/evidence conditions may populate surveyed/working proposed prices. Do not guess missing tax, transport, timestamp or evidence. Display progress, partial success, failed lookups, gaps.
4. **Sequential asset review (Excel order)** in a single Workbench: table on left/main area, contextual right panel open on selected asset. No per-row acceptance click if unchanged. Users may still jump, filter, bulk inspect or return to earlier rows.
5. **Missing-data assistance**: show similar assets with similarities/differences, origin and evidence; allow explicit choice or manual entry, without leaving asset context.
6. **Overall preliminary review**: show viewed/unviewed, missing price/evidence, sources requiring recheck, outstanding save/mapping conflicts. Link each issue to affected asset, then return to summary without lost context.
7. **Preview and overall confirmation → versioned XLSX export**. All assets included, unknown prices blank; total includes only known-value asset rows; evidence and images remain associated with source.
8. **Continue editing after export** and create a new immutable result version on next confirmation; optional official conversion to OS-G2 with customer and official-intake checks, inheriting editable work; OS-G1 becomes historical read-only after conversion.

Bulk Knowledge review from UX-G1.04–.07 is a **secondary on-demand route**, not a mandatory checkpoint preceding sequential review.

## 2. Workbench desktop composition

- **Shell:** Microsoft Fluent 2 light. Hierarchical clickable breadcrumb, Vietnamese labels, collapsible sidebar with real icon affordance/tooltips, consistent page header and command bar.
- **Main table:** dense enterprise data table (not 4-card list), original row order as default. Search, filters, visible results count, configurable column visibility, keyboard use, wrapping long specs. Upper and lower horizontal scroll affordance synchronized. Sticky STT and asset name when horizontally scrolling; mouse wheel behaves naturally vertically, even over table when table has no vertical scroll to consume.
- **Columns (subject to agreed column geometry):** STT; asset name; Đặc điểm; ĐVT; **SL nguồn** editable beside ĐVT; customer unit price and customer amount if available; surveyed/reference price; VAT/transport conditions; proposed unit price; proposed amount; price-source/evidence count; readiness/visit/alert. Preserve original Excel quantity separately, display delta and require explanation for modified SL nguồn. Do not restore eliminated 'SL làm việc' column.
- **Right asset panel:** inline contextual panel/drawer, toggles without navigation. Sections: asset information/specs; **Price source + evidence in same source card**; similar assets; changes/lineage. On desktop, allow sufficient width to paste/inspect links and images, with sticky previous/next controls. Close restores table width.
- **Evidence:** rich explanation accepts text, HTTP(S) URLs and clipboard images directly. Automatic identification and preview/removal; one source may own many links/images. No mandatory 'Add link' or 'Add image' step. Source/evidence edit updates table counts and statuses upon successful save; show saving/saved/failed feedback.
- **Price:** surveyed price + transport percentage yields a **suggested** proposed unit price when all inputs and business conditions are known; VAT/transport source conditions editable. Staff may manually enter proposed price, which is protected against future enrichment refresh. Never default unknown transport cost to zero.
- **Knowledge suggestions:** show exact model/variant confidence and differences; provenance of each price source, actual source type, timestamps and conditions. Knowledge Base is **retrieval/management**, not a fourth independent price-source type.
- **Page states:** loading, empty, in-progress auto match, partial match, awaiting input, reviewed, recheck needed, save pending, saved, failed, stale/conflict, permission denied, uncertain external result, export generation and failed export. Never claim success before server acknowledgement.

## 3. Per-asset handling

### A. Asset confidently auto-enriched

- Show indication 'VALORA đã tự điền', what was populated and which price/evidence originated from which source.
- User reads and optionally changes the working price/record. **No obligatory 'accept this line' action.**
- When moving to next item and changes are durably saved, record an 'đã xem' event; absence of price edit is not evidence of final appraisal acceptance.
- Warning for unusual source price spread is displayed **inside this review**, with source comparisons; user decides whether to maintain/alter price. No separate abnormal-price approval stage.

### B. No confident source

- Empty unknown fields (never render as 0 VND).
- Similar-asset search visible in panel: compare names, model, rated power/capacity, new/used, evidence age, supplier vs Internet vs historical appraisal price semantics.
- Explicitly applying an eligible source creates/links a price-source and evidence record **once**. Alternatively staff manually enter source details, links/images/notes.
- Staff may move on with incomplete data and return later; summary flags gaps.

### C. Staff edits identity-related characteristics

- After completed edit/save of material identity fields (not per keystroke), inline question within right panel:
  1. Correct existing shared Knowledge record → emit a non-activated proposal.
  2. New model or variant → search for duplicate; then propose identity/variant.
  3. Case-only correction → update case, no shared Knowledge change.
- Check suitability of previously suggested/used price sources; keep historical lineage and human proposed price even if source is marked 'recheck required'.
- Edits only to proposed unit price or narrative do **not** launch identity classification.

### D. Bulk source comparison (optional)

- In-workbench full-content mode, keep shell and review draft. Support compare/apply source to one or more assets, preview conflicts and count impact before applying.
- Draft selections are persisted separately from applied source facts. Quick inspect asset via panel; deep edit routes into Workbench then returns to draft/current row.
- On resume retain filters, search, selected asset, vertical/horizontal scroll and successful draft choices.
- Partial failure retains successful operations without duplicates, and offers bounded retry of failed ones.

## 4. Two independent status dimensions and request lifecycle

| Dimension | States (illustrative) |
|---|---|
| Knowledge/data preparation | Matching; auto-filled; similar-only; no source; recheck needed; lookup failed |
| Human progress | Not viewed; viewed unchanged; edited; incomplete; save failed |
| Preliminary request/export | Working; has exported version; changes since latest export; officially converted/read-only |

These states must not collapse into a misleading single 'complete'. 'Viewed' is not a final appraisal-basis approval. A case can be **saved** while having **changes not yet exported**.

## 5. Final summary, warnings and block conditions

Warning-only at OS-G1: some assets unviewed, missing suggested unit price, insufficient evidence, similar-only source, unexplained price spread. Provide exact counts, expandable affected rows, and route back to asset. Unknown prices remain blank and excluded from determined-value sum.

Must resolve before consistent export: unconfirmed/invalid mapping, unsaved change or save failure, broken/ambiguous currently chosen source that cannot be safely represented, or server-side rejection/invalid lineage. **Do not claim currently certified runtime already supports lenient missing-price export**: this is a new proposed contract, see authority reconciliation.

An export confirmation must state 'use present working data for this preliminary version', **not** 'final appraisal price accepted as basis'. Explicit final acceptance of appraisal basis happens only in authorized OS-G2 completion, as separately approved.

## 6. Excel output and versioning

- Exactly **one principal results table**. Preserve assets, descriptions, unit, source quantity, customer unit price/amount when provided, surveyed price, transport and VAT, proposed price/amount, explanations, source URLs and **embedded evidence images**.
- Multiple evidence items may require multi-line cells or subrows clearly excluded from asset count, quantity summation and amount total. No dedicated evidence sheet.
- Preserve raw customer workbook evidence, current working facts and provenance per output version. Historical XLSX files are immutable independent artifacts; repeated export gets version N+1 with stable identity and audit metadata.
- Generation failure is not a completed export; retry must be idempotent and must not accidentally create duplicates.
- After successful v01, Workbench remains editable. Show 'latest export v01' and 'unsent changes' independently of 'working data saved'. Official conversion archives preliminary editing, then routes changes into OS-G2.

## 7. UX acceptance tests (design-level)

| ID | Test |
|---|---|
| W-01 | Create → XLSX/mapping → automatic enrichment → single Workbench without duplicate source registration. |
| W-02 | Confident match auto-fills eligible fields with source/evidence lineage; uncertain asset only suggests. |
| W-03 | Sequential next/previous records viewed without per-row 'accept' operation; row order preserved. |
| W-04 | Inline edit of user-proposed price survives rematch/reload without silent overwrite. |
| W-05 | Important identity edit raises inline classification and source recheck; regular note/price edit does not. |
| W-06 | Similar-asset search displays material differences and does not auto-copy its proposed price. |
| W-07 | Pasted HTTP(S) link and clipboard image appear in source card and related table count after successful save. |
| W-08 | Editable source quantity preserves Excel original and reason; unknown amount not treated as 0. |
| W-09 | Summary warns overlapping missing/unviewed groups without double-counting; offers return links. |
| W-10 | Excel includes all rows and multiple evidence; evidence subrows cannot inflate totals. |
| W-11 | v01 remains immutable after edit/export v02; 'saved' and 'not yet exported' are distinct. |
| W-12 | OS-G2 conversion requires customer, inherits editable working material and locks OS-G1 history. |
| W-13 | Full keyboard/focus, sticky headers, synchronized horizontal scroll, natural mouse-wheel, long text wrap, narrow desktop viewport. |
| W-14 | Failure and stale/conflict paths never claim data applied/exported before durable server result. |

## 8. Boundaries

UI and design only at this phase. All novel auto-enrichment, relaxed preliminary line confirmation, rich-evidence persistence, versioned generation and official intake effects are subject to separate domain/API/schema/security gate. User approved design decisions are **not** authorization to operate on real data or merge new runtime.
