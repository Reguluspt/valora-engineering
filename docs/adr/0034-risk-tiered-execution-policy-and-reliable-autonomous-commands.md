# ADR 0034 — Risk-Tiered Execution Policy and Reliable Autonomous Commands

## Status

Accepted — owner-requested design authority, 2026-07-16.

This ADR defines a future-safe execution boundary. It does not activate autonomous behavior. Until a task-specific evaluated release explicitly promotes a capability, existing human-confirmation and human-Apply rules remain binding.

## Context

Valora must eventually automate repetitive, reversible work without allowing AI to bypass RBAC, workflow state, optimistic locking, validation, audit or professional approval.

The current runtime has useful foundations, including domain APIs, workflow records, staging/drafts, atomic command paths for selected official mutations and a worker boundary. It does not yet provide:

- a central deterministic policy decision for AI/system actions;
- a typed action proposal contract;
- a reliable asynchronous task/job runtime;
- a transactionally durable handoff from database state to background work;
- capability-specific shadow, promotion, rollback and kill-switch controls;
- a safe principal model distinguishing human, system and AI-service execution;
- a guarantee that every future AI-triggered write uses an idempotent domain command with atomic audit.

Scattering `if ai...` checks across endpoints would make authorization and rollback unreviewable. Allowing a future agent or provider to call database persistence directly would violate Valora's source-of-truth and human-control rules.

## Decision

### 1. AI produces typed action proposals only

An AI task, deterministic rule or future agent may produce an `ActionProposal` that names:

```text
task_type / contract_version
proposed_command
target references and expected versions
bounded proposed payload
evidence/context manifest reference
proposal source and version
calibrated system confidence inputs
reversibility classification
risk tier
```

An `ActionProposal` is not authorization and cannot mutate persistence.

AI providers, prompt code and frontend clients must never hold a database session or call repository mutation methods directly.

### 2. Introduce a deterministic Execution Policy

`ExecutionPolicy` is an application/domain service controlled by versioned code and policy data, not by model output.

It evaluates at minimum:

```text
authenticated/server principal
organization and customer policy
registered task and proposed command
risk tier and reversibility
target state and expected row/generation version
validation and blocking issues
source/evidence completeness
profile/alias status and structure drift
evaluation release and calibrated metrics
feature flag / capability status
rate, cost and operational limits
```

The policy returns exactly one typed outcome:

```text
allow_read
allow_suggest
allow_draft
allow_stage
require_human_review
blocked
```

Every result includes reason codes and `policy_version`. Unknown task, state, scope or evidence fails closed.

### 3. Use explicit risk tiers

| Tier | Examples | Maximum future automation |
| --- | --- | --- |
| R0 — read/explain | search, retrieve, explain validation | may run automatically within tenant/data policy |
| R1 — propose | mapping/identity/alignment suggestions | may run automatically; no mutation |
| R2 — reversible work | prepare draft, candidate or staging | only after task-specific evaluation, capability promotion and rollback proof |
| R3 — official mutation | promote official data, material workflow transition | authenticated human command and existing domain gates |
| R4 — professional approval | final price, QC approval, signature, report/certificate release | always human; automation prohibited |

Current S13–S16 baseline remains R0/R1 plus explicit human confirmation. This ADR does not promote any R2 capability.

### 4. Preserve principal and delegation identity

Execution provenance distinguishes:

```text
human
system
ai_service
```

An AI/system principal cannot impersonate a human. A command records both the initiating principal and, when applicable, the authenticated human who requested or approved it.

Client-supplied actor, tenant or approval claims are never trusted.

### 5. All writes use domain commands and one unit of work

Any policy-authorized write must execute through an allowlisted application/domain command that enforces:

- server-side tenant and RBAC checks;
- target workflow/state guards;
- optimistic row or generation version checks;
- idempotency;
- validation and evidence requirements;
- one transaction for state mutation and required audit/decision records;
- a safe before/after or reference-based audit summary.

Existing legacy endpoints are not automatically eligible for AI/system execution. A path must be audited and explicitly registered before ExecutionPolicy may return a write-capable result for it.

### 6. Use a reliable asynchronous execution boundary

Long-running parsing, extraction, retrieval and AI calls use a durable job contract rather than an untracked in-request background action.

The target architecture includes:

```text
transactional outbox
durable task/job record
append-only attempts
lease/claim with expiry
idempotency key
bounded retry/backoff
timeout and cancellation
dead-letter / exception-review state
generation token for stale-result rejection
correlation and causation identifiers
```

Publishing a task request and committing its source state must not leave an invisible gap. Outbox dispatch is at-least-once; consumers are idempotent.

### 7. Reconcile database and object storage failures

Source/result artifacts use explicit pending/available/failed/orphaned states or an equivalent recoverable protocol.

The implementation must define behavior for:

- object write succeeds, database commit fails;
- database reservation succeeds, object write fails;
- checksum mismatch;
- retry after timeout with an unknown provider outcome;
- stale generation completes after a replacement upload;
- cleanup of unreferenced objects after a retention window.

No prior reviewed generation is destroyed by a failed retry.

### 8. Register capabilities and feature controls

Automation is enabled per registered capability, not by a global “AI on” switch.

Conceptual scope:

```text
organization
task type / command
customer and template where relevant
minimum contract/model/policy versions
mode
effective period
kill switch
```

Modes are:

```text
disabled
observe
suggest
shadow
auto_draft
auto_stage
exception_only_review
```

`auto_draft`, `auto_stage` and `exception_only_review` require a future task-specific design/release decision. They are not enabled by repeated confirmations alone.

### 9. Promotion is evidence-based and reversible

Promotion requires at minimum:

- a versioned evaluation corpus with leakage controls;
- a minimum number of distinct dossiers/time windows appropriate to the task;
- acceptable correction and false-high-confidence rates;
- no unresolved drift or conflict class;
- rollback and kill-switch proof;
- explicit owner-approved release metadata;
- continued human gates for R3/R4.

Model self-confidence and raw confirmation count are insufficient.

Policy automatically degrades to review/blocked when source structure, task contract, provider/model, rule, retriever or data distribution moves outside the evaluated release envelope.

### 10. Shadow mode precedes reversible automation

In shadow mode, Valora records what the capability would have proposed or executed but makes no write. The result is compared with the independent human outcome.

Shadow evidence is evaluation data, not positive learning evidence unless a committed human decision separately confirms the outcome under ADR 0033.

### 11. Fallback behavior is task-specific

The deterministic/manual path remains available when AI is unavailable.

Provider failover is allowed only when the task registry explicitly permits the fallback model/version and the release gate evaluated that path. High-risk or semantically different tasks fall back to deterministic/manual review rather than silently changing providers.

### 12. Future agents use the same boundary

A future agent orchestrator, if approved, may call only typed read tools and submit registered `ActionProposal` objects. It receives explicit budgets, step limits, tenant context and tool allowlists.

It cannot bypass ExecutionPolicy, domain commands, human gates or job/audit contracts.

## Conceptual records and services

```text
ActionProposal
ExecutionPolicy
ExecutionPolicyDecision
AutomationCapabilityRelease
DurableTaskJob
TaskJobAttempt
TransactionalOutboxMessage
ExceptionReviewItem
```

The exact persistence split is implementation-task specific. The boundaries and invariants are mandatory.

## Commands and events

```text
EvaluateActionProposal
SubmitAuthorizedDomainCommand
PromoteAutomationCapability
SuspendAutomationCapability
CancelDurableTaskJob
RetryDurableTaskJob

ActionProposalEvaluated
AutomationCapabilityPromoted
AutomationCapabilitySuspended
DurableTaskQueued
DurableTaskAttempted
DurableTaskCompleted
DurableTaskFailed
StaleTaskResultDiscarded
```

## Consequences

### Positive

- Automation rights are reviewable in one deterministic control plane.
- AI/provider changes cannot bypass domain invariants.
- Low-risk automation can be promoted gradually without weakening official approval.
- Retries, timeouts and provider failures are recoverable and auditable.
- A future agent can be added as a constrained caller rather than a second application architecture.

### Cost

- Requires command hardening for any legacy path selected for automation.
- Requires outbox/job persistence and worker implementation before production AI runtime.
- Requires capability release, shadow evaluation and operational dashboards.

## Compatibility and supersession

- ADR 0028/0029 official mutation and Apply gates remain authoritative.
- ADR 0030 mapping confirmation, ADR 0031 identity confirmation and ADR 0032 alignment/bootstrap review remain mandatory.
- This ADR creates a future extension point; it does not silently change current APIs or lifecycle states.
- A future relaxation from human review to R2 `auto_draft`/`auto_stage` requires a task-specific accepted design change and evaluated release.

## Acceptance gates

- AI/provider/frontend code cannot call persistence mutation repositories directly.
- Unknown actions and contexts receive a deny/review result.
- Policy decisions include reason and version and are auditable.
- A write-capable path uses an idempotent command with tenant/RBAC/state/version checks and atomic audit.
- Outbox/job retry cannot duplicate a domain mutation.
- A stale task generation cannot overwrite a newer source/result generation.
- Kill switch and rollback are tested per promoted capability.
- R3/R4 actions remain human-controlled.
- Provider failure leaves a complete deterministic/manual path.

## Non-goals

- No R2 capability is promoted in S13–S16 by this ADR alone.
- No AI price approval, QC approval, signature or release is allowed.
- No open-ended autonomous agent is implemented.
- No migration of every legacy API into a command bus is required at once; only paths selected for automation must be hardened before use.
