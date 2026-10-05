# VALORA PM Operating Playbook v1

**Lifecycle/status:** CURRENT SUPPORTING PM OPERATING TOOLING — 2026-10-05.
**Authority role:** Process and delivery tooling only. This document creates no product, domain, runtime, deployment, provider, RBAC, security-policy, migration or downstream-gate authority.

This playbook operationalizes the current repository process for the Project Manager / Gate Owner. It is subordinate to live Product Owner decisions, `CODEX.md`, `ENGINEERING_GUARDRAILS.md`, accepted scoped authority and the current task contract.

## Canonical references

- `CODEX.md`
- `ENGINEERING_GUARDRAILS.md`
- `docs/plan/VALORA_AGENT_OPERATING_PROTOCOL_V2.md`
- `docs/plan/VALORA_COMPACT_TASK_CONTRACT_TEMPLATE.md`
- `.agents/skills/valora-live-authority-bootstrap/SKILL.md`
- `.agents/skills/valora-session-bootstrap/SKILL.md`
- `.agents/skills/valora-dev-handoff/SKILL.md`
- `.agents/skills/valora-high-risk-gate-review/SKILL.md`
- `.agents/skills/valora-integration-closeout/SKILL.md`
- `.agents/skills/valora-worktree-resume/SKILL.md`
- `docs/architecture/VALORA_FRONTEND_ARCHITECTURE_RULE.md` when frontend scope applies.

GitHub is the source of truth for review, CI, integration and certification. Local state, chat, memory, handoff prose and historical documents cannot certify live repository state.

## 1. Operating model

Every bounded delivery slice follows:

```text
Authority
→ Rebaseline
→ Compact Task Contract
→ Dev/Codex handoff
→ Bounded implementation
→ Freeze one candidate HEAD
→ Required review + exact-head CI
→ Gate Owner review
→ Expected-head guarded integration
→ Exact-main CI
→ Certification / closure
→ Rebaseline
→ Next already-authorized slice OR stop for authority
```

A task is not complete because development is finished, a Draft PR is green or a PR has merged. Certification requires the exact post-merge `main` SHA to pass the required exact-main CI.

## 2. Responsibility model

### Product Owner

Owns product/domain decisions, acceptance of authority proposals and decisions that are not already authorized. Roadmap order does not substitute for Product Owner authority.

### PM / Gate Owner

Owns:

- live authority bootstrap and rebaseline;
- task decomposition and risk tier;
- the Compact Task Contract;
- Dev/Codex handoff;
- Gate Review;
- authorized Draft → Ready transition;
- expected-head guarded integration;
- exact-main certification and Issue closure;
- release of the next already-authorized bounded slice.

The Gate Owner must not invent a later product gate.

### Dev / Codex

Owns bounded implementation, local-first verification, candidate evidence, Draft PR, frozen HEAD, reviewer packet/adjudication when required and exact-head CI evidence.

Unless the task explicitly delegates integration, Dev/Codex does not Mark Ready, merge or certify.

### Independent reviewer

Reviews one exact frozen candidate read-only. Required reviewers must inspect the same HEAD. A changed HEAD invalidates prior candidate review evidence.

## 3. Gate Owner session startup

At a fresh session and after a material checkpoint, rebaseline in this order:

```text
live repository
→ main SHA
→ CODEX blob
→ exact-main CI head/completion/SUCCESS
→ current Product Gate
→ active Issue / PR / task branch
→ applicable named authority
→ conflicts
→ next authorized action
```

Return:

```text
PROJECT AUTHORITY READY: YES | NO
```

Rebaseline after at least:

- merge;
- exact-main CI result;
- Product Gate close;
- ADR acceptance;
- material blocker or scope change;
- resume where live state may have changed.

A baseline mismatch or missing prerequisite is a stop condition. Do not silently replace the task baseline and continue.

## 4. Forming a bounded task

Do not issue a generic task such as “continue Valora”. A valid task has one coherent authority/capability outcome and a Compact Task Contract containing:

- task ID;
- objective;
- exact baseline + exact CI;
- risk tier;
- named authority;
- task-specific references;
- frontend architecture applicability;
- allowed scope;
- forbidden scope, especially later product gates;
- local-first work package;
- parallel ownership/integration serialization;
- acceptance;
- tests/evidence;
- stop conditions;
- closeout requirements.

Use `.github/ISSUE_TEMPLATE/valora_bounded_implementation_task.md` for new bounded implementation tasks.

## 5. Risk and review

| Risk | Default evidence model |
| --- | --- |
| Low | Codex verification + required CI |
| Medium | One independent reviewer only when materially useful and named in the contract |
| High / Product / Security | Freeze one HEAD + two independent reviewers + Gate Owner review + applicable E2E/CI |

Risk classification controls evidence depth; it does not grant integration authority.

## 6. Dev/Codex handoff

Every Dev/Codex prompt begins with the exact `CODEX MODEL` block required by `.agents/skills/valora-dev-handoff/SKILL.md`, then invokes `$valora-session-bootstrap` and supplies the Compact Task Contract by reference-first task delta.

The handoff must name:

- exact baseline/CI;
- risk;
- authority references;
- allowed/forbidden scope;
- dedicated worktree/package;
- acceptance and verification tiers;
- stop conditions;
- Draft/Ready/merge ownership;
- OpenViking compact policy block;
- frontend architecture rule when applicable.

Permanent policy stays in repository references. Do not paste full history into every prompt.

## 7. Candidate evidence rules

Evidence belongs to an exact SHA.

A candidate packet should include:

```text
base SHA
frozen HEAD
changed paths / manifest
scope statement
raw checks
limitations / skips
review evidence when required
exact-head CI run + head SHA + completion + conclusion
Draft PR
READY FOR GATE REVIEW: YES | NO
```

