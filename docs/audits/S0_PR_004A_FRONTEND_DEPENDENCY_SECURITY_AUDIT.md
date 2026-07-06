# S0-PR-004A Frontend Dependency Security Audit

**Task ID:** S0-PR-004A  
**Task name:** Frontend Dependency Security Review  
**Audit date:** 2026-07-06  
**Sprint:** Sprint 0  
**Final result:** PASS WITH FIXES

## Files Checked

Required Sprint 0 rules and prior audit:

- `CODEX.md`
- `ENGINEERING_GUARDRAILS.md`
- `PR_RULES.md`
- `.gitignore`
- `docs/01_SPRINT_0_PLAN.md`
- `docs/03_DEFINITION_OF_DONE.md`
- `docs/audits/S0_PR_004_FRONTEND_FOUNDATION_AUDIT.md`

Frontend dependency files:

- `frontend/package.json`
- `frontend/package-lock.json`

## Dependency State Reviewed

Current resolved frontend dependency path:

```text
vite@5.4.21
esbuild@0.21.5
@vitejs/plugin-react@4.7.0 -> vite@5.4.21
```

## Audit Result

`npm audit --json` result: FAIL.

Findings:

- `esbuild <=0.24.2`
  - Severity: moderate.
  - Advisory: `GHSA-67mh-4wv8-2f99`.
  - Current resolved version: `0.21.5`.
  - npm fix available through `vite@8.1.3`.
  - npm marks the fix as semver-major.
- `vite`
  - Severity reported by npm: high.
  - Current resolved version: `5.4.21`.
  - npm reports vulnerable Vite advisories affecting the current resolved Vite line.
  - npm fix available through `vite@8.1.3`.
  - npm marks the fix as semver-major.

`npm audit fix --dry-run --json` result: FAIL.

Dry-run decision:

- npm reported no non-breaking package changes.
- npm reported the available fix as `vite@8.1.3`.
- npm marked the fix as `isSemVerMajor: true`.

## Changes Made

No dependency updates were applied.

Reason:

- The available npm fix requires a semver-major Vite upgrade from Vite 5 to Vite 8.
- Applying a major Vite upgrade would exceed this review's safe non-breaking update boundary.
- Adding package overrides for `esbuild` was not applied because npm still reports direct Vite advisories on the current Vite line and an override would be an unproven dependency override, not npm's recommended safe fix.

Only this audit report was added.

## Checks Run

- `npm audit --json`
  - Result: FAIL.
  - Reason: Vite/esbuild advisories remain.
- `npm audit fix --dry-run --json`
  - Result: FAIL.
  - Reason: npm's available fix is semver-major `vite@8.1.3`.
- `npm list vite esbuild --depth=1`
  - Result: PASS.
  - Confirmed current resolved dependency path.
- `npm run build`
  - Result: PASS.
  - Output summary: Vite production build completed successfully.
- `npm run lint`
  - Result: PASS.
  - Output summary: `tsc --noEmit` completed without errors.

## Sprint 0 Scope Compliance

PASS.

Frontend remains a Sprint 0 shell only. This task did not change UI behavior, add routing, add auth, call backend APIs, add UI libraries, modify backend or worker code, or implement business/domain UI.

## Recommendation

Open a dedicated dependency upgrade task to evaluate Vite 8 migration intentionally. That task should:

- Review Vite 5 -> Vite 8 migration notes.
- Confirm Node runtime compatibility with Vite 8.
- Update `vite` and compatible `@vitejs/plugin-react` together.
- Run `npm audit`, `npm run build`, and `npm run lint`.
- Verify the Sprint 0 shell behavior remains unchanged.

## Final Result

PASS WITH FIXES.

The dependency/security decision is documented, build and lint pass, and no business/domain code was added. The remaining fix is a deliberate semver-major Vite upgrade task, not a blind audit fix.
