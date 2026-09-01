# PR-00 — Authority Alignment Guard Audit

**Result:** PASS

**Mode:** Ratchet-only

**Date:** 2026-09-01

**Implementation branch:** `pr-00-authority-alignment-guard`

**Starting authority tip:** `1cf50460e54ba19d2f6a9d8f933ab123e4e615d6`

**Accepted code ancestor:** `93f50f9ac81ab93e2361fffa8b71fc3bcfca57f6`

## Design authority

Read in order:

1. `docs/design/VALORA_UIUX_HANDOFF_v2.3.md`
2. `docs/design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md`
3. `VALORA_UIUX_HANDOFF_v2.3_CASE_OVERVIEW_ORCHESTRATION_BASELINE_ADDENDUM.md`
4. `VALORA_UIUX_HANDOFF_v2.3_CROSS_PRODUCT_STATE_PATTERN_BASELINE_ADDENDUM.md`
5. `VALORA_UIUX_HANDOFF_v2.3_AUDIT_LINEAGE_ENTRYPOINT_BASELINE_ADDENDUM.md`

## Scope delivered

- Added non-runtime constants for the exact 16 Global Case State stages and 17 cross-product UI
  states.
- Centralized the existing frontend Workbench route literals without changing their values or
  behavior.
- Added backend and frontend regression ratchets that prevent expansion of inventoried legacy
  QC/approval routes and commands.
- Guarded repository live-gate documents so future agents read the canonical v2.3 master, authority
  index and relevant addendum before implementation.
- Documented the known legacy conflicts without treating them as approved north-star behavior.

## Known legacy conflicts retained

- `SubmitProjectForQC`, `ApproveProject`, `RejectProject`.
- `/api/v1/workflow/approval-gates`.
- `/workbench/queue` review queue.
- `/workbench/validation` standalone validation dashboard.
- Related QC, assignment and approval terminology in the legacy Workbench UI.

The ratchet permits only the inventoried backend occurrences and the two exact legacy frontend
routes. Removal or semantic reinterpretation is deferred to a separately authorized runtime task.

## Explicitly not implemented

- no workflow runtime, enum, schema or migration change;
- no Global Case State endpoint or resume persistence;
- no NCC Selection, Microsoft 365 integration, Managed Region sync or Publishing;
- no removal, migration or rewriting of legacy workflow data;
- no GitHub push, PR creation or merge.

## Verification evidence

| Gate | Result |
|---|---|
| Backend focused design-contract tests | PASS — 4 passed |
| Frontend focused design-contract tests | PASS — 4 passed |
| Backend full CI-equivalent suite with PostgreSQL + MinIO | PASS — 1,079 passed, 0 skipped, 28 warnings |
| Worker suite | PASS — 5 passed |
| Frontend suite | PASS — 19 files, 90 tests |
| Backend Ruff | PASS |
| Worker Ruff | PASS |
| Frontend type-check/lint | PASS |
| Frontend production build | PASS — 172 modules; demonstration-data bundle guard passed |
| Alembic graph | PASS — single head `d2e3f4a5b6c7` |
| Alembic drift check | PASS — no new upgrade operations |
| Security policy/secret scan | PASS — local root `.venv` excluded to match a clean CI checkout |
| Python dependency audit | PASS — no known vulnerabilities; local project packages are not on PyPI |
| Frontend dependency audit | PASS — 0 vulnerabilities |
| Docker services | PASS — backend, PostgreSQL, Redis and MinIO healthy; frontend and worker running |

Environment-aware PostgreSQL tests used the isolated local database `valora_pr00_ci_test`. One
legacy auth-concurrency test hard-codes the local `valora` database; it ran `alembic upgrade head`,
created a uniquely named test organization and cleaned that test data afterward, without a schema
or application-data reset. An exploratory run that also set `DATABASE_URL` caused unit fixtures to
share and drop integration tables; that configuration was rejected. The final run matches CI
semantics for environment-aware tests by setting only `TEST_DATABASE_URL`.

## Local review remediation

The local review identified three non-runtime guard defects; all were corrected before PR-00
closeout:

1. `README.md` now points to the v2.3 authority and is included in the repository live-gate test.
2. The frontend contract test recursively scans production `.tsx` files for raw page-route
   literals, preventing a hard-coded route from bypassing `APP_ROUTES`.
3. Backend and frontend guards now distinguish forbidden workflow/UI surfaces from valid `NCCQ`
   terminology and concurrency-version fields.

The first remediation full-suite attempt omitted the repository virtual-environment Scripts folder
from `PATH`; one legacy auth test could not launch its `alembic` subprocess. The targeted test passed
after correcting `PATH`, and the clean full rerun then passed all 1,079 backend tests.

## Security and migration assessment

- No secrets or production credentials added.
- No authorization, tenant, mutation or audit path changed.
- No dependency added.
- No migration added or modified.
- No ADR required for this constants/tests/documentation-only ratchet.

## Scope assessment

PR-00 stayed within Authority Alignment Guard scope. The only production TypeScript edits replace
hard-coded route strings with identical constants. Product behavior and legacy runtime semantics are
unchanged.
