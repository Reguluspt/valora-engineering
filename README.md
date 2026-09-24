# Valora Engineering

**Phase:** Engineering — VALORA UI/UX v2.3 implementation alignment
**Accepted code baseline (not evergreen):** `27d1cc630f97cb9b56fbfbb4c5bc04d4be305cc6` (PR #31)
**Current roadmap:** `docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md`<br>
**AI architecture detail:** `docs/architecture/VALORA_AI_MASTER_PLAN_V1.md` — OS-G7 documentation authority only; runtime AI remains gated
**Canonical UI/UX authority:** `docs/design/VALORA_UIUX_HANDOFF_v2.3.md` + `docs/design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md`
**Documentation status map:** `docs/DOCUMENTATION_STATUS_INDEX.md`
**PR-00 through PR-04:** **MERGED by PR #29**
**PR-05 and PR-06:** **MERGED by PR #30 and PR #31; backend/provider slices only**
**PR-00 alignment gate:** **CLOSED**
**PR-01 / PR-02 / PR-03 / PR-04 implementation contracts:** **ACCEPTED**
**PR-01 schema scope:** no projection migration; durable downstream facts keep their owning migrations.
**Current execution direction:** **OS-G0 authority + Fluent 2 light visual-system reconciliation, then OS-G1 Pre-case Product Closure per Unified Roadmap v2.3**

Agents must `git fetch origin` and verify live `origin/main`.

## Product goal

Valora is a **valuation / asset-identity workbench** for non-IT business users. Primary UX language is **Vietnamese**. Current product visual authority is **Microsoft Fluent 2 light**, desktop-first and data-heavy/table-first. Word/Excel are input/output only — they are **not** the source of truth.

## Current status (truthful)

| Area | Status |
|---|---|
| Sprint 0–5 foundation domains | Implemented in monorepo (see module map) |
| Sprint 10–11 Live Workbench loop | Merged historically; readiness **superseded** by S12-R gates |
| S12-PR-001 / S12-PR-002 Excel staging + upload | Merged; hardened by S12-R-006 |
| **S12-R-001 … S12-R-008** | **Merged to `main`** |
| **S12-PR-003** Validation Engine | **Merged** (PR #8) |
| **S12-PR-004** Apply Command & Provenance | **Merged** (PR #10); engineering gate **closed** |
| S12 parser capability | `.xlsx` fixed-alias staging + validate + Apply v1 remains frozen |
| **S13-PR-002** Legacy Workbook Adapter / Source Artifact | **Merged** (PR #15) at `137f8c5…` |
| **S13-PR-003** Structure Discovery / Row Classification | **Merged** (PR #17) at `2af7535…` |
| Adaptive Intake / Column Mapping Memory | Implemented historical foundation; current product work follows Unified Roadmap `OS-G0 → OS-G7` |
| Asset Identity Memory / dossiers / AI matching | Identity-decision/feedback and dossier extraction/alignment foundations are implemented; provider-backed AI matching and the full OS-G7 assistant runtime are not implemented |
| **S13-PR-001** Design authority reconciliation | **Merged** (PR #11); design-authority gate **closed** |
| Bounded-AI task/decision/policy architecture | ADR 0033–0034 accepted; `TaskJob`/worker durable execution foundation exists, but `AITaskRun`/`AIContextManifest`/`DecisionEpisode`/`ExecutionPolicy` runtime and provider gateway are not implemented |
| UI/UX v2.3 PR-00 through PR-04 | **Merged** by PR #29 at `2775cb9…`; PR-01 remains a bounded prefix foundation |
| UI/UX v2.3 PR-05 / PR-06 | **Merged** by PR #30 / #31; OneDrive Personal backend/provider acceptance passed; frontend absent |
| UI/UX v2.3 downstream product stages | **Partially implemented on Draft PR #32**: Local G6 + OneDrive Exchange G8 are complete offline; F2-PR-001…003 are merged on integration head `d725bbc6…` with CI #454 green; F2-PR-004…008, canonical stages 5–16 and Release/Publishing remain incomplete. |
| Windows Preview | **Deferred until Software Completion** |
| Production-ready | **No** |

### Live task gate

```text
Accepted code baseline: origin/main 27d1cc6… (PR #31).
Canonical UI/UX authority: VALORA_UIUX_HANDOFF_v2.3.md +
VALORA_UIUX_V2_3_AUTHORITY_INDEX.md + Unified Appraisal OS roadmap v2.3 on the active repository branch.
PR-00 through PR-04 — MERGED by PR #29; PR-01 is a bounded prefix foundation.
PR-05 — MERGED by PR #30; OneDrive Personal backend/provider slice, no frontend.
PR-06 — MERGED by PR #31; OneDrive Personal return/revalidation backend/provider slice, no frontend.
Operational frontend entry — REQUIRED before Software Completion.
Draft PR #32 contains Operational Frontend, accepted Local G6 and completed G8 offline Exchange. The original direct OneDrive replacement path is historical/blocked; new document-change runtime requires the ADR-0045 implementation contract. Release/Publishing and the remaining canonical stages are still incomplete.
Software Completion — REQUIRED before Windows Preview.
Per-layer truth: docs/implementation/VALORA_UIUX_V2_3_PR00_PR13_FEATURE_ACCEPTANCE_MATRIX.md.
Known legacy QC/approval/standalone-validation surfaces are debt and must not expand or drive new UI.
Earlier S13 sequencing is historical context.
```

## Architecture (monorepo)

```text
backend/     FastAPI + SQLAlchemy + Alembic (Python ≥3.12)
frontend/    React 18 + TypeScript + Vite; Fluent 2 light product visual authority
worker/      Python reliable-job worker; durable TaskJob/attempt lease/retry/dead-letter runtime exists and is reused by document extraction/alignment; future AI must reuse it
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
ai_governance_security/        AI task/context/provider provenance + ExecutionPolicy boundary
excel_import/                  streaming parser + staging + Apply (S12 v1)
```

Future/continuing ownership follows current implementation state: mapping/identity memories remain in their existing bounded contexts; dossier extraction/alignment and durable job execution already have runtime foundations; future `AITaskRun`/context/attempt provenance, Task Registry/Gateway and deny-by-default `ExecutionPolicy` remain OS-G7 work under `ai_governance_security`/shared AI platform boundaries. AI must reuse the existing worker/runtime infrastructure.

### Non-negotiable invariants

- Tenant isolation: `organization_id` + project/session scope; **fail closed**.
- **ADR 0028** restricted Workbench fields require draft-commit + atomic audit.
- Excel **upload and validate** write **only** import batch + staging — **never** mutate official `ProjectAssetLine`.
- **Apply** (S12-PR-004 / ADR 0029 / `s12-pr-004-v1`) is the human-confirmed DRAFT-only promotion path.
- Upload lock order: **Project → batch → staging** (aligned with Apply).
- AI is advisory only; no auto-approve / auto-apply / auto knowledge activation.
- AI/rules/providers produce typed proposals only; no direct persistence mutation.
- Domain decisions remain authority; `AITaskRun`/`DecisionEpisode` provide provenance and learning lineage.
- No R2 auto-draft/auto-stage promotion in S13–S16; future writes require deterministic ExecutionPolicy and allowlisted idempotent commands.
- Workflow-pattern learning uses domain commands/outcomes, not UI clickstream.
- Local PostgreSQL test **skips are not PASS**.

## Authority hierarchy

Read order: explicit current Product Owner decision (named scope only) → `CODEX.md` → `ENGINEERING_GUARDRAILS.md` → UI/UX Handoff v2.3 → UI/UX Authority Index → applicable current v2.3 addendum → Unified Roadmap v2.3 → AI Master Plan v1 for OS-G7/AI-readiness → accepted scoped ADR → current task/implementation contract → current handoff/acceptance evidence → historical Design Book/sprint/audit/remediation/research evidence.

Historical roadmap only: S13 Adaptive Intake → S14 Asset Identity Memory → S15 dossiers → S16 AI suggestions → S17 reports → S18 pilot. **Do not execute this sequence as the current roadmap.** Current ordering is OS-G0 → OS-G7 in `docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md`.

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

- Current product-facing Adaptive Intake / mapping-confirmation UX completion (the historical workbook adapter and structure-discovery foundations already exist)
- Current product-facing Column Mapping / Asset Identity review-loop completion beyond the implemented historical foundations
- Productized paired Excel–Word/PDF dossier flow beyond the existing extraction/alignment foundations
- End-to-end provider-backed AI column/identity matching
- Full AI task/context/attempt/decision runtime; future AI must reuse the existing reliable `TaskJob`/worker background-job infrastructure
- Bounded R2 automation or an open-ended agent orchestrator
- Production certification

## License / ownership

Engineering repository for Valora. Follow `PR_RULES.md` for every change.


## Current roadmap

Use `docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md` as the current product/development roadmap. Historical sprint plans, audit reports and earlier handoffs are evidence/reference only and do not override current v2.3 authority.
