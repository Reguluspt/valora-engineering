# Valora Hybrid AI Delivery Workflow

**Status:** Canonical operational workflow for human and AI contributors

**Effective:** 2026-07-19

**Owner decision:** Hybrid delivery; Antigravity is not a required gate

**Applies to:** New Valora engineering tasks and future working sessions

This document defines **how** work is prepared, delegated, reviewed, published and handed off. It does not define product behavior and cannot override `CODEX.md`, `ENGINEERING_GUARDRAILS.md`, the Design Authority Index, an approved ADR or a frozen feature contract.

## 1. Outcomes

The hybrid workflow must:

- keep the owner in control of scope, Ready and merge decisions;
- let another AI perform most implementation work when desired;
- give the Codex Lead one compact integration and evidence path;
- preserve tenant, RBAC, mutation, audit, migration and CI gates;
- avoid re-reading historical audits or recreating team setup every session;
- produce one current handoff that a new session can trust after live verification.

## 2. Canonical documents

A new session reads only this default set, in order:

1. `CODEX.md` — live task gate and permanent agent rules.
2. `ENGINEERING_GUARDRAILS.md` — permanent security and mutation invariants.
3. `docs/VALORA_HYBRID_AI_DELIVERY_WORKFLOW.md` — operational workflow.
4. `docs/VALORA_PROJECT_HANDOFF.md` — accepted progress and next authorized task.
5. The active Task Packet and only the design/ADR sections referenced by it. For the transition task S13-PR-004, use the two frozen PR #19 documents listed in the canonical handoff.

`PR_RULES.md` is read before publishing or changing PR state. The Design Authority Index is consulted when selecting or reconciling domain sources.

Do **not** bulk-read `docs/audits/`, old corrective reports, old prompts or completed Task Packets during normal startup. Historical evidence is opened only when the active diff, an unresolved finding or a cited SHA requires it.

## 3. Stable team model

Roles are stable; the model or vendor filling a role may change.

| Role | Default responsibility | When active |
|---|---|---|
| Owner | Assign task ID and scope; approve design changes; control Ready and merge | Always |
| Codex Lead | Bootstrap, risk classification, Task Packet, delegation, integration review, GitHub App writes, CI evidence and handoff | Always |
| AI Coder | Implement only the frozen Task Packet; run local tests; return commit/evidence; make no remote writes | Code tasks |
| Planner | Resolve bounded architecture or sequencing questions without coding | Complex/high-risk only |
| Independent Reviewer | Review the diff against the Task Packet and directly relevant authority | Complex/high-risk code, or when Lead also coded |
| CI | Reproduce exact remote head, including PostgreSQL-specific gates where applicable | Before Ready/merge |

Default capacity assignment:

- Planner: one strong planning model (for example Sol Max or equivalent).
- AI Coder: an external coding AI or Sol High equivalent.
- Reviewer: one independent strong reasoning model, separate from the coding context.
- Codex Lead: orchestration and final evidence ownership; it does not duplicate every specialist's work.

Antigravity is **not** part of the mandatory workflow. It may be reinstated only by an explicit owner instruction for a named task.

## 4. Risk classification and minimum path

The Codex Lead classifies the task once, before delegation.

| Class | Typical change | Required path |
|---|---|---|
| R0 — Documentation | Prose or status only; no contract/guardrail change | Lead → lightweight check → Draft PR |
| R1 — Routine code | Localized implementation under existing authority | Lead/Task Packet → Coder → Lead diff review → CI |
| R2 — Complex runtime | Cross-module behavior, persistence, concurrency or migration | Planner if needed → Coder → Independent Reviewer → CI |
| R3 — Authority/high risk | Tenant/RBAC, official mutation, audit atomicity, security boundary, new domain contract or architectural dependency | Owner/design gate → Planner → Coder → Independent Reviewer → exact-head CI |

Escalate to R3 when any of these is true:

- domain behavior is missing, conflicting or newly invented;
- tenant isolation, RBAC, human confirmation or official data mutation changes;
- audit atomicity, migration order, locking, idempotency or concurrency changes;
- a new dependency or provider alters architecture, licensing or security posture;
- an approved contract, ADR or permanent guardrail would need modification.

