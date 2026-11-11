# OS-G1 vNext — Product Owner UX decision register

**Recorded:** 2026-10-31 (Asia/Ho_Chi_Minh)  
**Status:** Individual UX decisions approved by PO through conversation. The **consolidated workflow/mockup is not yet an implementation approval**.

## Original OS-G1 business decisions (preserved)

| ID | Decision | Boundary |
|---|---|---|
| OS-G1.01 A | Create a preliminary request without customer; bind customer at official intake. | No premature customer requirement. |
| OS-G1.02 B | Reuploaded Excel produces add/change/remove comparison with human confirmation; retain unaffected work/history. | No silent replacement. |
| OS-G1.03 B | Non-linear editing across assets, prices and evidence; incomplete drafts allowed. | Preserve editing flexibility. |
| OS-G1.04 B | Proposed price suggestion may derive from surveyed price + transportation (percentage supported); human can override. | Formula is not binding on human price. |
| OS-G1.05 B | Generate preliminary output with evidence gaps clearly warned. | Preliminary is not final basis acceptance. |
| OS-G1.06 C | Knowledge Base can suggest sources/prices/evidence in bulk. | Suggestions are candidates. |
| OS-G1.07 C | Multi-select/bulk application with provenance/history and later per-asset edit. | Explicit review for uncertain sources. |
| OS-G1.08 B | Notify better/new sources; do not silently override user inputs. | Human control. |
| OS-G1.09 B | Include assets with missing proposed prices in output; leave blank and exclude from known-value total. | Never treat unknown as zero. |
| OS-G1.10 A | Single Excel results table with surveyed/reference price, transportation, proposed prices, explanations, URLs and embedded evidence images. | Multiple evidence items must not be lost or double-count amount. |
| OS-G1.11 B | Every export is an immutable independent version; no mandatory inter-version comparison table. | Export history. |
| OS-G1.12 B | Official conversion requires valid customer, asset list and user confirmation; price/evidence can still be incomplete. | OS-G2 completes remaining work. |
| OS-G1.13 C | Automatically inherit quantities, prices, sources, links, images and reasoning into OS-G2 as editable work-in-progress. | No auto-accept as final appraisal basis. |
| OS-G1.14 B | Converted OS-G1 becomes read-only history; changes occur in OS-G2 without back-sync. | Preserve lineage. |

## UX decisions UX-G1.01–UX-G1.14

| ID | PO choice | Accepted UX decision | Implication |
|---|---|---|---|
| UX-G1.01 | C | Short Wizard for create/import/mapping, then unified Workbench. | No mandatory repeated registration. |
| UX-G1.02 | A | Right-hand asset detail panel, closable; table gets space when closed. | No page navigation for ordinary asset inspection. |
| UX-G1.03 | B | Price source and its evidence within one source card, including surveyed price, VAT, transport, links, images and explanation. | One entry context, live table reflection after saved changes. |
| UX-G1.04 | C | Support bulk knowledge suggestions AND single-asset inspection/editing. | Bulk review is supplemental. |
| UX-G1.05 | B | Bulk source-review uses the main Workbench content area while shell/nav remain. | Preserve return context. |
| UX-G1.06 | C | Persist bulk review selection drafts; quick-check assets without losing work. | Draft choice is not applied source. |
| UX-G1.07 | C | Quick-check asset in review panel; optionally open full Workbench, return to draft. | No duplicate data. |
| UX-G1.08 | B | After mapping, auto-populate price/evidence ONLY for high-confidence matching and source suitability. | Uncertain matches remain suggestions. |
| UX-G1.09 | B | On material identity edits, ask inline in asset panel: correct existing knowledge / new asset or variant / case-only edit. | Do not interrupt ordinary price/note changes. |
| UX-G1.10 | C | Mark viewed on leaving an asset; final summary warns unviewed assets, without per-line acceptance button. | View is not final source acceptance. |
| UX-G1.11 | B | Workbench remains editable after exporting Excel; each confirmation creates another independent immutable version. | OS-G1 read-only only after official conversion. |
| UX-G1.12 | B | With multiple valid sources, auto-pick only if one has a clearly justified preference; otherwise human chooses. | No arbitrary score winner. |
| UX-G1.13 | PO semantic correction | Detect abnormal price spread, display comparison/warning **during sequential human review**; pricing belongs to human. If a preferred source is clearly supported, do not add a separate spread-approval step or blanket auto-population block solely for spread. | Warn, preserve user's proposed price; do not equate warning with validated final price. |
| UX-G1.14 | B | Staff propose changes to shared Knowledge Base; authorized reviewer confirms activation/version. | Separate queue; proposal should not block case work. |

**Design pivot after UX-G1.07:** PO specified the primary flow as create → Excel/mapping → VALORA automatically retrieves and fills high-confidence matches → staff review each asset in original order → fill missing data assisted by similar-asset search → overall preliminary confirmation → versioned Excel. The previously described **manual bulk source-selection screen is no longer a mandatory stage**. Preserve it as an auxiliary tool when needed.

## Not yet signed off

- **UX-G1.15**: Workbench prototype v01 is exploratory, not final; PO asked for closer Microsoft Fluent 2 React component conformity. v02 remains to be built and reviewed.
- PO has NOT approved this package as a complete domain/API/runtime modification contract.
- No fixed machine-matching percentage, price-spread percentage, source-age cutoff or default monetary decision is approved.
- No delegation of final appraisal basis acceptance to AI/knowledge; human decision in OS-G2 case completion remains authoritative.
- **Knowledge approval role conflict:** UX-G1.14 B implies a distinct permission/approval decision, whereas current knowledge UX v2.3 documents a single-user domain-local review. See [authority reconciliation](AUTHORITY_RECONCILIATION.md); no multi-user workflow implementation has been approved.
- **Current preliminary confirmation conflict:** UX-G1.10 replaces line-by-line confirmation in future UX, but existing strict G1.1 line-manifest/API constraints and the archived Issue #222 mockup are not automatically amended. See reconciliation.

## Non-negotiable acceptance statements

1. AI/Knowledge suggestions are never a direct human appraisal basis decision.
2. Staff can edit proposed prices independently of source/transport formula; no automatic overwrite afterward.
3. New evidence/links/images displayed in the source card must reflect in the table after successful save.
4. Original Excel values are retained for traceability, including original quantity and customer price.
5. Saving work, accepting preliminary export, updating shared knowledge and accepting final appraisal basis are four distinct semantic operations.
6. No UAT #203 start, Codex implementation, repository runtime modification, CI/deploy, or merge is authorized by this register.
