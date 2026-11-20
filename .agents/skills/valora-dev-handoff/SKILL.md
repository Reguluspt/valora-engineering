---
name: valora-dev-handoff
description: Prepare or validate every Valora Dev or Codex handoff, including resumes, corrections, reviewer fixes and tiny continuations.
---

# Dev prompt contract

EVERY prompt handed to Dev/Codex must begin with this block, populated for the exact task:

```text
CODEX MODEL
Model: <exact model family>
Reasoning: <effort>

Selection reason:
<why this model and effort fit the bounded work>

Escalation:
<specific condition and destination model/effort>
```

A prompt missing this block is INVALID. Apply it to new tasks, resumes, follow-up corrections, reviewer findings, CI fixes, evidence fixes, acceptance reconciliation and tiny continuation prompts. `PRIMARY AGENT: Codex` or `Codex — Reasoning HIGH` is invalid because the exact model family is absent.

Routing guidance (PO decision 2026-11-18): GPT-6 Luna for small/mechanical/known-contract work; **GPT-6.2 Sol (`gpt-6.2-sol`) for default serious Dev/Codex implementation, integration and bounded read-only agent work**, replacing GPT-6.1 Sol for every NEW handoff, resume, correction and reissued held prompt; GPT-6 Astra for architecture/security/high ambiguity escalation only unless separately changed by PO. Select reasoning proportionally and document the exact model, effort, selection reason and escalation in the opening block. Verify `gpt-6.2-sol` under the actual authenticated Codex model picker or CLI before execution (e.g. `codex -m gpt-6.2-sol`); product release alone does not prove account/workspace availability. On unavailability STOP and report to PM/Gate Owner; never silently fall back to GPT-6.1 Sol or substitute any model or relax review/Gate policy. Preserve historical delivered prompts and evidence unmodified; publish a versioned replacement for an undelivered/historical GPT-6.1 Sol prompt, with the same task scope and authorities.

Then reference `$valora-session-bootstrap` and supply the [compact contract](../../../docs/plan/VALORA_COMPACT_TASK_CONTRACT_TEMPLATE.md) with verified baseline/CI, risk, named authority, bounded worktree/package, scope, acceptance and stops under the [current operating protocol](../../../docs/plan/VALORA_AGENT_OPERATING_PROTOCOL_V2.md). Prompt = task delta; permanent rules/procedure = repository references and reusable skills. Do not recopy permanent-policy prose or full history.

When handoff scope touches `frontend/**`, React presentation, design tokens/theme, shared UI components, feature presentation/components, screens/pages or a React/native or browser-side native bridge adapter, it MUST reference the [Frontend Architecture Rule](../../../docs/architecture/VALORA_FRONTEND_ARCHITECTURE_RULE.md) as named authority and select applicable frontend PR checklist acceptance checks. Keep all 16 sections in the repository rather than pasting them into the prompt. Unrelated backend/worker/DB/migration/server-deployment/docs work does not gain this reading requirement. Permanent rule = repository; task delta = prompt; tests remain task/risk based.

