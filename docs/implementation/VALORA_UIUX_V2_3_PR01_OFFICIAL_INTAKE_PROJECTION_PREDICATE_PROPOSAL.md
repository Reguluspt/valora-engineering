# VALORA UI/UX v2.3 — PR-01 Official Intake Projection Predicate

**Status:** HISTORICAL DESIGN AUTHORITY — RUNTIME SUBSEQUENTLY IMPLEMENTED/WIRED

**Task:** VALORA-PR01-DESIGN-002

**Scope:** Bounded predicate for the `OFFICIAL_INTAKE` canonical stage of Global Case State

**Date:** 2026-09-03

**Architecture:** ADR 0036 (computed-on-read, no projection migration) + ADR 0037 (durable official-intake fact)

> **2026-09-23 current disposition:** This file preserves the original predicate-design gate. `official_intake_commit_v1` and the four-stage computed Case State runtime were subsequently authorized, implemented and wired. Later implementation contracts/audits and the Unified Roadmap govern current runtime status; the historical “runtime not authorized” wording below is not a present blocker.

This document records the owner-approved bounded predicate for `OFFICIAL_INTAKE` (D1–D10, approved 2026-09-03). It does not authorize runtime wiring, endpoint implementation, frontend work, persistence changes, or reinterpretation of legacy status. The PR-01 projection runtime and `current_stage` publication remain blocked until a bounded contiguous prefix of canonical stages is accepted (D4).

---

## 1. Accepted facts and non-negotiable boundaries

The following are treated as fixed for this predicate; they derive from ADR 0036, ADR 0037, the PR-01 Case State Projection Contract, the PR-01 Official Intake Commit Contract, and the owner-approved decisions D1–D10.

- **Only `ProjectOfficialIntakeCommit` proves official-intake commitment.** `Project.status`, `WorkflowInstance.current_state`, `AuditEvent`, page visits, and generic `ProjectFile` rows are not authoritative for this stage.
- **Absence is not inferred from legacy project/workflow status.** A Project without a `ProjectOfficialIntakeCommit` row is reported as not committed, regardless of any legacy enum value.
- **Fact presence proves only the official-intake boundary and hub eligibility.** It does not complete `PRELIMINARY_REQUEST`, `PRELIMINARY_ANALYSIS`, `PRELIMINARY_READY`, `ASSET_REVIEW`, or any later canonical stage.
- **Tenant/project linkage fails closed.** Any query for the commit fact must be scoped by `organization_id` and `project_id`. A cross-tenant or unresolvable Project must produce a safe 404 and must not leak existence.
- **Authentication and authorization fail closed (D10).**
  - Anonymous, missing or invalid session → `401`.
  - Authenticated actor lacking read permission → `403`.
  - Missing, inaccessible or cross-tenant Project → safe `404`.
- **Warning is not converted to Blocking.** Open `ValidationIssue` rows with severity `WARNING` may be surfaced as warnings but cannot make `OFFICIAL_INTAKE` `BLOCKED`.
- **Missing provider capability is never reported as `COMPLETE` or `NOT_APPLICABLE`.** If the official-intake provider is unavailable or unregistered, the stage result is `NOT_AVAILABLE` with capability metadata. Missing, inaccessible or cross-tenant Project resolution remains a safe `404` at the boundary per D10; the provider is not invoked.
- **Unexpected provider failures are explicit typed projection errors.** An unexpected exception inside an implemented provider is surfaced as a typed projection error at the boundary; it must not be disguised as stage `NOT_AVAILABLE` and must not expose raw exception details (D7).
- **No projection persistence.** Global Case State remains computed-on-read; no case-state table, materialized column, or projection migration is introduced.
- **Audit is evidence, not the business fact.** The projection provider queries `ProjectOfficialIntakeCommit`, not `AuditEvent`.

---

## 2. Projection-provider contract

The projection runtime will contain one bounded provider named `official_intake_commit_v1`. Its responsibility is limited to answering, for a given tenant-scoped Project:

1. Does an official-intake commit fact exist?
2. Is the fact safely resolvable to the requested Project and tenant?
3. What stable identity/version data does it contribute to `case_version`?

