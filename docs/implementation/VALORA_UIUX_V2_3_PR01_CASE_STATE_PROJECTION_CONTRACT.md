# VALORA UI/UX v2.3 — PR-01 Case State Projection Contract

**Status:** OWNER CLOSEOUT COMPLETE LOCALLY — bounded provider slice and read endpoint
**Task:** PR-01 — Case State Projection Foundation
**Date:** 2026-09-01
**Architecture:** ADR 0036 — computed on read, no projection migration

## 1. Scope

This contract is the ratchet for the read-only Global Case State projection. The bounded first
runtime slice and `GET /api/v1/projects/{project_id}/case-state` are implemented locally under
`VALORA-PR01-IMPL-003` and `VALORA-PR01-IMPL-004`. Resume persistence and frontend URL wiring
remain out of scope.

## 2. Canonical output semantics

The eventual response must expose, at minimum:

- `case_version`: opaque equality token defined by ADR 0036;
- `current_stage`: one of the 16 canonical stages, derived from mandatory facts;
- ordered stage results with `COMPLETE | IN_PROGRESS | INCOMPLETE | BLOCKED | STALE |
  NOT_APPLICABLE | NOT_AVAILABLE`;
- exactly one `next_action`, or explicit published/no-action;
- separate blocker, warning and stale collections;
- semantic route key and typed target context, never a frontend URL;
- projection capability/availability metadata so missing providers are visible.

`current_stage` and `next_action.stage` may differ. Opening a screen is never a completion fact.

## 3. Source inventory verified in the current codebase

| Source | Verified reusable facts | Limits |
|---|---|---|
| `Project` | tenant, project identity, legacy status, `row_version` | legacy status is input only; no canonical-stage mapping is approved |
| `ProjectAssetLine` | review status, validation status, appraised price, `row_version` | does not prove supplier selection, quote completion or release readiness |
| `WorkflowInstance` | target, current state, lifecycle status, `row_version` | legacy state is not Global Case State or route authority |
| `ValidationIssue` | target, Warning/Blocking, open/resolved/ignored, `row_version` | target-to-project resolution must be explicit and tenant-safe |
| `ImportSourceArtifact` | `organization_id`, `project_id`, `import_batch_id`, `generation`, checksum, storage identity and availability state | authoritative provider `preliminary_request_v1` is wired |
| `PreliminaryResultArtifact` | immutable result version, content/source digests, lineage manifest | generation and authoritative provider `preliminary_ready_v1` are wired; generic ProjectFile is not substituted |
| `PreliminaryAnalysisSnapshot` | immutable, versioned analysis snapshot with canonical digest and lineage | schema, command and authoritative provider `preliminary_analysis_v1` are wired |
| `ProjectOfficialIntakeCommit` | durable official boundary, artifact/version snapshot, actor/time, idempotency | PR-01a authority closeout passed locally at `f0e7c73`; provider `official_intake_commit_v1` is wired |
| document-engine records | legacy document/render/package records | no approved M365 freshness, managed-region or Release Manifest semantics |
| resume context | none approved for v2.3 | deferred; no PUT endpoint in PR-01 |

## 4. Canonical stage authority matrix

`MISSING` means the repository does not yet have an implemented canonical fact provider.
`UNMAPPED` means facts exist but the authority does not define the exact predicate. Neither state
may be treated as completion.
`IMPLEMENTED / WIRED` means the predicate, required source fact and bounded runtime provider are
implemented and connected to the read endpoint. It does not imply completion for an individual
project; the provider still computes its result from authoritative facts on every read.

