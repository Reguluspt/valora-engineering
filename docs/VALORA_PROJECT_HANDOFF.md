# Valora Project Handoff (Canonical)

**Status:** Canonical handoff for coding agents
**Reconciled:** 2026-07-14 — S12-R-008
**Baseline `main` SHA:** `c2f154dda3ba9c9dd4bdbdb8ce23676315bba1b7` (S12-PR-003 merge #8)
**Do not use** protected untracked onboarding artifacts as authority.

---

## 1. Product goal and persona

Valora is a **valuation and asset-identity workbench** for business appraisers and review roles who are **not software engineers**. UX must be **Vietnamese-first**, non-IT error messages, and **Astryx**-aligned components.

Word/Excel are **ports** for import/export. The Workbench + database are the source of truth.

## 2. Vietnamese UX and Astryx

- Labels: `frontend/src/i18n/` + `docs/design/VALORA_VIETNAMESE_I18N_LABEL_DICTIONARY.md`
- Errors: `frontend/src/errors/` + `docs/design/VALORA_NON_IT_ERROR_MESSAGE_REGISTRY.md`
- Design system: `@astryxdesign/core`, `@astryxdesign/theme-neutral`
- Mapping notes: `docs/design/VALORA_ASTRYX_TOKEN_COMPONENT_MAPPING.md`

## 3. Bounded contexts and ownership

| Module | Responsibility |
|---|---|
| `project_master_data` | Org, users/roles, master data, projects, central models |
| `taxonomy_asset_identity` | Taxonomy, canonical assets, aliases, candidates |
| `knowledge_evidence` | Evidence library, knowledge versions, quotes |
| `workflow_workbench` | Workflow + workbench session helpers |
| `document_engine_intelligence` | Document templates/render/intelligence domain tables |
| `ai_governance_security` | Future AI governance boundary |
| `excel_import` | Streaming Excel parse + atomic staging replacement |

API surface lives under `backend/app/api/*`. Frontend focus is Live Workbench under `frontend/src/components/workbench/*`.

## 4. Backend / frontend / worker

| Layer | Role |
|---|---|
| Backend | Auth, RBAC, domain APIs, persistence, audit, Excel intake |
| Frontend | App shell, Workbench grid/drafts/session, API clients |
| Worker | Skeleton only (no heavy job pipeline yet) |

Local infra: PostgreSQL 16, Redis 7, MinIO via `docker-compose.yml`.

## 5. Tenant and auth model

- Production identity comes from authenticated session/token — **not** spoofable client headers.
- Tests may override dependencies; production must not trust `X-User-Id` for identity.
- All project/session/import resources scoped by `organization_id` (+ project where applicable).
- Cross-tenant access → safe `404` / deny-by-default.

## 6. Human Commit Gate and official mutation (ADR 0028 scope)

**Restricted Workbench-gated fields** (only):

```text
description
appraised_unit_price
review_status
validation_status
```

For those fields, official changes go through:

1. Draft edit path
2. Human confirmation
3. Single application command (`commit_asset_line_draft` pattern)
4. Permission + workflow state + exact optimistic version
5. Atomic `AuditEvent` in the same transaction

Direct PATCH of those four fields is rejected with 400 (S12-R-004 / ADR 0028).

**Non-restricted fields** (examples: `asset_name`, `quantity`, `unit_id`, `raw_price`,
`raw_price_currency_id`, `appraised_currency_id`, `brand_id`, `manufacturer_id`) may still be
updated via direct `PATCH` under `project:update` with optimistic locking. That path is
**outside** the R004 Human Commit Gate and atomic-command guarantee.

Excel intake never mutates official `ProjectAssetLine` (staging only).

## 7. Excel staging / parser / transaction model

Contract: `docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md`
Implementation: `backend/app/modules/excel_import/`

```text
Upload → batch lock → pre-fingerprint
  → nested savepoint: replace staging + success audit
  → outer commit
On failure: rollback preserve prior staging; optional failure audit with fingerprint guard
```

Invariants:

- Staging-only; **no** `ProjectAssetLine` mutation
- Bounded streaming + ZIP/XLSX safety + resource limits
- Positional `raw_values.cells` (duplicate/blank headers preserved)
- First-alias-wins mapping for known columns

## 8. Progress snapshot

### Sprint 11 (historical)

Live Workbench loop (asset lines, draft, human commit UI/API) merged.
**Historical READY labels are not current slice approval** — S12-R re-gated security and data integrity.

### S12-PR-001 / S12-PR-002 (historical)

Staging model + initial upload/parser.
Superseded in part by S12-R-002…006 for auth, transaction, streaming, and raw value shape.

### S12-R-001 … S12-R-006 (merged on `main`)

| ID | Focus | Merge evidence |
|---|---|---|
| R-001 | CI / default branch / gates | `6c64305` #1 |
| R-002 | Auth identity boundary | `b025b97` #2 |
| R-003 | Workbench tenant/session scope | `c46ea1c` #3 |
| R-004 | Official mutation + atomic audit | `e683757` #4 |
| R-005 | Dynamic project context / live data | `ff40fda` #5 |
| R-006 | Excel streaming + transaction harden | `54872c7` #6 |

R-006 code-bearing CI historical evidence (pre-squash): **375 passed, 0 skipped**, PG concurrency executed.

### S12-R-007 (historical handoff cycle)

Documentation reconciliation and final acceptance matrix.
**Does not** implement Validation Engine. **Merged historically** before S12-PR-003.

### S12-PR-003 (merged)

```text
S12-PR-003 — Excel Staging Validation Engine — MERGED (PR #8)
```

Validation Engine operates on **staging rows only**, does not apply to official lines, and does not introduce AI auto-approve.

### S12-R-008 (this handoff cycle)

```text
S12-R-008 — Post-Validation Reconciliation & Apply Design Authority
```

Documentation / design-authority only: ADR 0029, staging contract §15, ADR 0028 addendum, operator-doc reconciliation. **Does not** implement Apply.

## 9. Next approved implementation task

```text
S12-PR-004 — Excel Staging Apply Command & Provenance
```

Only after S12-R-008 Draft PR CI + independent audit PASS + merge to `main`.

Apply must follow ADR 0029 and contract §15 exactly (backend-only; human-confirmed DRAFT-only; all-valid all-or-nothing; lineage migration).

## 10. Out of scope (still)

- Frontend Apply UX (deferred; no task ID assigned here)
- AI provider runtime
- PDF/Word product reporting
- CRM/revenue dashboards
- Production certification

## 11. Safe onboarding for the next agent

1. Read `CODEX.md`, `ENGINEERING_GUARDRAILS.md`, `PR_RULES.md`, this handoff, ADR 0029, staging contract §15.
2. Verify `git rev-parse origin/main` against the task baseline.
3. Create a **new** branch from clean `main` for the assigned task ID.
4. Prefer code + tests + CI over stale audit prose.
5. Never touch protected untracked onboarding files outside scope.
6. Never treat local PG skips as PASS.
7. Do not implement S12-PR-004 until R008 acceptance criteria say so.
8. Do not re-open S12-PR-003 as blocked/not started — it is merged.

## 12. Key paths

```text
backend/app/main.py
backend/app/api/
backend/app/modules/excel_import/
backend/app/modules/project_master_data/commands/commit_asset_line_draft.py
frontend/src/App.tsx
frontend/src/components/workbench/
docs/remediation/S12_R_PRE_VALIDATION_REMEDIATION_SLICE.md
docs/audits/S12_R_00*_*.md
```
