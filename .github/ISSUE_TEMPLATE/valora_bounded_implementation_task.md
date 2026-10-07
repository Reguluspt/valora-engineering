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

Handoff state: `AUTHORIZED | HANDOFF PREPARED | HANDOFF DELIVERED | IN DEVELOPMENT | CANDIDATE READY | GATE REVIEW`.

Every new Dev/Codex assignment requires appropriate GitHub Issue/PR handoff evidence AND a complete copy/paste-ready Codex prompt delivered to the Product Owner under `.agents/skills/valora-dev-handoff/SKILL.md`. Preserve the populated CODEX MODEL block, bootstrap, compact OpenViking policy and all stricter existing rules. An Issue alone does not mean Codex received work. IN DEVELOPMENT only after the PO sends the prompt OR live candidate execution clearly appears.

- GitHub handoff evidence: <link>
- Complete Codex prompt delivered to PO: <delivery evidence>
- PO sent prompt / live candidate execution: <evidence or PENDING>

CANDIDATE READY requires frozen HEAD, mandatory checks, required reviews/adjudication and exact-head CI SUCCESS; GATE REVIEW means Gate Owner inspection, not certification.

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

### Definition of Ready — before implementation handoff

- [ ] predecessor certified
- [ ] authority accepted
- [ ] COMPLETE predicate known
- [ ] mutation commands known
- [ ] RBAC disposition known
- [ ] currentness/stale rule known
- [ ] downstream hold known
- [ ] API/read-model sufficient or bounded gap defined
- [ ] E2E acceptance matrix written
- [ ] forbidden scope written

Missing a critical item: **NO CODING — return to authority/design track**. For docs/tooling, map items to relevant process/tooling authority and acceptance with explicit N/A reasons; unresolved governing decisions block implementation.

### Stage slices / authority answers

`Authority → Runtime → Product Closure` only where appropriate; do not force three separate PRs.

| Authority question | Accepted answer / reference (or reasoned N/A for docs/tooling) |
| --- | --- |
| Business COMPLETE fact? | <...> |
| Prerequisite? | <...> |
| Currentness? | <...> |
| Human confirmation? | <...> |
| Mutation authority? | <...> |
| CAS? | <...> |
| Audit? | <...> |
| RBAC? | <...> |
| Next Action? | <...> |
| Downstream hold? | <...> |

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

