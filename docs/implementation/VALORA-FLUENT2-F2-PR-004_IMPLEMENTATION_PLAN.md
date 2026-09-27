# F2-PR-004 — Case Overview & Project List Golden Remediation

**Status:** MERGED ON INTEGRATION — PR #40 / `54cf769c89cc4f7601e8ffb89e25f925f6500483`
**Browser acceptance:** PASS — [evidence](evidence/F2-PR-004/BROWSER_ACCEPTANCE.md)
**Exact-head integration CI:** #461 — SUCCESS
**Depends on:** F2-PR-003
**Authority:** Orchestration Hub Iteration 2 + current shell authority

## File manifest
**MODIFY:** Case Overview TSX/CSS/tests; Project List TSX/CSS/tests.
**CREATE:** visual/browser fixture or screenshot spec using the repository's accepted browser-test mechanism; do not invent a second product router.

## Case Overview
Preserve server-ordered 16 stages, blocker/warning/stale separation, server-derived next action and current tests. Replace dark local variables/hard-coded colors with semantic tokens. Implement approved structure: project header; case-state summary; mandatory-stage progress; blocking/warning/stale sections; right rail Next Action / Resume context / recent activity when data exists. Do not invent missing backend facts; unavailable sections render authority-compliant unavailable/empty state rather than fabricated data.

Exactly one primary next-action CTA when projection supplies a valid route. No approval dashboard semantics.

## Project List
Migrate list/table-like entry surface to Fluent light/dense enterprise presentation. Preserve live project fetch and Overview/document navigation. Use `Không gian tài liệu`; no OneDrive parent-domain label. Do not expose technical row version as a prominent product status unless current authority requires it; if retained for diagnostics, make it secondary.

## CSS
Remove page-local dark canvas and cyan hard-coded values. Consume F2 semantic tokens/shared primitives. Responsive behavior may remain but desktop baseline is primary.

## Verification
Existing CaseOverview tests must remain green: 16 ordered stages, one mapped primary action, blocker/warning/stale behavior. Update ProjectList label test. Add screenshot acceptance for normal, blocker/stale and loading/error representative states when fixtures exist.

## DoD
No dark/cyan page foundation; no invented workflow state; current orchestration behavior preserved; browser/screenshot evidence attached.