| Stage | Provider gate | Current codebase evidence | Runtime status |
|---|---|---|---|
| `PRELIMINARY_REQUEST` | current `ImportSourceArtifact` in state `AVAILABLE` per ADR 0038 D1–D2 | `preliminary_request_v1` provider implemented | IMPLEMENTED / WIRED |
| `PRELIMINARY_ANALYSIS` | `PreliminaryAnalysisSnapshot` per ADR 0038 D3–D4 | source fact, command and `preliminary_analysis_v1` provider implemented | IMPLEMENTED / WIRED |
| `PRELIMINARY_READY` | finalized `PreliminaryResultArtifact` per ADR 0038 D5 | generation pipeline and `preliminary_ready_v1` provider implemented | IMPLEMENTED / WIRED |
| `OFFICIAL_INTAKE` | `ProjectOfficialIntakeCommit` per ADR 0037 | durable command and `official_intake_commit_v1` provider implemented | IMPLEMENTED / WIRED |
| `ASSET_REVIEW` | mandatory asset-review predicates | asset-line review/validation facts exist; completeness predicate not approved | UNMAPPED |
| `ASSET_WORKBENCH` | mandatory workbench completion facts | asset lines and sessions exist; completion predicate not approved | UNMAPPED |
| `PRICE_EVIDENCE` | required price-evidence coverage | evidence/quote primitives exist; project-line coverage predicate not approved | UNMAPPED |
| `SUPPLIER_QUOTES` | supplier-quote completion facts | quote primitives exist; v2.3 completion predicate not approved | UNMAPPED |
| `SUPPLIER_SELECTION` | accepted NCC-selection revision | PR-03 persistence not implemented | MISSING |
| `APPRAISAL_RESULT` | authoritative appraised-price decision coverage | appraised values exist; decision/completeness predicate not approved | UNMAPPED |
| `DOCUMENT_WORKSPACE` | required document/revision readiness | legacy document records exist; v2.3 document-set predicate not approved | UNMAPPED |
| `DOCUMENT_SYNC_REVIEW` | M365 freshness/revalidation/conflict facts | PR-05–PR-07 not implemented | MISSING |
| `PUBLISHING_PREPARATION` | release-readiness facts | PR-08 release domain not implemented | MISSING |
| `PUBLISHING_EXCEPTION_REVIEW` | release exception disposition facts | PR-08/PR-09 not implemented | MISSING |
| `PUBLISHING_CONFIRMATION` | publish confirmation readiness/commit boundary | PR-09 not implemented | MISSING |
| `PUBLISHED` | final immutable Release Manifest | PR-08/PR-09 not implemented | MISSING |

**Gate result:** The bounded preliminary prefix (`PRELIMINARY_REQUEST`, `PRELIMINARY_ANALYSIS`,
`PRELIMINARY_READY`) plus `OFFICIAL_INTAKE` is implemented and wired. The runtime computes a total
`current_stage` within that bounded prefix, publishes all 12 downstream stages as explicit
`NOT_AVAILABLE`, and exposes capability metadata. No downstream completion is inferred.

For the official boundary specifically, ADR 0037 defines the durable fact and command, and PR-01a
closed that source-domain authority slice locally. Its
presence proves only that official intake was committed and the Project is eligible for the hub;
it does not infer completion of other stages.

## 5. Cross-cutting predicates already locked

These rules are authorized independently of individual stage completion:

1. Open `ValidationIssue` with severity `BLOCKING` outranks all non-blocking next actions.
2. Open `WARNING` remains a warning and cannot block by severity conversion.
3. Stale state outranks valid in-progress and incomplete work, but only an authoritative provider
   may declare stale.
4. Ignored/resolved issues are not open blockers; any display/history treatment remains separate.
5. A target must be resolved to the requested project and organization before it contributes.
   Unknown target types fail closed and do not leak existence.
6. Missing provider capability is explicit `NOT_AVAILABLE`, never `NOT_APPLICABLE` or `COMPLETE`.
7. Later completion cannot make an earlier mandatory stage complete by implication.

## 6. `case_version` source contract

Canonical hash input uses a versioned envelope and lexicographically ordered entries:

```text
contract = "global-case-state-v1"
organization_id = <tenant UUID>
project_id = <project UUID>
facts[] = <provider>:<stable-id>:<row-version-or-authoritative-version>:<state>
```

The implementation must use a canonical serializer and SHA-256. It must not include secrets,
display text, unordered query results or database-specific object representations. A change in
the envelope requires a versioned contract update and tests.

## 7. Public read contract

`GET /api/v1/projects/{project_id}/case-state` returns:

- `case_version`, `current_stage` and one typed `next_action`;
- all 16 ordered stages with `result` and `provider_key`;
- separate `blockers`, `warnings` and `stale` collections (`stale` remains empty because PR-01
  has no authoritative stale provider);
- all 16 stage capabilities with availability, provider key and registry version.

Internal provider facts and per-stage `fact_token` values are deliberately excluded. Authentication
returns `401`; inactive or unauthorized actors receive typed `403`; missing and cross-tenant
projects receive the same safe `404`. Projection failures return a typed safe `500` without
internal detail.

## 8. First runtime acceptance checklist

PR-01a prerequisite status: **satisfied locally** at `f0e7c73`. The provider/aggregator slice and
the separately authorized endpoint implementation passed local technical acceptance on 2026-09-05.

- [x] Owner-approved predicates for every implemented stage the endpoint can return.
- [x] Explicit `NOT_AVAILABLE` behavior for every other canonical stage.
- [x] Tenant/RBAC and safe 404 tests.
- [x] Deterministic projection and `case_version` tests.
- [x] Blocking precedence and bounded next-action tests.
- [x] Warning-not-Blocking test.
- [x] Unknown target/provider fail-closed test.
- [x] No case-state projection migration and no resume-context endpoint.
- [x] Existing legacy-conflict ratchet does not expand.
