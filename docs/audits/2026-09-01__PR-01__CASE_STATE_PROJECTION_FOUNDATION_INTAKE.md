# PR-01 — Case State Projection Foundation Intake

**Date:** 2026-09-01
**Status:** DESIGN GATE OPEN — runtime held fail-closed
**Branch:** `pr-01-case-state-projection-foundation`
**Stacked baseline:** local PR-00 closeout `b1768209828e4a5167ddc72e704a13a7761a0564`

## Decision recorded

The Product Owner assigned PR-01 and accepted the ratchet-only architecture direction:

- computed-on-read Global Case State;
- no projection table or migration;
- PR-01 limited to the read endpoint;
- resume persistence deferred;
- fact/completion matrix locked before runtime code.

ADR 0036 records the architecture. The PR-01 implementation contract records the verified source
inventory and the current authority gaps.

## Intake findings

1. The codebase has Project, ProjectAssetLine, WorkflowInstance and ValidationIssue inputs.
2. No source may independently drive the v2.3 stage or route.
3. The authority defines 16 stages and next-action precedence, but not a complete predicate map
   from current legacy facts.
4. NCC selection, M365 freshness/revalidation, Release Manifest and publishing providers are not
   implemented.
5. Implementing an endpoint now would require invented completion semantics or would emit a
   misleading stage. Runtime is therefore intentionally held at the design gate.

## Exit criteria for the gate

- owner acceptance of a bounded, explicit fact predicate set for the first runtime slice;
- deterministic version/input contract tests;
- tenant/RBAC/fail-closed API coverage;
- focused baseline PASS with zero migration drift;
- local review and commit; no GitHub push until the local implementation is complete.
