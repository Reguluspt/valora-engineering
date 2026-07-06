# ADR 0005 - Audit and Event Persistence Strategy

## Status

Proposed

## Context

Valora guardrails require no official data change without authorization and audit trail. The Sprint 1 alpha design maps Project and Master Data mutations to commands and events. Sprint 1 needs a minimal audit/event persistence policy without implementing a full workflow or event-sourcing platform.

## Decision

Implement minimal append-only audit/event persistence for Sprint 1 mutations.

Policy:

- Every Project and Master Data mutation command persists an audit/event record in the same transaction as the state change.
- Audit/event records are append-only.
- Audit/event records include at minimum:
  - event id
  - organization id when scoped
  - actor user id
  - command name
  - event name
  - entity type
  - entity id
  - timestamp
  - request/correlation id when available
  - before/after summary or field-level change summary when safe
- Sensitive payloads, secrets, password hashes, and file contents are never stored in audit records.
- Audit/event records support traceability, not cross-module orchestration in Sprint 1.

Sprint 1 event coverage follows the alpha cross-reference map for:

- Project commands/events.
- Customer and Supplier commands/events.
- Reference data create events.
- Signer profile create/update events.
- User role assignment/revocation audit where implemented.

## Consequences

- Sprint 1 mutations have an auditable command path.
- Implementation avoids inventing a full event bus before workflow needs are designed.
- Future sprints can consume or extend audit/event records without changing the append-only rule.

## Design References

- `CODEX.md`
- `ENGINEERING_GUARDRAILS.md`
- `valora-design-book-v1.2-final-full-package/05_FINAL_HANDOFF/04_FINAL_IMPLEMENTATION_GUARDRAILS.md`
- `v1.2-alpha-project-master-data-completed/04_DOMAIN/04A_PROJECT_COMMANDS_EVENTS.md`
- `v1.2-alpha-project-master-data-completed/04_DOMAIN/04B_MASTER_DATA_COMMANDS_EVENTS.md`
- `v1.2-alpha-project-master-data-completed/15_CROSS_REFERENCE_MAP.md`

## Sprint 1 Scope Impact

This ADR unblocks implementing command/audit paths for Project and Master Data without waiting for the Workflow sprint.

## What Is Explicitly Not Implemented Yet

- No audit table.
- No event table.
- No event bus.
- No background consumers.
- No workflow engine.
- No cross-module event handling.

## Risks / Follow-up

- Confirm exact audit table name and indexes during migration design.
- Confirm how much before/after data is safe and useful for each mutation.
- Revisit event dispatch when Sprint 4 Workflow and Workbench are implemented.
