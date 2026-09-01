# PR-01a — Durable Official Intake Fact/Command Design Intake

**Date:** 2026-09-01
**Status:** PROPOSED — owner review required
**Branch:** `pr-01-case-state-projection-foundation`
**Parent design gate:** ADR 0036 / commit `3154d00e85bda0b2d83e3e6a3cfc1f1a15ad3732`

## Owner authorization

The Product Owner authorized opening a small design slice for a durable fact/command at
`Chuyển sang thẩm định chính thức`. This authorization opens design work only; it does not yet
approve migration, runtime endpoint or GitHub publication.

## Authority findings

- v2.1/v2.2 requires a preliminary-result file and explicit user action.
- Empty optional S09 fields are not automatically blocking.
- Preliminary proposed price must not become official appraised price.
- Successful transition changes the pre-case presentation to `Đã chuyển thành hồ sơ` and opens
  the official dossier flow.
- v2.3 requires Global Case State to use business facts rather than a legacy status or route visit.

## Codebase findings

- no canonical pre-case aggregate;
- no finalized/versioned preliminary-result artifact;
- no official-intake commit fact;
- Project/WorkflowInstance enums contain legacy semantics and cannot substitute for the fact;
- AuditEvent can provide atomic evidence but cannot be the business source of truth.

## Proposed resolution

ADR 0037 proposes a stable Project identity plus an append-only, one-per-Project
`ProjectOfficialIntakeCommit`, created only by an idempotent human-confirmed command. The command
requires a canonical immutable preliminary-result artifact and writes atomic audit evidence.

## Gate result

Design proposal is complete. Runtime remains blocked pending owner acceptance of ADR 0037 and a
narrow PreliminaryResultArtifact design decision.
