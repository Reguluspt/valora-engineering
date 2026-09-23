# Valora Project Handoff — Implementation Baseline Supplement

**Status:** Historical implementation context; UI/UX sequencing is governed by v2.3 authority
**Reconciled:** 2026-09-23 — Draft PR #32 integration head `d725bbc6…` includes F2-PR-001…003, accepted Local G6 and completed G8 offline Exchange; ADR 0045 remains current document-change direction; AI architecture detail is `docs/architecture/VALORA_AI_MASTER_PLAN_V1.md`
**Accepted merged code baseline:** `27d1cc630f97cb9b56fbfbb4c5bc04d4be305cc6` (PR #31); **active candidate:** Draft PR #32 / `feat/operational-frontend-m365` at reconciliation head `d725bbc6f60f2a21ec11a555d9565d2ab01470ae` (CI #454 SUCCESS)
**Current roadmap:** `docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md`
**Canonical UI/UX authority:** `docs/design/VALORA_UIUX_HANDOFF_v2.3.md` + `VALORA_UIUX_V2_3_AUTHORITY_INDEX.md`; Working-copy change semantics are governed by the 2026-09-21 addendum + ADR 0045
**v2.3 gate:** PR-00 — **CLOSED**; PR-01 / PR-02 / PR-03 / PR-04 contracts — **ACCEPTED** and merged.

### Live task gate

```text
Read the v2.3 master + authority index + directly relevant addendum before coding.

Merged main remains PR-00 through PR-06 at 27d1cc6.
Draft PR #32 is the active integration candidate and now carries:
- Operational Frontend entry and M365 workspace;
- Local immutable DocumentBlobStore accepted at G6;
- OneDrive Personal Exchange G8 offline implementation complete at f896f15…;
- ADR 0045 / Working Change Observation + DocumentChangeCandidate + Human Commit authority.

Do not infer "product complete" from those infrastructure/integration milestones.
Global Case State still has only the four prefix-stage providers; stages 5-16 remain unavailable.
Legacy global Review Queue / standalone Validation Dashboard production routes were removed by F2-PR-001. The old Workbench right-panel IA remains remediation debt until F2-PR-005; F2-PR-003 has already replaced the production Astryx shell/login/shared-state primitives.

The original PR-07 direct OneDrive replacement mechanism is blocked/historical. Reuse its Old/V/W,
protected-value and explicit-conflict semantics only where compatible. New document-change runtime
must follow ADR 0045:
automatic observation/revalidation -> DocumentChangeCandidate -> review/conflict -> explicit human commit
-> app-owned immutable Revision N+1.

G9 live AppFolder conformance is a separate Product Owner decision. ADR 0045 does not authorize
webhook/subscription/delta runtime by itself; freeze a task-specific implementation contract first.

North-star completion, Release/Publishing, traceability/state/fidelity and exact-SHA E2E remain
before Software Completion. Windows Preview follows Software Completion.
```

Agents must `git fetch origin` and verify live `origin/main`. Listed SHAs are evidence, not evergreen status.

---

## 1. Product goal and persona

Valora is a **single-user valuation and asset-identity workbench** for business appraisers who are **not software engineers**. UX must be **Vietnamese-first**, non-IT, desktop-first, data-heavy/table-first and conform to **Microsoft Fluent 2 light**.

Word/Excel are **ports** for import/export. The Workbench + database are the source of truth.

Design Book v1.4 adds two separate, auditable memories: **Column Mapping Memory** (workbook structure) and **Asset Identity Memory** (raw wording → canonical/variant). Raw observations remain immutable; only human-confirmed decisions become reusable feedback.

The 2026-07-16 extension adds provider-independent `AITaskRun`/context/attempt provenance, `DecisionEpisode` learning lineage, intent-level workflow-pattern inputs and a deny-by-default risk-tiered `ExecutionPolicy`. It prepares future automation but does not enable autonomous runtime or weaken human gates.

## 2. Vietnamese UX and Fluent 2 light

- Labels: `frontend/src/i18n/` + `docs/design/VALORA_VIETNAMESE_I18N_LABEL_DICTIONARY.md`
- Errors: `frontend/src/errors/` + `docs/design/VALORA_NON_IT_ERROR_MESSAGE_REGISTRY.md`
- Current visual authority: Microsoft Fluent 2 light, desktop-first, data-heavy/table-first.
- `docs/design/VALORA_ASTRYX_TOKEN_COMPONENT_MAPPING.md` is historical/low-level reference only; Astryx may not drive product visual language.

## 3. Bounded contexts and ownership

| Module | Responsibility (current + planned) |
|---|---|
| `project_master_data` | Org, users/roles, master data, projects, central models hub |
| `taxonomy_asset_identity` | Taxonomy, canonical assets, aliases, candidates; **planned** Raw Asset Observation + Asset Identity Memory |
| `knowledge_evidence` | Evidence library, knowledge versions, quotes; **planned** reviewed bootstrap candidates |
| `workflow_workbench` | Workflow + workbench session helpers; future patterns derive from domain commands/outcomes, not UI clickstream |
| `document_engine_intelligence` | Document templates/render/intelligence tables; dossier extraction/alignment runtime foundations exist and reuse the durable `TaskJob`/worker boundary; the productized paired-dossier flow remains incomplete |
| `ai_governance_security` | AI task/context/provider provenance and deterministic Execution Policy boundary; advisory only unless a later owner-approved task explicitly promotes capability |
| `excel_import` | S12 streaming staging + Apply; **planned** Adaptive Intake + Column Mapping Memory |

API surface lives under `backend/app/api/*`. Frontend focus is Live Workbench under `frontend/src/components/workbench/*`.

## 4. Backend / frontend / worker

| Layer | Role |
|---|---|
| Backend | Auth, RBAC, domain APIs, persistence, audit, Excel intake + Apply |
| Frontend | App shell, Workbench grid/drafts/session, API clients |
| Worker | Durable `TaskJob`/`TaskJobAttempt` lease/retry/dead-letter runtime and reliable worker are implemented for document extraction/alignment; future AI tasks must reuse this boundary, not create a second queue |

Local infra: PostgreSQL 16, Redis 7, MinIO via `docker-compose.yml`.

## 5. Tenant and auth model

- Production identity comes from authenticated session/token — **not** spoofable client headers.
- Tests may override dependencies; production must not trust `X-User-Id` for identity.
- All project/session/import resources scoped by `organization_id` (+ project where applicable).
- Cross-tenant access → safe `404` / deny-by-default.

## 6. Human Commit Gate and official mutation (ADR 0028)

**Restricted Workbench-gated fields:**

```text
description
appraised_unit_price
review_status
validation_status
```

Official changes go through draft → human confirmation → `commit_asset_line_draft` with atomic audit. Direct PATCH of those four fields is rejected.

**Non-restricted fields** may use direct `PATCH` under `project:update` with optimistic locking (outside R004 single-command guarantee).

Excel intake never mutates official `ProjectAssetLine` (staging only) until Apply.

## 7. Excel staging / Apply (S12 v1 — implemented)

Contract: `docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md` (§14–§15)
ADR: `docs/adr/0029-excel-staging-apply-command-and-lineage.md`
Implementation: `backend/app/modules/excel_import/`

```text
Upload → batch lock (Project → batch order) → staging replace → success audit
Validate → staging rows only
Apply (s12-pr-004-v1) → human confirm, DRAFT-only, all-valid all-or-nothing,
  lineage columns, atomic success audit
```

Current S12 v1 parser: **`.xlsx` only**, fixed aliases, positional `raw_values.cells`. It does **not** implement Adaptive Intake v2.

## 8. Progress snapshot

### Current UI/UX integration track

| Capability / gate | Current state | Evidence / next gate |
|---|---|---|
| PR-00–PR-04 | MERGED bounded foundations/slices | PR #29; PR-01 remains four-stage Case State prefix |
| PR-05 | MERGED backend/provider foundation | PR #30; delegated OneDrive Personal read/OAuth |
| PR-06 | MERGED return/revalidation foundation | PR #31; five-way revalidation + live read acceptance |
| Operational Frontend | IMPLEMENTED / PARTIALLY FLUENT-2-REMEDIATED ON DRAFT PR #32 | F2-PR-001…003 merged on integration head `d725bbc6…` (CI #454); F2-PR-004…008 remain; not merged to main |
| Local immutable storage | G6 ACCEPTED | reviewed snapshot `d71a42e…`; durable G6 closeout manifest `5c54116…` |
| OneDrive Exchange G8 | OFFLINE COMPLETE | code milestone `f896f15…`; exact-head CI #302 green; no live AppFolder conformance claim |
| Working Change Observation direction | DESIGN/ADR ACCEPTED | ADR 0045 + v2.3 addendum; runtime implementation contract still required |
| PR-07 direct replace path | BLOCKED / HISTORICAL | ADR 0042 D6 remains a constraint for any future direct replacement; not current primary roadmap |
| Historical PR-08–PR-13 labels | NOT PRODUCT-COMPLETE | evidence labels only; current closure order is OS-G0→OS-G7 in the Unified Roadmap |
| Software Completion | OPEN | requires full North-star, release/publishing, traceability/state/fidelity and exact-SHA E2E |
| Windows Preview | DEFERRED | only after Software Completion |

### Merged on main (do not re-open)

| ID | Focus |
|---|---|
| S12-R-001…008 | Remediation, auth, tenant, mutation, Excel harden, recon, Apply authority |
| S12-PR-003 | Validation Engine |
| **S12-PR-004** | Apply Command & Provenance — **merged** PR #10 at `a9f2c1e…` |
| **S13-PR-001** | Design Authority and Contract Reconciliation — **merged** PR #11 at `7f7473e…` |
| **S13-PR-002** | Legacy Workbook Adapter and Immutable Source Artifact — **merged** PR #15 at `137f8c5…` |
| **S13-PR-003** | Workbook Structure Discovery and Row Classification — **merged** PR #17 at `2af7535…` |

### Historical runtime assignment snapshot — superseded by v2.3

```text
Historical assignment: S13-PR-004 — Column Mapping Memory Persistence and Application Services
Assigned branch name: s13-pr-004-column-mapping-memory
Baseline: 2af753520ab6b7885555adc5b7945a28d32ee311
Gate: freeze task-specific design/evidence contract before runtime implementation
```

### Historical next-candidate record — not a current execution gate

```text
S13-PR-005 — Mapping Confirmation API and historical Astryx Vietnamese UX
```

This S13–S16 sequence is historical only. Do not use it as the current execution order; follow the Unified Roadmap OS-G0→OS-G7.

## 9. Out of scope (still)

- Historical S13-PR-005 Mapping-confirmation/Astryx UX sequence is not a current execution gate
- Asset Identity Memory runtime
- Productized paired Excel–Word/PDF dossier flow beyond the existing extraction/alignment runtime foundations
- AI provider runtime and end-to-end AI mapping/matching
- `AITaskRun`, `AITaskAttempt`, `AIContextManifest`, `DecisionEpisode` and the full AI task/provider runtime; existing durable `TaskJob`/worker infrastructure must be reused
- R2 auto-draft/auto-stage/exception-only-review capability promotion
- Open-ended agent orchestration or AI direct database mutation
- PDF export remains out of scope; DOCX Document Workspace/report/certificate generation is in product scope and must follow current v2.3 authority
- CRM/revenue dashboards
- Production certification
- Broad debt remains tracked separately; current cross-product visual debt is Fluent 2 light conformance and removal of dark/cyan/glassmorphic/Astryx product styling

## 10. Safe onboarding for the next agent

1. Read `CODEX.md`, `ENGINEERING_GUARDRAILS.md`, `PR_RULES.md`, this handoff, and `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md`.
2. Verify `git rev-parse origin/main` against the task baseline.
3. Create a **new** branch from clean `main` for the assigned task ID.
4. Prefer code + tests + CI over stale audit prose.
5. Never treat local PG skips as PASS.
6. Do not restart closed S13 work. Follow `VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md` (OS-G0→OS-G7); historical PR labels are acceptance evidence only.
7. Treat AI output as a proposal; mapping, identity, price, Apply and knowledge activation remain human-controlled.
8. Do not re-open S12-PR-003/004 as blocked/not started — they are merged.
9. Do not claim uncommitted local docs are already merged authority.
10. Treat `AITaskRun`/`DecisionEpisode` as provenance around authoritative domain decisions, not replacement business truth.
11. AI/rules submit typed proposals only; future writes must pass deterministic ExecutionPolicy and an allowlisted idempotent domain command.
12. Do not learn workflow patterns from UI clickstream or promote automation from raw confirmation count.

## 11. Key paths

```text
backend/app/main.py
backend/app/api/
backend/app/modules/excel_import/
backend/app/modules/project_master_data/commands/commit_asset_line_draft.py
frontend/src/App.tsx
frontend/src/components/workbench/
docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md
docs/design/VALORA_DESIGN_BOOK_V1_4_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_ADDENDUM.md
docs/adr/0029-excel-staging-apply-command-and-lineage.md
docs/adr/0030-versioned-column-mapping-memory-and-adaptive-workbook-intake.md
docs/adr/0031-contextual-asset-identity-memory-and-human-confirmed-feedback.md
docs/adr/0032-paired-dossier-aggregate-document-extraction-and-row-alignment.md
docs/adr/0033-audited-ai-task-runs-decision-episodes-and-learning-evidence.md
docs/adr/0034-risk-tiered-execution-policy-and-reliable-autonomous-commands.md
docs/adr/0045-working-copy-change-observation-and-human-confirmed-document-revision.md
docs/remediation/S13_S16_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_REMEDIATION_PLAN.md
```
