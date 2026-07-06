# CODEX.md — Valora Engineering Rules

**Created:** 2026-07-06  
**Applies to:** All Codex-generated code in the Valora repository  
**Source of truth:** Valora Design Book v1.2-final

## 1. Source of Truth

Valora Design Book v1.2-final is the only source of truth for domain behavior.

Codex must not invent domain behavior.

When ambiguity appears:

```text
1. Check v1.2-final full package.
2. Check the corresponding completed slice.
3. Check v1.2-rc consolidation.
4. If still unclear, stop and request an ADR or Design Change Request.
```

## 2. Current Engineering Phase

Current phase:

```text
Engineering Phase / Sprint 0
```

Sprint 0 is repository foundation only.

## 3. Sprint 0 Allowed Scope

Codex may implement:

```text
monorepo structure
Docker/dev environment
FastAPI skeleton
React skeleton
worker skeleton
PostgreSQL/Redis/S3-compatible storage wiring
CI skeleton
lint/test baseline
environment config
health checks
empty DDD module boundaries
documentation and guardrails
```

## 4. Sprint 0 Forbidden Scope

Codex must not implement:

```text
Project CRUD
Master Data CRUD
Taxonomy logic
Asset identity logic
Knowledge logic
Evidence logic
Workflow logic
Workbench business UI
Document rendering
Document Intelligence/OCR
AI provider integration
AI task execution
Security business logic beyond skeleton
database domain models
business migrations
approval workflows
permission override logic
```

## 5. Hard Rules

Codex must follow these rules:

```text
No business/domain logic unless explicitly assigned.
No hidden assumptions.
No schema invented outside Design Book.
No AI auto-approval.
No official data mutation without command/audit path.
No tenant boundary bypass.
No secrets committed.
No hard-coded credentials except local placeholder values in .env.example.
No unrelated file changes.
No skipped tests.
No broad refactors unless requested.
No deleting existing guardrails.
```

## 6. Domain Non-Negotiables

These are permanent Valora rules:

```text
Valora Workbench is the main workspace.
Word/Excel are input/output, not source of truth.
Market Quote is not Appraised Price.
AI suggests; human reviews; system audits.
AI cannot approve official data.
Evidence is immutable or append-only.
ReviewDecision is append-only.
Organization/tenant boundaries are enforced.
No official data change without authorization, workflow approval where applicable, and audit trail.
```

## 7. Required Output After Every Task

Codex must report:

```text
Task ID
Files changed
Design source used
Tests run
Known limitations
Whether sprint scope was respected
Whether any ADR is needed
```

## 8. Stop Conditions

Codex must stop and ask for clarification when:

```text
A domain rule is missing.
A data model is unclear.
A permission rule is ambiguous.
The task requires changing architecture.
The task requires implementing outside current sprint.
The task requires adding a new dependency with architectural impact.
The task appears to conflict with v1.2-final.
A secret, credential, or production config is needed.
```

## 9. Pull Request Behavior

Each Codex PR must be small and reviewable.

Preferred PR size:

```text
one task
one responsibility
tests included
no unrelated cleanup
```

## 10. Test Requirement

Every implementation task must include tests or explicitly state why tests are not applicable.

For Sprint 0, at minimum:

```text
backend /health test
worker config test
frontend build/lint
CI smoke checks
```

## 11. Security Requirement

Codex must not:

```text
commit plaintext secrets
disable security checks
weaken guardrails
create cross-tenant shortcuts
log sensitive payloads
store tokens in code
expose hidden config values
```

## 12. ADR Requirement

Create or request an ADR when:

```text
new architectural dependency is introduced
repository structure changes materially
a Design Book ambiguity must be resolved
a security tradeoff is required
a convention becomes permanent
```

## 13. Final Reminder

Codex is an implementation assistant, not a domain designer.

If a behavior is not in the Design Book, Codex must not create it.
