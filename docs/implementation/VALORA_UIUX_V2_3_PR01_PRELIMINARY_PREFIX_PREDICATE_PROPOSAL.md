# VALORA UI/UX v2.3 — PR-01 Preliminary Prefix Predicate

**Status:** HISTORICAL DESIGN AUTHORITY — RUNTIME SUBSEQUENTLY IMPLEMENTED/WIRED

**Task:** VALORA-PR01-DESIGN-003

**Scope:** Bounded predicates for `PRELIMINARY_REQUEST`, `PRELIMINARY_ANALYSIS` and `PRELIMINARY_READY`, forming a contiguous prefix ending at the already accepted `OFFICIAL_INTAKE` predicate

**Date:** 2026-09-03

**Architecture:** ADR 0036 (computed-on-read, no projection migration) + ADR 0037 (durable official-intake fact) + ADR 0038 (bounded preliminary-prefix predicates)

> **2026-09-23 current disposition:** This file preserves the pre-runtime predicate design. The separately authorized source facts/providers and `GET /api/v1/projects/{project_id}/case-state` were later implemented and accepted for the four-stage prefix. Read `VALORA_UIUX_V2_3_PR01_CASE_STATE_PROVIDER_IMPLEMENTATION_CONTRACT.md` and the current Unified Roadmap for runtime truth; statements below that runtime is still blocked are historical gate snapshots.

This document records the owner-approved bounded predicates for `PRELIMINARY_REQUEST`, `PRELIMINARY_ANALYSIS` and `PRELIMINARY_READY` (D1–D8, approved 2026-09-03). It does not authorize runtime wiring, endpoint implementation, frontend work, persistence changes, new migrations, or reinterpretation of legacy status. The source facts and providers described below remain unimplemented; the PR-01 projection runtime and `current_stage` publication remain blocked until a separately authorized implementation slice closes those gates.

---

## 1. Accepted authority and non-negotiable boundaries

The following are treated as fixed for this predicate set; they derive from ADR 0036, ADR 0037, ADR 0038, the PR-01 Case State Projection Contract, the PR-01 Official Intake Commit Contract, and the accepted `OFFICIAL_INTAKE` predicate (D1–D10).

- **Global Case State is computed on read.** No case-state table, materialized column or projection migration is introduced (ADR 0036 §1).
- **Facts remain authoritative.** Stage completion, blockers, stale state and next action are derived only from an approved, versioned fact matrix. `Project.status`, `WorkflowInstance.current_state`, `AuditEvent`, page visits and generic `ProjectFile` rows are not completion authority by themselves (ADR 0036 §2; ADR 0037 §8; ADR 0038 D1/D3; Case State Projection Contract §5).
- **Missing authority fails closed.** An absent fact provider or unapproved legacy-to-v2.3 mapping is `NOT_AVAILABLE`, never inferred as `COMPLETE` or `NOT_APPLICABLE` (ADR 0036 §3; Case State Projection Contract §5.6).
- **Warning remains distinct from Blocking.** Open `ValidationIssue` rows with `WARNING` severity cannot be converted to `BLOCKED` (Case State Projection Contract §5.2; ADR 0038 D7).
- **Tenant/project linkage fails closed.** Every provider query must be scoped by `(organization_id, project_id)`. Cross-tenant or unresolvable Projects produce a safe 404 without existence leak (ADR 0036 §7; OFFICIAL_INTAKE predicate D10).
- **Authentication and authorization fail closed.** Anonymous/missing session → `401`; authenticated actor lacking read permission → `403`; inaccessible/cross-tenant Project → safe `404` (OFFICIAL_INTAKE predicate D10).
- **Later completion cannot backfill earlier stages.** The presence of `PreliminaryResultArtifact` or `ProjectOfficialIntakeCommit` does not complete `PRELIMINARY_REQUEST` or `PRELIMINARY_ANALYSIS` by implication (ADR 0037 §8; ADR 0038; Case State Projection Contract §5.7; OFFICIAL_INTAKE predicate §7).
- **Unexpected provider failures are explicit typed projection errors.** They must not be disguised as stage `NOT_AVAILABLE` and must not expose raw exception details (OFFICIAL_INTAKE predicate D7).
- **No projection runtime is authorized.** The PR-01 projection endpoint and `current_stage` publication remain blocked until source facts, providers and focused tests are implemented and accepted (ADR 0038 runtime exit gates; Case State Projection Contract §4 gate result).

