---
name: VALORA bounded implementation task
about: Create one authority-bounded Valora implementation task with exact baseline, scope, evidence and Gate Owner ownership.
title: "VALORA-TASK-<ID> — <bounded outcome>"
labels: ""
assignees: ""
---

## Status

`AUTHORIZED IMPLEMENTATION TASK | AUTHORITY REQUIRED`

> Do not begin implementation while authority is missing or the live baseline conflicts with this contract.

## Objective

<One coherent, observable outcome.>

## Certified baseline

- main: `<40-character SHA>`
- CODEX blob: `<SHA>`
- exact-main CI: `<run/number>` — `COMPLETED / SUCCESS` on the exact baseline SHA
- predecessor / prerequisite: `<CERTIFIED/CLOSED checkpoint>`

**LIVE REPOSITORY WINS.**

## Risk

`Low | Medium | High/Product/Security` — <reason>.

For Medium: independent reviewer `REQUIRED | NOT REQUIRED` because <material reason>.

For High/Product/Security: freeze one HEAD, two independent read-only reviewers on the same exact HEAD, Gate Owner review, exact-head CI and exact-main post-merge certification are required unless stronger current authority applies.

## Authority contract

Named governing authority only; do not copy full policy/history.

- Product Owner decision: <if applicable>
- `CODEX.md`: <applicable sections>
- `ENGINEERING_GUARDRAILS.md`: <applicable invariant boundary>
- ADR / design / implementation contract: <exact references>
- current supporting process: `docs/plan/VALORA_AGENT_OPERATING_PROTOCOL_V2.md`

## Task-specific references

- <exact document section>
- <affected code path>
- <affected tests>

## Frontend Architecture applicability

`N/A | APPLIES` — <reason>.

If `APPLIES`, name `docs/architecture/VALORA_FRONTEND_ARCHITECTURE_RULE.md` and select the applicable frontend PR checklist checks in Acceptance.

## Allowed scope

- <file/subsystem/behavior>
- <file/subsystem/behavior>

## Forbidden scope

Explicitly list later gates and adjacent behavior that this task must not open.

- <forbidden scope>
- <downstream gate not authorized>

## Behavioral / authority delta

<Only the task-specific behavior or authority already accepted for this bounded slice. Do not invent missing domain decisions.>

## Local-first work package

- dedicated task worktree;
- branch: `<branch>`;
- one coherent capability/authority boundary;
- preserve unrelated work;
- T0/T1/selective T2 in edit loops;
- T3 only when risk/contract requires it;
- GitHub remains final review/integration/certification source of truth.

## Parallelism / integration serialization

`NO PARALLEL WORK | PARALLEL ALLOWED`

Owned paths/dependencies: <...>

Final freeze/review/CI serialization requirements: <...>

Treat workflows, CODEX/process authority, migrations/schema, shared APIs, RBAC, shared selectors and root dependencies/config as shared boundaries.

## Acceptance

- [ ] <observable outcome>
- [ ] scope is bounded to Allowed Scope
- [ ] Forbidden Scope remains unchanged/unavailable
- [ ] tenant/RBAC/security/audit/idempotency invariants remain correct where applicable
- [ ] frontend architecture checks selected when applicable
- [ ] documentation truth reconciled only where authorized

## Verification

### T0 — focused edit loop

- <checks>

### T1 — affected subsystem

- <regression checks>

### T2 — static/build/security

- <lint/type/build/security checks>

### T3 — full/real-stack/E2E when required

- <required evidence or N/A with reason>

### T4 — repository evidence

- exact-head PR CI on frozen candidate: REQUIRED unless current authority says otherwise
- exact-main post-merge CI on captured merge SHA: REQUIRED when integration/certification is part of this task

Skips are skips, never PASS.

## Stop conditions

Stop and report the next permitted action on:

- baseline drift;
- missing/conflicting authority;
- unmet prerequisite;
- unapproved scope expansion;
- security/tenant/RBAC/audit/idempotency ambiguity;
- shared schema/API/process collision;
- required reviewer unavailable;
- changed frozen HEAD;
- CI evidence not tied to the required exact SHA.

Before freeze: fetch/reverify live repository and return `BASELINE_DRIFT` rather than carrying stale evidence forward.

## GitHub candidate

- create Draft PR only unless this task explicitly delegates a later transition;
- use `Refs #<this issue>` unless automatic closure before certification is intentionally desired;
- freeze one clean candidate HEAD;
- post raw evidence and limitations;
- do not Mark Ready or merge unless explicitly delegated.

## Integration ownership

### Dev / Codex

- implementation;
- bounded verification;
- frozen candidate;
- reviewer packet/adjudication when required;
- Draft PR;
- exact-head CI;
- `READY FOR GATE REVIEW: YES | NO`.

### Gate Owner

- live Gate Review;
- authorized Ready transition;
- expected-head guarded squash merge;
- capture merge SHA;
- require exact-main CI SUCCESS on that SHA;
- certification comment;
- Issue closure;
- release only the next already-authorized bounded slice.

## Completion semantics

Certification means:

- <exact scope that becomes certified>.

Certification does **not** mean:

- <downstream/product/runtime authority not granted>.

## Required closeout

```text
PROJECT AUTHORITY READY: YES | NO
Task:
Baseline SHA / CI:
Changed paths:
Policy / behavior changed:
Raw checks:
Limitations / skips:
Frozen HEAD:
Required review evidence:
Exact-head CI:
Draft PR:
Runtime/product authority changed:
Forbidden/downstream scope changed: NO
READY FOR GATE REVIEW: YES | NO
```