### Provider interface

```text
inputs:
  organization_id: UUID
  project_id: UUID
  db_session: Session (single read transaction)

outputs:
  stage: OFFICIAL_INTAKE
  result: COMPLETE | INCOMPLETE | NOT_AVAILABLE
  fact_snapshot:
    commit_id: UUID | null
    artifact_id: UUID | null
    artifact_version: int | null
    artifact_checksum: hex64 | null
    source_snapshot_sha256: hex64 | null
    committed_at: ISO-8601 UTC | null
  diagnostics:
    provider_key: "official_intake_commit_v1"
    query_failed: bool
```

`result` follows the canonical stage-result enumeration (Projection Contract §2) but the raw provider intentionally emits only `COMPLETE`, `INCOMPLETE` or `NOT_AVAILABLE`. The aggregator maps the raw result to the final stage result per D1–D3 and D7. `BLOCKED` and `STALE` are never produced by this provider.

### Resolution rules

- Query `ProjectOfficialIntakeCommit` by `(organization_id, project_id)`.
- If the Project itself does not resolve inside the tenant, return safe 404 at the projection boundary; the provider is not invoked with an invalid Project.
- If the commit row exists and its foreign-key constraints are satisfied (enforced by the database), return `COMPLETE`.
- If the commit row does not exist, return `INCOMPLETE`.
- If the query raises an unexpected exception, return a typed error to the projection boundary; `diagnostics.query_failed` = true.

### Target/linkage safety

- The provider does not perform cross-tenant inference. Unknown or unsafe target resolution is delegated to the projection boundary, which fails closed.
- The provider does not resolve the commit through any path other than `(organization_id, project_id)`.

---

## 3. Truth table

The table below assumes the projection boundary has already authenticated the actor, verified read permission, and resolved `organization_id`/`project_id` to an accessible Project. Authentication and authorization boundary behavior is defined separately in §1.

| Condition | Commit fact | ValidationIssue interaction | Provider raw result | Final aggregator result | `diagnostics.query_failed` | Notes |
|---|---|---|---|---|---|---|
| Provider unavailable / not registered | N/A | N/A | N/A | `NOT_AVAILABLE` | N/A | Capability metadata exposes missing provider (D7). |
| Provider query failure (unexpected exception) | unknown | N/A | N/A | explicit typed projection error | true | Boundary returns typed error; no raw exception details (D7). |
| Accessible Project with no commit fact | absent | none | `INCOMPLETE` | `INCOMPLETE` | false | Absence is not inferred from legacy status. |
| Valid tenant-scoped commit fact present | exists | none | `COMPLETE` | `COMPLETE` | false | Only authoritative proof of official intake. |
| Open BLOCKING issue + no commit fact | absent | BLOCKING + OPEN + accepted target spelling | `INCOMPLETE` | `BLOCKED` (D1) | false | Blocker resolution takes `next_action` precedence. |
| Open BLOCKING issue + commit fact present | exists | BLOCKING + OPEN + accepted target spelling | `COMPLETE` | `COMPLETE` (D2) | false | Completed stage is not rewritten; blocker affects blocker collection and `next_action`. |
| Open WARNING ValidationIssue exists | exists or absent | WARNING + OPEN | per commit fact | per commit fact | false | Warning is never converted to Blocking. |
| Stale precedence declared by another provider | exists or absent | N/A | per commit fact | per commit fact | false | `OFFICIAL_INTAKE` never reports `STALE` in v1 (D3). |

### Cross-cutting constraints carried into the table

- `NOT_AVAILABLE` is never reported as `COMPLETE` or `NOT_APPLICABLE`.
- A missing commit fact is `INCOMPLETE` at the provider; the aggregator reports `BLOCKED` only when D1 applies.
- Only the official-intake provider evaluates the commit fact; no other provider may synthesize it.

---

## 4. Stage-result semantics for `OFFICIAL_INTAKE`

