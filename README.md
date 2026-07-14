# Valora Engineering

**Phase:** Engineering — post S12-PR-003 Validation Engine
**S12-R-008 starting baseline (`main` at R008 open):** `c2f154dda3ba9c9dd4bdbdb8ce23676315bba1b7` (S12-PR-003 squash-merge #8) — not an evergreen “current main” claim
**Active / next task:** use the **live merge gate** below (agents must `git fetch origin` and verify `origin/main`)

## Product goal

Valora is a **valuation / asset-identity workbench** for non-IT business users. Primary UX language is **Vietnamese**. Official UI/components follow the **Astryx** design system. Word/Excel are input/output only — they are **not** the source of truth.

## Current status (truthful)

| Area | Status |
|---|---|
| Sprint 0–5 foundation domains | Implemented in monorepo (see module map) |
| Sprint 10–11 Live Workbench loop | Merged historically; readiness **superseded** by S12-R gates |
| S12-PR-001 / S12-PR-002 Excel staging + upload | Merged historically; hardened by S12-R-006 |
| **S12-R-001 … S12-R-007** | **Merged to `main`** (PRs #1–#7) |
| **S12-PR-003** Validation Engine | **Merged / complete** (PR #8; starting baseline for R008 work) |
| **S12-R-008** Apply design authority | **Live gate** — active until ADR 0029 / R008 authority is on `main` |
| S12-PR-004 Apply Command & Provenance | **Live gate** — authorized only after R008 merges |
| Production-ready | **No** — remaining gates and product scope remain |

### Live task gate (before vs after R008 merge)

```text
If origin/main does not yet contain the merged S12-R-008 / ADR 0029 authority,
S12-R-008 is the active authority task and S12-PR-004 is blocked.

If origin/main contains the merged S12-R-008 / ADR 0029 authority,
S12-R-008 is complete and S12-PR-004 is the next authorized active implementation task.
```

Agents must fetch and verify live `origin/main`. Do not claim an unknown future squash-merge SHA.

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
- **ADR 0028 restricted Workbench fields** (`description`, `appraised_unit_price`, `review_status`, `validation_status`): authenticated draft-commit command path + RBAC + human confirmation + version safety + **atomic audit**. Direct PATCH of those fields is rejected.
- **Non-restricted** official line fields (e.g. asset name, quantity, unit, raw price/currency, appraised currency, brand, manufacturer) may still be updated via direct `PATCH` under `project:update` with optimistic locking; that path is **outside** the R004 Human Commit Gate / atomic-command guarantee (audit may be append-after-commit, not the R004 single-command transaction model).
- Excel **upload and validate** write **only** import batch + staging rows — **never** mutate official `ProjectAssetLine`.
- **Apply** (S12-PR-004, after R008) is a separate human-confirmed DRAFT-only command; see ADR 0029 and contract §15.
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
cd frontend && npm audit --audit-level=high
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
| S12-R-007 | (see merge history) Documentation Reconciliation | #7 |
| S12-PR-003 | `c2f154d` Excel Staging Validation Engine | #8 |

Historical code-bearing CI for R-006 (pre-squash evidence): backend **375 passed, 0 skipped** including PostgreSQL concurrency.

## What this repository is not yet

- Production hardened end-to-end deployment certification
- S12-PR-004 Apply staging → official `ProjectAssetLine` (**authority approved; implementation not started**)
- AI runtime providers
- Full document rendering productization

## License / ownership

Engineering repository for Valora. Follow `PR_RULES.md` for every change.