Rules:

1. Skips are skips, never PASS.
2. Parent/earlier green CI cannot certify a changed HEAD.
3. Any changed reviewed HEAD creates a new candidate; renew required reviews and exact-head CI.
4. `READY FOR GATE REVIEW: YES` means the candidate is ready for Gate Owner inspection, not that the task is certified.

## 8. Gate Review

Use `docs/templates/VALORA_GATE_REVIEW_CHECKLIST.md`.

Minimum Gate Owner checks:

- live task is still authorized;
- PR base and candidate HEAD are correct;
- live PR HEAD equals frozen reviewed HEAD;
- exact changed paths fit allowed scope;
- forbidden/downstream behavior is absent;
- required reviews exist on the same HEAD;
- material findings are resolved/adjudicated;
- exact-head CI matches the candidate SHA and is completed SUCCESS;
- task-specific acceptance is evidenced;
- no newer merge/authority change made evidence stale.

A reusable skill or checklist never creates permission to Mark Ready or merge.

## 9. Integration

Immediately before integration:

```text
fetch/reverify live PR
→ compare live PR HEAD with expected frozen HEAD
→ mismatch? STOP
→ authorized Ready
→ expected-head guarded SQUASH
→ capture merge SHA
```

If the HEAD changed, stop and renew candidate evidence. Never merge by branch name alone when exact-head evidence is the gate.

## 10. Post-merge certification

Merge success is `MERGED / UNCERTIFIED`.

Certification requires:

```text
main == captured merge SHA
AND
exact-main CI head SHA == captured merge SHA
AND
CI status == completed
AND
CI conclusion == success
```

Only then post the certification record using `docs/templates/VALORA_CERTIFICATION_COMMENT_TEMPLATE.md` and close the task as completed.

If GitHub auto-closes an Issue before exact-main certification, reopen it when necessary so repository state remains truthful.

## 11. CI failure after merge

Do not waive the gate because the candidate CI was green.

Classify the failure:

- deterministic code/product/security/migration failure → remain uncertified and remediate under explicit scope;
- plausible infrastructure/registry/transient failure → a same-SHA rerun may establish evidence if current policy permits it.

Never change code merely to relabel a failing run as transient. If code changes, the repository has a new SHA and needs the applicable evidence for that new state.

## 12. Downstream task rule

After exact-main SUCCESS:

- if the next bounded slice is already authorized and prerequisites are satisfied, rebaseline and open/resume it;
- if the next step requires a new Product Owner/authority decision, stop.

Do not infer authority from roadmap ordering, UI navigation, a successful upstream task or an AI recommendation.

## 13. Operational task states

Recommended PM delivery states:

```text
PROPOSED
AUTHORITY REQUIRED
AUTHORIZED
IN DEVELOPMENT
CANDIDATE FROZEN
UNDER REVIEW
EXACT-HEAD CI
READY FOR GATE REVIEW
GATE BLOCKED
MERGED / UNCERTIFIED
CERTIFIED / CLOSED
```

Avoid a generic `DONE` state because it hides the distinction between implementation, integration and certification.

## 14. PM Gate Board

For each active task track:

| Field | Meaning |
| --- | --- |
| Task | Stable task ID |
| Product Gate | Current authority boundary |
| Objective | One bounded outcome |
| Risk | Low / Medium / High-Product-Security |
| Baseline | Exact SHA |
| Baseline CI | Exact run on baseline |
| Authority | Named references/decision |
| Branch | Task branch |
| Candidate HEAD | Frozen SHA |
| PR | Draft/Ready/merged |
| Reviews | Required/received |
| Material findings | Unresolved count |
| Exact-head CI | pending/pass/fail |
| Gate Review | pending/pass/fail |
| Merge SHA | Captured integration SHA |
| Exact-main CI | pending/pass/fail |
| Certification | open/closed |
| Blocker | Current blocker |
| Next authorized action | Exactly one immediate authorized action |

The `Next authorized action` field is more important than a long unprioritized todo list.

## 15. Open does not mean active

Historical or stale Issues/PRs may remain open. Treat an object as active only when it matches current authority, current gate and current live baseline. File presence, Issue state or PR state alone does not establish authority.

## 16. Parallel work

Parallel implementation is allowed only when ownership and authority boundaries are separable. Be cautious around shared boundaries such as:

- `.github/workflows/**`;
- CODEX/process authority;
- migrations/schema;
- shared API contracts;
- RBAC;
- shared selectors;
- root dependencies/config.

Even when implementation can run in parallel, final freeze/review/CI/integration may need serialization. Rebaseline a dependent candidate if another merge can stale its evidence.

## 17. Stop conditions

Stop dependent work on any of the following until resolved:

- baseline drift;
- missing/conflicting authority;
- unapproved scope expansion;
- unmet prerequisite;
- security/tenant/RBAC/audit/idempotency ambiguity;
- migration/schema/shared-API collision;
- required review missing;
- reviewed HEAD changed;
- exact-head CI not completed SUCCESS;
- merge HEAD mismatch;
- exact-main CI not completed SUCCESS;
- downstream gate not authorized.

A stop is a control, not a delivery failure.

## 18. Definition of certified

A Valora task is `CERTIFIED / CLOSED` only when the current task requires integration and all applicable conditions are satisfied:

```text
authority satisfied
scope satisfied
acceptance satisfied
required verification satisfied
required reviews satisfied
zero unresolved material findings
exact-head CI SUCCESS
integration explicitly authorized
expected-head guard satisfied
merge SHA captured
exact-main CI SUCCESS on that merge SHA
certification recorded
Issue closed
no unauthorized downstream authority implied
```

If any applicable condition is missing, report the truthful intermediate state instead.