| Scenario | Final aggregator result |
|---|---|
| Commit fact present | `COMPLETE` |
| Commit fact absent, no applicable open BLOCKING issue | `INCOMPLETE` |
| Commit fact absent, applicable open BLOCKING issue | `BLOCKED` (D1) |
| Provider unavailable / not registered | `NOT_AVAILABLE` |
| Unexpected failure inside implemented provider | explicit typed projection error (D7) |

`OFFICIAL_INTAKE` never reports `STALE` in v1 (D3).

### Rationale

`OFFICIAL_INTAKE` is a discrete commit boundary, not an in-progress workspace. The existence of one valid `ProjectOfficialIntakeCommit` per Project maps directly to `COMPLETE`. The absence of the fact maps directly to `INCOMPLETE` at the provider level; an applicable blocker causes the aggregator to report `BLOCKED` per D1. There is no intermediate `IN_PROGRESS` state for this stage because the boundary is atomic.

---

## 5. Exact inputs contributed to `case_version`

ADR 0036 §5 requires `case_version` to be an opaque SHA-256 over a canonical, tenant-scoped source snapshot with deterministic ordering and serialization. Projection Contract §6 locks the global envelope:

```text
contract = "global-case-state-v1"
organization_id = <tenant UUID>
project_id = <project UUID>
facts[] = <provider>:<stable-id>:<row-version-or-authoritative-version>:<state>
```

The official-intake provider fits inside this envelope; it does not extend `global-case-state-v1`.

### Provider authoritative snapshot inputs

When the commit fact is present, the provider contributes the following stable inputs (Commit Contract §5, D8):

- `provider` = `official_intake_commit_v1`
- `commit_id` = `ProjectOfficialIntakeCommit.id`
- `artifact_id` = `ProjectOfficialIntakeCommit.preliminary_result_artifact_id`
- `artifact_version` = `ProjectOfficialIntakeCommit.preliminary_result_version`
- `artifact_checksum` = `ProjectOfficialIntakeCommit.preliminary_result_sha256`
- `source_snapshot_sha256` = `ProjectOfficialIntakeCommit.source_snapshot_sha256`
- `committed_at` = `ProjectOfficialIntakeCommit.committed_at` normalized to UTC with exactly six fractional digits: `YYYY-MM-DDTHH:MM:SS.ffffffZ` (D8)

If the fact is absent, the provider contributes an explicit absence marker.

### Accepted `facts[]` encoding (D9)

Present:

```text
facts[] = official_intake_commit_v1:<commit-id>:av1-<sha256>:complete
```

Absent:

```text
facts[] = official_intake_commit_v1:null:absent-v1:absent
```

The `av1` digest input is canonical UTF-8 JSON containing:

```json
{
  "schema": "official-intake-authoritative-version-v1",
  "artifact_id": "<UUID lowercase hyphenated>",
  "artifact_version": <integer>,
  "artifact_checksum": "<sha256 lowercase hex>",
  "source_snapshot_sha256": "<sha256 lowercase hex>",
  "committed_at": "<YYYY-MM-DDTHH:MM:SS.ffffffZ>"
}
```

Serialized with lexicographically sorted keys, compact separators `(",", ":")`, no ASCII escaping, lowercase hyphenated UUIDs, and lowercase hexadecimal digests. This encoding is locked and must be covered by future fixture tests.

### Ordering

Within the global snapshot, `facts[]` entries are sorted lexicographically. The official-intake entry therefore sits in a deterministic position relative to other providers. `null` values are represented as the literal string `"null"`.

### Serialization

- Deterministic canonical serialization required by ADR 0036 §5 over the `global-case-state-v1` envelope (Projection Contract §6).
- Accepted concrete serializer: `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"))`.
- UUIDs as lowercase hyphenated strings.
- Timestamps as UTC with exactly six fractional digits and `Z` suffix (D8).
- Excludes display text, filenames, secrets, audit payloads, and unordered collection representations.

---

## 6. Effects on `current_stage`, `next_action` and semantic target context

### `current_stage`

The official-intake provider contributes one stage result to the canonical 16-stage matrix. The aggregator applies the precedence defined in ADR 0036 and the orchestration addendum. Per D4, `current_stage` must not jump to `OFFICIAL_INTAKE` while preceding mandatory stages lack accepted predicates; the overall PR-01 projection runtime and `current_stage` publication remain blocked until a bounded contiguous prefix is accepted.

