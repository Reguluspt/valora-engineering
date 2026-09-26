# F2-PR-003 — Shell, Login & Shared State Primitives

**Status:** MERGED ON INTEGRATION — PR #38 / `d725bbc6f60f2a21ec11a555d9565d2ab01470ae`; exact-head CI #454 SUCCESS
**Depends on:** F2-PR-002
**Blocks:** F2-PR-004…007

## Objective
Remove production Astryx component dependency and establish the reusable shell/state components all golden-surface PRs consume.

## File manifest
**MODIFY:** `AppShell.tsx`, AppShell tests, `LoginPage.tsx`, `session.css`, `WorkbenchHeader.tsx`, `WorkbenchFooter.tsx`, `WorkbenchSessionStatus.tsx`, `ApiErrorBanner.tsx`, `ConflictWarning.tsx`, `EmptyState.tsx`, `ErrorState.tsx`, `LoadingState.tsx`, `RbacLockNotice.tsx`, `StatusBadge.tsx`.
**CREATE as needed:** small shared presentation components under `frontend/src/components/ui/`.
**KEEP TEMP:** Astryx packages/global imports until F2-PR-008, but production TS/TSX imports must reach zero here.

## Shell implementation
Replace Astryx `AppShell/SideNav` with semantic HTML + shared Fluent classes. Preserve navigation callbacks/hash routing/account/logout. Use current IA only: Workbench/project entry, Tổng quan hồ sơ, NCC Selection when contextual, Không gian tài liệu. Do not add historical workflow axes.

Required accessibility: `nav` landmark, current item via `aria-current`, keyboard-visible focus, buttons with accessible names.

## Shared states
Map components to Cross-product State Contract:
- Loading → INITIAL/SECTION loading surface; no fake progress.
- Empty → Vietnamese-first defaults and explicit first-use/no-results variants where caller knows scope.
- Error/API banner → Error Registry message first; retry at correct scope.
- Conflict → VERSION_CONFLICT presentation; remove full-screen dark glass treatment. A modal/dialog is allowed only when explicit decision is required; generic Workbench 409 should not force a universal full-screen pattern.
- RBAC → permission state, not “no data”.
- Session → lightweight status/message bar; keep usable content.

Replace English defaults such as “No Data Found”, “Retry Search”, “Error Loading Session”, “Retry Action”, “Loading…” and technical “Stale Row Collision” with Vietnamese business-facing copy.

## Workbench chrome
Remove visual/action affordances that imply deprecated QC/reviewer workflow. Header/footer may show valid draft/session facts, but disabled “Gửi KSCL/Xem trước phê duyệt/Phân công” controls must not survive as product navigation.

## Tests
Update existing component tests; add shell accessibility/navigation tests and shared-state tests for Vietnamese defaults, one primary recovery action, no raw technical detail as primary copy.

## Acceptance
Zero production TS/TSX imports from `@astryxdesign/*`; shell/auth/shared states are Fluent 2 light; behavior/API semantics unchanged; tests/build green.
