# VALORA PM Operating Playbook v1

**Lifecycle/status:** CURRENT SUPPORTING PM OPERATING TOOLING — 2026-10-07 (PM-OPS-002 / Issue #141).
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
AUTHORITY READY (rebaseline + Definition of Ready + delivered handoff)
→ DEDICATED WORKTREE
→ IMPLEMENT LOCALLY
→ T0
→ T1
→ T2
→ REQUIRED T3 (when required)
→ LOCAL FINAL DIFF REVIEW
→ LOCAL SATURATION GATE
→ FIRST PUSH
→ DRAFT PR
→ FREEZE HEAD
→ REVIEWS + EXACT-HEAD CI
→ GATE OWNER
→ GUARDED MERGE
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

Before handoff, satisfy the [Definition of Ready](VALORA_AGENT_OPERATING_PROTOCOL_V2.md#definition-of-ready-and-stage-contracts): predecessor certified, authority accepted, COMPLETE predicate, mutation commands, RBAC disposition, currentness/stale rule, downstream hold, sufficient API/read-model or bounded gap, written E2E acceptance matrix and forbidden scope. Missing a critical item means **NO CODING — return to authority/design track**. Docs/tooling may map these to process acceptance with reasoned N/A dispositions; unresolved governing decisions remain blockers.

Use `Authority → Runtime → Product Closure` only where those slices are needed. Authority must answer Business COMPLETE fact, prerequisite, currentness, human confirmation, mutation authority, CAS, audit, RBAC, Next Action and downstream hold. Do not force three separate PRs for a bounded task.

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

Every new assignment requires appropriate GitHub Issue/PR handoff evidence **and** a complete copy/paste-ready Codex prompt delivered to the Product Owner. Record both links/delivery evidence. Issue creation alone does not mean Codex received work. `IN DEVELOPMENT` requires evidence that the Product Owner sent the prompt or that live candidate execution clearly began. Preserve all stricter existing handoff rules, including the exact model block and compact OpenViking block on corrections/resumes.

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

Before first push, require the [Local Saturation Gate](VALORA_AGENT_OPERATING_PROTOCOL_V2.md#local-saturation-gate): bounded implementation complete, T0/T1/T2 PASS, required T3 PASS, local final diff reviewed, changed paths bounded, no debug/secrets/unwanted generated artifacts and worktree clean except expected changes. An edit/push/CI-fail loop is not normal delivery. Record the [Early Push Exception](VALORA_AGENT_OPERATING_PROTOCOL_V2.md#early-push-exception) only for mandatory remote-only evidence, using all four fields; “Push thử để xem CI nói gì” is invalid. It waives no mandatory evidence or gate.

Before freeze, fetch origin, reconcile live main under the task's rebaseline authority, validate references and docs/skill/template shape where available, run `git diff --check`, inspect bounded paths and commit to a clean worktree. #141 and #142 use separate worktrees; if #142 is merged/certified first, rebaseline #141 before freeze. No required review or exact-head CI survives a source HEAD change.

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
- Local Saturation proof or a valid Early Push Exception and subsequently completed mandatory evidence are recorded;
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

## 11. Async CI and failure handling

For exact-head and exact-main CI: sanity-check run/SHA, record exact run ID/URL and SHA, schedule a condition check at a reasonable interval, then move to other authorized work. Resume the gate only on terminal outcome; do not repeatedly poll CI manually. SUCCESS continues the gate after exact-SHA verification; FAIL requires blocker classification; IN PROGRESS waits without unnecessary user notification. If a watcher is unavailable, record a bounded next check and pending status.

Use the [CI failure taxonomy](VALORA_AGENT_OPERATING_PROTOCOL_V2.md#ci-failure-taxonomy):

```text
CODE_TEST_FAILURE
SECURITY_VULNERABILITY
DEPENDENCY_FEED_FAILURE
INFRASTRUCTURE_TRANSIENT
ENVIRONMENT_MISMATCH
FLAKY_TEST
UNKNOWN
```

Record run/SHA/job, log-backed classification, blocker, authorized remedy and rerun justification. Rerun only when classification and current policy justify it; no blind rerun. UNKNOWN remains blocked pending diagnosis. Preserve failed attempts/flaky counts; never waive security/dependency thresholds or skip tests. After merge retain MERGED / UNCERTIFIED; green candidate CI does not waive exact-main CI. A source change renews the applicable exact-SHA evidence.

## 12. Downstream task rule

After exact-main SUCCESS:

- if the next bounded slice is already authorized and prerequisites are satisfied, rebaseline and open/resume it;
- if the next step requires a new Product Owner/authority decision, stop.

Do not infer authority from roadmap ordering, UI navigation, a successful upstream task or an AI recommendation.

## 13. Operational task states

Canonical assignment/handoff states:

```text
AUTHORIZED
→ HANDOFF PREPARED
→ HANDOFF DELIVERED
→ IN DEVELOPMENT
→ CANDIDATE READY
→ GATE REVIEW
```

Use the [protocol transition evidence](VALORA_AGENT_OPERATING_PROTOCOL_V2.md#direct-devcodex-handoff-states). Candidate freeze, review progress and CI run state are evidence fields rather than substitutes for delivered handoff. CANDIDATE READY requires the frozen candidate's mandatory checks, reviews/adjudication and exact-head CI SUCCESS.

Additional authority/integration dispositions remain:

```text
PROPOSED / AUTHORITY REQUIRED
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
| Track / WIP | A implementation, B next authority/design, C optional read-only discovery |
| Handoff state | Canonical state plus GitHub evidence, PO prompt delivery and execution evidence |
| Branch | Task branch |
| Candidate HEAD | Frozen SHA |
| PR | Draft/Ready/merged |
| Reviews | Required/received |
| Material findings | Unresolved count |
| Exact-head CI | pending/pass/fail |
| CI condition check | Exact run/SHA, watcher or scheduled next check, failure classification if any |
| First-push evidence | Local Saturation result, Early Push Exception if any and First Push Maturity |
| Gate Review | pending/pass/fail |
| Merge SHA | Captured integration SHA |
| Exact-main CI | pending/pass/fail |
| Certification | open/closed |
| Blocker | Current blocker |
| Next authorized action | Exactly one immediate authorized action |

The `Next authorized action` field is more important than a long unprioritized todo list.

## 15. Open does not mean active

Historical or stale Issues/PRs may remain open. Treat an object as active only when it matches current authority, current gate and current live baseline. File presence, Issue state or PR state alone does not establish authority.

## 16. Dual-track delivery / WIP

Hard WIP: **1 implementation stage + 1 next authority/design stage + 1 optional read-only discovery stage**.

| Track | Allowed work | Authority barrier |
| --- | --- | --- |
| A — Stage N | Implementation/delivery within accepted authority | One implementation stage; all quality/integration gates apply. |
| B — Stage N+1 | Inventory, proposal, PO decision table, rejected alternatives, risk/trade-off, preliminary acceptance matrix | No migration, runtime implementation, public API activation, new RBAC grant, stage-cap advancement or UI activation. No N+1 runtime before accepted authority and implementation prerequisites. |
| C — Stage N+2 (optional) | Read-only discovery | No mutation or runtime authority. |

Separable tasks within this WIP may proceed in separate dedicated worktrees with owned paths/dependencies. This does not permit parallel implementation stages. Be cautious around shared boundaries such as:

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

## 19. Delivery metrics

Record timestamp/evidence links per task; use one declared reporting window and retain all failed attempts. A candidate renewal is a changed source HEAD after first remote push; record each distinct replacement SHA. Do not count read-only PR-body/evidence updates as source renewals.

| Metric | Per-task record / target |
| --- | --- |
| PO authorization → first local candidate | Authorization timestamp → first bounded local candidate timestamp; elapsed time, no invented savings. |
| First push → frozen candidate | First remote push timestamp → final frozen candidate timestamp; elapsed time. |
| Post-first-push candidate renewals | Count distinct replacement source HEADs; target median <=1 across implementation tasks. |
| Exact-head CI attempts | Record every run/rerun attempt and SHA across the task, including superseded candidates; target 1. |
| Exact-main CI attempts | Record every run/rerun attempt on merge SHA; target 1. |
| Material findings after freeze | Count material VALID findings after first freeze, with disposition. |
| E2E flaky failures | Count failures classified FLAKY_TEST with evidence, including rerun successes. |
| Certified issue reopen | Count reopens after certification; target 0. |
| Escaped security findings | Count security findings discovered after certification; target 0. |
| Baseline-drift stops | Count BASELINE_DRIFT stops with observed/task SHA and reason. |
| First Push Maturity (primary) | YES only if the candidate passed required local T0/T1/T2/T3 before first remote push; target >=90% of implementation tasks = YES. |

First Push Maturity reporting = YES implementation tasks / all implementation tasks first pushed in the window. An Early Push Exception with an unmet required local tier is NO; absent evidence is UNKNOWN and is not credited as YES. Record explicit task-backed N/A tiers and docs/tooling task type; do not silently exclude exceptions or change the denominator. Targets are improvement goals, never permission to suppress findings, rerun history or gates. **Do not claim time savings or lead-time reduction without measured data.**

## 20. Deferred incremental tooling

PM-OPS-002 documents but does not implement `scripts/valora_candidate_preflight.py`, `scripts/valora_candidate_evidence.py`, reusable CaseFactory, structured security-artifact automation or CI workflow changes. Schedule them only as later bounded engineering slices after governance integration, with their own authority/acceptance. Browser/live-stack E2E, real PostgreSQL proof when applicable, risk-based independent review, exact-head CI, expected-head guarded merge, exact-main CI, security/dependency thresholds, Gate Owner certification, server-authoritative truth and human professional decisions remain required.