---

## 2. Evidence inventory

Repository code and tests are implementation evidence, not authority. The facts below were observed in the current codebase and are now selected by ADR 0038 as authoritative inputs.

### 2.1 Project and workflow primitives

| Source | Verified reusable facts | Limits |
|---|---|---|
| `Project` | `id`, `organization_id`, `customer_id`, `code`, `name`, `row_version`, `created_at`, `updated_at` | `status` is the legacy `ProjectWorkflowStatus` enum and is input only; no canonical-stage mapping is approved |
| `WorkflowInstance` | `id`, `workflow_definition_id`, `target_type`, `target_id`, `current_state`, `status`, `row_version` | legacy state is not Global Case State or route authority |
| `ValidationIssue` | `target`, `severity` (`WARNING`/`BLOCKING`), `status` (`OPEN`/`RESOLVED`/`IGNORED`), `row_version` | target-to-project resolution must be explicit and tenant-safe; applicability to a specific preliminary stage must be explicit (ADR 0038 D7) |
| `ProjectFile` | generic file container with `file_category`, `processing_status`, `checksum_sha256`, `storage_object_key`, `row_version` | **not** the canonical `PRELIMINARY_REQUEST` fact; ADR 0038 D1 rejects it as completion authority |
| `PreliminaryResultArtifact` | immutable, versioned preliminary result with `organization_id`, `project_id`, `version`, `content_checksum_sha256`, `storage_object_key`, `source_snapshot_sha256`, `lineage_manifest`, `created_by_user_id`, `created_at` | generation command is deferred; ADR 0038 D5 accepts its finalized presence as the `PRELIMINARY_READY` fact |
| `ProjectOfficialIntakeCommit` | durable official boundary fact | already accepted predicate for `OFFICIAL_INTAKE`; does not backfill preliminary stages |

### 2.2 Upload / mapping / analysis primitives

| Source | Verified reusable facts | Role under ADR 0038 |
|---|---|---|
| `ProjectAssetImportBatch` | `organization_id`, `project_id`, `source_filename`, `source_sheet_name`, `status`, `current_source_artifact_id`, `row_version` | identifies the current source generation; batch lifecycle state is not stage completion by itself |
| `ProjectAssetImportStagingRow` | `organization_id`, `project_id`, `import_batch_id`, `source_row_number`, `raw_values`, `mapped_values`, `validation_status`, `validation_errors`, `validation_warnings`, `proposed_*` fields | import pipeline state; not official ProjectAssetLine |
| `ImportSourceArtifact` | `organization_id`, `project_id`, `import_batch_id`, `generation`, `original_filename`, `detected_format`, `content_type`, `file_size_bytes`, `checksum_sha256`, `storage_object_key`, `state` (`PENDING`, `AVAILABLE`, `FAILED`, `ORPHANED`) | **canonical fact for `PRELIMINARY_REQUEST`** (ADR 0038 D1–D2) |
| `WorkbookStructureSnapshot` | `organization_id`, `project_id`, `import_batch_id`, `source_artifact_id`, `snapshot_version`, `source_checksum_sha256`, `rule_version`, `adapter_name`, `adapter_version`, `disposition`, `candidate_count`, `structure_payload`, `analysis_digest_sha256` | required lineage input to `PreliminaryAnalysisSnapshot` (ADR 0038 D3) |
| `ColumnMappingProfile` | `organization_id`, `customer_id`, `source_project_id`, `source_import_batch_id`, `scope_type`, `profile_family_id`, `profile_version`, `status`, `template_fingerprint_sha256`, `mapping_digest_sha256`, `source_artifact_id`, `structure_snapshot_id`, `sheet_name`, bounds, `confirmed_by_user_id`, `confirmed_at` | required lineage input to `PreliminaryAnalysisSnapshot` |
| `ColumnMappingField` | per-profile semantic role assignments | implementation detail of a profile; not a standalone completion fact |
| `ColumnMappingDecision` | `decision_kind` (`proposal`, `confirmation`, `rejection`), `outcome` (`proposed`, `accepted`, `corrected`, `rejected`), `mapping_snapshot`, `mapping_digest_sha256`, `template_fingerprint_sha256`, lineage to artifact/snapshot | required lineage input to `PreliminaryAnalysisSnapshot`; not standalone completion authority (ADR 0038 D3) |
| `ColumnMappingProfileUsage` | links a confirmed decision/profile to one source generation, with `materialized_asset_row_count`, `source_checksum_sha256`, `structure_digest_sha256`, `mapping_digest_sha256` | required lineage input to `PreliminaryAnalysisSnapshot`; not standalone completion authority |
| `RawAssetObservation` | per-row raw asset extraction linked to artifact, snapshot and optionally staging row | candidate evidence within the analysis pipeline; not standalone completion authority (ADR 0038 D3) |
| `PreliminaryAnalysisSnapshot` | new immutable, versioned authoritative fact concept authorized by ADR 0038 D3 | **canonical fact for `PRELIMINARY_ANALYSIS`**; no schema, migration or command exists yet |

