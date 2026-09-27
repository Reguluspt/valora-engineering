> **HISTORICAL DIRECT-WRITE RESEARCH — 2026-09-21**
> Retained as evidence only. Do not execute/reopen this plan from current roadmap. Direct replacement of an existing OneDrive item is historical/blocked. Current document direction is ADR 0043–0045 + `docs/VALORA_APPRAISAL_OS_UNIFIED_ROADMAP_V2_3.md`.

# PR-07 stale upload-session `404` architecture evaluation

**Start time:** 2026-09-19, Asia/Saigon
**Status:** amended 2026-09-19 — recommended Option A accepted by Product Owner

## Initial purpose

Decide whether the single `C2_AUTO_V2` live observation of HTTP `404 itemNotFound` after a verified
concurrent write is sufficient to amend ADR 0042/D6, or whether PR-07 must remain blocked pending a
documented provider guarantee or a different mechanism.

This evaluation does not authorize another live invocation, an Entra change, implementation of the
PR-07 runtime, a migration, PR-08 work, or an amendment to accepted authority.

## Strategy

1. Separate the sanitized live facts from interpretations of provider behavior.
2. Compare those facts with accepted ADR 0042/D6 and the PR-07 contract.
3. Check current Microsoft Graph and OneDrive documentation for normative status/error semantics.
4. Apply the conservative acceptance test: a production write mechanism must protect the invariant
   across executions, not merely preserve bytes in one observed run.

## Checklist

- [x] Confirm the exact attempt, snapshot and no-retry boundary.
- [x] Confirm fresh commit, concurrent write, stale response and coherent post-read facts.
- [x] Confirm recycle cleanup, resolved ledger and restored Entra baseline.
- [x] Re-read ADR 0042/D6 and the accepted provider-commit contract.
- [x] Check current Microsoft documentation for upload-session `If-Match`, completion and `404`.
- [x] Test the proposed relaxation against ambiguity, recovery and future provider drift.
- [x] Produce a bounded G3 decision plan without changing accepted authority.

## Result

### Verified live facts

Attempt `2a06438c-5ad2-46f1-8da2-b60776647f86` was the only authorized `C2_AUTO_V2` invocation.
Fresh partial/final requests returned HTTP `202`/`200`; coherent post-read proved the fresh commit.
After the concurrent write, the stale partial request returned HTTP `202` and the stale final request
returned HTTP `404` with `itemNotFound`. Coherent same-item post-read proved that item identity and
the concurrent bytes/eTag were preserved. The result was therefore safe in the observed run but
`INCONCLUSIVE` / `ALTERNATE_REJECTION`, not the candidate `SAFE_412` observation.

The stale session was cancelled, the fixture was deleted to the recycle bin, the ledger resolved and
local credential/listener state was cleared. Read-only Entra verification confirmed the PR-05
baseline of one existing secret and delegated `Files.Read` only.

### Documented provider boundary

Microsoft documents `If-Match` on `createUploadSession`: a mismatch at that request returns HTTP
`412`. It documents automatic completion of the final fragment as HTTP `200` or `201`. For resumable
uploads, HTTP `404` means the upload session no longer exists and the generic guidance is to start
the upload over. The error catalogue describes `itemNotFound` as a missing resource and separately
lists `uploadSessionNotFound`.

The documentation does not state that a concurrent destination write must invalidate an exact-item
upload session, that such invalidation must return `404 itemNotFound`, or that this response is a
durable equivalent of an eTag precondition failure. It also does not document an `If-Match` header on
the preauthenticated final fragment URL.

### Architecture consequence

The observed post-read proves that no stale overwrite occurred in this attempt. It does not prove
why the session returned `404`, whether the behavior is stable across accounts/regions/time, or
whether every stale final fragment is rejected before commit. Treating all `404 itemNotFound`
responses as accepted stale-plan outcomes would therefore convert an ambiguous provider failure into
a production concurrency guarantee without normative support.

ADR 0042/D6 intentionally places this uncertainty before runtime implementation. Its safety goal is
not the literal number `412`; it is a provider-backed conditional commit that cannot overwrite a
concurrent writer. The number remains useful because it is the currently accepted, unambiguous proof
shape. The single safe `404` observation is evidence about one execution, not enough authority to
relax that proof shape.

## Verification

- Sanitized evidence: `local-artifacts/pr07/20260919T034221.242513Z-2a06438c-5ad2-46f1-8da2-b60776647f86.json`.
- [Microsoft Graph `createUploadSession`](https://learn.microsoft.com/en-us/graph/api/driveitem-createuploadsession?view=graph-rest-1.0).
- [Microsoft Graph `uploadSession` resource](https://learn.microsoft.com/en-us/graph/api/resources/uploadsession?view=graph-rest-1.0).
- [OneDrive error responses](https://learn.microsoft.com/en-us/onedrive/developer/rest-api/concepts/errors?view=odsp-graph-online).
- [Historical OneDrive docs issue: concurrent upload and `itemNotFound`](https://github.com/OneDrive/onedrive-api-docs/issues/1132) — corroborating only, not normative authority.
- ADR 0042/D6 and the accepted PR-07 sync/conflict contract were checked against the current working
  tree at HEAD `46e0792b3ae697158f0fe38db8100fbd4afdc6fc`.

## Decision

**Recommendation for Product Owner approval:** do not amend ADR 0042/D6 from this observation. Mark
`C2_AUTO_V2` as a completed research candidate that is not accepted for production. Keep PR-07
runtime/migrations, G4 and PR-08 closed.

**Action:** use [the completed G3 architecture decision](../plan/done/pr07-g3-architecture-decision.md)
and [the completed read-only clarification plan](../plan/done/pr07-provider-clarification-read-only.md).
The accepted choice retains D6; the public-source pass stopped at `UNDOCUMENTED`. Any external
Microsoft clarification requires new send-time authority and is not another live retry.

**Reopen trigger:** Microsoft publishes or supplies a clear guarantee that binds the frozen eTag to
the exact-item session through commit, including stable stale-response semantics, or a different
Graph mechanism is documented and locally reviewable as an exact-item conditional commit.

## Amendments

- 2026-09-19 · § Decision: the Product Owner approved recommended Option A. ADR 0042/D6 and the
  PR-07 contract remain unchanged; `C2_AUTO_V2` research is closed, `runtime_gate=BLOCKED`, and only
  the separate read-only provider-clarification workstream may continue.
