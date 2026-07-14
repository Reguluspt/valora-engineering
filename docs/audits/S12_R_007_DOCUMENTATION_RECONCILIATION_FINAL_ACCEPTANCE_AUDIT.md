# S12-R-007 — Documentation Reconciliation & Final Acceptance Audit

## Status
```text
S12-R-007 CORRECTIVE DOCUMENTATION PASS COMPLETE - AWAITING FINAL AUDIT-HEAD CI AND INDEPENDENT RE-AUDIT
```

| Field | Value |
|---|---|
| Task | S12-R-007 |
| Purpose | Reconcile authority docs after S12-R-001…006; truthful acceptance matrix; corrective pass after independent audit FAIL |
| Scope | Documentation / audit only |
| Out of scope | Production code/tests/workflows/config/deps; S12-PR-003 implementation |
| Starting `main` SHA | `54872c764399182efae496e89dae9bd6ebdba9af` |
| Branch | `s12-r-007-documentation-reconciliation-final-acceptance` |
| Draft PR | **#7** — https://github.com/Reguluspt/valora-engineering/pull/7 (open, draft=true) |
| Independent audit | **FAIL** (requires corrective pass) — re-audit **PENDING** |
| Commit D | `1c9430a401bce9794c83f3e96c12b80917cefa50` |
| Commit E | this audit-evidence commit |

## Independent audit FAIL findings and corrective resolution

| ID | Severity | Finding | Resolution in corrective pass |
|---|---|---|---|
| B-01 | BLOCKER | Official-mutation authority overstated as universal for every `ProjectAssetLine` field | Scoped to ADR 0028 restricted fields only; documented non-restricted direct PATCH under `project:update` |
| M-01 | MAJOR | Matrix disposition invalid (`ACCEPTED WITH process` / unsupported) | Matrix uses only allowed dispositions; row 20 = **BLOCKED**; totals FIXED 19 / ACCEPTED WITH ADR 0 / BLOCKED 1 |
| M-02 | MAJOR | PR #7 body incomplete/stale vs PR_RULES | PR body updated with required metadata, full file list, limitations, ADR needed = NO |
| N-01 | MINOR | Trailing whitespace in authority docs | Stripped; `git diff --check` clean on Commit D paths; this audit written without trailing spaces |
| N-02 | MINOR | CI SHA attribution conflated branch head vs PR merge checkout | Full SHAs recorded separately below for #94/#95/#96 and Commit D runs |
| N-03 | MINOR | Local npm audit used `--omit=dev` weaker than CI | Operator guidance uses `npm audit --audit-level=high`; corrective local result recorded |

Implementer does **not** declare independent re-audit PASS.

## Official mutation authority (ADR 0028)

Restricted Workbench-gated fields (Human Commit Gate + draft-commit command + atomic audit):

```text
description
appraised_unit_price
review_status
validation_status
```

Direct PATCH of those fields is rejected (400).

Non-restricted fields may still be updated via direct `PATCH` under `project:update` with optimistic locking (examples: asset_name, quantity, unit_id, raw_price, currencies, brand_id, manufacturer_id). That path is **outside** the R004 Human Commit Gate and R004 single-command atomic-audit model.

Excel intake never mutates official `ProjectAssetLine` (staging only).

## Final acceptance matrix (corrective)

| # | Area | Disposition | Source | Evidence | Limitation |
|---|---|---|---|---|---|
| 1 | default/CI baseline | FIXED | R-001 #1 | CI | admin protection ops |
| 2 | authentication | FIXED | R-002 #2 | auth tests | test overrides |
| 3 | tenant isolation | FIXED | R-003 #3 | tenant tests | 404 enumeration safety |
| 4 | official mutation command (ADR 0028 restricted fields) | FIXED | R-004 + ADR 0028 | command + forbidden PATCH tests | Non-restricted direct PATCH remains |
| 5 | human confirmation (restricted fields) | FIXED | R-004 / S11-006 | API+UI gates | Four restricted fields only |
| 6 | version safety | FIXED | R-004 | optimistic lock tests | Also used on direct PATCH |
| 7 | atomic audit (restricted commit path) | FIXED | R-004 | same-txn audit tests | Non-restricted PATCH ≠ R004 atomic model |
| 8 | dynamic project context | FIXED | R-005 #5 | FE resolve tests | — |
| 9 | fabricated-data removal | FIXED | R-005 | integrity tests | panel depth limits |
| 10 | pagination/race safety | FIXED | R-005 | pagination tests | perf SLO deferred |
| 11 | Vietnamese UX | FIXED | S10/S11 | i18n tests | coverage ongoing |
| 12 | Astryx compliance | FIXED | S10 | shell/mapping | design review ongoing |
| 13 | Excel bounded streaming | FIXED | R-006 #6 | parser+scanner | SQLite savepoint recipe local |
| 14 | ZIP/XLSX security | FIXED | R-006 | zip tests | threat model expand |
| 15 | resource limits | FIXED | R-006 | limit tests | versioned policy |
| 16 | positional raw values | FIXED | R-006 | raw tests | contract authority |
| 17 | failure preservation | FIXED | R-006 | fault tests | — |
| 18 | PostgreSQL concurrency | FIXED | R-006 + R007 CI | PG CI 0 skips | local skip without PG |
| 19 | ProjectAssetLine immutability (intake) | FIXED | R-006 | immutability tests | apply deferred |
| 20 | documentation consistency / R007 final acceptance | **BLOCKED** | R-007 | corrective docs + CI | Independent re-audit required |

**Totals:** FIXED **19** · ACCEPTED WITH ADR **0** · BLOCKED **1**

Deferred roadmap (outside the 20-row matrix): S12-PR-003 Validation Engine; apply staging→official; AI runtime; production certification.

## Commit lineage