### 2.3 Tests observed as implementation evidence

- `test_pr01_official_intake_service.py` asserts that `Project.status` remains `DRAFT` after a successful `ProjectOfficialIntakeCommit`, confirming no legacy-status backfill.
- Existing import/upload tests exercise `ProjectAssetImportBatch`, `ImportSourceArtifact`, `WorkbookStructureSnapshot`, `ColumnMappingDecision`, `ColumnMappingProfileUsage` and `RawAssetObservation`, but none are framed as v2.3 Global Case State predicate authority until ADR 0038.

---

## 3. Accepted stage predicates

Each stage is classified by its current authority and implementation state.

---

### 3.1 `PRELIMINARY_REQUEST`

```text
STAGE: PRELIMINARY_REQUEST
IMPLEMENTATION_STATUS: PREDICATE ACCEPTED — source fact exists, provider not wired
CANDIDATE_PROVIDER: preliminary_request_v1
AUTHORITATIVE_FACT: Tenant-scoped current ImportSourceArtifact in state AVAILABLE for the Project's
  current import batch (ADR 0038 D1).
COMPLETION_PREDICATE (accepted):
  The Project's current import batch points to its current source generation, and that exact
  ImportSourceArtifact is AVAILABLE. PENDING, FAILED, ORPHANED, absent, superseded or non-current
  artifacts produce INCOMPLETE (ADR 0038 D2).
ABSENCE_MEANING: INCOMPLETE — no accepted current request artifact is available for the Project.
TENANT_PROJECT_LINKAGE: Enforced by Project.organization_id / Project.id and
  ImportSourceArtifact.organization_id / project_id / import_batch_id. Queries must scope by
  (organization_id, project_id) and fail closed with safe 404.
CASE_VERSION_INPUT (accepted design contract; exact encoding subject to implementation contract):
  - provider = preliminary_request_v1
  - artifact_id = current ImportSourceArtifact.id
  - artifact_generation = ImportSourceArtifact.generation
  - artifact_checksum = ImportSourceArtifact.checksum_sha256
  - artifact_state = AVAILABLE
  - authoritative_timestamp = ImportSourceArtifact.created_at or availability timestamp,
    normalized to UTC with six fractional digits per OFFICIAL_INTAKE predicate D8
BLOCKING_WARNING_STALE_BEHAVIOR (ADR 0038 D7/D8):
  - An INCOMPLETE stage becomes BLOCKED only when an open BLOCKING ValidationIssue is explicitly
    registered as applicable to this stage and target; blocker resolution takes next_action precedence.
  - WARNING is surfaced separately and never converted to Blocking.
  - No STALE semantics in v1; lineage mismatch produces INCOMPLETE.
NEXT_ACTION_ROUTE_KEY (accepted): preliminary_request_pending
VIETNAMESE_LABEL (accepted): Tạo yêu cầu sơ bộ
AUTHORITY_GAP: None for the predicate; implementation gap is the unwired provider.
DESIGN_RECORD: ADR 0038 D1–D2.
```

#### Truth table — `PRELIMINARY_REQUEST`

| Condition | Fact state | Provider raw result | Final aggregator result | Notes |
|---|---|---|---|---|
| Provider unavailable / not registered | N/A | N/A | `NOT_AVAILABLE` | Capability metadata exposes missing provider. |
| Provider unexpected failure | unknown | typed projection error | typed projection error | No raw exception details. |
| Tenant/project inaccessible | N/A | N/A | safe 404 | Provider not invoked. |
| Current artifact AVAILABLE | `AVAILABLE` | `COMPLETE` | `COMPLETE` | ADR 0038 D2. |
| Current artifact not AVAILABLE or absent | `PENDING` / `FAILED` / `ORPHANED` / absent / superseded | `INCOMPLETE` | `INCOMPLETE` or `BLOCKED` under D7 | Absence not inferred from Project.status. |
| Open WARNING exists | any | per fact state | per fact state; warning surfaced | Warning never blocks. |