### `next_action`

The official-intake provider does not directly emit a `next_action`. The aggregator:

- If `OFFICIAL_INTAKE` is `INCOMPLETE` and no applicable blocker or stale condition exists, `next_action.stage` is `OFFICIAL_INTAKE` with semantic route key `official_intake_pending` (D5).
- If `OFFICIAL_INTAKE` is `BLOCKED` under D1, blocker resolution controls `next_action`; the ordinary pending-intake action must not be emitted.
- If `OFFICIAL_INTAKE` is `COMPLETE` and no higher-precedence condition exists, `next_action` moves toward the next incomplete mandatory stage, subject to owner acceptance of those predicates.

### Semantic target context

The official-intake provider does not carry a semantic target context. The commit fact identity may be used by traceability entry points such as `Xem nguồn gốc` or `Xem quyết định`, reconciled with `docs/design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md` §2.

### Vietnamese stage-card label

Accepted label: `Chuyển sang thẩm định chính thức` (D6).

---

## 7. Explicit non-effects on preliminary and downstream stages

The following are treated as non-effects of the official-intake predicate:

- `PRELIMINARY_REQUEST`, `PRELIMINARY_ANALYSIS`, and `PRELIMINARY_READY` remain independent; their predicates must be accepted separately.
- `ASSET_REVIEW`, `ASSET_WORKBENCH`, `PRICE_EVIDENCE`, `SUPPLIER_QUOTES`, `SUPPLIER_SELECTION`, `APPRAISAL_RESULT`, and all publishing stages are not completed or advanced by the presence of the official-intake fact.
- `Project.status` and `WorkflowInstance.current_state` are not reinterpreted or advanced.
- No official appraised price, supplier selection, document revision, or release manifest is created or implied.
- No resume-context persistence is introduced.

---

## 8. Owner-approved decisions

The following decisions were owner-approved on 2026-09-03 and are now bounded predicate authority for `OFFICIAL_INTAKE`:

1. **D1 — BLOCKING issue with no commit fact:** raw provider result `INCOMPLETE`; aggregator final stage result is `BLOCKED`; blocker is surfaced separately and blocker resolution takes `next_action` precedence.
2. **D2 — BLOCKING issue with commit fact present:** `OFFICIAL_INTAKE` remains `COMPLETE`; the blocker affects blocker collections and `next_action` only.
3. **D3 — Stale:** `OFFICIAL_INTAKE` never reports `STALE` in v1.
4. **D4 — `current_stage` fallback:** `current_stage` must not jump to `OFFICIAL_INTAKE` while preceding mandatory stages lack accepted predicates; runtime/current-stage publication remains blocked until a bounded contiguous prefix is accepted.
5. **D5 — Pending route key:** semantic route key `official_intake_pending`.
6. **D6 — Vietnamese label:** stage-card label `Chuyển sang thẩm định chính thức`.
7. **D7 — Failure semantics:** missing/unregistered capability → `NOT_AVAILABLE` with capability metadata; unexpected failure inside an implemented provider → explicit typed projection error; no raw exception details.
8. **D8 — Timestamp normalization:** `committed_at` normalized to UTC with exactly six fractional digits: `YYYY-MM-DDTHH:MM:SS.ffffffZ`.
9. **D9 — `facts[]` encoding:** keep four-slot envelope; use composite authoritative version `av1-<sha256>` in slot three, with canonical UTF-8 JSON digest input as specified in §5; no envelope extension.
10. **D10 — Authentication/authorization:** anonymous/missing/invalid session → `401`; authenticated lacking read permission → `403`; missing/inaccessible/cross-tenant Project → safe `404`.

No unresolved owner question remains for this bounded predicate.

---

## 9. Runtime-test matrix

**Tests are described only; they are not implemented by this task.**

When the owner authorizes runtime wiring, the following tests are required:

