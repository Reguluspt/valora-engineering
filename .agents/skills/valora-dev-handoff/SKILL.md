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

Routing guidance: GPT-6 Luna for small/mechanical/known-contract work; GPT-6.1 Sol for default serious implementation/integration; GPT-6 Astra for architecture/security/high ambiguity only. Verify provider availability live; do not silently substitute. Route effort proportionally and name concrete escalation triggers.

Then reference `$valora-session-bootstrap` and supply the [compact contract](../../../docs/plan/VALORA_COMPACT_TASK_CONTRACT_TEMPLATE.md) with verified baseline/CI, risk, named authority, bounded worktree/package, scope, acceptance and stops under the [current operating protocol](../../../docs/plan/VALORA_AGENT_OPERATING_PROTOCOL_V2.md). Prompt = task delta; permanent rules/procedure = repository references and reusable skills. Do not recopy permanent-policy prose or full history.

When handoff scope touches `frontend/**`, React presentation, design tokens/theme, shared UI components, feature presentation/components, screens/pages or a React/native or browser-side native bridge adapter, it MUST reference the [Frontend Architecture Rule](../../../docs/architecture/VALORA_FRONTEND_ARCHITECTURE_RULE.md) as named authority and select applicable frontend PR checklist acceptance checks. Keep all 16 sections in the repository rather than pasting them into the prompt. Unrelated backend/worker/DB/migration/server-deployment/docs work does not gain this reading requirement. Permanent rule = repository; task delta = prompt; tests remain task/risk based.

EVERY Dev/Codex handoff includes the compact [OpenViking policy block](../../../docs/plan/VALORA_OPENVIKING_OPERATING_PROFILE_V1.md#mcp-usage-block); actual MCP recall remains optional. Carry the block even for tiny corrections and resumes. Full-profile reading is needed only for MCP use/debug/persistence, not merely to carry policy. Declare parallel ownership and whether final freeze/review/CI must serialize with another candidate. The prompt grants no later product or integration gate beyond its explicit authorization.
