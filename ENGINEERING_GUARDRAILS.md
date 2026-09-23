## Unified roadmap guardrail

`docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md` is the current product/development ordering. `docs/architecture/VALORA_AI_MASTER_PLAN_V1.md` details OS-G7 architecture and AI-readable-by-design requirements, but does not authorize runtime AI. Sub-domain plans (storage, M365, template/Office, AI) may not reorder the North-star roadmap unless a new Product Owner decision explicitly amends it.

## Current document authority guardrail

Word Save, provider notification, revalidation and Change Candidate creation are non-authoritative.
They must never create a DocumentRevision or mutate business truth automatically.

Canonical Working flow:

```text
observe/revalidate
→ DocumentChangeCandidate
→ Old / V / W
→ review/conflict
→ explicit human-confirmed command
→ immutable DocumentRevision N+1
```

OneDrive is a non-authoritative port. App-owned immutable storage + PostgreSQL CurrentHead remain
authoritative for accepted document revisions.

# ENGINEERING_GUARDRAILS.md — Valora Engineering Guardrails

**Created:** 2026-07-06
**Last reconciled:** 2026-09-23 (integration head/F2 progress + AI Master Plan authority reconciliation)
**Applies to:** All engineering work after Design Book v1.2-final
**v2.3 gate:** PR-00 — **CLOSED**; PR-01 / PR-02 / PR-03 / PR-04 contracts — **ACCEPTED** and merged.

## 1. Engineering Mode

Valora is in the **Engineering Phase**.

### Current phase (authoritative — live gate)

```text
VALORA UI/UX v2.3 implementation alignment

Accepted code baseline: `origin/main`
`27d1cc630f97cb9b56fbfbb4c5bc04d4be305cc6` (PR #31).
Canonical authority: `docs/design/VALORA_UIUX_HANDOFF_v2.3.md` plus
`docs/design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md` and the directly relevant addendum.

PR-00 through PR-04 — MERGED by PR #29 at `2775cb9a96a8067be3e558a84c96bb69566859cb`; PR #28 is the merged integration precursor. PR-01 remains a bounded prefix foundation, not complete coverage of all 16 stages. PR-02 browser acceptance and the PR-03 migration round-trip regression are part of the rollup now on `main`.
PR-05 — MERGED by PR #30 at `42a87fca1a90f5b94724a4ca0d7a83fa5dec1699`; OneDrive Personal only. OneDrive for Business and SharePoint remain deferred.
PR-06 — MERGED by PR #31 at `27d1cc630f97cb9b56fbfbb4c5bc04d4be305cc6`; read-only return/revalidation acceptance passed.
The authoritative per-layer status is `docs/implementation/VALORA_UIUX_V2_3_PR00_PR13_FEATURE_ACCEPTANCE_MATRIX.md`. Do not infer frontend, browser or E2E completion from merge status or backend acceptance.
Operational Frontend — implemented on Draft PR #32. At reconciliation head `d725bbc6…`, F2-PR-001/#34, F2-PR-002/#36 and F2-PR-003/#38 are merged on the integration branch and exact-head CI #454 is green; F2-PR-004…008 remain. The candidate is still unmerged to main and is not North-star product-completion evidence.
The original PR-07 direct OneDrive replacement execution is historical/blocked. Protected-value and Old/V/W conflict semantics remain reusable. New Working-copy change runtime must follow ADR 0045 and a task-specific implementation contract before coding. Release/Publishing and canonical stages 5–16 remain incomplete.
Software Completion — the full authorized North-star under the Unified Roadmap (Pre-case, Appraisal Core, Document Runtime, Release/Publishing, traceability/state/fidelity and exact-SHA E2E) must pass before Windows Preview. Historical PR-08–PR-13 labels are acceptance evidence, not current sequencing authority.
Windows Preview — `VALORA-WIN-PREVIEW-001` is the local UAT gate after Software Completion and before cloud staging. Preview packaging must not broaden or substitute for incomplete product scope.
Existing QC/approval/standalone-validation implementation is legacy debt: prevent expansion and do
not use it as the source for new navigation or Global Case State.
```

Agents must `git fetch origin` and verify live `origin/main`. Listed SHAs are evidence, not evergreen.

### Historical roadmap (completed slices)

```text
Sprint 0  — Repository Foundation          [historical]
Sprint 1  — Project + Master Data          [merged foundation]
Sprint 2  — Taxonomy + Asset Identity      [merged foundation]
Sprint 3  — Knowledge + Evidence           [merged foundation]
Sprint 4  — Workflow + Workbench           [merged foundation]
Sprint 5  — Document Engine + Intelligence [merged foundation]
Sprint 6+ — AI governance / production     [partial / deferred]
Sprint 10 — Design system, i18n, errors    [merged]
Sprint 11 — Live Workbench loop            [merged; readiness superseded by S12-R]
Sprint 12 — Excel import pipeline          [PR-001…PR-004 merged; Apply v1 frozen]
S12-R-001…008 — Remediation / recon        [merged to main]
S12-PR-004 — Apply Command & Provenance    [MERGED; engineering gate closed]
S13-PR-001 — Design authority reconciliation [merged / gate closed; main 7f7473e…]
S13-PR-002 — Legacy workbook/source artifact [merged / closed; main 137f8c5…]
S13-PR-003 — Structure discovery/row classification [merged / closed; main 2af7535…]
```