---

### 3.2 `PRELIMINARY_ANALYSIS`

```text
STAGE: PRELIMINARY_ANALYSIS
IMPLEMENTATION_STATUS: PREDICATE ACCEPTED — source fact authorized but not implemented, provider not wired
CANDIDATE_PROVIDER: preliminary_analysis_v1
AUTHORITATIVE_FACT: PreliminaryAnalysisSnapshot, a new immutable, versioned authoritative fact
  authorized by ADR 0038 D3. It records completion of preliminary catalog and price analysis for
  the current source generation and carries lineage to ImportSourceArtifact, WorkbookStructureSnapshot,
  ColumnMappingDecision, ColumnMappingProfileUsage and bounded line-level preliminary analysis/pricing
  results.
COMPLETION_PREDICATE (accepted):
  A current PreliminaryAnalysisSnapshot has been finalized through an explicit human-confirmed command,
  it matches the current source generation and accepted mapping digests, and every in-scope line
  satisfies: sufficient identity, at least one user-accepted price basis, confirmed market/reference
  price, valid transport percentage (including 0%), proposed unit price, explicit human line
  confirmation, and no unresolved blocking line (ADR 0038 D4).
  A workbook with zero valid equipment rows remains INCOMPLETE in v1.
ABSENCE_MEANING: INCOMPLETE — the source workbook has not been analyzed or the analysis has not been
  finalized.
TENANT_PROJECT_LINKAGE: Enforced through ProjectAssetImportBatch → ImportSourceArtifact →
  WorkbookStructureSnapshot → ColumnMappingDecision / ColumnMappingProfileUsage / RawAssetObservation,
  all carrying organization_id and project_id, and through the tenant-scoped PreliminaryAnalysisSnapshot
  once implemented.
CASE_VERSION_INPUT (accepted design contract; exact encoding subject to implementation contract):
  - provider = preliminary_analysis_v1
  - snapshot_id = PreliminaryAnalysisSnapshot.id
  - snapshot_version = PreliminaryAnalysisSnapshot.version
  - snapshot_digest = PreliminaryAnalysisSnapshot.canonical digest
  - source_artifact_id = current ImportSourceArtifact.id
  - source_artifact_generation = current ImportSourceArtifact.generation
  - mapping_decision_id = confirming ColumnMappingDecision.id
  - mapping_decision_digest = ColumnMappingDecision.mapping_digest_sha256
  - profile_usage_id = ColumnMappingProfileUsage.id
  - profile_usage_mapping_digest = ColumnMappingProfileUsage.mapping_digest_sha256
  - authoritative_timestamp = PreliminaryAnalysisSnapshot.finalized_at, normalized to UTC with six
    fractional digits per OFFICIAL_INTAKE predicate D8
BLOCKING_WARNING_STALE_BEHAVIOR (ADR 0038 D7/D8):
  - An INCOMPLETE stage becomes BLOCKED only when an open BLOCKING ValidationIssue is explicitly
    registered as applicable to this stage and target.
  - WARNING is surfaced separately.
  - No STALE semantics in v1; lineage mismatch produces INCOMPLETE.
NEXT_ACTION_ROUTE_KEY (accepted): preliminary_analysis_pending
VIETNAMESE_LABEL (accepted): Phân tích danh mục
AUTHORITY_GAP: None for the predicate; implementation gaps are the unwired fact, command and provider.
DESIGN_RECORD: ADR 0038 D3–D4.
```

#### Truth table — `PRELIMINARY_ANALYSIS`

| Condition | Fact state | Provider raw result | Final aggregator result | Notes |
|---|---|---|---|---|
| Provider unavailable / not registered | N/A | N/A | `NOT_AVAILABLE` | Capability metadata exposes missing provider. |
| Provider unexpected failure | unknown | typed projection error | typed projection error | No raw exception details. |
| Tenant/project inaccessible | N/A | N/A | safe 404 | Provider not invoked. |
| Snapshot finalized and all line conditions satisfied | current / finalized | `COMPLETE` | `COMPLETE` | ADR 0038 D4. |
| No snapshot or any line condition unsatisfied | absent / not finalized / unmet conditions | `INCOMPLETE` | `INCOMPLETE` or `BLOCKED` under D7 | |
| Zero valid equipment rows | current source has zero valid rows | `INCOMPLETE` | `INCOMPLETE` | Requires corrected/replacement input in v1. |
| Open WARNING exists | any | per fact state | per fact state; warning surfaced | Warning never blocks. |

