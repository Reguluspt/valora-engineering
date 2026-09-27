# F2-PR-008 — Residual Sweep, Visual Regression & Astryx Retirement

**Status:** READY FOR DEV
**Depends on:** F2-PR-004, 005, 006, 007

## Objective
Close OS-G0 visual remediation and remove temporary Astryx/legacy compatibility.

## File manifest
**MODIFY:** residual production UI files, `frontend/src/index.css`, visual-system ratchet, production-bundle assertion, `frontend/package.json`, `frontend/package-lock.json`.
**DELETE:** `frontend/src/components/common/AstryxIntegrationProbe.tsx`.
**REMOVE DEPENDENCIES:** `@astryxdesign/core`, `@astryxdesign/theme-neutral`, `@astryxdesign/cli` when zero production dependency is proven.

## Residual scan
Fail closeout if production source contains:
- `@astryxdesign/`;
- Astryx CSS imports;
- legacy global Review Queue/Validation Dashboard route registrations;
- `#66fcf1`, `#45f3ff`, glass/backdrop product styling;
- legacy dark token declarations/usages outside explicitly historical/demo files;
- provider-specific `Tài liệu OneDrive` as product parent;
- English default common-state copy where Vietnamese authority applies.

Do not ban valid domain-local words such as “review” in source code or evidence.

## Visual regression matrix
At minimum capture/compare authority-defined golden surfaces available in current runtime: Project/Case Overview, Workbench/Asset Context Drawer, NCC Selection, Không gian tài liệu/M365 Return, shared loading/error/conflict states. Historical S10/S12/S13/NCCQ assets are comparison authority only where the current runtime surface exists and semantics have not been superseded.

## Final verification
Run full frontend lint/build/unit; production bundle assertion; browser acceptance; screenshot suite; exact-head CI. Verify package lock no longer resolves Astryx packages after uninstall.

## Closeout evidence
Create a dated audit recording final HEAD, changed-file inventory, residual exceptions (if any), screenshots, tests and exact-head CI. Update parent contract status to COMPLETE only after this evidence exists.

## DoD
Zero production Astryx dependency; zero legacy global routes; no dark/cyan/glass product foundation; golden surfaces accepted; exact-head CI green.
