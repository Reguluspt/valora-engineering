# VALORA — Fluent 2 UI/UX Static Audit

**Date:** 2026-10-31  
**Scope:** Read-only inspection of selected frontend sources on repository default branch, and Microsoft Fluent 2 web/React guidance.  
**Disposition:** **Design audit only.** No code changes, migration, deployment, CI/UAT execution or implementation approval.

**Method caveat:** This is a **sampled static code audit**, not a complete repository census, running-browser visual audit, accessibility test, or product certification. No compliance percentage is asserted.

## Executive finding

VALORA **really uses** `@fluentui/react-components` v9, but adoption is **inconsistent**. Microsoft `Button`, `Field`, `Input`, `Tab`, `Dialog` and `Table` are present in some screens, with locally-scoped `FluentProvider theme={webLightTheme}`. The root shell and a number of Pre-case and Workbench screens use native HTML controls and proprietary CSS classes. The archived 26-Oct preliminary mockup and UX-G1.15 v01 were hand-styled HTML prototypes, **not React Fluent component prototypes**. A look-and-feel resemblance does not establish Microsoft component behavior, accessibility or documented interaction compliance.

## Evidence and remediation matrix

| ID | Priority | Verified finding | Files / evidence | Design recommendation |
|---|---|---|---|---|
| F2-01 | P0 | Fluent v9 is declared as actual dependency: `@fluentui/react-components: ^9.74.9`. | [package.json](../../frontend/package.json) | Reuse library instead of building competing design system. |
| F2-02 | P0 | No root-level `FluentProvider` in sampled `main.tsx` or `App.tsx`, while several features introduce their own `webLightTheme`. Prior UAT repair documents a Fluent theme context failure in a feature. | [main.tsx](../../frontend/src/main.tsx), [App.tsx](../../frontend/src/App.tsx), [PreliminaryRequestCreatePage](../../frontend/src/components/precase/PreliminaryRequestCreatePage.tsx), [UAT repair](../implementation/VALORA_UAT203_217_PRELIMINARY_CREATE_CONTRACT.md) | Define root theme/provider and portal semantics as bounded future task; test computed styles. |
| F2-03 | P0 | Global breadcrumb uses native `nav`, span separators and strong current label; no Microsoft Breadcrumb in inspected AppShell. | [AppShell](../../frontend/src/components/layout/AppShell.tsx) | Review Fluent `Breadcrumb` composition, links, current-page semantics, overflow, keyboard and focus. |
| F2-04 | P0 | Preliminary Analysis uses native `table`, `button`, `input` and proprietary classes, no Fluent imports. | [PreliminaryAnalysisPage](../../frontend/src/components/precase/PreliminaryAnalysisPage.tsx) | Specify shared Fluent-native or compliant domain grid; preserve asset-specific density/lineage. |
| F2-05 | P1 | Sidebar uses glyphs (`▤`, `▦`) for icons and custom navigation. | [AppShell](../../frontend/src/components/layout/AppShell.tsx) | Assess Fluent icon/Nav patterns; collapsed label/tooltips, arrow/focus semantics. |
| F2-06 | P1 | Proprietary `.valora-button`, `.valora-message`, `.valora-status` remain alongside Microsoft components. | [primitives CSS](../../frontend/src/styles/fluent2-primitives.css), [MessageBar](../../frontend/src/components/ui/MessageBar.tsx), [StatusBadge](../../frontend/src/components/common/StatusBadge.tsx) | Establish shared wrappers and reduce divergent control behavior; native HTML is not intrinsically noncompliant. |
| F2-07 | P1 | Asset right-panel tab strip uses real Fluent `TabList/Tab`, but drawer body/header/close uses custom HTML/CSS. | [WorkbenchRightPanelShell](../../frontend/src/components/layout/WorkbenchRightPanelShell.tsx) | Compare to Fluent inline Drawer; test return focus, Escape, scroll, tabpanel labels, narrow viewport. |
| F2-08 | P1 | Workbench and additional Pre-case components have native tables/buttons; some other regions use real Fluent. | [AssetGrid](../../frontend/src/components/workbench/AssetGrid.tsx), [PreliminaryIntakePage](../../frontend/src/components/precase/PreliminaryIntakePage.tsx), [PreliminaryCompletionPage](../../frontend/src/components/precase/PreliminaryCompletionPage.tsx) | Inventory by surface, not a blanket migration. |
| F2-09 | Positive | Light-theme token sheet defines canvas, typography, spacing, density, status, radius and elevation. | [fluent2-tokens.css](../../frontend/src/styles/fluent2-tokens.css) | Retain investment; bridge to official Fluent theme tokens rather than competing constants. |
| F2-10 | Positive | Genuine Fluent field integration exists; some quote/import regions use Fluent tables/dialogs. | [FormField](../../frontend/src/components/ui/FormField.tsx), [SupplierQuotesRegion](../../frontend/src/components/workbench/supplier-quotes/SupplierQuotesRegion.tsx) | Reuse established component integration where appropriate. |

## Specific breadcrumb deficiency (from inspected source)

AppShell currently renders a parent `nav`, visible static text and `›` separators, plus a bold page label. It does not instantiate the official Fluent `Breadcrumb`/item composition and inspected parent labels are not links. This is a concrete interaction/accessibility gap to review against [Microsoft Breadcrumb usage](https://fluent2.microsoft.design/components/web/react/core/breadcrumb/usage), **not** proof every custom breadcrumb is inaccessible.

## Theme architecture observation

`frontend/src/index.css` imports `fluent2-tokens.css` and `fluent2-primitives.css`. These are VALORA CSS conventions, not themselves evidence that components conform to Fluent v9 usage. The known 2026-10 UAT feature repair reported absent `.fui-FluentProvider` around a recovery region and unresolved Microsoft CSS variables despite stylesheet presence; a locally scoped provider fixed the particular region. This is evidence for reviewing cross-app theme scope; **not proof all other screens are broken at runtime**.

## Compliance boundaries and planned validation

1. Component-by-component inventory: classify genuine Microsoft, approved Valora wrapper, necessary native semantic controls and divergent custom controls.
2. Validate installed Fluent v9 exports and official documentation for breadcrumb, navigation, drawer, table/data grid, inputs, dialogs, messages and badges.
3. Review semantic themes, portals, focus and keyboard behavior by running UI at representative viewport/zoom; static inspection cannot prove these.
4. Preserve core domain/lineage semantics under the approved [frontend architecture](../architecture/VALORA_FRONTEND_ARCHITECTURE_RULE.md).
5. Produce v02 React Fluent mockup and capture reproducible visual plus keyboard/accessibility checks; compare with v2.3 [visual-reference bundle](../design/visual-reference/v2.3/README.md) and [Issue #222](https://github.com/Reguluspt/valora-engineering/issues/222).

## Governance recommendation

**Do not approve UX-G1.15 v01 as a final Microsoft Fluent 2-compliant visual baseline.** Maintain its business-flow learnings, design v02 using actual Microsoft components where appropriate, and record exceptions and acceptance evidence. Keep OS-G1 decisions separate from implementation and the deferred UAT #203.

No repository source, API or environment behavior is changed by this audit file.