Sprint 0 “foundation only” boundaries are **historical**. They must not be stated as the current repository status.
S12-PR-003, S12-PR-004, S13-PR-002 and S13-PR-003 are **merged/complete** and must not be described as blocked or not started.

## 2. Design Authority

```text
docs/design/VALORA_UIUX_HANDOFF_v2.3.md
docs/design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md
directly relevant VALORA_UIUX_HANDOFF_v2.3_* addendum
accepted scoped ADR(s)
docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md
task-specific implementation contract
docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md
docs/design/* current contracts (including Excel staging §15, frozen s12-pr-004-v1)
docs/VALORA_PROJECT_HANDOFF.md
Historical reference only where not superseded:
  Design Book v1.2/v1.3/v1.4
  docs/remediation/S13_S16_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_REMEDIATION_PLAN.md
```

## 3. Module Boundaries

```text
backend/app/modules/project_master_data/
backend/app/modules/taxonomy_asset_identity/
backend/app/modules/knowledge_evidence/
backend/app/modules/workflow_workbench/
backend/app/modules/document_engine_intelligence/
backend/app/modules/ai_governance_security/
backend/app/modules/excel_import/
```

No module should depend on another without a clear application service or domain contract.

## 4. Source of Truth Rules

### Workbench

```text
Valora Workbench is the main workspace.
Vietnamese-first UX; Microsoft Fluent 2 light design compliance; desktop-first, data-heavy/table-first. Astryx may remain only as a low-level primitive if fully remapped and visually conformant.
```

### Word / Excel

```text
Word and Excel are input/output only.
They are not the source of truth.
Excel upload/validate target import batch + staging only.
Official promotion for S12 staging uses Apply (ADR 0029 / s12-pr-004-v1) — implemented.
S12 parser v1 remains `.xlsx` + fixed aliases for its historical upload path.
S13-PR-002 adds bounded `.xls`/`.xlsx` source adapters and immutable source artifacts;
S13-PR-003 adds deterministic structure discovery and row classification.
S13-PR-004 mapping-memory persistence/application services are implemented historical foundation.
The old S13-PR-005 API/UX sequence no longer authorizes current work; follow the Unified Roadmap OS-G0→OS-G7.
Any replacement of S12 Apply v1 still requires explicit authority and ADR review.
```

### Price

```text
Market Quote != Appraised Price.
Supplier quotes and appraised price decisions must remain separate.
```

### Evidence / Review

```text
Evidence is immutable or append-only.
ReviewDecision is append-only.
Corrections use ChangeRequest/Reversal, not silent edit/delete.
```

### AI

```text
AI is advisory only.
AI cannot approve official data or auto-apply staging.
AI cannot confirm mapping, identity, price, or activate knowledge.
AI output must be candidate/reviewed/audited.
AI/rules/providers/frontends submit typed proposals only and never call persistence mutations directly.
AITaskRun/DecisionEpisode provide task/learning provenance but do not replace domain truth or atomic audit.
Workflow-pattern inputs are domain commands and committed outcomes, never UI clickstream.
Temporary/autosave/unreviewed/failed/stale/rolled-back output is not positive learning evidence.
Human, system and ai_service principals are distinct; AI/system cannot impersonate human approval.
Gemini/DeepSeek (or other providers) are replaceable future gateway candidates only through the OS-G7 Task Registry/ModelPolicy/ProviderGateway gates in the AI Master Plan. Provider-backed runtime remains unauthorized until the applicable OS-G7 prerequisites and explicit task/provider authorization are satisfied.
```

### Adaptive Intake / Memory (v1.4 design authority and phased runtime)

```text
Column Mapping Memory and Asset Identity Memory are separate.
Workbook source/adapter and structure-discovery foundations are implemented by S13-PR-002/003.
Column Mapping Memory persistence/application services are implemented historical foundation.
RawAssetObservation is immutable; normalization never overwrites raw wording.
Human confirmation is required before reusable feedback or active knowledge.
No cross-organization learning. No per-click online training.
No direct bulk SQL into active knowledge from historical dossiers.
Public fixtures must be anonymized; real client files stay private.
.xls support requires a security/dependency spike before runtime adoption.
```

### Bounded automation readiness (ADR 0033–0034)

