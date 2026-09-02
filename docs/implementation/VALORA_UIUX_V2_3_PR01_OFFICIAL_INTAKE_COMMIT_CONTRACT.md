# VALORA UI/UX v2.3 — PR-01 Official Intake Commit Contract

**Status:** AUTHORITY ACCEPTED AND RUNTIME FOUNDATION IMPLEMENTED LOCALLY — HTTP not authorized
**Task:** PR-01a — Durable Official Intake Fact/Command
**Date:** 2026-09-01
**Architecture:** ADR 0037

## 1. Authorized scope

This slice may define the durable fact and command boundary for
`Chuyển sang thẩm định chính thức`. It does not authorize:

- the case-state GET endpoint;
- resume persistence;
- frontend implementation;
- NCC, M365, document release or publishing persistence;
- reuse of legacy submit/QC/approval commands;
- artifact generation or direct/manual artifact creation outside an accepted generation command.

## 2. Command

Semantic command: `CommitProjectOfficialIntake`.

Minimum request contract:

```text
project_id
preliminary_result_artifact_id
expected_project_version
expected_preliminary_result_version
idempotency_key
confirmed = true
```

Identity and organization come from the authenticated server context. They are never accepted
from spoofable headers or request ownership fields.

## 3. Preconditions

All conditions are mandatory:

1. actor is an active human in an active organization with the explicit
   `project:official_intake:commit` permission, derived from active, non-revoked role bindings
   in the existing organization-scoped RBAC model on every invocation, including replay;
2. Project resolves inside that organization, otherwise safe 404;
3. expected Project version matches;
4. preliminary-result artifact resolves to the same organization and Project;
5. artifact is finalized, immutable, checksum-verified and lineage-complete;
6. expected artifact version matches;
7. explicit confirmation is true;
8. no official-intake commit exists for the Project;
9. idempotency key is valid and not bound to another request digest;
10. no authoritative open blocker prohibits the transition.

The owner-accepted bounded v1 blocker registry resolves only `OPEN` + `BLOCKING`
`ValidationIssue` rows directly targeting the scoped Project or one of its scoped
ProjectAssetLine rows. It accepts exactly the existing target spellings `project | Project` and
`project_asset_line | ProjectAssetLine`. `WARNING`, `RESOLVED`, `IGNORED`, unknown target types,
other-Project targets and cross-tenant targets do not block. Rule category, rule `is_blocking`
and rule active state are not additional v1 filters. There is no blocker bypass. Empty optional
S09 fields are not synthesized into blockers.

The permission is not a Project ACL. Actor and organization are trusted server context; neither
is accepted as request-owned authority. This slice does not grant the permission to any seeded
role.

## 4. Lock and transaction order

```text
scoped Project FOR UPDATE
→ scoped PreliminaryResultArtifact FOR UPDATE (or immutable version lock)
→ scoped preliminary aggregate/version, if separately persisted
→ idempotency resolution/recheck
→ ProjectOfficialIntakeCommit insert
→ AuditEvent insert
→ one outer commit
```

Every query includes tenant/project scope. No lock is acquired from an unscoped identifier. A
replay does not short-circuit the permission check or the canonical Project/artifact lock order.

## 5. Fact semantics for Global Case State

The projection provider exposes:

```text
provider_key = "official_intake_commit_v1"
fact_id = ProjectOfficialIntakeCommit.id
project_id
artifact_id + artifact_version + artifact_checksum
source_snapshot_sha256
committed_at
```

For `case_version`, the provider contributes stable IDs, versions, digests and commit timestamp in
canonical order. Presence means `official_intake_committed = true` and makes the Project eligible
for the official dossier hub. Absence means “not committed”; it is not inferred from Project or
WorkflowInstance status.

The fact does not, by itself, mark `PRELIMINARY_REQUEST`, `PRELIMINARY_ANALYSIS`,
`ASSET_REVIEW` or later stages complete.

## 6. Audit

Successful command writes exactly one atomic `AuditEvent`:

```text
command_name = "CommitProjectOfficialIntake"
event_name = "ProjectOfficialIntakeCommitted"
entity_type = "ProjectOfficialIntakeCommit"
entity_id = <commit id>
organization_id = <server-scoped organization>
actor_user_id = <authenticated human>
correlation_id = <request correlation>
```

Payload contains only IDs, versions, semantic role and SHA-256 digests. It excludes raw workbook
content, client data, credentials and display text. Audit does not replace the commit row.

## 7. Error semantics

| Condition | Response class | Persistence |
|---|---|---|
| confirmation false | 400 typed validation | none |
| permission denied | 403 | none |
| inaccessible resource | safe 404 | none |
| stale Project/artifact version | 409 version conflict | none |
| artifact not finalized/lineage incomplete | 409 state conflict | none |
| idempotency digest conflict | 409 idempotency conflict | none |
| already committed through another key | 409 state conflict | none |
| success replay | original success representation | none new |
| internal failure | safe 500 | full rollback |

Vietnamese UI copy is supplied later through the shared error registry; technical detail stays
secondary and must not leak identifiers across tenants.

## 8. Preliminary-result foundation

The owner accepted a narrow `PreliminaryResultArtifact`, implemented locally with:

- tenant-safe Project and creator references;
- positive per-Project version and unique storage object identity;
- content checksum, source-snapshot digest and lineage manifest;
- append-only model with no update/delete application command.

This slice deliberately does not expose a generic artifact-creation API. A later accepted
preliminary-result generation command must produce the file, verify its content and persist this
artifact atomically. The current generic `ProjectFile` remains insufficient.

## 9. Runtime exit checklist

- [x] ADR 0037 accepted.
- [x] PreliminaryResultArtifact authority accepted and implemented.
- [x] Exact permission `project:official_intake:commit` accepted and enforced through existing
  organization-scoped RBAC on every invocation; no seeded-role grant.
- [x] Exact v1 blocker registry owner-accepted and implemented for the four accepted target
  spellings and state/tenant behavior.
- [x] Migration has one linear head and tenant-safe constraints.
- [x] Idempotency replay/conflict tests.
- [x] Cross-tenant safe 404 and inactive actor/org tests.
- [x] PostgreSQL two-session concurrency and lock-order tests.
- [x] Atomic fact + audit rollback tests.
- [x] No appraised-price promotion or legacy workflow transition.
- [ ] Global Case State consumes the fact, not the audit event.
