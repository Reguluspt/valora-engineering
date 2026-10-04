# VALORA Agent Operating Protocol v2

**Lifecycle/status:** CURRENT GENERAL OPERATING-PROCESS ENTRYPOINT — 2026-10-04.
**Authority role:** Process/developer tooling only, for both fresh Gate Owner / Architect sessions and Dev/Codex sessions. No product, domain, runtime, deployment, provider, RBAC, security-policy or later-gate authority is created.

[CODEX §1](../../CODEX.md#1-source-of-truth) retains authority precedence; [Engineering Guardrails](../../ENGINEERING_GUARDRAILS.md) retain permanent invariants. This protocol supersedes [Lean v1](VALORA_LEAN_AGENT_PROTOCOL_V1.md), whose body remains historical. GitHub remains the source of truth for review, CI, integration and certification; local-first is bounded package delivery, not local-only whole-project development.

## Canonical supporting references

| Reference | Role / reading trigger |
| --- | --- |
| [CODEX](../../CODEX.md) | Live task gates, authority precedence and hard agent rules; read relevant sections. |
| [Engineering Guardrails](../../ENGINEERING_GUARDRAILS.md) | Permanent invariants governing the assigned boundary. |
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

## Parallel implementation and serialized evidence

Parallel implementation is allowed when ownership and authority boundaries are separable. Declare owned paths/dependencies in the contract. Serialize final freeze/review/CI when one merge can stale another candidate's evidence; rebaseline the dependent candidate before freezing it.

Shared-boundary warnings include `.github/workflows/**`, CODEX/process authority, migrations/schema, shared API contracts, RBAC, common selectors and root dependencies/config. Separately edited files alone do not prove separable authority. Optional workers retain CODEX §10.1 limits.

## Pre-freeze and integration

```text
fetch origin
→ compare live baseline with contract
→ drift? STOP with BASELINE_DRIFT before reviewer/full CI
→ inspect exact diff/changed paths and scope
→ complete focused checks, reviewed checkpoint and clean worktree
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
