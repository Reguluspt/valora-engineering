# ENGINEERING_GUARDRAILS.md — Valora Engineering Guardrails

**Created:** 2026-07-06
**Last reconciled:** 2026-07-13 (S12-R-007)
**Applies to:** All engineering work after Design Book v1.2-final

## 1. Engineering Mode

Valora is in the **Engineering Phase**.

### Current phase (authoritative)

```text
S12-R Remediation Closure
Active documentation task: S12-R-007
Next product task (blocked): S12-PR-003 Excel Staging Validation Engine
```

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
Sprint 12 — Excel import pipeline          [PR-001/002 merged; PR-003 blocked on S12-R]
S12-R-001…006 — Remediation                [merged to main]
S12-R-007 — Documentation reconciliation   [active]
```

Sprint 0 “foundation only” boundaries are **historical**. They must not be stated as the current repository status.

## 2. Design Authority

```text
Valora Design Book v1.2-final + v1.3 MVP completion addendum
docs/design/* contracts
docs/adr/*
docs/remediation/S12_R_PRE_VALIDATION_REMEDIATION_SLICE.md
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
Excel intake targets import batch + staging only.
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
AI output must be candidate/reviewed/audited.
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
starts S12-PR-003 before S12-R closure criteria are met
```
