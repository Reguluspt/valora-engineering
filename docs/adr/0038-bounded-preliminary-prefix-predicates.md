# ADR 0038 — Bounded Preliminary Prefix Predicates

**Status:** Accepted for design authority — source facts, providers and runtime remain unimplemented

**Date:** 2026-09-03

**Context:** VALORA UI/UX v2.3 PR-01 — Preliminary prefix predicate design closeout

**Deciders:** Project Owner, Core Engineering Team

## Context

The PR-01 Global Case State projection requires a bounded contiguous prefix of canonical stages before `current_stage` can be truthfully published (ADR 0036; OFFICIAL_INTAKE predicate D4). The three preliminary stages `PRELIMINARY_REQUEST`, `PRELIMINARY_ANALYSIS` and `PRELIMINARY_READY` were previously classified as `MISSING` or `FACT_EXISTS_PREDICATE_UNAPPROVED` in the parent projection contract. This ADR records the owner-approved predicates for those stages and the minimum authoritative facts required.

This ADR does **not** authorize any persistence migration, command implementation, provider wiring, HTTP endpoint exposure, frontend work or runtime connection. It is a design-authority closeout only.

## Decision

### D1 — `PRELIMINARY_REQUEST` canonical fact

The canonical fact is the tenant-scoped current `ImportSourceArtifact` in state `AVAILABLE`.

- Generic `ProjectFile` with `file_category = INPUT_CONTRACT` is **not** completion authority.
- A request saved without a valid source file remains a legitimate draft but does **not** complete this stage.
- The artifact must be the current source generation for the Project's current import batch.

### D2 — `PRELIMINARY_REQUEST` completion

`PRELIMINARY_REQUEST` is `COMPLETE` only when the current import batch points to its current source generation and that exact `ImportSourceArtifact` is `AVAILABLE`.

- `PENDING`, `FAILED`, `ORPHANED`, absent, superseded or non-current artifacts produce `INCOMPLETE`.
- Historical artifacts do not satisfy the predicate.

For `case_version`, the provider contributes stable artifact identity, generation, checksum, state and authoritative timestamp under ADR 0036 canonical ordering.

### D3 — `PRELIMINARY_ANALYSIS` canonical fact

Adopt a new immutable, versioned authoritative fact concept named `PreliminaryAnalysisSnapshot`.

It records completion of preliminary catalog and price analysis for the current source generation. Required lineage includes:

- current `ImportSourceArtifact`;
- `WorkbookStructureSnapshot`;
- human-confirmed `ColumnMappingDecision`;
- `ColumnMappingProfileUsage`;
- the bounded line-level preliminary analysis and pricing results;
- stable IDs, versions and digests required by ADR 0036.

`ColumnMappingDecision`, `ColumnMappingProfileUsage` and `RawAssetObservation` rows remain inputs/evidence; none independently proves completion.

This ADR authorizes the fact and completion contract only. It does **not** authorize a persistence schema, migration or command implementation.

### D4 — `PRELIMINARY_ANALYSIS` completion

`PRELIMINARY_ANALYSIS` is `COMPLETE` only when a current `PreliminaryAnalysisSnapshot` has been finalized through an explicit human-confirmed command and every in-scope line satisfies:

1. sufficient identity for comparison;
2. at least one user-accepted price basis;
3. confirmed market/reference price;
4. valid transport percentage, including `0%`;
5. proposed unit price;
6. explicit human line confirmation;
7. no unresolved blocking line.

The snapshot must match the current source generation and accepted mapping digests.

A workbook with zero valid equipment rows does **not** auto-complete in v1. It remains `INCOMPLETE` and requires corrected/replacement input. Any future empty-scope completion requires a separate owner-approved ratchet update.

### D5 — `PRELIMINARY_READY` authority

Accept Option B: a current `PreliminaryResultArtifact` that is finalized, immutable, checksum-verified and lineage-complete is the readiness fact.

It must:

- belong to the same tenant and Project;
- reference the current accepted `PreliminaryAnalysisSnapshot` through lineage;
- be the current applicable artifact version.

