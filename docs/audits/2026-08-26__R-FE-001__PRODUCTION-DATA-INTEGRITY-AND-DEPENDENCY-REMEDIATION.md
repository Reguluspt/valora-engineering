# R-FE-001 Production Data Integrity and Dependency Remediation

**Implementation SHA:** `3b3f3d78a8bd6a851e2b7ff47895e9b9dc22bcc5`

**Classification:** Implementation PASS; repository release gate remains pending because the local Docker daemon is unavailable.

## Task

Remove production mock/fallback behavior, isolate demonstration data behind a separate build entry point with an explicit label, align the React/Astryx/StyleX peer graph, remediate the two High dependency advisories, and make CI use clean `npm ci`.

## Root cause evidence

- The production review route imported `mockReviewQueue.ts`, initialized four fabricated records, and allowed a client-side mock role selector.
- The archived local-only `assetLines.ts` additionally caught every API failure and returned fabricated PD-001 asset/appraisal data. The accepted clean baseline already propagated that error; a regression test now freezes this behavior.
- Astryx 0.1.4 requires React/React DOM 19 and StyleX `^0.18.3`, while the baseline declared React 18 and StyleX 0.19.
- The lockfile resolved vulnerable `nanoid` and `postcss` releases. CI used `--legacy-peer-deps`, hiding the invalid graph.

## Implemented scope

- Production `ReviewQueueDashboard` defaults to an empty server-data boundary and has no fixture or role-switcher import.
- Production mutations remain disabled when no authenticated role is supplied.
- Demo records and role switching live under `frontend/src/demo/` and build only through `demo.html` / `npm run build:demo`.
- Demo surfaces display `DỮ LIỆU MINH HỌA — KHÔNG PHẢI HỒ SƠ THẬT`.
- Production build runs `assert-production-bundle.mjs`, which fails if known demo markers enter `dist`.
- React/React DOM/test renderer were aligned at 19.2.8; StyleX at 0.18.3; the Astryx CLI peer `gpt-tokenizer` was satisfied.
- `nanoid` 3.3.18 and `postcss` 8.5.26 are enforced; CI now runs plain `npm ci`.
- React 19 test scheduling was corrected by wrapping state-changing test actions and cleaning session-renderer roots between tests.

## Design sources

- Design Book v1.3 Vietnamese-first/Astryx/error-masking rules.
- Design Book v1.4 human-review and no-fabricated-authority rules.
- `ENGINEERING_GUARDRAILS.md` fail-closed tenant/security and truthful evidence semantics.
- Local remediation design Decision D-006 and R-FE-001 contract.

## Verification on implementation tree

```text
npm ci                              PASS; 176 packages installed; 0 vulnerabilities
npm ls --all --depth=1              PASS; required peers resolved (platform/tool peers remain optional)
npm run lint                        PASS
npm test                            PASS; 18 files, 86 tests
npm run build                       PASS; 171 modules; production demo-marker assertion PASS
npm run build:demo                  PASS; 35 modules
npm audit --audit-level=high        PASS; 0 vulnerabilities
git diff --check                    PASS before commit
```

The focused production regression test covers API failures `401`, `403`, `404`, and `500` and verifies they propagate without substituted asset data.

## Known limitation

`docker version` could not connect to `dockerDesktopLinuxEngine`. The frontend Dockerfile uses the now-verified plain `npm ci`, but an actual image build is not claimed until the daemon is available.

## Scope and security

- No backend, database, credential, production data, or deployment change.
- No production fixture import remains in the review route.
- Frontend role visibility is not represented as server authorization.
- No push, PR, merge, or deployment performed.
- ADR needed: **No**. This remediation restores existing Design Book contracts and adds no domain behavior.
