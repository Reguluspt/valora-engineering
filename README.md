# Valora Engineering

**Phase:** Engineering — VALORA UI/UX v2.3 implementation alignment
**Historical OS-G0 milestone (2026-09-27; not current baseline):** `51eab8648005186197d2fbb37a19bde4332aeaa5` (squash PR #32; exact-head CI #485 SUCCESS)
**Current roadmap:** `docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md`<br>
**AI architecture detail:** `docs/architecture/VALORA_AI_MASTER_PLAN_V1.md` — OS-G7 documentation authority only; runtime AI remains gated
**Canonical UI/UX authority:** `docs/design/VALORA_UIUX_HANDOFF_v2.3.md` + `docs/design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md`
**Documentation status map:** `docs/DOCUMENTATION_STATUS_INDEX.md`
**PR-00 through PR-04:** **MERGED by PR #29**
**PR-05 and PR-06:** **MERGED by PR #30 and PR #31; backend/provider slices only**
**PR-00 alignment gate:** **CLOSED**
**PR-01 / PR-02 / PR-03 / PR-04 implementation contracts:** **ACCEPTED**
**PR-01 schema scope:** no projection migration; durable downstream facts keep their owning migrations.
**Current execution direction:** **OS-G0 complete; OS-G1 CERTIFIED/CLOSED; OS-G2 PARTIAL / certified through ASSET_REVIEW. Full OS-G2 remains incomplete; ASSET_WORKBENCH and later stages are unavailable/not authorized.**

Agents must run `valora-live-authority-bootstrap`: `git fetch origin`, verify live `origin/main` and CODEX, inspect the assigned task and require successful CI on the exact claimed SHA. README milestone SHAs do not certify the current baseline or authorize the next stage.

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
| S12 parser / Apply versions | Historical `.xlsx` fixed-alias parser and Apply v1 contract remain frozen evidence; current post-Intake promotion uses guarded Apply v2 under ADR 0048 |
| **S13-PR-002** Legacy Workbook Adapter / Source Artifact | **Merged** (PR #15) at `137f8c5…` |
| **S13-PR-003** Structure Discovery / Row Classification | **Merged** (PR #17) at `2af7535…` |
| Adaptive Intake / Column Mapping Memory | Bounded G1.1H Intake & Mapping UX certified by PR #63; G1.1K / PR #68 certified/closed the Pre-case journey. Human-confirmed mapping/current selection and recovery are implemented; future provider AI matching is not implied |
| Asset Identity Memory / dossiers / AI matching | Identity-decision/feedback and dossier extraction/alignment foundations are implemented; provider-backed AI matching and the full OS-G7 assistant runtime are not implemented |
| **S13-PR-001** Design authority reconciliation | **Merged** (PR #11); design-authority gate **closed** |
| Bounded-AI task/decision/policy architecture | ADR 0033–0034 accepted; `TaskJob`/worker durable execution foundation exists, but `AITaskRun`/`AIContextManifest`/`DecisionEpisode`/`ExecutionPolicy` runtime and provider gateway are not implemented |
| UI/UX v2.3 PR-00 through PR-04 | **Merged** by PR #29 at `2775cb9…`; PR-01 remains a bounded prefix foundation |
| UI/UX v2.3 PR-05 / PR-06 | **Merged** by PR #30 / #31; OneDrive Personal backend/provider acceptance passed; frontend absent |
| UI/UX v2.3 product closure | OS-G0 complete (historical PR #32 / CI #485); OS-G1 CERTIFIED/CLOSED (G1.1K / PR #68 / CI #527); ASSET_REVIEW CERTIFIED/CLOSED (A5 / PR #86 / CI #555). Full OS-G2 and stages 6–16 remain incomplete/unavailable; no ASSET_WORKBENCH+ authorization. Local G6 + OneDrive Exchange G8 remain accepted/offline-complete foundations; Release/Publishing and full product completion remain open |
| Windows Preview | **Deferred until Software Completion** |
| Production-ready | **No** |

### Live task gate

```text
Live baseline: perform valora-live-authority-bootstrap; fetch origin/main, verify live HEAD/CODEX, assigned task and CI SUCCESS on that exact SHA.
Historical OS-G0 milestone (2026-09-27): `51eab8648005186197d2fbb37a19bde4332aeaa5` (squash PR #32; exact-head CI #485 SUCCESS), not current main truth.
Canonical UI/UX authority: VALORA_UIUX_HANDOFF_v2.3.md +
VALORA_UIUX_V2_3_AUTHORITY_INDEX.md + Unified Appraisal OS roadmap v2.3 on the active repository branch.
PR-00 through PR-04 — MERGED by PR #29; PR-01 is a bounded prefix foundation.
PR-05 — MERGED by PR #30; OneDrive Personal backend/provider slice, no frontend.
PR-06 — MERGED by PR #31; OneDrive Personal return/revalidation backend/provider slice, no frontend.
Operational frontend entry — MERGED TO MAIN by squash PR #32 at `51eab864…`; exact-head CI #485 SUCCESS.
The historical PR32 milestone contains Operational Frontend, accepted Local G6 and completed G8 offline Exchange. Subsequently OS-G1 closed through G1.1K / PR68 / CI527 and ASSET_REVIEW closed through A5 / PR86 / CI555. Current provider coverage reaches the first five stages; case completion remains fact-derived. Full OS-G2 is incomplete; ASSET_WORKBENCH+ stays NOT_AVAILABLE / UNAUTHORIZED. The original direct OneDrive replacement path is historical/blocked; new document-change runtime requires the ADR-0045 implementation contract. Release/Publishing and remaining stages are incomplete.
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
- [ADR 0028](docs/adr/0028-official-mutation-command-and-atomic-audit-gate.md) value edits use `CommitProjectAssetLineDraft`: draft → explicit human confirmation → command, exact draft/line versions and atomic audit. Direct PATCH of all four restricted fields remains blocked.
- [ADR 0049](docs/adr/0049-asset-line-human-review-and-validation-authority.md) supplies dedicated `ValidateProjectAssetLine` (human-confirmed request, server-derived verdict) and `DecideProjectAssetLineReview` (explicit human decision). New mutations retain tenant/RBAC, owned session, DRAFT, exact row/Case State CAS, current seal/lineage and atomic audit; no generic draft statuses or user-selected validation verdict.
- Excel **upload and validate** write **only** import batch + staging — **never** mutate official `ProjectAssetLine`.
- Current guarded Apply v2 uses the existing `ApplyProjectAssetImportBatch`, `s12-post-intake-guarded-apply-v2`, under [ADR 0048](docs/adr/0048-post-intake-guarded-apply-and-asset-review-authority.md): explicit human confirmation, DRAFT, post-Official-Intake exact lineage/CAS and atomic initial-set seal/audit; no naked v1 bypass. [ADR 0029](docs/adr/0029-excel-staging-apply-command-and-lineage.md) / `s12-pr-004-v1` remain frozen historical/foundation authority, not an alternate current entry path.
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

## Deployment/client v1 direction

[ADR 0050](docs/adr/0050-linux-server-windows-native-client.md) records the Product Owner decision: Linux single-node Server with Docker Engine + Compose, HTTPS over LAN and a Windows 11 x64-first WinUI 3/WebView2 Evergreen client hosting server-served React / Microsoft Fluent 2 light. MSIX carries the shell and small typed native bridge; PostgreSQL, domain enforcement, immutable blobs and worker stay on the server. No client backend/database, React rewrite or Docker Desktop production stack.

Server v1 deploys no local LLM/model weights and needs no GPU; core workflow needs no AI provider. Future provider AI remains OS-G7 gated. [Windows Client](docs/plan/VALORA_WINDOWS_CLIENT_V1_PLAN.md) and [Linux Server](docs/plan/VALORA_LINUX_SERVER_V1_PLAN.md) plans do not authorize implementation/deployment. Formal Windows Preview/UAT stays after Software Completion; explicitly assigned architecture/skeleton work and Linux Deployment Pilot are distinct gates. Local setup below is developer tooling, not production deployment.

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

- Broader Asset Identity review/automation beyond the implemented human-confirmed foundations; the bounded G1.1H/K Intake & Mapping / Pre-case journey is already certified
- Productized paired Excel–Word/PDF dossier flow beyond the existing extraction/alignment foundations
- End-to-end provider-backed AI column/identity matching
- Full AI task/context/attempt/decision runtime; future AI must reuse the existing reliable `TaskJob`/worker background-job infrastructure
- Bounded R2 automation or an open-ended agent orchestrator
- Production certification

## License / ownership

Engineering repository for Valora. Follow `PR_RULES.md` for every change.


## Current roadmap

Use `docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md` as the current product/development roadmap. Historical sprint plans, audit reports and earlier handoffs are evidence/reference only and do not override current v2.3 authority.