EVERY Dev/Codex handoff includes the compact [OpenViking policy block](../../../docs/plan/VALORA_OPENVIKING_OPERATING_PROFILE_V1.md#mcp-usage-block); actual MCP recall remains optional. Carry the block even for tiny corrections and resumes. Full-profile reading is needed only for MCP use/debug/persistence, not merely to carry policy. Declare parallel ownership and whether final freeze/review/CI must serialize with another candidate. The prompt grants no later product or integration gate beyond its explicit authorization.

## Independent review handoff (AGY **and** OpenCode)

Use the [shared two-lane procedure](../../../docs/plan/VALORA_INDEPENDENT_REVIEW_PROCESS_V1.md) and distinguish:
- **D — design advisory, before implementation:** Codex directly sends one short whole-review prompt to the assigned AGY and/or OpenCode reviewer with readable approved Contract/source, lets the reviewer select its own investigative tools (read/grep/shell/web/MCP etc.), waits for the native final, and forwards the **complete unedited** report to PM. **PM** verifies/analyzes findings and proposes PO decisions. Do not impose default VM, AGY C1–C8, staged W1–W5, tool-count monitors or an automatic MCP feasibility subtask as requirements for this advisory. Existing ambient MCP exposure is a disclosed limitation, not a security PASS; never include credentials/customer data or authorize project edits/external side-effecting changes.
- **P — formal frozen candidate/PR review:** Keep CODEX §10.1 and Issue #221 same-HEAD independent A/B, technically read-only candidate protection, appropriate CI/T0–T3 and full Gate Owner assessment. D **cannot substitute** for P or signed named Security Owner/Domain Owner acceptance.
- **For either lane:** request actual model availability (AGY `gemini-3.8-flash-high` HIGH; OpenCode currently `opencode-go/deepseek-v4.1-flash` subject to live route). Codex retains reviewer/model/effort/status, complete native final with hash/ref, actual source SHA, tools observed if available, missing canonical sources, and raw vs historical test provenance. Codex never promotes a reviewer's finding directly to PM approval or grants a new source path. Official OpenCode [permission schema](https://opencode.ai/docs/permissions) is versioned; inspect installed CLI rather than assuming legacy `permission/bash` or new `permissions/shell` works universally.

## Definition of Ready

Validate the [Definition of Ready](../../../docs/plan/VALORA_AGENT_OPERATING_PROTOCOL_V2.md#definition-of-ready-and-stage-contracts) before preparing an implementation handoff:

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

Missing a critical item means **NO CODING — return to authority/design track**. For docs/tooling tasks, map to process acceptance and relevant tooling authority with explicit N/A reasons; no unresolved governing decision may be hidden. Where needed, identify `Authority → Runtime → Product Closure` slices and answer Business COMPLETE fact, prerequisite, currentness, human confirmation, mutation authority, CAS, audit, RBAC, Next Action and downstream hold. Do not force three PRs.

## Direct delivery and state evidence

```text
AUTHORIZED
→ HANDOFF PREPARED
→ HANDOFF DELIVERED
→ IN DEVELOPMENT
→ CANDIDATE READY
→ GATE REVIEW
```

For EVERY new Dev/Codex assignment, preserve both:

1. Appropriate GitHub Issue/PR handoff evidence referencing the full task contract.
2. A complete copy/paste-ready Codex prompt delivered to the Product Owner, including the exact model block, bootstrap, task delta/references and compact OpenViking block above.

An Issue alone does not mean Codex received work. Record GitHub evidence, PO prompt delivery and execution evidence separately. HANDOFF PREPARED means the complete prompt is ready; HANDOFF DELIVERED means both delivery requirements are evidenced. IN DEVELOPMENT only after the Product Owner sends the prompt OR live candidate execution clearly appears. A branch name without execution evidence is insufficient. CANDIDATE READY requires the frozen candidate's mandatory checks, required reviews/adjudication and exact-head CI SUCCESS; GATE REVIEW means Gate Owner inspection, not certification. Preserve stricter rules for resumes/corrections.

## Candidate delivery requirements in the prompt

- Dedicated worktree; bounded implementation locally; T0 → T1 → T2 → required T3 → local final diff review → [Local Saturation Gate](../../../docs/plan/VALORA_AGENT_OPERATING_PROTOCOL_V2.md#local-saturation-gate) → FIRST PUSH → DRAFT PR → FREEZE HEAD → reviews + exact-head CI → Gate Owner → guarded merge → exact-main CI → certification, stopping at the task's authorized delivery boundary.
- Before first push: implementation complete; T0/T1/T2 PASS; required T3 PASS or explicit contract-backed N/A; diff reviewed; bounded paths; no debug/secrets/unwanted generated artifacts; worktree clean except expected changes. Do not use CI as an edit/push/fail loop.
- [Early Push Exception](../../../docs/plan/VALORA_AGENT_OPERATING_PROTOCOL_V2.md#early-push-exception) only for mandatory remote-only evidence; include `Reason`, `Remote-only evidence required`, `Local work already completed`, `Why local saturation cannot continue`. “Push thử để xem CI nói gì” is invalid. The exception waives no mandatory evidence/gate.
- Hard WIP: 1 Stage N implementation + 1 Stage N+1 authority/design + 1 optional Stage N+2 read-only discovery. Track B may prepare inventory/proposal/PO decision table/rejected alternatives/risk/trade-off/preliminary acceptance matrix; no migration/runtime/public API/new RBAC/stage-cap/UI activation. No N+1 runtime before accepted authority and satisfied prerequisites.
- Before freeze: fetch live main; reconcile only task-authorized rebaseline or stop BASELINE_DRIFT; validate bounded paths, references, docs/skill/template shape and `git diff --check`; freeze one clean HEAD. Source HEAD changes invalidate required review/exact-head CI.
- Async CI: verify and record run/SHA; schedule condition check; move to authorized work; resume gate on terminal outcome. SUCCESS continues, FAIL classifies, IN PROGRESS waits without user noise. No repeated manual polling or blind rerun; use the [CI failure taxonomy](../../../docs/plan/VALORA_AGENT_OPERATING_PROTOCOL_V2.md#ci-failure-taxonomy) and record justified attempts.
- Record [delivery metrics](../../../docs/plan/VALORA_PM_OPERATING_PLAYBOOK_V1.md#19-delivery-metrics), especially First Push Maturity (required local T0/T1/T2/T3 passed before first remote push; target >=90% implementation tasks YES). Targets never waive gates; do not claim savings without measurements.

Reference these requirements rather than duplicating full permanent policy in the prompt. Candidate-preflight/evidence scripts, CaseFactory, structured security-artifact automation and CI workflow changes remain deferred incremental tasks; this handoff does not authorize them or any later product/runtime stage.