---

### 3.3 `PRELIMINARY_READY`

```text
STAGE: PRELIMINARY_READY
IMPLEMENTATION_STATUS: PREDICATE ACCEPTED — persistence exists, generation pipeline and provider not wired
CANDIDATE_PROVIDER: preliminary_ready_v1
AUTHORITATIVE_FACT: Current PreliminaryResultArtifact that is finalized, immutable, checksum-verified
  and lineage-complete (ADR 0038 D5).
COMPLETION_PREDICATE (accepted):
  A PreliminaryResultArtifact exists for the same tenant and Project, references the current accepted
  PreliminaryAnalysisSnapshot through lineage, and is the current applicable artifact version. An
  absent, invalid, older or lineage-mismatched artifact produces INCOMPLETE.
ABSENCE_MEANING: INCOMPLETE — readiness to transition to official intake has not been achieved or the
  artifact does not exist.
TENANT_PROJECT_LINKAGE: Enforced by Project.organization_id / Project.id and the tenant-safe
  PreliminaryResultArtifact references, mirroring the ProjectOfficialIntakeCommit pattern.
CASE_VERSION_INPUT (accepted design contract; exact encoding subject to implementation contract):
  - provider = preliminary_ready_v1
  - artifact_id = PreliminaryResultArtifact.id
  - artifact_version = PreliminaryResultArtifact.version
  - artifact_checksum = PreliminaryResultArtifact.content_checksum_sha256
  - source_snapshot_sha256 = PreliminaryResultArtifact.source_snapshot_sha256
  - analysis_snapshot_id = referenced PreliminaryAnalysisSnapshot.id
  - authoritative_timestamp = PreliminaryResultArtifact.created_at, normalized to UTC with six
    fractional digits per OFFICIAL_INTAKE predicate D8
BLOCKING_WARNING_STALE_BEHAVIOR (ADR 0038 D7/D8):
  - An INCOMPLETE stage becomes BLOCKED only when an open BLOCKING ValidationIssue is explicitly
    registered as applicable to this stage and target.
  - WARNING is surfaced separately.
  - No STALE semantics in v1; lineage mismatch produces INCOMPLETE.
NEXT_ACTION_ROUTE_KEY (accepted): preliminary_ready_pending
VIETNAMESE_LABEL (accepted): Tạo file kết quả sơ bộ
AUTHORITY_GAP: None for the predicate; implementation gap is the unwired artifact-generation pipeline
  and provider.
DESIGN_RECORD: ADR 0038 D5.
```

#### Truth table — `PRELIMINARY_READY`

| Condition | Fact state | Provider raw result | Final aggregator result | Notes |
|---|---|---|---|---|
| Provider unavailable / not registered | N/A | N/A | `NOT_AVAILABLE` | Capability metadata exposes missing provider. |
| Provider unexpected failure | unknown | typed projection error | typed projection error | No raw exception details. |
| Tenant/project inaccessible | N/A | N/A | safe 404 | Provider not invoked. |
| Current finalized artifact with correct lineage | finalized / current lineage | `COMPLETE` | `COMPLETE` | ADR 0038 D5. |
| Artifact absent, invalid, older or lineage-mismatched | absent / invalid / stale lineage | `INCOMPLETE` | `INCOMPLETE` or `BLOCKED` under D7 | |
| Open WARNING exists | any | per fact state | per fact state; warning surfaced | Warning never blocks. |

---

## 4. Cross-stage non-inference rules

The following rules are locked by authority and apply to all preliminary stages:

