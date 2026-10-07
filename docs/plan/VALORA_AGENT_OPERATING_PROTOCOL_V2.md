# VALORA Agent Operating Protocol v2

**Lifecycle/status:** CURRENT GENERAL OPERATING-PROCESS ENTRYPOINT — 2026-10-07 (PM-OPS-002 / Issue #141).
**Authority role:** Process/developer tooling only, for both fresh Gate Owner / Architect sessions and Dev/Codex sessions. No product, domain, runtime, deployment, provider, RBAC, security-policy or later-gate authority is created.

[CODEX §1](../../CODEX.md#1-source-of-truth) retains authority precedence; [Engineering Guardrails](../../ENGINEERING_GUARDRAILS.md) retain permanent invariants. This protocol supersedes [Lean v1](VALORA_LEAN_AGENT_PROTOCOL_V1.md), whose body remains historical. GitHub remains the source of truth for review, CI, integration and certification; local-first is bounded package delivery, not local-only whole-project development.

## Canonical supporting references

| Reference | Role / reading trigger |
| --- | --- |
| [CODEX](../../CODEX.md) | Live task gates, authority precedence and hard agent rules; read relevant sections. |
| [Engineering Guardrails](../../ENGINEERING_GUARDRAILS.md) | Permanent invariants governing the assigned boundary. |
| [Frontend Architecture Rule](../architecture/VALORA_FRONTEND_ARCHITECTURE_RULE.md) | Task-scoped implementation authority: read when changing `frontend/**`, React/frontend presentation, tokens/theme/shared UI, feature/screen composition or a React/native or browser-side native bridge adapter. Unrelated backend/worker/DB/migration/server-deployment/docs tasks do not require it. |
| [OpenViking profile](VALORA_OPENVIKING_OPERATING_PROFILE_V1.md) | Specialized MCP use, hook controls, privacy, debugging and persistence; full read only when needed for those actions. |
| [Compact Task Contract](VALORA_COMPACT_TASK_CONTRACT_TEMPLATE.md) | Reference-first task delta and evidence requirements. |
| [Session bootstrap skill](../../.agents/skills/valora-session-bootstrap/SKILL.md) | Compact startup, delegating live checks to the [live-authority skill](../../.agents/skills/valora-live-authority-bootstrap/SKILL.md). |
| [Dev handoff skill](../../.agents/skills/valora-dev-handoff/SKILL.md) / [local skills](../../.agents/skills) | Reusable procedures selected for the task. |

Supporting references specialize this entrypoint; do not create a separate Local-first or duplicate OpenViking manual. Gate Owner resolves authority, declares risk and issues the contract. Codex verifies, implements, checks and adjudicates findings within it. Optional workers own bounded mechanical work; independent reviewers are read-only. Gate Owner owns integration and the next product gate under CODEX §10.1.

## Gate Owner session startup and rebaseline

```text
fetch/reverify live repo
→ main SHA
→ CODEX blob
→ exact-main CI (head SHA, completion, SUCCESS)
→ current Issue/PR/gate and task branch/worktree
→ relevant CODEX sections + named task authority only
→ PROJECT AUTHORITY READY
→ derive/issue compact task contract
```

Rebaseline on a fresh session and after a merge, exact-main CI result, Product Gate close, ADR acceptance or material blocker/scope change. Verify any separately claimed execution baseline's exact CI too. Live state wins over a prompt, prior chat or memory. A mismatch, missing prerequisite or authority conflict stops dependent work; output readiness NO and the next permitted action rather than silently replacing the baseline.

The compact readiness record contains `PROJECT AUTHORITY READY: YES/NO`, live main, CODEX blob, exact-main CI, current gate, active task/Issue/PR, branch/worktree, conflicts and next authorized action. Collapse prior gates to their certified checkpoints; do not replay historical task chains.

When allowed scope contains frontend implementation, Gate Owner MUST name the [Frontend Architecture Rule](../architecture/VALORA_FRONTEND_ARCHITECTURE_RULE.md) in the compact contract and mark its applicability APPLIES. Select applicable frontend PR checklist checks; keep test scope task/risk based. This also covers React/native and browser-side native bridge adapters. Permanent architecture remains a repository reference, not copied policy or a new process entrypoint.

## Codex session startup

```text
CODEX MODEL (exact model, reasoning, selection reason, escalation)
→ $valora-session-bootstrap
→ compact task contract
→ named authority
→ compact OpenViking policy
→ relevant task-specific skill
→ optional recall only if useful
→ local-first execution and proportional verification
```

Use the assigned worktree. If native skill discovery predates the files, read the exact committed SKILL.md. Bootstrap checks the supplied task identifiers and baseline before implementation; then read/validate the compact contract and its named authority. Every Dev/Codex handoff carries the compact [OpenViking policy block](VALORA_OPENVIKING_OPERATING_PROFILE_V1.md#mcp-usage-block), including resumes and tiny corrections. Carrying policy does not require an MCP call or a full profile read.

## Reference-first context

Permanent rules stay in the repository; reusable procedure stays in skills; the prompt carries the task delta and named references. Do not recopy permanent-policy prose. Verify the live CODEX blob every session, but read only the applicable sections. Full CODEX/history inspection is an exception for explicit governance/reconciliation scope or a concrete unresolved authority conflict, with a recorded reason. Precedence is not a reading checklist.

| Tier | Context |
| --- | --- |
| C0 | Task contract, exact baseline/CI, current gate and applicable rule references. |
| C1 | Named authority sections, affected code and tests. |
| C2 | Adjacent authority/subsystem needed for a concrete dependency; record why. |
| C3 | Broad/full inspection only when explicitly required or a scoped conflict cannot be resolved; justify it. |

A missing domain/permission decision goes to Gate Owner; do not invent behavior or reconstruct history to replace approval.

## Local-first bounded delivery

Use a dedicated task worktree and one larger but bounded work package within a coherent authority/capability boundary. Do not bundle unrelated product gates to reduce CI. Inspect ownership/status/diff before editing; preserve unrelated work. Make reviewed local checkpoints when commit authorization exists. Stage only explicit reviewed task-owned paths; never use `git add -A`, `git add .`, `git reset --hard`, `git clean -fd` or `git restore .`. Apply the [resume skill](../../.agents/skills/valora-worktree-resume/SKILL.md) after interruption.

Use T0/T1 and selective T2 in edit loops. Run T3 when risk or the contract requires it. Keep GitHub for final review/integration/certification; no local PASS replaces exact-SHA CI. Commit, push, Draft/Ready, merge and deployment require the task's existing authorization; procedure grants none by itself.

### Local Saturation Gate

Canonical implementation flow:

```text
AUTHORITY READY
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
→ EXACT-MAIN CI
→ CERTIFICATION
```

Before FIRST PUSH, record all of:

- [ ] Bounded implementation complete.
- [ ] T0 focused checks PASS.
- [ ] T1 affected regressions PASS.
- [ ] T2 scope-appropriate lint/type/build/security checks PASS.
- [ ] Required T3 PASS, or contract-backed N/A with reason if not required.
- [ ] Local final diff reviewed; changed paths bounded to the contract.
- [ ] No debug/secrets/unwanted generated artifacts.
- [ ] Worktree clean except expected task changes; commit only reviewed task paths before push.

The edit loop stays local until saturation. `edit → push → CI fail → edit → push → CI fail` is not a normal workflow. Selective checks during editing do not waive final T0/T1/T2 or required T3. Docs/tooling tasks use relevant document, skill, template and reference checks; runtime tests may be N/A with an explicit scope reason. A required unavailable check remains incomplete, never PASS.

### Early Push Exception

An early push is allowed only when mandatory evidence cannot exist locally: a GitHub-only environment, remote-only secret/service, required cross-platform runner or remote-only integration/permission. Complete every locally possible implementation/check first; record the remaining remote evidence and why local saturation cannot continue:

```text
EARLY PUSH EXCEPTION
Reason:
Remote-only evidence required:
Local work already completed:
Why local saturation cannot continue:
```

“Push thử để xem CI nói gì” is invalid. An exception does not waive the missing gate, review, security threshold or exact-SHA CI; candidate readiness waits for mandatory evidence. Record First Push Maturity truthfully, including exception tasks.

## Definition of Ready and stage contracts

Before an implementation handoff, verify:

```text
[ ] predecessor certified
[ ] authority accepted
[ ] COMPLETE predicate known
[ ] mutation commands known
[ ] RBAC disposition known
[ ] currentness/stale rule known
[ ] downstream hold known
[ ] API/read-model sufficient or bounded gap defined
[ ] E2E acceptance matrix written
[ ] forbidden scope written
```

A missing critical item means **NO CODING — return to authority/design track**. For docs/tooling, map COMPLETE to process acceptance, mutation/RBAC/currentness to the actual tooling boundary and the E2E matrix to observable process acceptance; document N/A reasons. Do not use N/A to conceal an unresolved governing decision.

Where a stage needs distinct slices, use `Authority → Runtime → Product Closure`. Its authority contract answers Business COMPLETE fact, prerequisite, currentness, human confirmation, mutation authority, CAS, audit, RBAC, Next Action and downstream hold. Do not force three PRs when one bounded task suffices. Authority preparation and roadmap order never authorize runtime by themselves.

## Direct Dev/Codex handoff states

```text
AUTHORIZED
→ HANDOFF PREPARED
→ HANDOFF DELIVERED
→ IN DEVELOPMENT
→ CANDIDATE READY
→ GATE REVIEW
```

| State | Required evidence |
| --- | --- |
| AUTHORIZED | Scoped owner authority and prerequisites identified. |
| HANDOFF PREPARED | Definition of Ready satisfied; complete prompt validated by the handoff skill. |
| HANDOFF DELIVERED | Appropriate GitHub Issue/PR handoff evidence AND complete copy/paste-ready Codex prompt delivered to the Product Owner. |
| IN DEVELOPMENT | Product Owner sent the prompt to Dev/Codex OR live candidate execution clearly appears; record evidence. |
| CANDIDATE READY | Saturation/exception evidence, frozen HEAD, required reviews/adjudication and exact-head CI SUCCESS support Gate Review. |
| GATE REVIEW | Gate Owner has taken the exact candidate for inspection; this is not certification. |

A GitHub Issue alone does not mean Codex received work. New assignments require both delivery surfaces above; maintain the existing model block, bootstrap, compact OpenViking policy and all stricter handoff rules for resumes/corrections too. Record evidence for each transition; a live branch name alone without execution evidence is insufficient.

## Verification and review

| Tier | Required evidence when applicable |
| --- | --- |
| T0 | Focused edit-loop checks. |
| T1 | Affected subsystem regression. |
| T2 | Candidate static/lint/type/build/security checks proportional to scope. |
| T3 | Full local, real-stack or E2E only when risk/task requires it under CODEX §10.3. |
| T4 | Exact-head PR CI and exact-main post-merge CI wherever required by the current gate. |

Skips are skips, never passes. A parent/earlier green run does not certify a changed HEAD, including docs-only candidates.

| Risk | Review |
| --- | --- |
| Low | Codex verification and required CI. |
| Medium | One independent reviewer only when materially useful and named in the contract. |
| High / Product / Security | Frozen snapshot, two independent reviewers, Gate Owner and applicable E2E/CI, as required by current CODEX/task authority. |

Reviewer packets are reference-first: exact base/HEAD, changed-file/hash manifest, authority references, review focus and evidence links. Reviewers read exact Git blobs where possible; all required reviewers inspect the same HEAD. Reviewer absence leaves review INCOMPLETE. Codex adjudicates findings as VALID, INVALID, DUPLICATE, OUT_OF_SCOPE or ADVISORY. Fix material valid findings, then renew the candidate and required review/CI. Prior evidence stays historical.

## Dual-track delivery and serialized evidence

Hard business-stage WIP limit:

```text
Track A — Stage N implementation/delivery (1)
Track B — Stage N+1 authority/design (1)
Track C — Stage N+2 read-only discovery (optional, 1)
```

Track B may produce inventory, proposal, PO decision table, rejected alternatives, risk/trade-off and a preliminary acceptance matrix. It must NOT perform migration, runtime implementation, public API activation, new RBAC grant, stage-cap advancement or UI activation. **No N+1 runtime before accepted authority** and satisfaction of its implementation prerequisites. Track C stays read-only and supplies no implementation authority.

Separable task work within these limits may run in separate dedicated worktrees with declared paths/dependencies; this is not permission for a second implementation stage. Serialize final freeze/review/CI when one merge can stale another candidate's evidence; rebaseline the dependent candidate before freezing it. For #141/#142, keep worktrees separate and, if #142 is merged/certified first, rebaseline #141 onto current main before freeze as explicitly authorized by the task. Any source HEAD change invalidates previous review/exact-head CI evidence.

Shared-boundary warnings include `.github/workflows/**`, CODEX/process authority, migrations/schema, shared API contracts, RBAC, common selectors and root dependencies/config. Separately edited files alone do not prove separable authority. Optional workers retain CODEX §10.1 limits.

## Pre-freeze and integration

```text
fetch origin
→ compare live baseline with contract
→ material drift? STOP with BASELINE_DRIFT (only task-authorized rebaseline may proceed)
→ inspect exact diff/changed paths and scope
→ verify Local Saturation / Early Push Exception evidence and required local gates
→ links/references + docs/skill/template checks where available + git diff --check
→ reviewed checkpoint and clean worktree
→ freeze ONE HEAD
→ required reviews + exact-head CI SUCCESS on that same SHA
→ Gate Owner
→ authorized Ready
→ expected-head guarded SQUASH
→ exact-main CI SUCCESS on the resulting main SHA
→ CERTIFIED/CLOSED
```

Check the live expected PR HEAD before integration; stop on mismatch. Changed HEAD invalidates its prior candidate evidence and requires renewed gates. Only the authorized Gate Owner advances Draft/Ready/merge and releases dependent tasks after certification. A Draft-only contract stops at draft closeout even when review and CI pass. [CODEX §8.1](../../CODEX.md#81-exact-head-baseline-and-dependent-task-gate) remains binding.

Ideal CI KPI per package: **one final exact-head PR CI + one exact-main CI**. This is a target, not a correctness constraint. A material finding can require renewed candidate/CI; never suppress a valid finding to meet the count.

## Async CI and failure classification

After a candidate or main CI trigger, sanity-check the run and SHA, record run ID/URL plus exact SHA, schedule a condition check at a reasonable interval using the available watcher, and move to other authorized work within the WIP limit. Resume the gate only on a terminal outcome. Do not repeatedly poll CI manually or substitute an older green run. If no watcher is available, record a bounded next check and pending state; do not create a polling loop.

- SUCCESS → continue the gate after verifying completed/success and the required exact SHA.
- FAIL → classify the exact blocker from job/log evidence before remediation or rerun.
- IN PROGRESS → keep waiting; no unnecessary user notification.

### CI failure taxonomy

| Classification | Disposition / rerun rule |
| --- | --- |
| CODE_TEST_FAILURE | Fix within authority; changed source requires a new candidate and renewed required review/CI. No blind same-SHA rerun. |
| SECURITY_VULNERABILITY | Gate blocked; remediate under authorized scope. Never waive security/dependency thresholds or rerun to hide a finding. |
| DEPENDENCY_FEED_FAILURE | Prove advisory/registry/feed unavailability rather than a vulnerability; same-SHA rerun only with evidence of recovery. |
| INFRASTRUCTURE_TRANSIENT | Prove runner/network/service transient; bounded same-SHA rerun only when policy and recovery evidence justify it. |
| ENVIRONMENT_MISMATCH | Identify the required environment/configuration and correct it within authority; rerun only after the mismatch is resolved. Source changes renew candidate evidence. |
| FLAKY_TEST | Record flaky evidence and cause; controlled same-SHA rerun only when justified by current policy. Preserve failed attempts and the flaky count; fix under bounded authority without skipping/weakening tests. |
| UNKNOWN | Gate blocked pending diagnosis. No rerun without a supported classification. |

Record failed run/SHA/job, classification, evidence, authorized next action and rerun justification/attempt when applicable. No blind rerun. For a failed exact-main run, retain MERGED / UNCERTIFIED and downstream holds until certification requirements pass.

## Delivery metrics and deferred tooling

The [PM playbook metrics](VALORA_PM_OPERATING_PLAYBOOK_V1.md#19-delivery-metrics) define per-task measurements and targets. First Push Maturity means the candidate passed required local T0/T1/T2/T3 before first remote push; target **>=90% of implementation tasks = YES**. Preserve failed attempts and post-push renewals; targets never override required gates. Do not claim time savings without measured data.

Follow-on incremental work is explicitly deferred: `scripts/valora_candidate_preflight.py`, `scripts/valora_candidate_evidence.py`, CaseFactory, structured security-artifact automation and CI workflow changes. This governance task builds none of them and grants no product/runtime stage. Risk-based independent review, browser/live-stack E2E, real PostgreSQL proof when applicable, exact-head CI, expected-head guarded merge, exact-main CI, security/dependency thresholds, Gate Owner certification, server-authoritative truth and the human professional decision boundary remain binding.

## Compact state, OpenViking and durable memory

| Item | Token target / ceiling |
| --- | --- |
| TASK_STATE at interruption | Approximately 150–250; baseline, branch/HEAD, checks, blocker, next action. |
| Low/Medium closeout | Approximately 300–500; scope/evidence/limits, exact HEAD/PR/CI, gate readiness. |
| High/Security closeout | Approximately 500–800, retaining required evidence. |
| Normal recall | ≤300 total returned tokens per bounded task. |
| Resume/debug recall | ≤600 total returned tokens. |
| Exceptional recall | ≤1000, with explicit justification before retrieval. |

Mode `VALORA_LEAN_MCP` is NON-AUTHORITATIVE. After bootstrap, recall is optional only when a concrete historical question makes it useful: find/search → small context → targeted read, stopping at the first sufficient result. Count all returned context including wrappers/abstracts across calls. No automatic recall/capture/injection. No memory certification of SHA, CI, PR, Issue, worktree or changed files. If MCP is unavailable, continue this protocol with live repository and local skills.

Persist only reusable certified lessons under the profile's privacy/persistence rules, never secrets/client data, current SHA/CI/PR/Issue/worktree state or pending decisions. The specialized profile governs hook verification and manual persistence; this document creates no new dependency or automatic memory permission. Stop on missing/conflicting authority, security/tenant/audit/idempotency ambiguity, unapproved architecture/scope expansion or unmet prerequisite; permanent human-approval and domain-command gates remain intact.
