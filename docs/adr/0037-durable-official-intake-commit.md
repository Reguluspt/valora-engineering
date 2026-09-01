# ADR 0037 — Durable Official Intake Commit

**Status:** Proposed — owner review required
**Date:** 2026-09-01
**Context:** VALORA UI/UX v2.3 PR-01 official-intake design slice
**Deciders:** Product Owner, Core Engineering Team

## Context

The north-star flow crosses an explicit business boundary at `Chuyển sang thẩm định chính thức`.
The inherited v2.1/v2.2 authority requires a finalized preliminary-result file and an explicit
user action. A successful transition changes the pre-case presentation to
`Đã chuyển thành hồ sơ`, opens the official dossier flow and must preserve lineage to the
preliminary request, source workbook, analysis snapshot and preliminary result.

The current repository has no canonical pre-case or finalized preliminary-result artifact model.
It also has no durable fact for the transition. `Project.status`,
`WorkflowInstance.current_state`, `AuditEvent` and page visits cannot fill that role:

- the project/workflow enums carry legacy QC/approval semantics;
- audit is mutation evidence, not the business fact itself;
- a route visit is not a commit;
- inferring the boundary would make Global Case State non-deterministic.

ADR 0036 therefore cannot connect the case-state endpoint until this boundary has an
authoritative source fact.

## Decision

1. **Stable Project identity.** `Project` remains the case identity across preliminary and
   official phases. The UX phrase “hồ sơ mới” means activation of the official dossier phase;
   the transition does not clone or silently replace the Project row.
2. **Dedicated append-only fact.** The successful boundary is represented by one
   `ProjectOfficialIntakeCommit` per Project. It is business truth; `AuditEvent` is written
   atomically as evidence but is not queried as a substitute.
3. **Explicit human command.** Only `CommitProjectOfficialIntake` may create the fact. The
   command requires authenticated human confirmation, tenant/RBAC scope, optimistic versions,
   a bounded idempotency key and a canonical request digest.
4. **No legacy status mutation.** The command does not reinterpret or advance
   `Project.status` and does not execute legacy QC/approval workflow commands. The presence of
   the commit fact is the only authority that the official-intake boundary was crossed.
5. **Finalized result prerequisite.** The command requires a canonical, immutable
   `PreliminaryResultArtifact` belonging to the same tenant and Project. It must have a stable
   artifact ID, version, content checksum and lineage to the source workbook/analysis snapshot.
   A generic `ProjectFile` or generated filename alone is insufficient.
6. **Atomic success.** One transaction locks Project, preliminary result and any required
   preliminary aggregate in deterministic order, validates the expected versions, inserts the
   commit fact and writes exactly one success audit. Any failure rolls back all of them.
7. **No silent pricing promotion.** Preliminary proposed prices and inherited evidence remain
   lineage inputs. The command must not populate an official appraised price, accept asset
   review, select a supplier or mark downstream stages complete.
8. **Global Case State meaning.** Fact presence proves only that the official-intake commit
   occurred and that the Project is eligible for `Tổng quan hồ sơ`. It must not backfill
   completion for unrelated preliminary or downstream stages.
9. **No endpoint in this design commit.** Migration, command runtime, HTTP contract and
   case-state wiring require the prerequisites and acceptance criteria in the accompanying
   implementation contract.

## Proposed persistence shape

`project_official_intake_commits` is append-only:

```text
id                              UUID primary key
organization_id                 UUID not null
project_id                      UUID not null
preliminary_result_artifact_id  UUID not null
preliminary_result_version      integer not null
preliminary_result_sha256       char(64) not null
source_snapshot_sha256          char(64) not null
project_version_before          integer not null
idempotency_key                 varchar(128) not null
request_digest_sha256           char(64) not null
committed_by                    UUID not null
committed_at                    timestamptz not null
```

Required database invariants:

- unique `(organization_id, project_id)`;
- unique `(organization_id, idempotency_key)`;
- tenant-safe references to Project, PreliminaryResultArtifact and committing User;
- positive versions, non-empty bounded key and lowercase 64-character SHA-256 checks;
- no update/delete application command.

The final migration may refine names to match the accepted preliminary-artifact foundation but
must preserve these semantics.

## Command outcome contract

| Outcome | Commit fact | Success audit | Failure audit |
|---|---:|---:|---:|
| confirmation absent/false | 0 | 0 | 0 |
| inaccessible tenant/project/artifact | 0 | 0 | 0 |
| artifact not finalized or lineage incomplete | 0 | 0 | 0 |
| expected version stale | 0 | 0 | 0 |
| first valid commit | exactly 1 | exactly 1 | 0 |
| same idempotency key + same request digest | replay existing result | 0 new | 0 |
| same key + different digest | 0 | 0 | 0 |
| Project already committed through another key | 0 | 0 | 0 |
| engine/commit failure | rollback | 0 | at most 1 only under an accepted recovery design |

Rejected attempts return typed safe errors. They must not leak cross-tenant existence or persist
partial lineage.

## Consequences

- Global Case State gains a truthful official-intake boundary without using legacy workflow
  status as route authority.
- The transition is idempotent, auditable and lineage-preserving.
- A preliminary-result artifact foundation must be designed and implemented before this command
  can ship; the current `ProjectFile` model is not silently promoted to that role.
- A later reversal/cancellation is a separate explicit business command and fact. This ADR does
  not permit deletion or mutation of the original commit.
- Accepting this ADR expands PR-01 with a source-domain migration, but still does not create a
  persisted Global Case State projection.
