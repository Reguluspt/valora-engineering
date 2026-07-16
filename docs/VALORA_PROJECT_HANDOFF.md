# Valora Project Handoff (Canonical)

**Status:** Canonical handoff for coding agents
**Reconciled:** 2026-07-16 — Gate 0c closeout / live-gate reconciliation
**Main evidence (not evergreen):** `99dfccbc7bf2893fa5b0dce8d52a01068655e39a` (Gate 0c PR #13)
**Main CI evidence:** run `29504915362` PASS

### Live task gate

```text
S12-PR-004 is MERGED and its engineering gate is CLOSED.
S13-PR-001 design-authority gate is CLOSED. Gate 0b is SATISFIED.
Gate 0c bounded-AI automation readiness is CLOSED / SATISFIED.
Evidence (not evergreen): main squash 99dfccbc7bf2893fa5b0dce8d52a01068655e39a (PR #13);
main CI 29504915362 PASS; audited head 656dc9ff70a453ee5b83f47d13b7040b3f062076.

Runtime assignment state: S13-PR-002 assigned / in progress on branch s13-pr-002-legacy-workbook-source-artifact from baseline 949903f3912aa65f8b990852756aeef7981bca08 (not merged).
S13-PR-002 is owner-authorized on its feature branch only; it is NOT merged and must not be treated as main PASS/closed.
Further candidates (S13-PR-003 onward) still require separate explicit owner assignment from the then-current accepted origin/main.
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

### Merged on main (do not re-open)

| ID | Focus |
|---|---|
| S12-R-001…008 | Remediation, auth, tenant, mutation, Excel harden, recon, Apply authority |
| S12-PR-003 | Validation Engine |
| **S12-PR-004** | Apply Command & Provenance — **merged** PR #10 at `a9f2c1e…` |
| **S13-PR-001** | Design Authority and Contract Reconciliation — **merged** PR #11 at `7f7473e…` |

### Runtime assignment state

```text
Active runtime assignment: S13-PR-002 — Legacy Workbook Adapter and Immutable Source Artifact
Branch: s13-pr-002-legacy-workbook-source-artifact (not merged)
Baseline: 949903f3912aa65f8b990852756aeef7981bca08
Gate 0c: CLOSED / SATISFIED (main 99dfccb…; CI 29504915362)
```

### Next candidate after S13-PR-002 merge (requires separate owner assignment)

```text
S13-PR-003 — structure discovery / Column Mapping Memory (per remediation plan)
```

Then follow S13–S16 plan: Column Mapping Memory → Asset Identity Memory → dossier/job foundation → reliable audited AI suggestions and shadow evaluation.

## 9. Out of scope (still)

- Adaptive `.xls`/`.xlsx` runtime and mapping-confirmation UX
- Column Mapping Memory / Asset Identity Memory runtime
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
6. Do not restart closed S13-PR-001 or Gate 0c. S13-PR-002 is the active assigned runtime task on its feature branch only (not merged). Do not start S13-PR-003+ until a separate owner assignment names that task ID from accepted main.
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
