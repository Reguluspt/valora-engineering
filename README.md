# Valora Engineering

**Phase:** Engineering — post S12-R remediation  
**Baseline `main`:** `54872c764399182efae496e89dae9bd6ebdba9af` (S12-R-006 squash-merge #6)  
**Active task:** `S12-R-007` — Documentation Reconciliation & Final Acceptance  
**Next approved task (not started):** `S12-PR-003` — Excel Staging Validation Engine  

## Product goal

Valora is a **valuation / asset-identity workbench** for non-IT business users. Primary UX language is **Vietnamese**. Official UI/components follow the **Astryx** design system. Word/Excel are input/output only — they are **not** the source of truth.

## Current status (truthful)

| Area | Status |
|---|---|
| Sprint 0–5 foundation domains | Implemented in monorepo (see module map) |
| Sprint 10–11 Live Workbench loop | Merged historically; readiness **superseded** by S12-R gates |
| S12-PR-001 / S12-PR-002 Excel staging + upload | Merged historically; hardened by S12-R-006 |
| **S12-R-001 … S12-R-006** | **Merged to `main`** (PRs #1–#6) |
| **S12-R-007** | **In progress** — documentation reconciliation only |
| S12-PR-003 Validation Engine | **Blocked** until S12-R slice (incl. R007) reaches independent acceptance |
| Production-ready | **No** — remaining gates and product scope remain |

S12-R is a **blocking remediation** before any Validation Engine work.

## Architecture (monorepo)

```text
backend/     FastAPI + SQLAlchemy + Alembic (Python ≥3.12)
frontend/    React 18 + TypeScript + Vite + Astryx
worker/      Python worker skeleton
infra/       Local infra notes
docs/        ADR, design contracts, audits, remediation, handoff
.github/     CI workflows
```

### Bounded contexts (`backend/app/modules/`)

```text
project_master_data/           org, identity, master data, project, models hub
taxonomy_asset_identity/
knowledge_evidence/
workflow_workbench/
document_engine_intelligence/
ai_governance_security/
excel_import/                  streaming parser + atomic staging replacement
```

### Non-negotiable invariants

- Tenant isolation: `organization_id` + project/session scope; **fail closed**.
- Official mutation: authenticated command path + RBAC + human confirmation + version safety + **atomic audit**.
- Excel intake writes **only** import batch + staging rows — **never** mutates official `ProjectAssetLine`.
- Parser: bounded/chunked streaming, secure ZIP/XLSX validation, explicit limits, positional `raw_values.cells`.
- Staging replacement: nested savepoint + outer commit; failure preserves prior generation; fingerprint guard against stale failure overwrite.
- AI is advisory only; no auto-approve / auto-apply.
- Local PostgreSQL test **skips are not PASS** — only CI with PostgreSQL proves PG behavior.

## Authority hierarchy

Read in this order before implementing:

1. `CODEX.md` — agent operating rules (current task)
2. `ENGINEERING_GUARDRAILS.md` — permanent engineering invariants
3. `PR_RULES.md` — PR shape and description requirements
4. `docs/VALORA_PROJECT_HANDOFF.md` — canonical project handoff
5. `docs/remediation/S12_R_PRE_VALIDATION_REMEDIATION_SLICE.md` — S12-R slice
6. Design contracts under `docs/design/`
7. ADRs under `docs/adr/`
8. Per-task audits under `docs/audits/` (historical unless labeled current)

Design Book authority: **v1.2-final** foundation with **v1.3 MVP completion addendum** and design contracts for Workbench/Excel/i18n.

## Local setup

```bash
cp .env.example .env
docker compose up -d          # postgres, redis, minio
make backend-dev              # uvicorn :8000
make frontend-dev             # vite
```

### Verified local commands

```bash
# Backend
cd backend && python -m ruff check app tests
cd backend && python -m pytest -q
cd backend && python tests/check_security.py
cd backend && python -m alembic heads

# Worker
cd worker && python -m ruff check worker tests
cd worker && python -m pytest -q

# Frontend
cd frontend && npm run lint
cd frontend && npm run build
cd frontend && npm test
cd frontend && npm audit --omit=dev
```

Local backend runs without PostgreSQL will **skip** PG-gated tests. That is not CI evidence.

## S12-R merge map (on `main`)

| Task | Merge commit (subject) | PR |
|---|---|---|
| S12-R-001 | `6c64305` Repository Baseline & CI Gate Repair | #1 |
| S12-R-002 | `b025b97` Authentication Identity Boundary Hardening | #2 |
| S12-R-003 | `c46ea1c` Workbench project and session tenant scoping | #3 |
| S12-R-004 | `e683757` Official mutation command atomic audit gate | #4 |
| S12-R-005 | `ff40fda` Dynamic project context live data integrity | #5 |
| S12-R-006 | `54872c7` Excel Intake Streaming & Transaction Hardening | #6 |

Historical code-bearing CI for R-006 (pre-squash evidence): backend **375 passed, 0 skipped** including PostgreSQL concurrency.

## What this repository is not yet

- Production hardened end-to-end deployment certification
- Excel Staging Validation Engine (S12-PR-003)
- Apply staging → official `ProjectAssetLine`
- AI runtime providers
- Full document rendering productization

## License / ownership

Engineering repository for Valora. Follow `PR_RULES.md` for every change.
