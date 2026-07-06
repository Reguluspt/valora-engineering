# ENGINEERING_GUARDRAILS.md — Valora Engineering Guardrails

**Created:** 2026-07-06  
**Applies to:** All engineering work after v1.2-final

## 1. Engineering Mode

Valora has moved from Design Phase to Engineering Phase.

Engineering may now start with:

```text
Sprint 0 — Repository Foundation
```

## 2. Design Authority

The design authority is:

```text
Valora Design Book v1.2-final full package
```

Implementation order follows:

```text
Sprint 0 — Repository Foundation
Sprint 1 — Project + Master Data
Sprint 2 — Taxonomy + Asset Identity
Sprint 3 — Knowledge + Evidence
Sprint 4 — Workflow + Workbench
Sprint 5 — Document Engine + Document Intelligence
Sprint 6 — AI Governance + Security Hardening
```

## 3. Sprint 0 Boundary

Sprint 0 creates the technical foundation only.

Allowed:

```text
repository structure
backend skeleton
frontend skeleton
worker skeleton
local infrastructure
CI baseline
docs
guardrails
empty module boundaries
```

Forbidden:

```text
business APIs
domain tables
business migrations
approval workflows
AI execution
document rendering
Workbench implementation
security admin business logic
```

## 4. Module Boundaries

Backend module boundaries:

```text
backend/app/modules/project_master_data/
backend/app/modules/taxonomy_asset_identity/
backend/app/modules/knowledge_evidence/
backend/app/modules/workflow_workbench/
backend/app/modules/document_engine_intelligence/
backend/app/modules/ai_governance_security/
```

No module should depend on another module directly without a clear application service or domain contract.

## 5. Source of Truth Rules

### Workbench

```text
Valora Workbench is the main workspace.
```

### Word / Excel

```text
Word and Excel are input/output only.
They are not the source of truth.
```

### Price

```text
Market Quote != Appraised Price.
Supplier quotes and appraised price decisions must remain separate.
```

### Evidence

```text
Evidence is immutable or append-only.
Do not overwrite official evidence.
```

### Review

```text
ReviewDecision is append-only.
Corrections use ChangeRequest/Reversal, not edit/delete.
```

### AI

```text
AI is advisory.
AI cannot approve official data.
AI output must be candidate/reviewed/audited.
```

### Tenant Boundary

```text
Organization/tenant boundaries must be enforced server-side.
Frontend visibility is not security.
```

## 6. Security Guardrails

Engineering must preserve these security rules:

```text
deny by default
least privilege
server-side authorization
short-lived tokens
refresh token rotation
temporary overrides must expire
API keys are hashed and shown once
secrets are never stored in plaintext application tables
sensitive file access is logged
audit logs are append-only
```

## 7. Data Guardrails

Do not introduce data mutation paths that bypass:

```text
command/application service
validation
permission check
workflow state check
audit log
```

## 8. File Guardrails

Do not overwrite:

```text
official generated documents
evidence files used in decisions
approved templates used in official rendering
audit-relevant files
```

Use archive/revision flows when needed.

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

Before adding major dependencies, check:

```text
purpose
license
security implications
maintenance health
fit with architecture
ADR needed or not
```

## 11. Audit Expectations

Every PR is auditable against:

```text
scope
Design Book compliance
security
tests
file changes
migration impact
```

## 12. Merge Gate

A PR should not be merged if it:

```text
exceeds sprint scope
implements invented domain logic
lacks required tests
introduces secrets
weakens security
bypasses tenant boundary
creates irreversible data mutation without audit
```
