# Valora Engineering

**Phase:** Engineering — post S13-PR-001 design authority (merged)
**Main evidence (not evergreen):** `7f7473e459f592deac1054be3935d7f911b760a2` (S13-PR-001 squash #11); main CI `29429680504` PASS
**Runtime assignment state:** **NONE**
**Next runtime candidate:** S13-PR-002 — not started; requires a separate explicit owner assignment from accepted `main`

Agents must `git fetch origin` and verify live `origin/main`.

## Product goal

Valora is a **valuation / asset-identity workbench** for non-IT business users. Primary UX language is **Vietnamese**. Official UI/components follow the **Astryx** design system. Word/Excel are input/output only — they are **not** the source of truth.

## Current status (truthful)

| Area | Status |
|---|---|
| Sprint 0–5 foundation domains | Implemented in monorepo (see module map) |
| Sprint 10–11 Live Workbench loop | Merged historically; readiness **superseded** by S12-R gates |
| S12-PR-001 / S12-PR-002 Excel staging + upload | Merged; hardened by S12-R-006 |
| **S12-R-001 … S12-R-008** | **Merged to `main`** |
| **S12-PR-003** Validation Engine | **Merged** (PR #8) |
| **S12-PR-004** Apply Command & Provenance | **Merged** (PR #10); engineering gate **closed** |
| S12 parser capability (today) | `.xlsx` only; fixed column aliases; staging + validate + Apply v1 |
| Adaptive Intake / Column Mapping Memory | **Design only** (v1.4 / ADR 0030) — not implemented |
| Asset Identity Memory / dossiers / AI matching | **Design only** (v1.4 / ADR 0031–0032) — not implemented |
| **S13-PR-001** Design authority reconciliation | **Merged** (PR #11); design-authority gate **closed** |
| Production-ready | **No** |

### Live task gate

```text
S12-PR-004 is merged and closed.
S13-PR-001 design-authority gate is closed (merged to main).
Runtime assignment state: NONE.
S13-PR-002 is the next candidate only — not started; requires separate owner assignment.
```

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
taxonomy_asset_identity/       taxonomy, canonical assets, aliases, candidates
knowledge_evidence/            evidence library, knowledge versions, quotes
workflow_workbench/            workflow + workbench session helpers
document_engine_intelligence/  document templates/render/intelligence tables
ai_governance_security/        AI task/provider governance (boundary)
excel_import/                  streaming parser + staging + Apply (S12 v1)
```

Future ownership (design only until runtime PRs): Adaptive Intake + Column Mapping Memory → `excel_import`; Raw Asset Observation / Identity Memory → `taxonomy_asset_identity`; dossier extraction/alignment → `document_engine_intelligence`.

### Non-negotiable invariants

- Tenant isolation: `organization_id` + project/session scope; **fail closed**.
- **ADR 0028** restricted Workbench fields require draft-commit + atomic audit.
- Excel **upload and validate** write **only** import batch + staging — **never** mutate official `ProjectAssetLine`.
- **Apply** (S12-PR-004 / ADR 0029 / `s12-pr-004-v1`) is the human-confirmed DRAFT-only promotion path.
- Upload lock order: **Project → batch → staging** (aligned with Apply).
- AI is advisory only; no auto-approve / auto-apply / auto knowledge activation.
- Local PostgreSQL test **skips are not PASS**.

## Authority hierarchy

Read order: `CODEX.md` → `ENGINEERING_GUARDRAILS.md` → `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md` → handoff → Design Book v1.2/v1.3/v1.4 → contracts/ADRs → S13–S16 plan.

Roadmap (active): S13 Adaptive Intake + Column Mapping Memory → S14 Asset Identity Memory → S15 paired dossiers → S16 audited AI suggestions → S17 reports → S18 auth/pilot.

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

## What this repository is not yet

- Adaptive `.xls`/`.xlsx` structure discovery and mapping-confirmation UX
- Column Mapping Memory / Asset Identity Memory runtime
- Paired Excel–Word/PDF extraction, row alignment, historical bootstrap
- End-to-end AI column/identity matching
- Production certification

## License / ownership

Engineering repository for Valora. Follow `PR_RULES.md` for every change.