```text
ExecutionPolicy is deterministic, versioned and deny-by-default.
No R2 auto-draft/auto-stage/exception-only-review promotion in S13–S16.
Any future write-capable automation uses an allowlisted idempotent domain command
  with server tenant/RBAC/state/version checks and atomic required audit.
Final price, QC approval, signature and report/certificate release remain human-only.
Long-running production AI/extraction work must reuse the implemented durable `TaskJob`/`TaskJobAttempt`/worker boundary with lease/retry/timeout/cancellation/dead-letter and stale-generation protection; no second AI queue is permitted.
Provider fallback is task-specific and evaluated; deterministic/manual fallback remains complete.
Future agents use typed allowlisted tools and the same policy/command gates.
```

### Tenant Boundary

```text
Organization/tenant boundaries must be enforced server-side.
Frontend visibility is not security.
Fail closed on missing/invalid identity, inactive user/org, cross-tenant access.
```

## 5. Security Guardrails

```text
deny by default
least privilege
server-side authorization
short-lived tokens
refresh token rotation
no client-supplied identity spoofing (e.g. production X-User-Id)
temporary overrides must expire
API keys are hashed and shown once
secrets never stored in plaintext application tables
sensitive file access is logged
audit logs are append-only
```

## 6. Official Mutation Guardrails

### ADR 0028 restricted Workbench-gated fields

These fields must **not** be mutated via direct PATCH. They require the draft-commit command path:

```text
description
appraised_unit_price
review_status
validation_status
```

For those fields, do not introduce mutation paths that bypass:

```text
authenticated actor
permission check
workflow/project state check (e.g. Project.status == DRAFT for commit)
exact optimistic version match
human confirmation (Workbench Human Commit Gate)
command/application service
atomic AuditEvent in the same transaction as the official write
```

### Non-restricted official fields

Direct `PATCH /asset-lines/{id}` under `project:update` may still update non-restricted fields
(e.g. asset_name, quantity, unit_id, raw_price, currencies, brand_id, manufacturer_id) with
optimistic locking. That path is **outside** the R004 Human Commit Gate and does **not** share
the R004 single-command atomic-audit guarantee. Do not document it as blocked or as R004-gated.

Excel upload/parser/validation must not mutate `ProjectAssetLine` at all (staging only).

## 7. File / Excel Guardrails

```text
No unbounded whole-file materialization on Excel runtime path
No bare file.file.read() without size bound
No BytesIO(file.read()) whole-copy pattern
No list(ws.iter_rows()) materialization
Enforce request/file/ZIP/row/column/cell limits explicitly
Preserve prior staging generation when a new upload fails
Use generation fingerprint to prevent stale failure overwrite
Preserve immutable source artifact/checksum before adaptive analysis
Define recoverable database/object-storage partial-failure states
```

Do not overwrite:

```text
official generated documents
evidence files used in decisions
approved templates used in official rendering
audit-relevant files
```

## 8. Evidence Semantics (CI vs local)

```text
Local pytest skips for missing PostgreSQL are NOT PASS.
PostgreSQL concurrency/integration proof requires CI (or equivalent) with PostgreSQL.
Historical audit PASS for an earlier PR is not automatic READY for a later slice.
Documentation claims must match code + CI evidence for the cited SHA.
```

## 9. AI Guardrails

Do not implement:

```text
AI auto-approval
AI direct write to active KnowledgeVersion
AI workflow approval
AI price approval
AI document correction commit without human review
AI context bundle without tenant boundary check
AI provider call without audit
AI/provider/frontend direct database mutation
AI/system impersonation of a human actor or approval
learning from UI clickstream or temporary/autosave state
unregistered provider fallback or unbounded context/tool access
production AI job without idempotency, durable state and stale-result rejection
R2 capability promotion without task-specific accepted design, shadow evaluation and rollback proof
open-ended autonomous agent bypassing ExecutionPolicy/domain commands
```

## 10. Dependency Guardrails

Before adding major dependencies, check purpose, license, security, maintenance, architecture fit, ADR need.

## 11. Audit Expectations

Every PR is auditable against scope, Design Book compliance, security, tests, file changes, migration impact.

### Exact-head evidence guardrail

```text
Execution baseline = named branch + exact commit SHA + successful required CI on that exact SHA.
Parent/earlier CI is never evidence for a changed HEAD.
Docs-only changes are not exempt when the resulting commit becomes the baseline for downstream work.

Dependent implementation work must not start until its predecessor/baseline gate is green.
After implementation, the changed exact HEAD must pass all task-required focused gates and CI before
the task is considered complete or its dependent task is released.

If the reviewed/tested HEAD changes, previous CI/review evidence is retained as history but must not
be reported as exact-head acceptance for the new commit.
```

## 12. Merge Gate

A PR should not be merged if it:

```text
exceeds assigned task scope
implements invented domain logic
lacks required tests (or docs-only justification)
introduces secrets
weakens security or tenant isolation
bypasses ADR 0028 restricted-field human commit / command gates
creates irreversible data mutation without audit
treats local PG skips as PASS
starts S13 runtime without a separate owner-assigned task ID or from a baseline that does not match the task prompt
silently promotes an R2 capability or weakens current mapping/identity/alignment/Apply review gates
```
