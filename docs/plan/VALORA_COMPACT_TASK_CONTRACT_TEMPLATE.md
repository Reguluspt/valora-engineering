# VALORA Compact Task Contract

**Lifecycle/status:** CURRENT DEVELOPER TOOLING / OPERATING PROCESS — 2026-10-03.
**Authority role:** Developer task preparation/execution support only; not product, domain, runtime or deployment authority. Live CODEX, permanent guardrails, accepted scoped authority and the assigned task govern. No product/runtime dependency or new permission is created.

## TASK ID
`<ID>`

## OBJECTIVE
`<One bounded outcome>`

## BASELINE + exact CI
`<branch>` at `<40-character SHA>`; `<CI run/number>` = SUCCESS on that SHA. Name predecessor state.

## RISK TIER
`Low | Medium | High/Product/Security` — `<reason>`; for Medium, state whether one independent review is materially useful.

## AUTHORITY CONTRACT
`<Gate Owner's compressed domain/security/tenant/audit/idempotency/human-gate invariants>`

## TASK-SPECIFIC REFERENCES
`<Exact document sections, code paths and tests needed for this task>`

## ALLOWED SCOPE
`<Files or bounded subsystem; expected behavior>`

## FORBIDDEN SCOPE
`<Explicit exclusions, including later product gates>`

## ACCEPTANCE
`<Observable outcomes and evidence>`

## TESTS
`<T0/T1/T2/T3 as risk requires; T4 exact-head PR CI and applicable post-merge exact-main CI>`

## STOP CONDITIONS
`<Baseline mismatch, missing authority, conflicting invariant, scope expansion or prerequisite failure>`

## TASK_STATE
Persist at interruption; revalidate SHA/CI on resume. Do not include secrets.

**SESSION REBASELINE:** On a fresh session or [material checkpoint](VALORA_LEAN_AGENT_PROTOCOL_V1.md#gate-owner-session-rebaseline), check live main, CODEX blob, exact CI, current gate/task, conflicts and next authorized action before issuing the contract.

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
Keep near 800 tokens: task ID, baseline, files changed, policy/behavior changed, raw checks, limitations, local/remote HEAD, Draft PR/CI and `READY FOR GATE REVIEW: YES/NO`.