Do not add a Planner, Mapper or second Auditor merely because the task is large. Add a role only when its decision is distinct and necessary.

## 5. One active Task Packet

Starting with the task after the already-frozen S13-PR-004 packet, each task uses one canonical file:

```text
docs/tasks/<TASK-ID>__TASK_PACKET.md
```

The Task Packet replaces duplicated design packets, coding packets, audit prompts and session-specific handoffs. It should normally stay below 300 lines and contain:

```markdown
# <TASK-ID> — <title>

Status: DRAFT | FROZEN | IMPLEMENTED | VERIFIED | CLOSED
Owner authorization:
Accepted baseline commit/tree:
Branch / PR:
Risk class:

## Outcome and acceptance criteria
## In scope
## Explicit non-goals
## Authority references and exact sections
## Frozen decisions and invariants
## Allowed files / protected files
## Implementation sequence
## Required tests and exact-head CI
## Evidence manifest
## Stop conditions
## Coder handoff
## Reviewer findings / resolution
## Closeout
```

Rules:

- Refer to authority by path and section; do not paste whole design books into the packet.
- Freeze decisions before coding for R2/R3 work.
- Record findings in the same packet; do not create a new corrective report per loop.
- Update status and evidence in place. Git history preserves prior states.
- If a true architecture decision is needed, create an ADR and link it; do not hide it in the packet.

## 6. Five-minute bootstrap for every new session

The session Lead performs this sequence and no broader setup:

1. Resolve the repository and run `git fetch origin`.
2. Record `origin/main` commit and tree; verify the worktree and active PR head.
3. Read the five canonical inputs in section 2.
4. Read only the active PR diff, current Task Packet and its directly cited authority sections.
5. Confirm task ID, risk class, scope, non-goals, branch, PR state and stop conditions.
6. Produce a compact Start Gate of at most 12 lines, then continue the authorized work.

If live GitHub state conflicts with the handoff, live code/PR/CI wins. Correct the handoff in the same task or closeout; do not silently continue from stale SHAs.

### Copy/paste bootstrap prompt

```text
Tiếp tục dự án Valora theo mô hình hybrid trong
docs/VALORA_HYBRID_AI_DELIVERY_WORKFLOW.md.

Hãy fetch và xác minh origin/main + PR đang hoạt động; đọc CODEX.md,
ENGINEERING_GUARDRAILS.md, docs/VALORA_PROJECT_HANDOFF.md và Task Packet hiện tại.
Không quét toàn bộ docs/audits hoặc lịch sử corrective. Báo Start Gate tối đa 12 dòng:
task ID, baseline, PR/head, risk class, scope, non-goals, gate còn thiếu và hành động kế tiếp.
Sau đó tiếp tục đúng vai trò Codex Lead; dùng GitHub App cho remote writes, không dùng gh.
```

## 7. Delivery sequence

### Gate A — Start

- Finish or explicitly pause the current PR before preparing the next runtime branch.
- Verify accepted baseline and owner authorization.
- Classify risk and create/update the single Task Packet.
- For R2/R3, freeze the design/evidence section before code starts.

### Gate B — Delegate

Give the AI Coder a short prompt containing only:

- task and role;
- repository/worktree path and exact baseline;
- Task Packet path;
- required canonical files;
- allowed/protected paths;
- tests and stop conditions;
- required return evidence;
- explicit prohibition on remote writes.

The prompt should stay below 500 words. Use file references instead of copying source material.

### Gate C — Implement

The AI Coder:

1. verifies baseline and reads the named inputs;
2. implements only the allowed scope;
3. adds or updates tests with the code;
4. runs focused tests first, then the required regression set;
5. commits locally and returns changed files, raw counts, skips/failures, limitations, commit and tree SHAs;
6. stops on authority, baseline, permission, protected-file or architectural conflicts.

### Gate D — Review

Review only the Task Packet, changed files, diff and directly relevant authority.

- R1: Codex Lead performs a focused diff review.
- R2/R3: one independent reviewer checks correctness, security and test sufficiency.
- Re-review only changed hunks and unresolved findings.
- Maximum two targeted correction loops. If the same defect class persists, stop and perform a bounded RCA or reopen design; do not repeat a full audit.

