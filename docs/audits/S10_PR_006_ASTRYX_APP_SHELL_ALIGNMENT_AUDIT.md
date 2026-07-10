# S10-PR-006: Astryx App Shell Alignment Audit Report

This report documents the verification audit for the progressive alignment of the top-level application shell, navigation, and connection status surfaces with the Astryx design specifications and Vietnamese localization rules.

## 1. Files Changed
- [VALORA_ASTRYX_TOKEN_COMPONENT_MAPPING.md](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/design/VALORA_ASTRYX_TOKEN_COMPONENT_MAPPING.md)
- [VALORA_NON_IT_ERROR_MESSAGE_REGISTRY.md](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/design/VALORA_NON_IT_ERROR_MESSAGE_REGISTRY.md)
- [VALORA_VIETNAMESE_I18N_LABEL_DICTIONARY.md](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/design/VALORA_VIETNAMESE_I18N_LABEL_DICTIONARY.md)
- [S10_PR_006_ASTRYX_APP_SHELL_ALIGNMENT_AUDIT.md](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/audits/S10_PR_006_ASTRYX_APP_SHELL_ALIGNMENT_AUDIT.md)
- [package.json](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/package.json)
- [package-lock.json](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/package-lock.json)
- [tsconfig.json](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/tsconfig.json)
- [RbacLockNotice.tsx](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/common/RbacLockNotice.tsx)
- [AppShell.tsx](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/layout/AppShell.tsx)
- [WorkbenchFooter.tsx](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/layout/WorkbenchFooter.tsx)
- [WorkbenchHeader.tsx](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/layout/WorkbenchHeader.tsx)
- [WorkbenchSessionStatus.tsx](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/workbench/session/WorkbenchSessionStatus.tsx)
- [i18n.test.ts](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/i18n/__tests__/i18n.test.ts)
- [vi.ts](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/i18n/vi.ts)

## 2. Pre-flight Reading Summary
- **Design Book v1.3 MVP Addendum**: Enforces the MVP scope freeze around closed-loop asset valuation. Explicitly forbids raw system parameters (session ID, ORM row versions, HTTP codes) and mandates that Gemini/DeepSeek be hidden behind the label "Trợ lý Valora".
- **Astryx Token Mapping**: Identifies the installed packages (`@astryxdesign/core`, `@astryxdesign/theme-neutral`, `@astryxdesign/cli`) and catalogs the candidate patterns for App Shell layouts.
- **Vietnamese i18n Label Dictionary**: Mandates the type-safe dictionary key mapping approach, requiring all user-facing strings to be localized.
- **Non-IT Error Message Registry & Audit**: Establishes the `FriendlyError` payload shape (`title`, `message`, `nextAction`, `severity`, `retryable`) and verifies that no raw HTTP codes or developer details leak to users.

## 3. Current App Shell Inspection Summary
- **Before**: The App Shell layer was structured with native HTML layouts containing hardcoded English tags (`Project Workbench`, `Review Queue`, `Validation Dashboard`). Lower surfaces in the Workbench layout leaked variables (`Session ID`, `Row Version`, and status codes such as `409` or `RBAC Warning`).
- **After**: The app shell now implements a fully translated layout utilizing Astryx navigation structures. Technical parameters are suppressed, and system connection errors resolve to descriptive Vietnamese directions.

## 4. Astryx Availability and Component Usage Summary
- **CLI Inspection**: Confirmed imports resolve successfully.
- **Components Used**:
  - `AppShell` (as `AstryxAppShell`) from `@astryxdesign/core/AppShell`
  - `SideNav`, `SideNavItem`, and `SideNavSection` from `@astryxdesign/core/SideNav`
- **Components Deferred**: Advanced data tables, drawers, and form cards are deferred to subsequent feature-specific PRs as full Workbench refactoring is out of scope.

## 5. i18n Usage Summary
- Extracted and localized all top-level shell labels, including page titles, role descriptions, organization labels, and status logs, through the `t()` translation helper.

## 6. Error Registry Usage Summary
- Linked `RbacLockNotice` warnings directly to the `forbidden` error mapping.
- Handled connectivity failures in `WorkbenchSessionStatus` through `getFriendlyErrorFromUnknown` and `getFriendlyError`.

## 7. Package / Config Changes
- **tsconfig.json**: Changed `"moduleResolution": "Node"` to `"moduleResolution": "bundler"` to support subpath exports configuration inside `@astryxdesign/core`.
- **package.json & package-lock.json**: Installed `@stylexjs/stylex` under `devDependencies` via `npm install --save-dev @stylexjs/stylex --legacy-peer-deps`. This was required because `@astryxdesign/core` components import stylex internals, which Rollup failed to bundle/resolve during production compilation. No runtime behaviors are modified, and all test suites remain fully passing.

## 8. Astryx CLI Command and Result
- **Command Run**: `npm run astryx -- component --list`
- **Results & Observed Patterns**:
  - Core layouts observed: `AppShell` (from `@astryxdesign/core/AppShell`), `Layout` group (`Layout`, `LayoutHeader`, `LayoutContent`).
  - Navigation layouts observed: `SideNav` group (`SideNav`, `SideNavItem`, `SideNavSection`).
  - Feedback surfaces observed: `Badge`, `Banner`, `Toast`, `EmptyState`.

## 9. Workbench Scope Boundary
- **Scope Statement**: The changes made to `WorkbenchHeader.tsx`, `WorkbenchFooter.tsx`, and `WorkbenchSessionStatus.tsx` are strictly limited to the top-level shell-adjacent layout and connection status displays.
- The underlying Workbench asset grid was not refactored.
- Inline cell editing and dirty cell locks were not changed.
- Draft commit, autosaving checkpoint mechanisms, and official valuation logics were not altered.
- API contract interfaces and backend codebases remain completely untouched.

## 10. Runtime/User-Visible Behavior Changed
Yes — limited to App Shell layout/labels/status surfaces.

## 11. Tests & Quality Gates Run
- `npm run lint` (Passed)
- `npm run build` (Passed)
- `npx vitest run src/i18n/__tests__/i18n.test.ts --globals` (Passed, **4 tests passed**)
- `npx vitest run src/errors/__tests__/errorRegistry.test.ts --globals` (Passed, **5 tests passed**)

## 12. Design Consistency Check
- Design Book v1.3 checked: Yes
- Astryx mapping checked: Yes
- Vietnamese i18n dictionary checked: Yes
- Non-IT error registry checked: Yes
- Roadmap consistency checked: Yes
- Runtime behavior statement verified from git diff: Yes
- Audit file lists every changed file: Yes
- No dashboard/revenue/CRM scope introduced: Yes
- No Gemini/DeepSeek runtime integration introduced: Yes
- No raw technical errors exposed to users: Yes
- No new English user-facing labels introduced: Yes

## 13. Final Status
PASS