1. **Later completion cannot make an earlier mandatory stage complete by implication.** `PreliminaryResultArtifact` presence does not make `PRELIMINARY_REQUEST` or `PRELIMINARY_ANALYSIS` `COMPLETE`. `ProjectOfficialIntakeCommit` presence does not backfill any preliminary stage.
2. **`Project.status` and `WorkflowInstance.current_state` are inputs only.** They may be read for display or correlation, but they cannot determine stage completion or select UI routes.
3. **`AuditEvent` is evidence, not the business fact.** Projection providers query canonical facts, not audit rows.
4. **Generic `ProjectFile` is not a canonical fact.** ADR 0038 D1 explicitly rejects `ProjectFile INPUT_CONTRACT` as the `PRELIMINARY_REQUEST` authority.
5. **Warning is never Blocking.** Open `WARNING` `ValidationIssue` rows are surfaced in the warning collection and do not change stage result to `BLOCKED`.
6. **Missing provider capability is `NOT_AVAILABLE`.** If a stage provider is not registered, its result is `NOT_AVAILABLE`, never `COMPLETE` or `NOT_APPLICABLE`.
7. **Tenant boundary is enforced on every query.** Unscoped identifiers or cross-tenant access fail closed with safe 404.

---

## 5. Contiguous-prefix feasibility result

The predicate-design contiguous prefix `PRELIMINARY_REQUEST → PRELIMINARY_ANALYSIS → PRELIMINARY_READY → OFFICIAL_INTAKE` is **accepted at the design-authority level**.

| Stage | Authority state | Implementation state | Blocks `current_stage` publication? |
|---|---|---|---|
| `PRELIMINARY_REQUEST` | PREDICATE ACCEPTED | Source fact exists; provider not wired | Yes, until provider/tests implemented. |
| `PRELIMINARY_ANALYSIS` | PREDICATE ACCEPTED | Source fact authorized but not implemented; provider not wired | Yes, until fact/command/provider/tests implemented. |
| `PRELIMINARY_READY` | PREDICATE ACCEPTED | Persistence exists; generation pipeline/provider not wired | Yes, until generation pipeline/provider/tests implemented. |
| `OFFICIAL_INTAKE` | PREDICATE ACCEPTED | Source fact implemented; provider not wired | Yes, until contiguous prefix implementation accepted. |

`current_stage` publication and projection runtime connection remain blocked until the implementation gates listed in ADR 0038 runtime exit gates are closed.

---

## 6. Owner-approved decisions

The following decisions were owner-approved on 2026-09-03 and are now bounded predicate authority for the preliminary prefix:

1. **D1 — `PRELIMINARY_REQUEST` canonical fact:** tenant-scoped current `ImportSourceArtifact` in state `AVAILABLE`; generic `ProjectFile INPUT_CONTRACT` is not authority.
2. **D2 — `PRELIMINARY_REQUEST` completion:** current import batch → current source generation → exact `AVAILABLE` artifact; non-current or non-AVAILABLE states produce `INCOMPLETE`.
3. **D3 — `PRELIMINARY_ANALYSIS` canonical fact:** new immutable, versioned `PreliminaryAnalysisSnapshot` with required lineage to source artifact, structure snapshot, confirmed mapping decision, profile usage and line-level analysis/pricing results.
4. **D4 — `PRELIMINARY_ANALYSIS` completion:** finalized snapshot matching current source generation and accepted mapping digests, with every in-scope line satisfying the seven required conditions; zero valid rows remains `INCOMPLETE` in v1.
5. **D5 — `PRELIMINARY_READY` authority:** finalized, lineage-complete `PreliminaryResultArtifact` referencing the current `PreliminaryAnalysisSnapshot`; no separate readiness table or command.
6. **D6 — Labels and route keys:** `Tạo yêu cầu sơ bộ` / `preliminary_request_pending`; `Phân tích danh mục` / `preliminary_analysis_pending`; `Tạo file kết quả sơ bộ` / `preliminary_ready_pending`.
7. **D7 — `BLOCKED` semantics:** OFFICIAL_INTAKE D1/D2 pattern extended to preliminary stages; explicit stage-specific applicability required.
8. **D8 — `STALE` semantics:** no preliminary stage reports `STALE` in v1; lineage mismatch produces `INCOMPLETE`.

No unresolved owner question remains for this bounded predicate design.

---

## 7. Implementation blockers

The following must be closed in a separately authorized implementation slice before the projection runtime or `current_stage` publication is connected:

- `PreliminaryAnalysisSnapshot` source fact persistence, human-confirmed command and atomic audit.
- `PreliminaryResultArtifact` generation pipeline.
- Projection providers `preliminary_request_v1`, `preliminary_analysis_v1`, `preliminary_ready_v1`.
- Design-contract/runtime tests for tenant/RBAC, `case_version`, blocking, warning, non-inference and contiguous-prefix gate.
- Parent projection contract ratchet update from `NOT WIRED` to `WIRED` only after the above gates close.