The reviewer reports findings first by severity and file/line. A PASS report must state tested evidence and remaining limitations; absence of findings alone is not evidence.

### Gate E — Publish and verify

- The AI Coder does not push, create a PR, mark Ready or merge.
- The Codex Lead performs remote writes through the GitHub App; `gh` is not used.
- Default state is Draft.
- Verify the remote head SHA/tree after publishing.
- CI must run against that exact head. PostgreSQL-specific behavior requires PostgreSQL CI; local skips are not PASS.
- Owner controls Ready and merge unless explicitly delegated for the named PR.

### Gate F — Closeout

After merge:

1. verify merge SHA, `origin/main` and required post-merge CI;
2. record the compact closeout in the merged PR and mark the Task Packet `CLOSED` in the next authorized documentation change;
3. reconcile `CODEX.md`/handoff immediately only when the old text would materially misdirect the next session;
4. identify the next candidate but do not start it without owner assignment;
5. retain one short evidence manifest instead of a new narrative report.

Do not create a standalone closeout PR solely to copy SHAs or change a status word. Bundle routine reconciliation into the next owner-authorized task; use a separate closeout only when authority, safety evidence or the live gate would otherwise be ambiguous.

## 8. Token and output budget

These are operating caps, not quality exemptions:

- One Planner, one Coder and one Reviewer maximum per task; inactive roles consume no context.
- Pass file paths and exact sections; do not fork full conversation history into specialists.
- One Task Packet per task; no parallel copies of the same requirements.
- Normal tool output: request at most about 2,000 tokens; expand only around a failure.
- Successful test/CI output: command, counts, SHA and status only.
- Failure logs: show the smallest relevant excerpt, normally no more than 200 lines.
- Start Gate: at most 12 lines.
- Coder prompt: at most 500 words.
- Review/closeout report: normally at most 800 words.
- Never print a full repository diff, PR JSON payload or workflow log when a compact extraction answers the gate.

Safety evidence, an ADR or a necessary failure investigation may exceed a cap, but the Lead must state why.

## 9. Evidence manifest

Every implementation task records this minimum evidence in the Task Packet and final handoff:

```text
Task ID and risk class
Accepted baseline commit/tree
Local implementation commit/tree
Remote head commit/tree
Files changed
Authority/ADR sections used
Focused and regression commands with raw pass/fail/skip counts
Exact-head CI run(s) and conclusion
Open limitations or follow-up task IDs
Scope respected: YES/NO
ADR needed: YES/NO
Owner-controlled next action
```

Do not label a task PASS when required evidence is skipped, runs against another SHA, or depends on an unverified local environment.

## 10. Session handoff format

Before a session ends, update the canonical Task Packet or handoff with only:

```text
Repository and current branch
origin/main commit/tree
Active task and risk class
PR number/state/head/tree
Last completed gate
Tests/CI with raw counts or run IDs
Unresolved findings/limitations
Exact next action
Actions requiring owner approval
```

Do not use chat history as the only record of a material decision or unfinished remote state.

## 11. Transition from the previous workflow

- S13-PR-004 keeps its already-frozen design and coding packet; do not rewrite them mid-task.
- Complete S13-PR-004 with one Coder path, one appropriate review path and exact-head CI. Do not add Antigravity or repeat discovery/planning unless a stop condition is hit.
- From the next owner-assigned task, create `docs/tasks/<TASK-ID>__TASK_PACKET.md` and use it as the single task artifact.
- Historical S13 corrective and independent-audit reports remain evidence only. They are not mandatory startup reading and do not create future gates.

## 12. Stop conditions

Stop and ask the owner when:

- the baseline, active PR head or task assignment does not match the packet;
- domain authority is missing or conflicts;
- protected files or out-of-scope behavior are required;
- tenant, RBAC, human gate, audit atomicity or official mutation semantics are ambiguous;
- required CI cannot exercise the relevant environment;
- the requested action changes Ready/merge state without authorization;
- completing the task would require a new architecture decision, dependency or material scope expansion.
