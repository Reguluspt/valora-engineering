# ADR 0036 — Computed Global Case State Projection

**Status:** Accepted for architecture; fact-mapping gate remains open
**Date:** 2026-09-01
**Context:** VALORA UI/UX v2.3 PR-01 — Case State Projection Foundation
**Deciders:** Product Owner, Core Engineering Team

## Context

The UI/UX v2.3 orchestration authority requires a project-level `Global Case State` for
`Tổng quan hồ sơ`. It combines Project, WorkflowInstance, mandatory domain completion facts,
ValidationIssue, document/release state and meaningful resume context. Neither
`Project.status` nor `WorkflowInstance.current_state` is sufficient route authority by itself.

The current schema contains reusable Project, ProjectAssetLine, WorkflowInstance and
ValidationIssue facts. It does not yet contain the v2.3 NCC-selection, Microsoft 365
sync/revalidation, Release Manifest and publishing facts needed to evaluate every canonical
stage. Persisting a synthetic case-state row now would duplicate incomplete truth and create a
second workflow authority.

## Decision

1. **Compute on read.** PR-01 will implement Global Case State as an application-level,
   read-only projection. It will not add a case-state table, materialized state column,
   migration or hidden workflow enum.
2. **Facts remain authoritative.** Stage completion, blockers, stale state and next action are
   derived only from an approved, versioned fact matrix. Project/workflow status values may be
   inputs, but neither may select a UI route or claim completion alone.
3. **Missing authority fails closed.** An absent fact provider, unsupported target linkage or
   unapproved legacy-to-v2.3 mapping is `NOT_AVAILABLE`, never inferred as complete. Runtime
   must not ship an evaluator that fabricates later-stage progress.
4. **One deterministic evaluator.** The backend owns canonical stage evaluation and the
   next-action precedence: blocking, stale review, valid in-progress work, nearest incomplete
   mandatory step, next north-star step, then published/no action. Warning remains distinct
   from Blocking.
5. **Opaque computed version.** `case_version` is an opaque SHA-256 token over a canonical,
   tenant-scoped source snapshot. The snapshot includes stable source identity plus each
   participating row version; append-only/non-versioned facts contribute their stable identity,
   status and authoritative timestamp. Ordering and serialization are deterministic. The token
   is not a business sequence and clients must only compare it for equality.
6. **Read consistency.** A projection response is built from one database transaction. Future
   mutations using `expected_case_version` must recompute and compare the current projection
   after tenant/RBAC checks, and return an explicit version conflict on mismatch.
7. **API boundary.** PR-01 is limited to conceptual read endpoint
   `GET /api/v1/projects/{project_id}/case-state`. It is tenant scoped, permission checked and
   fail-closed. The backend returns semantic route keys; the frontend owns URL mapping.
8. **Resume is deferred.** No resume-context table or
   `PUT /api/v1/projects/{project_id}/resume-context` is introduced by PR-01. Resume persistence,
   freshness and conflict semantics require their own accepted design slice.
9. **No frontend state machine.** PR-02 may render the projection but may not reconstruct
   completion or routing from legacy endpoints when the projection is unavailable.

## Fact-mapping gate

Before the read endpoint is connected, the PR-01 implementation contract must identify, for
all 16 canonical stages:

- the mandatory facts and owning bounded context;
- the exact completion, blocking, warning, stale and not-applicable predicates;
- target linkage and tenant boundary;
- version contribution and deterministic ordering;
- semantic route key and default resume target;
- explicit behavior when the provider is not implemented.

Any row without approved predicates keeps runtime implementation blocked. Adding or changing a
provider later is a ratchet-only contract update with tests; it must not reinterpret historical
facts silently.

## Consequences

- No migration is required for PR-01.
- The projection cannot drift independently from business facts.
- Cache invalidation and projection-row synchronization are avoided.
- `case_version` changes when any participating authoritative fact changes, but is intentionally
  not human-readable or monotonic.
- The first PR-01 commit may be documentation/design-gate only. This is preferable to exposing a
  plausible but non-authoritative stage mapping.
- NCC, M365 and publishing PRs must register their canonical fact providers before their stages
  can be reported complete.
