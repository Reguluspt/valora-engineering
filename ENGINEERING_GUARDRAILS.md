# ENGINEERING_GUARDRAILS.md — Valora Engineering Guardrails

**Created:** 2026-07-06
**Last reconciled:** 2026-07-15 (S13-PR-001)
**Applies to:** All engineering work after Design Book v1.2-final

## 1. Engineering Mode

Valora is in the **Engineering Phase**.

### Current phase (authoritative — live gate)

```text
Post S12-PR-004 — Design Authority Reconciliation

S12-PR-004 is MERGED (main squash evidence a9f2c1e…; main CI 29419008129 PASS).
Its engineering gate is CLOSED.

While origin/main does not contain merged S13-PR-001 documentation authority,
S13-PR-001 is the only active task (docs-only).
No Sprint 13 runtime implementation is authorized.

After independent design audit PASS and owner merge of S13-PR-001,
S13-PR-002 becomes the next candidate runtime slice from the accepted main baseline.
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
S13-PR-001 — Design authority reconciliation [active docs-only until merge]
```

Sprint 0 “foundation only” boundaries are **historical**. They must not be stated as the current repository status.
S12-PR-003 and S12-PR-004 are **merged/complete** and must not be described as blocked or not started.

## 2. Design Authority

```text
Valora Design Book v1.2-final
+ v1.3 MVP completion addendum
+ v1.4 Adaptive Intake / Knowledge Memory addendum
docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md
docs/design/* contracts (including Excel staging §15, frozen s12-pr-004-v1)
docs/adr/* (including ADR 0028–0032)
docs/remediation/S13_S16_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_REMEDIATION_PLAN.md
docs/VALORA_PROJECT_HANDOFF.md
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
Vietnamese-first UX; Astryx design compliance.
```

### Word / Excel

```text
Word and Excel are input/output only.
They are not the source of truth.
Excel upload/validate target import batch + staging only.
Official promotion for S12 staging uses Apply (ADR 0029 / s12-pr-004-v1) — implemented.
S12 parser v1 remains .xlsx + fixed aliases; Adaptive Intake v2 (.xls/.xlsx, mapping memory)
is design authority only until S13 runtime PRs are authorized.
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
Gemini/DeepSeek (or other providers) are future gateway candidates only after
deterministic S13–S15 foundations and ADR-governed provider integration.
```

### Adaptive Intake / Memory (v1.4 design authority)

```text
Column Mapping Memory and Asset Identity Memory are separate.
RawAssetObservation is immutable; normalization never overwrites raw wording.
Human confirmation is required before reusable feedback or active knowledge.
No cross-organization learning. No per-click online training.
No direct bulk SQL into active knowledge from historical dossiers.
Public fixtures must be anonymized; real client files stay private.
.xls support requires a security/dependency spike before runtime adoption.
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
```

## 10. Dependency Guardrails

Before adding major dependencies, check purpose, license, security, maintenance, architecture fit, ADR need.

## 11. Audit Expectations

Every PR is auditable against scope, Design Book compliance, security, tests, file changes, migration impact.

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
starts S12-PR-004 before S12-R-008 authority merges to main
```