| Test | Scenario | Expected projection behavior |
|---|---|---|
| T.1 | Project exists, no `ProjectOfficialIntakeCommit` | `OFFICIAL_INTAKE` = `INCOMPLETE`; no blocker from this provider. |
| T.2 | Valid tenant-scoped commit fact exists | `OFFICIAL_INTAKE` = `COMPLETE`; `case_version` includes commit identity per D9. |
| T.3 | Commit fact belongs to another tenant | Tenant-scoped query does not see foreign row → `OFFICIAL_INTAKE` = `INCOMPLETE`. Safe 404 only when Project itself is inaccessible. |
| T.4 | Provider raises unexpected exception | Explicit typed projection error at boundary; no raw exception details; `diagnostics.query_failed` = true (D7). |
| T.5 | Provider is not registered | `OFFICIAL_INTAKE` = `NOT_AVAILABLE`; aggregator capability metadata reflects missing provider (D7). |
| T.6 | Open WARNING ValidationIssue exists | `OFFICIAL_INTAKE` result follows commit fact; warning surfaced separately; stage not `BLOCKED`. |
| T.7 | Open BLOCKING ValidationIssue + no commit fact | `OFFICIAL_INTAKE` = `BLOCKED`; blocker takes `next_action` precedence (D1). |
| T.8 | `case_version` equality and sensitivity | Same facts produce identical tokens; changing any digest input or normalized timestamp changes token (D8–D9). |
| T.9 | `case_version` determinism | Repeated reads in the same transaction produce identical tokens regardless of row order. |
| T.10 | `case_version` excludes display text/secrets | Token input contains no filenames, user names, audit payloads, credentials, or display text. |
| T.11 | `current_stage` does not jump to downstream stage | Even with commit fact, `ASSET_REVIEW` and later stages remain unapproved/NOT_AVAILABLE (D4). |
| T.12 | Preliminary stages not backfilled | Commit fact does not make `PRELIMINARY_*` stages `COMPLETE`. |
| T.13 | Authentication/authorization boundary | Anonymous/missing session → `401`; authenticated without read permission → `403`; inaccessible/cross-tenant Project → safe `404` without leak (D10). |
| T.14 | Read consistency | Each projection response is built within one transaction; concurrency uses separate sessions/transactions, each response internally consistent. |
| T.15 | Blocking > stale > in-progress > incomplete precedence | Aggregator respects ADR 0036 precedence using official-intake result as one input. |

---

## 10. Summary of accepted authority

| Topic | Source | Accepted decision |
|---|---|---|
| Source fact | ADR 0037 / Commit Contract | `ProjectOfficialIntakeCommit` only |
| Computed-on-read / no migration | ADR 0036 | No projection persistence |
| Tenant/project fail-closed | ADR 0037 / Contract | Safe 404, no existence leak |
| Warning ≠ Blocking | Cross-cutting contract | WARNING never blocks |
| Provider key | Commit Contract §5 | `official_intake_commit_v1` |
| Stage result mapping | D1–D3, D7 | `COMPLETE` / `INCOMPLETE` / `BLOCKED` / `NOT_AVAILABLE` / typed error as defined |
| `case_version` encoding | D8–D9, Projection Contract §6 | Four-slot envelope, composite `av1-<sha256>`, UTC six-digit timestamp |
| `current_stage` fallback | D4 | Do not jump to `OFFICIAL_INTAKE` until contiguous prefix accepted |
| Pending route key | D5 | `official_intake_pending` |
| Vietnamese label | D6 | `Chuyển sang thẩm định chính thức` |
| Authentication/authorization | D10 | `401` / `403` / safe `404` |

---

## 11. Stop conditions observed

No stop condition from the task packet is triggered:

- Branch is `pr-01-case-state-projection-foundation`.
- HEAD matches expected baseline `c380bc0eac05e8790f7dc4fb9e1f46dd38eabd7b`.
- Only the allowlisted documentation files changed.
- Authority read in required order; D1–D10 recorded without reinterpretation.
- No runtime, endpoint, migration, frontend, ADR, or predicate expansion authorized.
- Overall PR-01 projection runtime and `current_stage` gate remain open per D4.

This predicate authority is ready for independent Qwen review and Codex/owner gate closeout.
