# VALORA — Editable Data Grid Contract v1 (proposed shared reference)

**Status:** NCCQ Prototype 04 interaction direction PO-approved; detailed reusable grid engineering contract proposed; other screens not activated. No dependency installation, frontend code or shared primitive rollout under current docs-only authorization.

The [Iteration 7 baseline](assets/VALORA_NCCQ_BASELINE_v2.3.md) defines the target screen. [Workflow v2](VALORA_NCCQ_WORKFLOW_CONTRACT_V2.md) owns quotation semantics, and [#251](https://github.com/Reguluspt/valora-engineering/issues/251#issuecomment-7233061803) remains design/DoR only.

## 1. Data and edit boundaries

Render stable row identity and field identity independent of visual order. NCCQ price cells bind exact `project/group/line/supplier slot/revision`; STT, asset, specification, unit, quantity, confirmed TĐG are read-only in NCCQ. Confirmed quote values are immutable; opening a permitted new draft/revision does not mutate old facts. One group is one grid; no cross-group paste. Render server-authorized actions and revision status; permissions do not derive from UI. Distinguish local draft buffer from committed data; preserve across navigation, tab switches, reload/unknown result per authorized persistence. Never mark local state confirmed or save to knowledge automatically.

## 2. Keyboard and interaction

Use spreadsheet-style direct typing/Enter/F2 or double-click, Tab/Shift+Tab, arrows, Shift+arrows and mouse range selection; Ctrl+C/V; Delete for allowed draft cells; undo/redo for working changes only (not reversing official commands). Provide toolbar equivalents, visible focus/selection, accessible row/column names and feedback. Existing confirmed cells may be selected/copied subject to read permission, not edited/cleared/pasted. Controls remain keyboard accessible after error, return focus after modal, keep selected cell stable during re-render. Ctrl+S if supported must mean explicit authorized draft save, not business confirmation. Native clipboard permissions/consent honored.

## 3. Clipboard contract

Copy/paste rectangular price range from Excel TSV and Word HTML table using safe inert parse, plain text fallback. Treat clipboard content as untrusted text, never execute HTML/scripts/formulas or external links. Parse locale-aware VND numeric text (integer/decimal scale defined by domain, not silently guessed); recognize approved grouping/decimal formats, currency suffix and blanks. Ambiguous separators, mixed currencies, merged cells, unexpected headers, nonnumeric/formulas, negative or invalid magnitude → report exact cell and no write. For explicit blank values distinguish intentional clear from missing/no-op; policy must be decided before production. Do not silently normalize ambiguous values. Do not use table row position when row order/mapping is uncertain; require explicit exact target selection, verify current row order and stable identity; no guessing by asset name.

Plan entire rectangular matrix first, validate shape/bounds, current group and revision, read-only/locked cells, all values and line IDs; reject atomically if any invalid. Do not expand columns, create assets, reassign suppliers, write appraisal price, or cross groups. Single/three-column paste allowed; preserve formatting, origin marker and actual vs draft provenance. No confirmation modal for valid routine paste. Exceptions clearly explain and retain data for correction; no silent truncation. Undo/redo restores working change as one operation; official save CAS and audit separate. Fill auto only eligible blanks; never overwrite manual or confirmed.

## 4. Persistence/concurrency (proposed)

Batched patch against exact server snapshot, field/row version and policy mode; authorization and integrity checked atomically. Receipt/replay distinguish original operation and current state. On server conflict/revocation/unknown result, preserve unsaved buffer, show stale/conflict and reload/reconcile; no auto-retry into different row order. No UI-only validation or stored COMPLETE Boolean. Virtualization/pagination must not change full coverage. Native Office integration is future acceptance, not established by synthetic clipboard event. Reuse shared component only with owning contract for each surface; #251 stays design/DoR.

## 5. Acceptance (future)

| ID | Test |
|---|---|
| DG01 | paste 1×1, 2×3 and 150×3, TSV and Word HTML; stable line/slot mapping, read-only TĐG untouched. |
| DG02 | overflow, ragged, merged, protected, wrong group/version, reordered rows, malicious HTML/formula, ambiguous decimal/invalid price: no partial write and actionable error. |
| DG03 | keyboard focus, range selection, copy/delete/undo/redo and mode change; confirm immutable column; accessible controls. |
| DG04 | reload/nav/tab/stale response, two operators/races, permission revoked and replay/unknown result: no lost draft or false commit, no extra confirmation. |
| DG05 | real Word/Excel on authorized Windows synthetic fixture, 3/150 lines, responsive/focus/error states; no UAT/customer data. |
