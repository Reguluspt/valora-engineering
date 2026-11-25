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
**Appraisal Core:** Full OS-G2 remains partial. Use the [dated workflow status](docs/DOCUMENTATION_STATUS_INDEX.md#current-status-by-workflow) for bounded certifications and verify the assigned task before acting. A past milestone is not current execution authorization.

Agents must run `valora-live-authority-bootstrap`: `git fetch origin`, verify live `origin/main` and CODEX, inspect the assigned task and require successful CI on the exact claimed SHA. README milestone SHAs do not certify the current baseline or authorize the next stage.

## Product goal

Valora is a **valuation / asset-identity workbench** for non-IT business users. Primary UX language is **Vietnamese**. Current product visual authority is **Microsoft Fluent 2 light**, desktop-first and data-heavy/table-first. Word/Excel are input/output only — they are **not** the source of truth.

## Start here

- [Documentation entry point](docs/index.md): where to find governing decisions, scope-specific references and evidence, without rereading the repository.
- [Status by workflow](docs/DOCUMENTATION_STATUS_INDEX.md#current-status-by-workflow): what is designed, integrated, or certified, with separate UAT and deployment boundaries.
- For assigned work, start with the [Compact Task Contract](docs/plan/VALORA_COMPACT_TASK_CONTRACT_TEMPLATE.md) and the [live task gate](CODEX.md#2-current-engineering-phase). Verify live main, the governing CODEX blob, exact-commit CI and the current task before changing anything.

A documented design, a merged PR, product acceptance, UAT and deployment are different states. The linked status table is a dated navigation aid: it does not grant work or widen an existing task.

## Architecture (monorepo)

```text
backend/     FastAPI + SQLAlchemy + Alembic (Python ≥3.12)
frontend/    React 19 + TypeScript + Vite; Fluent 2 light product visual authority
worker/      Python reliable-job worker; durable TaskJob/attempt lease/retry/dead-letter runtime exists and is reused by document extraction/alignment; future AI must reuse it
infra/       Development and Linux server foundation
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
excel_import/                  streaming parser, mapping, staging and guarded Apply
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
