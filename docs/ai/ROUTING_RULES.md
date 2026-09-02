# VALORA AI Routing Rules

**Status:** Coordination policy only — subordinate to repository authority  
**Goal:** Route work to the lowest-cost capable model while reserving ChatGPT for decisions and high-risk exceptions.

## 1. Plane separation

### ChatGPT — Control Plane

Use for:

- owner requirement clarification;
- business analysis;
- UX/product decisions;
- architecture and cross-domain tradeoffs;
- Task Packet creation;
- RED-risk decision gates;
- resolving ambiguous/conflicting authority;
- compact final review when explicitly required.

Do **not** default to ChatGPT for repository search, routine code edits, test execution, raw log analysis, or mechanical review.

### OpenCode — Execution Plane

Use for:

- repo inspection/search;
- implementation discovery;
- gap classification;
- code/docs/test changes;
- lint/build/test/security execution;
- migration/schema inspection;
- cross-review;
- Task Result generation.

## 2. Default worker profiles

### DeepSeek V4 Flash

Prefer for:

- repository inspection;
- gap maps / implementation inventory;
- focused code reading;
- test creation/repair;
- deterministic CRUD/pattern-following changes;
- independent review;
- documentation updates;
- regression triage with clear evidence.

### Muse Spark 1.2

Prefer for:

- multi-file implementation;
- debugging;
- frontend/component work;
- refactoring strictly inside authorized scope;
- codebase-oriented repair;
- implementation after an inspection packet already exists.

### Fallback

If a preferred model is unavailable, use the cheapest available model that can satisfy the task. Record the actual model in the Task Result. Model choice never changes repository authority or review requirements.

## 3. Risk classes

Every Task Packet must declare one of: `GREEN`, `YELLOW`, `RED`.

### GREEN — routine / bounded

Typical examples:

- typo/copy/docs correction;
- test additions for already-defined behavior;
- small UI wiring following an established component pattern;
- low-risk bug fix with obvious root cause and no authority change;
- mechanical code cleanup required by lint within task scope;
- small deterministic implementation entirely inside one established contract.

GREEN must **not** touch security, tenant behavior, official mutation semantics, schema/data migration, authority, price semantics, immutable evidence, human gates, AI write capability, or architectural dependencies.

Default route:

```text
OpenCode worker
  -> relevant tests/gates
  -> cheap-model review when code changed
  -> PASS result
  -> close without ChatGPT code review unless blocked/deviated
```

### YELLOW — implementation complexity, authority already clear

Typical examples:

- new API/UI behavior defined by an accepted contract;
- multi-file change within one bounded context;
- state-management change with established semantics;
- new application service following existing authority;
- non-destructive migration explicitly specified by accepted design;
- integration work with known boundaries;
- substantial bug repair that does not change product/domain policy.

Default route:

```text
ChatGPT-created Task Packet
  -> OpenCode inspection
  -> DeepSeek or Muse implementation
  -> different-model cross-review when practical
  -> required tests/gates
  -> compact Task Result
  -> ChatGPT sees only Control Plane Summary unless escalation/review requested
```

### RED — decision/security/domain/architecture sensitive

RED includes any task that may change or determine:

- product/domain behavior not already explicit;
- architecture or bounded-context ownership;
- tenant/auth/RBAC/security behavior;
- official mutation boundaries;
- human confirmation/approval gates;
- audit/append-only/immutable evidence semantics;
- appraised-price / quote / evidence semantics;
- destructive/transformative data migration;
- AI approval/write authority or ExecutionPolicy scope;
- schema reconciliation with material data risk;
- new major dependency/provider with security/architecture impact;
- document/signature/release/QC authority;
- conflict between current request, authority, and live implementation;
- anything requiring a new ADR/design change.

Default route:

```text
ChatGPT / owner decision first
  -> approved Task Packet / ADR reference
  -> OpenCode implementation
  -> independent cross-review
  -> full relevant tests/gates
  -> compact result + decision evidence
  -> ChatGPT final gate before owner merge/release action
```

A cheap model may inspect a RED task and collect evidence, but it must not invent the missing decision.

## 4. Complexity does not equal risk

A large but mechanically defined test migration can be YELLOW.
A one-line change to tenant authorization or official price mutation is RED.

Classify by **consequence and decision authority**, not diff size.

## 5. Worker/reviewer pairing

Preferred patterns:

```text
DeepSeek implements -> Muse reviews
Muse implements     -> DeepSeek reviews
```

For GREEN docs-only/mechanical changes, a second-model review may be omitted if tests/gates and diff are trivially auditable.

For YELLOW code changes, cross-review is strongly preferred.

For RED changes, independent review is mandatory unless the owner explicitly records an exception.

Reviewer should receive:

- Task Packet;
- exact changed files/diff;
- test/gate output summary;
- relevant authority refs.

Reviewer does **not** need the implementer's full conversation history.

## 6. Escalation matrix

| Situation | Action |
|---|---|
| Behavior already defined; implementation missing | stay OpenCode |
| Existing pattern + small bug | stay OpenCode |
| Test failure with local, deterministic cause | stay OpenCode and repair |
| Task scope insufficient | BLOCKED -> ChatGPT/owner |
| Authority conflict/ambiguity | BLOCKED -> ChatGPT/owner |
| Business rule choice required | RED -> ChatGPT/owner |
| New ADR likely | RED -> ChatGPT/owner |
| Tenant/auth/security semantics change | RED -> ChatGPT/owner |
| Human/AI mutation authority changes | RED -> ChatGPT/owner |
| Destructive migration/data rewrite | RED -> ChatGPT/owner |
| Reviewer and implementer disagree on domain meaning | BLOCKED -> ChatGPT/owner |
| Tests fail due to environment only | report evidence; do not claim PASS |
| Canonical docs appear stale vs merged main | gather evidence, then BLOCKED if authorization depends on stale text |

## 7. ChatGPT token gate

Do not send raw execution context to ChatGPT by default.

Send only the `CONTROL_PLANE_SUMMARY` from `TASK_RESULT.md` when all are true:

```text
STATUS = PASS
AUTHORITY_DEVIATION = NONE
SCOPE_DEVIATION = NONE
ADR_REQUIRED = NO
SECURITY_RISK = NONE
UNRESOLVED = NONE
```

Send additional evidence only when one of those fields is non-clean or ChatGPT/owner asks for it.

## 8. No-chatGPT fast path

A task can complete without ChatGPT re-review when:

- risk = GREEN;
- exact authority is already explicit;
- implementation stays in scope;
- tests/gates pass with valid evidence;
- reviewer verdict is PASS when review is required;
- no ADR/security/domain ambiguity exists;
- owner merge policy does not require a separate ChatGPT gate.

This is the primary token-saving path.

## 9. Reclassification

Any worker/reviewer may increase risk (`GREEN -> YELLOW -> RED`) when new evidence appears.

Do not silently downgrade risk. A downgrade requires an explicit rationale in the Task Result and, for RED -> lower, Control Plane/owner approval.

## 10. Owner control

The human owner retains final control over:

- product decisions;
- authorization of new runtime/task scope when required by repository rules;
- ADR/design approval;
- PR readiness;
- merge/release actions.

AI routing optimizes execution cost; it does not transfer ownership or approval authority.
