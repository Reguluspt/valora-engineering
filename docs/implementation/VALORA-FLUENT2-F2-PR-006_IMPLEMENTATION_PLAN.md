# F2-PR-006 — NCC Selection Golden Remediation

**Status:** READY FOR DEV
**Depends on:** F2-PR-003
**Authority:** NCC Selection Baseline Iteration 1

## File manifest
**MODIFY:** `NccSelectionPage.tsx`, `NccSelectionTable.tsx`, `NccSelectionKpis.tsx`, `NccSelectionDrawer.tsx`, `nccSelection.css`, focused tests.
**PRESERVE:** `useNccSelection.ts`, API contract unless test-only wiring is required.

## Target
Implement the approved data-heavy Fluent light surface:
- KPI summary: total, selected, unselected, stale/review, eligible quotes;
- search/filter;
- table with current price, selected supplier/price, delta/%/warning/state;
- contextual right drawer;
- drawer sections for eligible quotes, current selection, history;
- exactly one primary `Xác nhận NCC đã chọn cho dòng này` action.

## Behavior locks
Warning is non-blocking. Ineligible candidate cannot commit. 409 → VERSION_CONFLICT/reload/review/explicit confirm; no last-write-wins. Preserve selection revision, warning acknowledgement and idempotency-key reuse/new-attempt behavior.

## Visual
Remove dark fallbacks/cyan focus/primary styling. Use semantic status + text/icon so warning/stale is not color-only. Drawer must be keyboard reachable with focus handling appropriate to its modality.

## Tests
All existing NCC tests remain green, especially first-use/no-results distinction, confirmation payload, idempotency retry semantics and real 409 mapping. Add visual/accessibility assertions for primary action and drawer state.

## DoD
Approved NCC Selection baseline represented; no standalone NCCQ intermediate route; behavior unchanged; screenshot/browser evidence accepted.