```text
main 54872c7 (S12-R-006 #6)
  └─ s12-r-007-documentation-reconciliation-final-acceptance
       ├─ A b05906b docs: reconcile Valora phase and remediation records
       ├─ B 4d683b1 docs: add S12-R-007 pre-PR final acceptance evidence
       ├─ C 60e9c98 docs: record S12-R-007 Draft PR CI evidence
       ├─ D 1c9430a docs: correct S12-R-007 authority and acceptance matrix
       └─ E (this) docs: record S12-R-007 corrective pass evidence
```

### Commit D changed files (exactly five)
```text
README.md
CODEX.md
ENGINEERING_GUARDRAILS.md
docs/VALORA_PROJECT_HANDOFF.md
docs/remediation/S12_R_PRE_VALIDATION_REMEDIATION_SLICE.md
```

### Commit E changed files (exactly one)
```text
docs/audits/S12_R_007_DOCUMENTATION_RECONCILIATION_FINAL_ACCEPTANCE_AUDIT.md
```

## Local gates (corrective pass, raw)

| Gate | Result |
|---|---|
| Backend ruff | All checks passed |
| Backend pytest | **370 passed, 5 skipped, 20 warnings** |
| Security scanner | Scan passed |
| Alembic heads | `db5977424e7b (head)` |
| Worker ruff | All checks passed |
| Worker pytest | **1 passed** |
| Frontend lint | PASS |
| Frontend build | PASS |
| Frontend vitest | **15 files / 80 tests passed** |
| `npm audit --audit-level=high` | **found 0 vulnerabilities** |
| `git diff --check` on Commit D paths | clean (authority five-file set) |

### Exact local skips (SKIPPED, not PASS)
```text
tests/test_auth_endpoints.py:737
tests/test_s12_r_004_official_mutation.py:1049
tests/test_s12_r_006_excel_intake_hardening.py::TestPGIsolatedConcurrencyRestored::test_concurrent_upload_serialization
tests/test_workbench_api.py:696
tests/test_workbench_api.py:980
```

Historical note: earlier local evidence used `npm audit --omit=dev` (weaker). Current operator guidance and corrective measurement use `--audit-level=high`.

## CI evidence with branch head vs checkout SHA

### Historical code-bearing / doc-head (pre-corrective)

| Run | Event | Branch-head SHA | Actual checkout/tested SHA | Backend | Jobs |
|---|---|---|---|---|---|
| **29254007448** (#94) | `pull_request` | `4d683b184c7bb7456bfdbbdaa0ab1cbb2c7e4c9e` | `31576f7acc2e2492b1b10b5be76a7a5cb03dbf20` (Merge head into `54872c7…`) | 375 passed, 0 skipped, 27 warnings | backend/worker/frontend SUCCESS |
| **29254276646** (#95) | `push` | `60e9c980d331664633f1c62cb306835754861857` | same branch head (direct push checkout) | 375 / 0 skip / 27 warn | all SUCCESS |
| **29254279730** (#96) | `pull_request` | `60e9c980d331664633f1c62cb306835754861857` | `ad5a718ef7a85d71f9c20877257a5cad80b38f90` (Merge head into `54872c7…`) | 375 / 0 skip / 27 warn | all SUCCESS |

Non-authoritative: **29253478077** (#93) frontend failed with Actions `Service Unavailable` (infra transient).

A PR merge-ref run is **not** a direct test of the branch-head commit object alone; it tests the merge commit.

### Commit D corrective-head CI

| Run | URL | Event | Branch-head SHA | Checkout/tested SHA | Jobs | Backend |
|---|---|---|---|---|---|---|
| **29257459535** (#97) | https://github.com/Reguluspt/valora-engineering/actions/runs/29257459535 | `push` | `1c9430a401bce9794c83f3e96c12b80917cefa50` | branch head (push) | all SUCCESS | 375 passed, 0 skipped, 27 warnings |
| **29257465125** (#98) | https://github.com/Reguluspt/valora-engineering/actions/runs/29257465125 | `pull_request` | `1c9430a401bce9794c83f3e96c12b80917cefa50` | `3cd8a20c9d645aa5300310d92a8983a559396c15` (Merge into `54872c7…`) | all SUCCESS | 375 passed, 0 skipped, 27 warnings |

PostgreSQL skips in CI: **0**. Formerly local-skipped tests executed.

Ruff, Alembic upgrade + single head, security scanner, pip-audit, frontend lint/build/vitest, npm audit: green on successful jobs.

### Commit E / final audit-head CI

**PENDING at time of writing this file** — will be reported externally after push; no further commit to close the evidence loop.

## Limitations

1. Matrix row 20 remains **BLOCKED** until independent re-audit.
2. S12-PR-003 not started.
3. No production behavior changes in R007.
4. Non-restricted direct PATCH remains outside R004 Human Commit Gate (future ADR if product wants universal command coverage).
5. Local PostgreSQL skips remain expected without PG service.
6. PR #7 stays Draft until independent re-audit PASS and process owner decides Ready.

## Final verdict
```text
S12-R-007 CORRECTIVE DOCUMENTATION PASS COMPLETE - AWAITING FINAL AUDIT-HEAD CI AND INDEPENDENT RE-AUDIT
```

---

## Post-merge addendum (S12-R-008, 2026-07-14)

**Label:** Historical R007 audit evidence above is unchanged.

| Field | Value |
| --- | --- |
| S12-R-007 | Completed historically (documentation reconciliation); merged prior to S12-PR-003 |
| S12-PR-003 | **Merged** to `main` (PR #8) — statements above that PR-003 is “not started” are **historical** |
| Current authority task | **S12-R-008** (Apply design authority; docs only) |
| Next implementation | **S12-PR-004** after S12-R-008 merges |
