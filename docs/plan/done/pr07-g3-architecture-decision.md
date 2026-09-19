# PR-07 — G3 architecture decision plan

**Status:** COMPLETE — OPTION A APPROVED BY PRODUCT OWNER
**Date:** 2026-09-19
**Scope:** architecture authority only; no provider mutation, runtime, migration, PR-08, commit or push

## Goal

Close G3 explicitly after the single `C2_AUTO_V2` observation without converting one safe
`404 itemNotFound` result into an undocumented production concurrency guarantee.

## Inputs

- [Stale-session `404` architecture evaluation](../../research/pr07-stale-session-404-decision.md).
- [ADR 0042](../../adr/0042-onedrive-personal-protected-values-and-sync-write-transactions.md),
  especially D5–D7.
- [Accepted PR-07 sync/conflict contract](../../implementation/VALORA_UIUX_V2_3_PR07_SYNC_CONFLICT_CONTRACT.md).
- [Provider-conformance runbook](../../implementation/VALORA_UIUX_V2_3_PR07_PROVIDER_CONFORMANCE_RUNBOOK.md).
- Sanitized attempts `af114cc0-4a10-46eb-ba60-108facc7daa0` and
  `2a06438c-5ad2-46f1-8da2-b60776647f86`.

## Decision options

| Option | Meaning | Consequence |
|---|---|---|
| A — retain D6 and close C2 research | `404 itemNotFound` is safe evidence for one run but not a documented commit guarantee | Recommended. Keep runtime blocked; seek Microsoft clarification or a different supported mechanism |
| B — amend D6 to accept bounded alternate rejection | Accept `404 itemNotFound` only with mandatory coherent same-item post-read proving concurrent state | Not recommended from one run; ambiguous `404` causality and undocumented stability become accepted residual risk |
| C — authorize another provider experiment | Design and run a new candidate to seek repetition or a narrower mechanism | Does not resolve the documentation gap; requires new research design, independent review and action-time authority |

## Approved decision

The Product Owner approved Option A on 2026-09-19:

1. Preserve ADR 0042/D6 and the PR-07 contract unchanged.
2. Record `C2_AUTO_V2` as completed research, not an accepted production adapter mechanism.
3. Keep `runtime_gate=BLOCKED`; do not begin PR-07 runtime, migrations, G4 or PR-08.
4. Permit read-only provider clarification through Microsoft documentation/support channels. This
   permission does not include another Graph mutation or live probe.
5. Reopen architecture only on the research document's explicit trigger.

## Why Option A is proportionate

- **Reach:** every future PR-07 document write would depend on the mechanism.
- **Capability:** an ordinary concurrent edit can reach the protected state; no adversarial skill is
  required.
- **Motive:** accidental edits are sufficient; malicious intent is irrelevant.
- **Blast radius:** silently overwriting a user's document is cross-system data loss and can be hard
  to reconstruct.
- **Control:** retain the existing trust-boundary block until provider conditional-commit semantics
  are documented. Post-read reconciliation remains necessary but does not retroactively make an
  ambiguous response a pre-commit guarantee.

## Adversarial check

The strongest case for Option B is that the actual safety invariant held: the stale candidate did
not overwrite the concurrent bytes, and mandatory post-read can classify the final state. However,
post-read observes the result after the commit boundary; it cannot guarantee that a stale overwrite
never occurred transiently or that future `404` cases share the same cause. Accepting B now would
bind production behavior to an undocumented provider detail.

Option A can also be wrong by being too strict: Microsoft may intentionally invalidate stale exact-
item sessions with `404`, making the status-code distinction incidental. The reopen trigger keeps
that path available as soon as normative evidence exists, without spending another mutation merely
to reproduce the same ambiguity.

## Execution checklist

- [x] Record the selected option and rationale in this plan.
- [x] Add a dated ADR/contract status note because the owner formally retired the research candidate;
      do not alter D6 semantics.
- [x] Do not create an Option B ADR successor or contract semantics change.
- [x] Do not create an Option C candidate or reuse `C2_AUTO_V2` authority.
- [x] Synchronize the acceptance matrix, runbook, research handoff and documentation index.
- [x] Open a separate read-only provider-clarification plan.
- [x] Run `git diff --check`; no independent implementation review is required because no accepted
      semantics or executable code changed.

The rejected-option actions remain recorded for traceability:

- If B were ever reconsidered: create a proposed ADR successor/amendment and contract diff for
  explicit review; do not implement runtime in the same step.
- If C were ever reconsidered: create a new bounded research doc and plan; do not reuse
  `C2_AUTO_V2` or its consumed authority.

## Stop conditions

- The Product Owner decision is complete; do not reinterpret the rejected options as authority.
- No documented provider guarantee: Option A remains the recommendation.
- Any proposal that treats generic `404` as success without coherent exact-item post-read: reject.
- Any request to rerun the consumed candidate: require a new research decision and authority.
