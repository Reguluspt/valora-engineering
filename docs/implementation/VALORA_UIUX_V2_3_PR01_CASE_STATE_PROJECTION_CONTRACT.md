# VALORA UI/UX v2.3 — PR-01 Case State Projection Contract

**Status:** ACTIVE PREDICATE GATE — PR-01a source fact closed; projection runtime not authorized
**Task:** PR-01 — Case State Projection Foundation
**Date:** 2026-09-01
**Architecture:** ADR 0036 — computed on read, no projection migration

## 1. Scope

This contract is the ratchet for the future read-only Global Case State projection. PR-01 may
add `GET /api/v1/projects/{project_id}/case-state` only after every predicate used by the first
runtime slice is accepted below. Resume persistence and frontend URL wiring are out of scope.

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
| `PreliminaryResultArtifact` | immutable result version, content/source digests, lineage manifest | generation command is deferred; generic ProjectFile is not substituted |
| `ProjectOfficialIntakeCommit` | durable official boundary, artifact/version snapshot, actor/time, idempotency | PR-01a authority closeout passed locally at `f0e7c73`; projection provider not wired yet |
| document-engine records | legacy document/render/package records | no approved M365 freshness, managed-region or Release Manifest semantics |
| resume context | none approved for v2.3 | deferred; no PUT endpoint in PR-01 |

## 4. Canonical stage authority matrix

`MISSING` means the repository does not yet have an approved canonical fact provider.
`UNMAPPED` means facts exist but the authority does not define the exact predicate. Neither state
may be treated as completion.

| Stage | Provider gate | Current codebase evidence | Runtime status |
|---|---|---|---|
| `PRELIMINARY_REQUEST` | preliminary request facts + completion predicate | no canonical provider identified | MISSING |
| `PRELIMINARY_ANALYSIS` | preliminary analysis decision/facts | no canonical provider identified | MISSING |
| `PRELIMINARY_READY` | explicit readiness fact | no canonical provider identified | MISSING |
| `OFFICIAL_INTAKE` | `ProjectOfficialIntakeCommit` per ADR 0037 | PR-01a artifact/fact/command authority closeout passed locally; projection provider not wired | IMPLEMENTED / NOT WIRED |
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

**Gate result:** The architecture is accepted, but a truthful `current_stage` cannot yet be
computed for all valid projects. Runtime connection remains blocked until the owner accepts a
bounded first-stage predicate set or the missing providers are implemented in their assigned PRs.

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

## 7. First runtime acceptance checklist

PR-01a prerequisite status: **satisfied locally** at `f0e7c73`, with independent review and a
PostgreSQL-backed backend baseline of `1111 passed`, `0 failed`, `0 skipped`. This closes only the
official-intake source fact; it does not authorize the projection endpoint.

- [ ] Owner-approved predicates for every stage the endpoint can return.
- [ ] Explicit behavior for every other canonical stage.
- [ ] Tenant/RBAC and safe 404 tests.
- [ ] Deterministic projection and `case_version` tests.
- [ ] Blocking > stale > in-progress > incomplete > next > published precedence tests.
- [ ] Warning-not-Blocking test.
- [ ] Unknown target/provider fail-closed test.
- [ ] No case-state projection migration and no resume-context endpoint.
- [ ] Existing legacy-conflict ratchet does not expand.