An absent, invalid, older or lineage-mismatched artifact produces `INCOMPLETE`.

Do **not** introduce a second readiness table or readiness command.

Artifact generation remains unimplemented and separately gated.

### D6 — Labels and route keys

Accept backend semantic route keys:

- `preliminary_request_pending`
- `preliminary_analysis_pending`
- `preliminary_ready_pending`

Accept Vietnamese stage-card labels:

- `PRELIMINARY_REQUEST` → `Tạo yêu cầu sơ bộ`
- `PRELIMINARY_ANALYSIS` → `Phân tích danh mục`
- `PRELIMINARY_READY` → `Tạo file kết quả sơ bộ`

These are backend semantic keys; the frontend owns URL mapping.

### D7 — `BLOCKED` semantics

Apply the accepted OFFICIAL_INTAKE D1/D2 pattern to all three preliminary stages:

- raw providers return fact-derived `COMPLETE` or `INCOMPLETE`;
- an `INCOMPLETE` stage becomes `BLOCKED` only when an open `BLOCKING` `ValidationIssue` is explicitly registered as applicable to that stage and target;
- blocker resolution takes `next_action` precedence;
- `WARNING` never becomes `BLOCKED`;
- a later blocker does not rewrite an already valid completion fact.

Applicability must be explicit and stage-specific.

### D8 — `STALE` semantics

No preliminary stage reports `STALE` in v1.

If current source generation, mapping or analysis lineage no longer matches:

- the affected predicate evaluates to `INCOMPLETE`;
- `next_action` points to the required corrective step.

Future `STALE` behavior requires a separately approved ratchet update with facts, truth table and tests.

## Rejected alternatives

- **Using `Project.status` or `WorkflowInstance.current_state` as completion authority:** rejected because these carry legacy QC/approval semantics and are not tenant-scoped canonical facts.
- **Using generic `ProjectFile` `INPUT_CONTRACT` for `PRELIMINARY_REQUEST`:** rejected in favor of the current `ImportSourceArtifact`, which is the actual source generation processed by the import pipeline.
- **Using `ColumnMappingDecision` alone as `PRELIMINARY_ANALYSIS` completion:** rejected because a confirmed mapping does not by itself prove line-level analysis and pricing are complete.
- **Creating a separate readiness table/command for `PRELIMINARY_READY`:** rejected in favor of Option B, reusing the finalized `PreliminaryResultArtifact` as the readiness fact.
- **Allowing zero-row workbooks to auto-complete `PRELIMINARY_ANALYSIS`:** rejected for v1; requires corrected input or a future ratchet update.

## Consequences

- A bounded contiguous predicate-design prefix `PRELIMINARY_REQUEST → PRELIMINARY_ANALYSIS → PRELIMINARY_READY → OFFICIAL_INTAKE` is now accepted.
- The parent Case State Projection Contract and `CODEX.md` live gate will be updated to reflect predicate-design acceptance while keeping implementation/runtime gates closed.
- Source facts/providers are **not** implemented: `PreliminaryAnalysisSnapshot` is authorized but has no schema, migration or command; `PreliminaryResultArtifact` persistence exists but its generation pipeline is not implemented.
- The projection endpoint, `current_stage` publication and provider runtime remain unauthorized until a separately authorized implementation slice closes those gates.
- No backfill semantics are introduced: later facts cannot complete earlier stages by implication.

## Runtime exit gates (all remain blocked)

- [ ] `PreliminaryAnalysisSnapshot` source fact persistence and human-confirmed command defined and accepted.
- [ ] `PreliminaryResultArtifact` generation pipeline implemented and accepted.
- [ ] Projection providers for `preliminary_request_v1`, `preliminary_analysis_v1`, `preliminary_ready_v1` implemented.
- [ ] Design-contract/runtime tests for D1–D8 pass (tenant/RBAC, `case_version`, blocking, warning, non-inference, contiguous-prefix gate).
- [ ] Parent projection contract ratchet updated to `IMPLEMENTED / WIRED` only after the above gates close.
