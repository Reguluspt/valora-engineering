# VALORA Compact Task Contract

**Lifecycle/status:** CURRENT SUPPORTING TASK-CONTRACT TEMPLATE — 2026-10-04.
**Authority role:** Developer task preparation/execution support only; not product, domain, runtime or deployment authority. Live CODEX, permanent guardrails, accepted scoped authority and the assigned task govern. No product/runtime dependency or new permission is created.

Supporting template for the [current Agent Operating Protocol v2](VALORA_AGENT_OPERATING_PROTOCOL_V2.md). Handoffs begin with the [CODEX MODEL block](../../.agents/skills/valora-dev-handoff/SKILL.md) and invoke `$valora-session-bootstrap`. Prompt = task delta plus named references; permanent rules/procedure stay in repository/skills. Every Dev/Codex handoff includes the compact [OpenViking policy block](VALORA_OPENVIKING_OPERATING_PROFILE_V1.md#mcp-usage-block); actual recall is optional and full-profile reading is needed only for MCP use/debug/persistence.

## TASK ID
`<ID>`

## OBJECTIVE
`<One bounded outcome>`

## BASELINE + exact CI
`<branch>` at `<40-character SHA>`; `<CI run/number>` = SUCCESS on that SHA. Name predecessor state.

## RISK TIER
`Low | Medium | High/Product/Security` — `<reason>`; for Medium, state whether one independent review is materially useful.

## AUTHORITY CONTRACT
`<Named governing CODEX/task authority sections and task-specific invariant delta; preserve domain/security/tenant/audit/idempotency/human gates without recopying permanent policy>`

## TASK-SPECIFIC REFERENCES
`<Exact document sections, code paths and tests needed for this task>`

## ALLOWED SCOPE
`<Files or bounded subsystem; expected behavior>`

## FORBIDDEN SCOPE
`<Explicit exclusions, including later product gates>`

## LOCAL-FIRST WORK PACKAGE
`<Dedicated worktree + branch; one coherent authority/capability boundary; bounded outcome; reviewed local checkpoints within commit authorization; T0/T1/selective T2 edit-loop checks; risk/contract-driven T3; GitHub final integration/certification>`

## PARALLELISM / INTEGRATION SERIALIZATION
`<Separable path/authority ownership and dependencies, or no parallel work; serialize final freeze/review/CI if another merge can stale evidence; name shared workflow/process/schema/API/RBAC/selector/root-config boundaries>`

## ACCEPTANCE
`<Observable outcomes and evidence>`

## TESTS
`<T0/T1/T2/T3 as risk requires; T4 exact-head PR CI and applicable post-merge exact-main CI>`

## STOP CONDITIONS
`<Baseline mismatch, missing authority, conflicting invariant, scope expansion or prerequisite failure; pre-freeze fetch origin, compare baseline, return BASELINE_DRIFT before reviewer/full CI if changed>`

## TASK_STATE
Record at interruption in task evidence, targeting approximately 150–250 tokens; revalidate SHA/CI on resume. Do not include secrets or persist volatile state to durable memory.

**SESSION REBASELINE:** On a fresh session or [material checkpoint](VALORA_AGENT_OPERATING_PROTOCOL_V2.md#gate-owner-session-startup-and-rebaseline), check live main, CODEX blob, exact CI, current Issue/PR/gate/task and worktree, conflicts and next authorized action; output `PROJECT AUTHORITY READY: YES/NO` before issuing the contract.

```json
{
  "task_id": "VALORA-TASK-EXAMPLE",
  "baseline_sha": "d283c690b9f014833fa5c98e1125939351966b81",
  "baseline_ci": "#527 SUCCESS",
  "branch": "codex/example",
  "head_sha": null,
  "phase": "implement",
  "checks": {"T0": "pending", "T4": "pending"},
  "blocker": null,
  "next": "Verify the bounded change"
}
```

## CLOSEOUT
Target approximately 300–500 tokens for Low/Medium and 500–800 for High/Security: task ID, baseline, files changed, policy/behavior changed, raw checks, limitations, local/remote HEAD, Draft PR/CI and `READY FOR GATE REVIEW: YES/NO`. Freeze one clean HEAD after the pre-freeze checks; required reviews and exact-head CI must certify that SHA. Gate Owner owns authorized Ready/expected-head guarded squash and exact-main certification. Ideal one final exact-head PR CI + one exact-main CI is a target; material findings justify renewed evidence.