---

## 8. Future runtime-test matrix

**Tests are described only; they are not implemented by this task.**

| Test | Scenario | Expected projection behavior |
|---|---|---|
| T.1 | Project exists, current ImportSourceArtifact not AVAILABLE | `PRELIMINARY_REQUEST` = `INCOMPLETE` or `BLOCKED` under D7. |
| T.2 | Current ImportSourceArtifact AVAILABLE | `PRELIMINARY_REQUEST` = `COMPLETE`; `case_version` includes artifact identity/generation/checksum. |
| T.3 | Cross-tenant or superseded source artifact | Tenant-scoped query does not see foreign/superseded row; accessible Project → `INCOMPLETE`. Safe 404 only when Project itself is inaccessible. `NOT_AVAILABLE` reserved for missing provider. |
| T.4 | Source workbook not yet analyzed | `PRELIMINARY_ANALYSIS` = `INCOMPLETE`. |
| T.5 | `PreliminaryAnalysisSnapshot` finalized and all line conditions satisfied | `PRELIMINARY_ANALYSIS` = `COMPLETE`; `case_version` includes snapshot/version/digests. |
| T.6 | Mapping decision rejected or snapshot not finalized | `PRELIMINARY_ANALYSIS` = `INCOMPLETE`. |
| T.7 | Zero valid equipment rows | `PRELIMINARY_ANALYSIS` = `INCOMPLETE`; requires corrected/replacement input in v1. |
| T.8 | `PreliminaryResultArtifact` finalized with correct lineage | `PRELIMINARY_READY` = `COMPLETE`; `case_version` includes artifact version/checksum/timestamp. |
| T.9 | `PreliminaryResultArtifact` absent or lineage-mismatched | `PRELIMINARY_READY` = `INCOMPLETE`. |
| T.10 | `PreliminaryResultArtifact` present but earlier stages incomplete | `PRELIMINARY_REQUEST`/`PRELIMINARY_ANALYSIS` remain incomplete unless their own predicates are met. |
| T.11 | `ProjectOfficialIntakeCommit` present but preliminary stages incomplete | Same as T.10. |
| T.12 | Open BLOCKING ValidationIssue applicable to an incomplete preliminary stage | Aggregator reports `BLOCKED` under D7. |
| T.13 | Open WARNING ValidationIssue | Stage result follows fact state; warning surfaced separately. |
| T.14 | Tenant/RBAC safe 404/403/401 | Anonymous → `401`; no read permission → `403`; inaccessible/cross-tenant Project → safe `404`. |
| T.15 | `case_version` determinism and sensitivity | Same facts produce identical tokens; changing any canonical input changes token; repeated reads in one transaction are identical. |
| T.16 | `case_version` excludes display text/secrets | Token input contains no filenames, user names, audit payloads, credentials, or display text. |
| T.17 | Contiguous-prefix gate | Even if `OFFICIAL_INTAKE` is `COMPLETE`, `current_stage` must not jump to `OFFICIAL_INTAKE` while any preceding stage is `NOT_AVAILABLE` or `INCOMPLETE`. |

---

## 9. Runtime gate conclusion

- **Predicate-design gate:** CLOSED — ADR 0038 and D1–D8 accepted.
- **Source-fact implementation gate:** OPEN — `PreliminaryAnalysisSnapshot` fact/command not implemented; `PreliminaryResultArtifact` generation pipeline not implemented.
- **Provider/runtime gate:** OPEN — providers for `preliminary_request_v1`, `preliminary_analysis_v1`, `preliminary_ready_v1` are not wired.
- **Projection endpoint / `current_stage` publication:** NOT AUTHORIZED until the implementation gates above are closed.

---

## 10. Stop conditions observed

No stop condition from the task packet is triggered:

- Branch is `pr-01-case-state-projection-foundation`.
- HEAD matches expected baseline `aa5cd3a433e0f94d7b53c3331ef2145a2c672767`.
- Only the allowlisted documentation files differ from baseline.
- Authority read in required order; no material contradiction found.
- Active worker model is `opencode-go/kimi-k2.7-code` (task execution observation, not a predicate semantic).
- The accepted `OFFICIAL_INTAKE` predicate and D1–D10 are unchanged.
- No runtime, endpoint, migration, frontend, or predicate for other stages is authorized.

This predicate authority is ready for independent Qwen review and Codex/owner gate closeout.
