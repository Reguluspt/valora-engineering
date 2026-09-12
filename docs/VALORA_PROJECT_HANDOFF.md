# Valora Project Handoff — Implementation Baseline Supplement

**Status:** Historical implementation context; UI/UX sequencing is governed by v2.3 authority
**Reconciled:** 2026-09-12 — PR-05 engineering and live-account gates passed
**Accepted code baseline:** `93f50f9ac81ab93e2361fffa8b71fc3bcfca57f6` (R-GATE-001 / PR #26)
**Canonical UI/UX authority:** `docs/uiux-handoff-v2.2` at `1cf50460e54ba19d2f6a9d8f933ab123e4e615d6`

### Live task gate

```text
Read `docs/design/VALORA_UIUX_HANDOFF_v2.3.md`, then
`docs/design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md`, then the directly relevant v2.3 addendum.

PR-00 — Authority Alignment Guard: COMPLETE / CLOSED locally.
PR-01 / PR-01a — Case State Projection Foundation and durable official intake: ACCEPTED foundation.
PR-02 through PR-04 were implemented together by GitHub PR #28 from base
`5ed0922f50ae1ef3b31346f7245423aae9c01cd2` to reviewed head
`51db33ec7fc7a82b9abba151e13f268b5e875fc4`. The formal acceptance gate and current CI checks
PASS with no P0, P1 or P2 findings. This disposition is exact-head evidence, not an evergreen claim.
PR #28 remains open and Draft; it is not merged, released or deployed.
The two residual evidence gaps are CLOSED locally. PR-02 browser acceptance PASS is recorded against
local corrective commit `69ecd97a6383c10d5cb024c6bb06df87ebbc6d24`; migration `d4b7c9e2f1a6`
upgrade/downgrade/upgrade CI regression is committed at
`ad3faad4063de111bd6c5a45dc8b847329bfd9af`. These local closeout commits are not part of the
reviewed remote head above and do not change PR #28's Draft/unmerged status.
PR-05 — M365 Integration Foundation now has separate local task `VALORA-PR05-IMPL-001` on branch `integration/phase1c-pr05-m365-foundation`, based at local closeout head `839debf`. Its read-only survey and architecture challenge are complete, and ADR 0040 is accepted for delegated OneDrive Personal access only; OneDrive for Business and SharePoint integration are deferred. The bounded runtime implementation passed the fake-provider, full backend and live OneDrive Personal acceptance gates. This local task does not change PR #28's remote Draft head.
PR-01 remains the historical `OWNER-ASSIGNED` gate: ADR 0036 and ADR 0037 are accepted, with computed-on-read and no projection migration under ADR 0036.
Known legacy QC/approval/standalone-validation implementation remains unchanged but must not expand
or drive new UI. Earlier S13 sequencing below is historical context only.
```

Agents must `git fetch origin` and verify live `origin/main`. Listed SHAs are evidence, not evergreen status.

---

## 1. Product goal and persona

Valora is a **valuation and asset-identity workbench** for business appraisers and review roles who are **not software engineers**. UX must be **Vietnamese-first**, non-IT error messages, and **Astryx**-aligned components.

Word/Excel are **ports** for import/export. The Workbench + database are the source of truth.

Design Book v1.4 adds two separate, auditable memories: **Column Mapping Memory** (workbook structure) and **Asset Identity Memory** (raw wording → canonical/variant). Raw observations remain immutable; only human-confirmed decisions become reusable feedback.

The 2026-07-16 extension adds provider-independent `AITaskRun`/context/attempt provenance, `DecisionEpisode` learning lineage, intent-level workflow-pattern inputs and a deny-by-default risk-tiered `ExecutionPolicy`. It prepares future automation but does not enable autonomous runtime or weaken human gates.

## 2. Vietnamese UX and Astryx

- Labels: `frontend/src/i18n/` + `docs/design/VALORA_VIETNAMESE_I18N_LABEL_DICTIONARY.md`
- Errors: `frontend/src/errors/` + `docs/design/VALORA_NON_IT_ERROR_MESSAGE_REGISTRY.md`
- Design system: `@astryxdesign/core`, `@astryxdesign/theme-neutral`
- Mapping notes: `docs/design/VALORA_ASTRYX_TOKEN_COMPONENT_MAPPING.md`

## 3. Bounded contexts and ownership

| Module | Responsibility (current + planned) |
|---|---|
| `project_master_data` | Org, users/roles, master data, projects, central models hub |
| `taxonomy_asset_identity` | Taxonomy, canonical assets, aliases, candidates; **planned** Raw Asset Observation + Asset Identity Memory |
| `knowledge_evidence` | Evidence library, knowledge versions, quotes; **planned** reviewed bootstrap candidates |
| `workflow_workbench` | Workflow + workbench session helpers; future patterns derive from domain commands/outcomes, not UI clickstream |
| `document_engine_intelligence` | Document templates/render/intelligence tables; **planned** dossier extraction/alignment |
| `ai_governance_security` | AI task/context/provider provenance and deterministic Execution Policy boundary; advisory only in S13–S16 |
| `excel_import` | S12 streaming staging + Apply; **planned** Adaptive Intake + Column Mapping Memory |

API surface lives under `backend/app/api/*`. Frontend focus is Live Workbench under `frontend/src/components/workbench/*`.

## 4. Backend / frontend / worker

| Layer | Role |
|---|---|
| Backend | Auth, RBAC, domain APIs, persistence, audit, Excel intake + Apply |
| Frontend | App shell, Workbench grid/drafts/session, API clients |
| Worker | Skeleton only; planned durable outbox/job/attempt/lease/retry runtime before long-running dossier extraction and production AI tasks |

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

| ID | Status | Evidence / next gate |
|---|---|---|
| PR-00 | COMPLETE / CLOSED locally | closeout `b176820` |
| PR-01 / PR-01a | ACCEPTED FOUNDATION | PR-01 runtime closeout is the PR #28 base `5ed0922f50ae1ef3b31346f7245423aae9c01cd2` |
| PR-02 | IMPLEMENTED IN DRAFT PR #28; RESIDUAL EVIDENCE CLOSED LOCALLY | reviewed remote head `51db33ec7fc7a82b9abba151e13f268b5e875fc4`; desktop/laptop browser acceptance PASS after corrective commit `69ecd97` |
| PR-03 | IMPLEMENTED IN DRAFT PR #28; RESIDUAL EVIDENCE CLOSED LOCALLY | append-only tenant-safe NCC Selection persistence; committed PostgreSQL upgrade/downgrade/upgrade CI regression `ad3faad` |
| PR-04 | IMPLEMENTED IN DRAFT PR #28 | API/UI slice included in the exact reviewed head; formal gate PASS with no P0/P1/P2 findings |
| PR-05 | ENGINEERING + LIVE ACCOUNT ACCEPTANCE PASSED | task `VALORA-PR05-IMPL-001`; 1,360 backend tests, final Qwen review and live OneDrive Personal delegated OAuth/Graph verification passed; OneDrive for Business and SharePoint deferred |

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
S13-PR-005 — Mapping Confirmation API and Astryx Vietnamese UX
```

Then follow S13–S16 plan: Column Mapping Memory → Asset Identity Memory → dossier/job foundation → reliable audited AI suggestions and shadow evaluation.

## 9. Out of scope (still)

- Mapping-confirmation API/Astryx UX (S13-PR-005)
- Asset Identity Memory runtime
- Paired Excel–Word/PDF extraction, row alignment, historical bootstrap
- AI provider runtime and end-to-end AI mapping/matching
- `AITaskRun`, `DecisionEpisode`, AI context manifest and reliable AI job runtime
- R2 auto-draft/auto-stage/exception-only-review capability promotion
- Open-ended agent orchestration or AI direct database mutation
- PDF/Word product reporting
- CRM/revenue dashboards
- Production certification
- Broad debt F-01 tenant isolation, F-02 legacy atomic audit, F-05 Astryx, etc. (tracked separately)

## 10. Safe onboarding for the next agent

1. Read `CODEX.md`, `ENGINEERING_GUARDRAILS.md`, `PR_RULES.md`, this handoff, and `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md`.
2. Verify `git rev-parse origin/main` against the task baseline.
3. Create a **new** branch from clean `main` for the assigned task ID.
4. Prefer code + tests + CI over stale audit prose.
5. Never treat local PG skips as PASS.
6. Do not restart closed S13 work. Follow the v2.3 PR-00 → PR-13 execution track and its dependency gates.
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
docs/remediation/S13_S16_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_REMEDIATION_PLAN.md
```
