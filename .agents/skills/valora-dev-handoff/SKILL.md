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

Then supply the [compact contract](../../../docs/plan/VALORA_COMPACT_TASK_CONTRACT_TEMPLATE.md) with verified baseline/CI, risk, authority, scope, acceptance and stops. Include the [MCP usage block](../../../docs/plan/VALORA_OPENVIKING_OPERATING_PROFILE_V1.md#mcp-usage-block) when relevant. The prompt grants no later product or integration gate beyond its explicit authorization.
