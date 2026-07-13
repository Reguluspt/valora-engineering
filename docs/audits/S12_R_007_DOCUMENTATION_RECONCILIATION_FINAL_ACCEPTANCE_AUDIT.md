# S12-R-007 — Documentation Reconciliation & Final Acceptance Audit

## Status
```text
S12-R-007 DRAFT PR CI VALIDATED — AWAITING FINAL DOCUMENTATION-HEAD CI AND INDEPENDENT AUDIT
```

| Field | Value |
|---|---|
| Task | S12-R-007 |
| Purpose | Reconcile authoritative docs with post S12-R-001…006 main reality; publish acceptance matrix |
| Scope | Documentation / audit only |
| Out of scope | Production code, tests, migrations, workflows, config, deps, S12-PR-003 implementation |
| Starting `main` SHA | `54872c764399182efae496e89dae9bd6ebdba9af` |
| Branch | `s12-r-007-documentation-reconciliation-final-acceptance` |
| Draft PR | **#7** — https://github.com/Reguluspt/valora-engineering/pull/7 |
| PR base / head | `main` ← `s12-r-007-documentation-reconciliation-final-acceptance` |
| PR state | **open + draft=true** |
| Code-bearing SHA tested | `4d683b184c7bb7456bfdbbdaa0ab1cbb2c7e4c9e` |
| Authoritative code-bearing CI | run **29254007448** (#94) **SUCCESS** |
| Code-bearing CI URL | https://github.com/Reguluspt/valora-engineering/actions/runs/29254007448 |
| Documentation-head CI | **PENDING** for the audit-evidence commit that records this section |
| Independent audit | **PENDING** |

## Authority inventory (read)

| Document | Role |
|---|---|
| `CODEX.md` | Agent rules (updated) |
| `ENGINEERING_GUARDRAILS.md` | Permanent invariants (updated) |
| `PR_RULES.md` | PR process — **intentionally unchanged** |
| `README.md` | Repo entrypoint (updated) |
| `docs/remediation/S12_R_PRE_VALIDATION_REMEDIATION_SLICE.md` | Canonical S12-R slice (reconciled §12) |
| `docs/design/*` + `docs/adr/*` | Design/ADR authority |
| `docs/audits/S11_PR_007_*` | Historical S11 (addendum) |
| `docs/audits/S12_PR_001_*` / `S12_PR_002_*` | Historical Excel PRs (addenda) |
| `docs/audits/S12_R_001…006_*` | Remediation task audits (read) |
| `docs/VALORA_PROJECT_HANDOFF.md` | Canonical handoff (created) |

Protected untracked file **not read / not modified**:  
`docs/remediation/S12_R_004_ONBOARDING_REPORT_2026_07_12.md`

## Changed-file allowlist

### Commit A (documentation reconciliation)
```text
README.md
CODEX.md
ENGINEERING_GUARDRAILS.md
docs/VALORA_PROJECT_HANDOFF.md
docs/remediation/S12_R_PRE_VALIDATION_REMEDIATION_SLICE.md
docs/audits/S11_PR_007_SPRINT_11_FINAL_ACCEPTANCE_AUDIT.md
docs/audits/S12_PR_001_EXCEL_IMPORT_CONTRACT_STAGING_MODEL_AUDIT.md
docs/audits/S12_PR_002_EXCEL_FILE_UPLOAD_PARSER_INTAKE_AUDIT.md
```

### Commit B (pre-PR audit)
```text
docs/audits/S12_R_007_DOCUMENTATION_RECONCILIATION_FINAL_ACCEPTANCE_AUDIT.md
```

### Commit C (this CI-evidence update)
```text
docs/audits/S12_R_007_DOCUMENTATION_RECONCILIATION_FINAL_ACCEPTANCE_AUDIT.md
```

`PR_RULES.md`: **intentionally unchanged**.

## Stale-claim inventory and disposition

| Claim | Location | Disposition |
|---|---|---|
| Repo is Sprint 0 starter / foundation only | README (was) | **stale → corrected** to current phase |
| Active phase Sprint 0 | CODEX / GUARDRAILS (was) | **stale → corrected**; Sprint 0 labeled historical |
| S11 READY as current approval | S11 audit | **historical retained + addendum** re-scope |
| S12-PR-001 raw/auth/CI incomplete picture | S12-PR-001 audit | **historical + addendum** |
| S12-PR-002 X-User-Id, file:///, inline parser, old counts | S12-PR-002 audit | **historical + addendum** |
| Sprint 0 in module README / docs/01_* | various | **historical and clearly labeled** (not current authority) |
| `X-User-Id` in tests/scanner | code | **current and correct** (deny/spoof detection / fixtures) |
| `hd-98-gia-lai` in S11 | historical example | **historical** slug example |
| Local PG skips | local pytest | **current and correct** as local-only; not PASS |

## Final acceptance matrix

Mirrored from remediation §12.3 (20 rows):

| # | Area | Disposition | Source | Evidence | Limitation |
|---|---|---|---|---|---|
| 1 | default/CI baseline | FIXED | R-001 #1 | CI | admin protection ops |
| 2 | authentication | FIXED | R-002 #2 | auth tests | test overrides |
| 3 | tenant isolation | FIXED | R-003 #3 | tenant tests | 404 enumeration safety |
| 4 | official mutation command | FIXED | R-004 #4 | mutation tests | allowlist fields |
| 5 | human confirmation | FIXED | R-004/S11-006 | API+UI | copy may evolve |
| 6 | version safety | FIXED | R-004 | version tests | client must send version |
| 7 | atomic audit | FIXED | R-004 | txn tests | payload schema |
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
| 18 | PostgreSQL concurrency | FIXED | R-006 + R007 CI | PG test in CI (0 skips) | local skip without PG |
| 19 | ProjectAssetLine immutability | FIXED | R-006 | immutability tests | apply deferred |
| 20 | documentation consistency | ACCEPTED WITH process | R-007 | recon + Draft PR CI | needs documentation-head CI + independent audit |

**Totals:** FIXED **19** · ACCEPTED WITH process **1** · DEFERRED Validation Engine / apply / AI / prod cert · BLOCKED process gates for overall S12-R PASS until independent audit.

## Static scan summary

| Pattern | Current-authority docs | Notes |
|---|---|---|
| Sprint 0 | labeled historical only | corrected in README/CODEX/GUARDRAILS |
| file:/// | 0 in current authority set | remain in historical audits (labeled by addenda) |
| X-User-Id | deny-spoof / historical remediation text | correct |
| list(iter_rows / bare .read() | blocked by security scanner on Excel path | current correct |
| PASS/READY in old audits | retained historical + addenda | not current slice READY |

## Local gate raw evidence (R007 docs-only baseline)

### Backend
| Gate | Result |
|---|---|
| ruff | All checks passed |
| pytest | **370 passed, 5 skipped, 20 warnings** |
| check_security.py | Scan passed |
| alembic heads | `db5977424e7b (head)` |

### Worker
| Gate | Result |
|---|---|
| ruff | All checks passed |
| pytest | **1 passed** |

### Frontend
| Gate | Result |
|---|---|
| lint | PASS |
| build | PASS |
| vitest | **15 files / 80 tests passed** |
| npm audit --omit=dev | **0 vulnerabilities** |

### Exact local skips (NOT PASS)
```text
SKIPPED LOCALLY — REQUIRES CI WITH POSTGRESQL
tests/test_auth_endpoints.py:737
tests/test_s12_r_004_official_mutation.py:1049
tests/test_s12_r_006_excel_intake_hardening.py::TestPGIsolatedConcurrencyRestored::test_concurrent_upload_serialization
tests/test_workbench_api.py:696
tests/test_workbench_api.py:980
```

## Draft PR and code-bearing CI evidence (2026-07-13)

| Item | Value |
|---|---|
| Draft PR | https://github.com/Reguluspt/valora-engineering/pull/7 |
| Base | `main` |
| Head | `s12-r-007-documentation-reconciliation-final-acceptance` |
| Draft | **true** (not Ready, not merged) |
| Tested SHA | `4d683b184c7bb7456bfdbbdaa0ab1cbb2c7e4c9e` (Commit B) |
| Authoritative workflow run | **29254007448** / run number **94** |
| Run URL | https://github.com/Reguluspt/valora-engineering/actions/runs/29254007448 |
| Overall conclusion | **SUCCESS** |
| Job backend | **SUCCESS** |
| Job worker | **SUCCESS** |
| Job frontend | **SUCCESS** |

### Backend job (authoritative logs)
| Gate | Result |
|---|---|
| Ruff | All checks passed |
| Alembic upgrade head | PASS against PostgreSQL to `db5977424e7b` |
| Alembic single head | PASS |
| Pytest | **375 passed, 0 skipped, 27 warnings** (`collected 375 items`) |
| pip-audit | No known vulnerabilities found |
| Security scanner | Scan passed |

PostgreSQL skips in CI: **0**. The five former local-skip tests **executed** (suite finished with zero skips).

Log confirmation of concurrency node:
```text
tests/test_s12_r_006_excel_intake_hardening.py::TestPGIsolatedConcurrencyRestored::test_concurrent_upload_serialization
```

### Worker job
| Gate | Result |
|---|---|
| Ruff | All checks passed |
| Pytest | **1 passed** |
| Dependency audit | No known vulnerabilities found |

### Frontend job
| Gate | Result |
|---|---|
| Lint / build | PASS (job success) |
| Vitest | **15 files / 80 tests passed** |
| npm audit | **0 vulnerabilities** |

### Non-authoritative / duplicate run
| Run | Result | Classification |
|---|---|---|
| **29253478077** (#93) | **failure** | Non-authoritative. Backend SUCCESS, worker SUCCESS, frontend FAILED with GitHub Actions infra error: `Failed to resolve action download info. Error: Service Unavailable`. Transient platform failure, not product failure. Superseded by **29254007448**. |

### Local vs code-bearing CI distinction
| Environment | Backend pytest |
|---|---|
| Local (no PG) | 370 passed, **5 skipped**, 20 warnings |
| Code-bearing CI (PG 16) on `4d683b1…` | **375 passed, 0 skipped**, 27 warnings |

## Historical R-006 CI evidence (baseline, separate from this PR)

| Item | Value |
|---|---|
| Nature | Historical code-bearing CI for R-006 before squash-merge to main |
| Backend | **375 passed, 0 skipped, 27 warnings** |
| Main squash merge | `54872c764399182efae496e89dae9bd6ebdba9af` (#6) |

R007 now has **its own** Draft PR CI on documentation head `4d683b1…`.

## Limitations

1. Code-bearing Draft PR CI validated on SHA `4d683b1…` via run `29254007448`.
2. Documentation-head CI for **this** audit-evidence commit is not claimed until that run completes.
3. Independent audit PENDING — implementer must not self-declare independent PASS.
4. Overall S12-R slice not declared final PASS.
5. S12-PR-003 not started.
6. Local PG skips remain expected without PostgreSQL service.
7. PR remains Draft only.

## Commit lineage

```text
main 54872c7 (S12-R-006 #6)
  └─ branch s12-r-007-documentation-reconciliation-final-acceptance
       ├─ Commit A b05906b: docs: reconcile Valora phase and remediation records
       ├─ Commit B 4d683b1: docs: add S12-R-007 pre-PR final acceptance evidence
       └─ Commit C (this): docs: record S12-R-007 Draft PR CI evidence
```

## Final verdict
```text
S12-R-007 DRAFT PR CI VALIDATED — AWAITING FINAL DOCUMENTATION-HEAD CI AND INDEPENDENT AUDIT
```