Canonical flow (stop at this task's authorized boundary):

```text
AUTHORITY READY → DEDICATED WORKTREE → IMPLEMENT LOCALLY
→ T0 → T1 → T2 → REQUIRED T3 (when required)
→ LOCAL FINAL DIFF REVIEW → LOCAL SATURATION GATE → FIRST PUSH
→ DRAFT PR → FREEZE HEAD → REVIEWS + EXACT-HEAD CI → GATE OWNER
→ GUARDED MERGE → EXACT-MAIN CI → CERTIFICATION
```

### Local Saturation Gate — before first push

- [ ] bounded implementation complete
- [ ] T0 PASS
- [ ] T1 PASS
- [ ] T2 scope-appropriate lint/type/build/security PASS
- [ ] required T3 PASS (or contract-backed N/A with reason)
- [ ] local final diff reviewed
- [ ] changed paths bounded
- [ ] no debug/secrets/unwanted generated artifacts
- [ ] worktree clean except expected task changes; commit only reviewed paths before push

Record checks/results against the first-pushed candidate. Selective edit-loop checks do not waive final candidate checks. Reject `edit → push → CI fail → edit → push → CI fail` as normal workflow.

### Early Push Exception — NONE unless mandatory evidence is remote-only

Only for GitHub-only environment, remote-only secret/service, required cross-platform runner or remote-only integration/permission; complete locally possible work first. No mandatory gate is waived. “Push thử để xem CI nói gì” is invalid.

```text
EARLY PUSH EXCEPTION
Reason:
Remote-only evidence required:
Local work already completed:
Why local saturation cannot continue:
```

## Parallelism / integration serialization

`NO PARALLEL WORK | PARALLEL ALLOWED`

Hard WIP: **1 Stage N implementation/delivery + 1 Stage N+1 authority/design + 1 optional Stage N+2 read-only discovery**. Parallel task work must stay within this limit and use separate dedicated worktrees.

Track B may do inventory, proposal, PO decision table, rejected alternatives, risk/trade-off and preliminary acceptance matrix. It must NOT do migration, runtime implementation, public API activation, new RBAC grant, stage-cap advancement or UI activation. **No N+1 runtime before accepted authority** and satisfied implementation prerequisites. Track C remains read-only.

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

### Async CI / blocker record

After trigger: sanity-check run/SHA → record exact run/SHA → schedule condition check at a reasonable interval → move to other authorized work → resume gate only on terminal outcome. SUCCESS continues after exact-SHA verification; FAIL classifies the blocker; IN PROGRESS waits without unnecessary user notification. No repeated manual polling or blind rerun.

Use `docs/plan/VALORA_AGENT_OPERATING_PROTOCOL_V2.md` / CI failure taxonomy:

```text
CODE_TEST_FAILURE | SECURITY_VULNERABILITY | DEPENDENCY_FEED_FAILURE
INFRASTRUCTURE_TRANSIENT | ENVIRONMENT_MISMATCH | FLAKY_TEST | UNKNOWN
```

Record run/SHA/job, classification, log evidence, authorized remedy and rerun justification/attempt. Rerun only when classification and current policy justify it; UNKNOWN blocks pending diagnosis. Preserve failed attempts and security/dependency thresholds.

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

Task-authorized rebaseline, if any: <exact condition and authority; otherwise STOP>. If it changes source HEAD, renew required review and exact-head CI. Before freeze require clean worktree, bounded changed paths, valid links/references, docs/skill/template validation where available and `git diff --check` PASS. For a governance-only task, confirm no product/runtime files or workflow YAML changed.

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

## Delivery metrics

Use `docs/plan/VALORA_PM_OPERATING_PLAYBOOK_V1.md` / Delivery metrics. Record evidence rather than estimated savings:

```text
PO authorization → first local candidate (timestamps / elapsed):
First push → frozen candidate (timestamps / elapsed):
Post-first-push candidate renewals (replacement SHAs / count):
Exact-head CI attempts (all runs/reruns / SHAs):
Exact-main CI attempts (all runs/reruns / merge SHA):
Material findings after freeze:
E2E flaky failures:
Certified issue reopen:
Escaped security findings:
Baseline-drift stops:
First Push Maturity: YES | NO | UNKNOWN
```

First Push Maturity = candidate passed required local T0/T1/T2/T3 before first remote push; target **>=90% implementation tasks = YES**. Targets: post-first-push candidate renewals median <=1, exact-head CI attempts 1, exact-main CI attempts 1, certified issue reopen 0, escaped security findings 0. Count exceptions truthfully; unknown evidence is not YES. Targets never weaken gates. Do not claim time savings without measured data.

## Deferred follow-on tooling

Candidate-preflight/evidence scripts (`scripts/valora_candidate_preflight.py`, `scripts/valora_candidate_evidence.py`), CaseFactory, structured security-artifact automation and CI workflow changes are deferred incremental slices, not authorization from this template. PM-OPS-002 implements none of them. Risk-based reviewers, browser/live-stack E2E, real PostgreSQL proof when applicable, exact-head CI, expected-head guarded merge, exact-main CI, security/dependency thresholds, Gate Owner certification, server-authoritative truth and human professional decision boundaries remain binding.

## Required closeout

```text
PROJECT AUTHORITY READY: YES | NO
Task:
Baseline SHA / CI:
Changed paths:
Policy / behavior changed:
Local Saturation Gate:
Early Push Exception:
Handoff state / delivery evidence:
Dual-track / WIP and authority barriers:
Definition of Ready:
First Push Maturity / delivery metrics:
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
