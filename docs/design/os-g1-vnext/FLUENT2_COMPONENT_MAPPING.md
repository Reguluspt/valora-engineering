# OS-G1 vNext — Microsoft Fluent 2 React component mapping and v02 mockup brief

**Status:** Design checklist, based on read-only frontend static audit. Does not certify Microsoft visual/behavioral compliance.

## 1. Component design policy

Use Microsoft [Fluent 2 web React components](https://fluent2.microsoft.design/) via existing `@fluentui/react-components` v9 when their behavior fits; compose VALORA-specific components over Fluent primitives/tokens. Native HTML is **not categorically prohibited**, but custom controls must demonstrate documented semantic and keyboard parity. Design direction:

**Valora Design Tokens → Fluent 2 primitives → Valora shared UI → feature components → screens**.

Avoid independent per-screen dark/cyan/teal visual systems and CSS mimicking Microsoft behavior without interaction/accessibility checks.

## 2. Gap-to-component matrix (source-verified)

| Surface | Current source evidence | Fluent v02 target / evaluation | Tests |
|---|---|---|---|
| App theme | `frontend/src/main.tsx` / `App.tsx` lack root provider; feature-specific `FluentProvider(webLightTheme)` exists | Define app-level provider/theme and bounded nested/portal contexts; map CSS variables to semantic tokens | Computed theme, nested overlays/portals, contrast, no style regressions |
| Breadcrumb | `frontend/src/components/layout/AppShell.tsx` hand-builds spans/›/strong | `Breadcrumb`, `BreadcrumbItem`, `BreadcrumbButton`/links and current item as appropriate | Linked ancestors, current-page semantics, truncation/overflow, keyboard, screen reader |
| Navigation | AppShell custom `<nav>`, anchors and glyph icons | Evaluate official Nav and Fluent icons; if custom, maintain correct navigation/active-state semantics and collapsed icon tooltips | Active route, keyboard navigation, collapse/expand, 200–400% zoom |
| Inputs | Pre-case analysis native HTML; `FormField.tsx` already uses `Field`, `Input`, `Textarea`, `Select` | Prefer reusable Fluent field wrappers with localized labels, validation and disabled/error semantics | Label/description/error association, input precision, focus, keyboard |
| Buttons | `.valora-button` CSS/native and Microsoft `Button` coexist | Standardize Microsoft `Button`/tokens through shared wrapper; only one primary CTA in local context | Disabled, busy, keyboard, focus ring, screenreader label |
| Bulk grid | `AssetGrid.tsx`/preliminary analysis native table; some quote/import views use Fluent `Table` | Assess Fluent `DataGrid` or semantic custom virtualized grid with Fluent tokens; preserve pinned STT/name, dense rows, synchronized top/bottom horizontal scroll, keyboard grid behavior | Hundreds of assets, sticky columns, sorting/filter, row edit, wheel/scroll, accessibility |
| Right panel | `WorkbenchRightPanelShell.tsx`: real `TabList/Tab`, custom outer drawer | Evaluate Fluent `Drawer` with **inline/non-modal** behavior, sticky prev/next, tab content, focus/escape and scroll | Focus restore, overlay containment, close, narrow width and long evidence |
| Alerts | `MessageBar.tsx` custom, separate status classes | Evaluate Fluent `MessageBar` and `Badge` plus shared Valora semantics | Status live region, retry/error, colors not sole carrier |
| Dialogs | Quote/evidence/import views already use real `Dialog` family | Reuse these patterns only where a genuine blocking dialog is needed; inline identity classification should not use dialog | Focus trap, dismiss, confirmation, semantic integrity |
| Tabs | Drawer uses real `TabList/Tab` | Reuse with correct connected tabpanel and focus | Keyboard selection, labelled panel, no content loss |
| Rich evidence | Archived 26-Oct mockup custom clipboard/paste behavior | Fluent fields + **domain custom** clipboard/link/image viewer with validation, attachment preview, evidence lineage | Paste URL/images, remove, counting, large attachments, errors, security |
| Export & history | Preliminary completion native buttons and cards | Fluent command bar/summary/table/status elements; separate 'saved' vs 'exported' | No phantom success, version snapshot immutability, recovery states |

Important: Microsoft component names are **mapping candidates**, not a promise that every component fits current functionality. Validate against installed v9 exports and official usage/accessibility guidance before committing an implementation architecture.

## 3. Fluent 2 v02 mockup structure

**Prototype medium:** React + `@fluentui/react-components` v9 on `webLightTheme`, ideally same version as repo and VALORA token bridge. This should run locally with fictitious data; it is **not production code or an approved runtime dependency change**.

Demonstrate three mandatory states within a realistic dense desktop layout:

1. **Confidently populated asset:** price source card with explicit type, price, conditions, URLs/images and staff-owned proposed price. Next/previous works without per-item acceptance.
2. **Asset with no eligible source:** similar-asset candidates, what matches/differs, manual source/evidence input and unresolved state.
3. **Identity changed:** inline classification under edited critical specification, source recheck, derived Knowledge proposal, no automatic activation or duplicated data entry.

Additional required states:
- Batch enrichment progress and partial failure.
- Abnormal source price spread warning **within** sequential review.
- Search/filter and context-preserving bulk source-review supplemental mode.
- Overall preliminary summary: viewed, missing, unverified, preview, versioned XLSX action.
- Saved vs unsent export changes, loading/empty/error/stale/conflict/uncertain, permissions and keyboard/focus.

## 4. Visual composition standards

- **Light** canvas/surfaces and Microsoft semantic light theme, not custom dark navy shell.
- Sidebar with Fluent-compatible iconography, tooltips when collapsed and consistent active state.
- Table-first density, not oversized cards replacing the real business grid. Respect raw Excel and normalized/working fields.
- Panel responsive at desktop viewport, split without covering editing context. No forced modal for ordinary asset review.
- Fixed row order by Excel source, efficient sticky headers/columns and multiple evidence previews.
- Vietnamese-first text labels; avoid misleading 'Đã chấp nhận nguồn làm cơ sở' in preliminary flow.
- Correct disabled/hover/pressed/focus/selected states; no click-only behavior without keyboard path.
- No hidden mismatch with OS-G2 pricing authority or other module layout.

## 5. Acceptance evidence expected before PO mockup approval

- Screen recording/screenshot for each required state at a **fixed desktop viewport** plus long-table and narrow viewport.
- Component provenance sheet: native Fluent component vs VALORA wrapper/custom, and why custom is necessary.
- Accessibility review: keyboard tab order, grid interaction, focus retention after drawer close, screen reader announcements for async states, adequate contrast.
- Interaction assertions: source/evidence updates reflect in table, preserved proposed price, no silent overwrite, versioned export narrative.
- Visual comparison against [S12 and S13 approved images](../visual-reference/v2.3/README.md) and [archived 26-Oct mockup in Issue #222](https://github.com/Reguluspt/valora-engineering/issues/222), with deviations explicitly documented.
- PO sign-off explicitly labels v02 as a new OS-G1 design, **not** a rewrite of existing archived design evidence.

## 6. Suggested task decomposition (future only)

1. Theme/provider/component inventory and design contract (no runtime).
2. Breadcrumb/sidebar component design.
3. Workbench grid/drawer visual prototype.
4. Asset source/evidence component prototype and states.
5. Sequential review/summary/export prototype.
6. Keyboard/accessibility and visual regression review.

Each future Codex task should have independent evidence and independent review. None is authorized by this documentation PR.
