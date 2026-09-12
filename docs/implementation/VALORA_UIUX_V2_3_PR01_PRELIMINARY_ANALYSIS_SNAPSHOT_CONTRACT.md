# VALORA UI/UX v2.3 — PR-01 PreliminaryAnalysisSnapshot Contract

**Status:** IMPLEMENTATION PACKET — VALORA-PR01-IMPL-002
**Scope:** Immutable, versioned `PreliminaryAnalysisSnapshot` source fact, strict v2 line manifest, human-confirmed command and focused tests. Does not include artifact generation, projection providers, case-state/current_stage publication, HTTP endpoints, frontend or deployment.
**Authority:** ADR 0038 D3–D4, ADR 0037/OFFICIAL_INTAKE commit pattern, Case State Projection Contract §5.

## 1. Schema

New table: `preliminary_analysis_snapshots`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, composite tenant FK to `projects` |
| `customer_id` | UUID | NOT NULL, composite tenant FK to `projects` |
| `project_id` | UUID | NOT NULL, composite tenant FK to `projects` |
| `version` | integer | NOT NULL, `> 0`, unique per `(organization_id, project_id, version)` |
| `import_batch_id` | UUID | NOT NULL, composite FK to `project_asset_import_batches` |
| `source_artifact_id` | UUID | NOT NULL, composite tenant FK to `import_source_artifacts` |
| `structure_snapshot_id` | UUID | NOT NULL, composite tenant FK to `workbook_structure_snapshots` |
| `mapping_decision_id` | UUID | NOT NULL, composite tenant FK to `column_mapping_decisions` |
| `mapping_profile_usage_id` | UUID | NOT NULL, composite tenant FK to `column_mapping_profile_usages` |
| `source_artifact_generation` | integer | NOT NULL, `> 0` |
| `mapping_decision_digest_sha256` | char(64) | NOT NULL, lowercase hex |
| `profile_usage_mapping_digest_sha256` | char(64) | NOT NULL, lowercase hex |
| `line_manifest` | JSONB | NOT NULL, bounded line-level analysis/pricing results |
| `line_manifest_digest_sha256` | char(64) | NOT NULL, lowercase hex |
| `finalized_by_user_id` | UUID | NOT NULL, composite tenant FK to `users` |
| `finalized_at` | timestamptz | NOT NULL, default `now()` |
| `created_at` | timestamptz | NOT NULL, default `now()` |
| `idempotency_key` | varchar(128) | NOT NULL, unique per `(organization_id, idempotency_key)` |
| `request_digest_sha256` | char(64) | NOT NULL, lowercase hex |

Indexes:
- `idx_preliminary_analysis_project` on `(organization_id, project_id)`.

Checks:
- All SHA-256 columns match `^[0-9a-f]{64}$` and are lowercase.
- `version > 0`.
- `source_artifact_generation > 0`.
- `idempotency_key` non-empty after trim, max 128 chars.

Uniqueness:
- One row per `(organization_id, project_id, version)`.
- One row per `(organization_id, idempotency_key)`.
- This slice enforces version `1` per project; future slices may introduce lineage-bump revisions.

## 2. Lineage validation

The command validates, in tenant/project scope:

1. `Project` exists in the actor's organization.
2. `ProjectAssetImportBatch` belongs to the project and its `current_source_artifact_id` equals the requested `source_artifact_id`.
3. `ImportSourceArtifact` is `AVAILABLE` and matches the requested batch/generation.
4. `WorkbookStructureSnapshot` belongs to the requested source artifact.
5. `ColumnMappingDecision` is a human-confirmed decision (`decision_kind = 'confirmation'`, `outcome IN ('accepted', 'corrected')`, `proposal_source_kind = 'human'`) and its lineage points to the same source artifact and structure snapshot.
6. `ColumnMappingProfileUsage` links the same confirmed decision, source artifact and structure snapshot.
7. Requested digests match the stored `mapping_digest_sha256` of the decision and usage, preventing mixed-lineage snapshots.

Missing, foreign, superseded or inconsistent lineage fails closed with a typed 409.

## 3. v2 line manifest schema

Every object in `line_manifest` must contain **exactly** these nine keys:

| Key | Type | Constraints |
|---|---|---|
| `identity` | string | non-empty after trim |
| `accepted_price_basis` | string | non-empty after trim |
| `confirmed_reference_price` | number | finite real, `>= 0` |
| `transport_percentage` | number | finite real, `>= 0` and `<= 100` |
| `proposed_unit_price` | number | finite real, `>= 0` |
| `human_line_confirmed` | boolean | exactly `true` |
| `has_unresolved_blocking_line` | boolean | exactly `false` |
| `source_row_number` | integer | `>= 1` and `<= 1,048,576`, unique within the manifest |
| `quantity` | number | finite real, `>= 0` |

Any missing key, extra key, or non-strict type is rejected. This is the **v2 contract shape**.

## 4. Branch A — v1 contract superseded

v1-shaped manifests (missing `source_row_number`/`quantity`, extra keys, or non-dict lines) are **rejected before any database lookup** with:

- HTTP `409`
- `error_code = "preliminary_analysis_contract_superseded"`

This gate is unconditional: even an idempotency replay of a v1-shaped request is superseded and produces no database writes. Existing v1 snapshots remain readable for audit/history but cannot generate artifacts and do not block new v2 snapshots under a different key.

## 5. Digest/version strategy

- `line_manifest_digest_sha256` is a SHA-256 over canonical UTF-8 JSON of the submitted line manifest: `json.dumps(line_manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))`.
- The manifest is stored as submitted; the digest guarantees immutability and determinism.
- `version` starts at `1` per project. Concurrent finalization races are resolved by the unique `(organization_id, project_id, version)` constraint and explicit idempotency checks.

## 6. Command authorization

Permission identifier: `project:preliminary_analysis:finalize`

- Actor must be an active `User` in an active `OrganizationProfile`.
- Actor must hold the permission through an active, non-revoked `UserRole` binding on every invocation, including replay.
- Identity and organization come from trusted server context; they are never read from request-owned fields.
- This slice does not seed the permission into any role.

## 7. Transaction/lock order

Inside one outer transaction:

1. Validate command confirmation and idempotency key shape.
2. Validate `line_manifest` non-emptiness and every line's v2 completion rules.
3. Apply Branch A shape gate (v1 superseded).
4. Reload active actor + org and derive effective permissions.
5. Compute `line_manifest_digest_sha256` and `request_digest` from canonical JSON.
6. `Project FOR UPDATE` scoped by `(organization_id, project_id)`.
7. `ImportSourceArtifact FOR UPDATE` scoped by tenant/project and verify state/generation.
8. Resolve `ProjectAssetImportBatch`, `WorkbookStructureSnapshot`, `ColumnMappingDecision`, `ColumnMappingProfileUsage` with tenant/project scope and verify digests/lineage.
9. Validate expected `Project.row_version`.
10. Recheck existing `PreliminaryAnalysisSnapshot` for the project and resolve idempotency.
11. Insert `PreliminaryAnalysisSnapshot`.
12. Insert `AuditEvent`.
13. `commit()`.

Unexpected failures roll back the whole transaction; no partial accepted fact.

## 8. Idempotency

Request digest canonical input:

```json
{
  "actor_id": "<UUID>",
  "contract": "preliminary-analysis-finalize-v2",
  "expected_project_version": <int>,
  "line_manifest_digest_sha256": "<hex>",
  "mapping_decision_digest_sha256": "<hex>",
  "mapping_decision_id": "<UUID>",
  "mapping_profile_usage_digest_sha256": "<hex>",
  "mapping_profile_usage_id": "<UUID>",
  "project_id": "<UUID>",
  "source_artifact_id": "<UUID>",
  "structure_snapshot_id": "<UUID>"
}
```

Serialized with `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"))`.

Behavior:
- Same `(organization_id, idempotency_key)` + same digest → replay existing snapshot.
- Same key + different digest → `409 preliminary_analysis_idempotency_key_reused`.
- Project already has a snapshot from another key → `409 preliminary_analysis_already_finalized`.

## 9. Line-completion rules (D4/v2)

Every object in `line_manifest` must satisfy:

- `identity` non-empty string.
- `accepted_price_basis` non-empty string.
- `confirmed_reference_price` finite real number `>= 0`; booleans, numeric strings, `NaN` and infinities are rejected.
- `transport_percentage` finite real number `>= 0` and `<= 100` (0% allowed); booleans, numeric strings, `NaN` and infinities are rejected.
- `proposed_unit_price` finite real number `>= 0`; booleans, numeric strings, `NaN` and infinities are rejected.
- `human_line_confirmed` is exactly the boolean `true`; strings, integers, floats, `null` and any other value are rejected.
- `has_unresolved_blocking_line` is exactly the boolean `false`; strings, integers, floats, `null` and any other value are rejected.
- `source_row_number` is exactly an integer `>= 1`; floats, strings, booleans, `null`, zero and negatives are rejected.
- `quantity` is a finite real number `>= 0`; strings, booleans, `NaN`, infinities and negatives are rejected.
- Duplicate `source_row_number` values inside one manifest are rejected.

Empty `line_manifest` (zero valid rows) is rejected. Mapping/raw observations alone do not prove completion; the submitted manifest must record explicit human confirmation per line.

## 10. Audit

Successful command writes one atomic `AuditEvent`:

```text
command_name = "FinalizePreliminaryAnalysisSnapshot"
event_name = "PreliminaryAnalysisSnapshotFinalized"
entity_type = "PreliminaryAnalysisSnapshot"
entity_id = <snapshot id>
organization_id = <server-scoped organization>
actor_user_id = <authenticated human>
correlation_id = <request correlation>
```

Payload contains only IDs, versions, digests and semantic role. No raw workbook content, filenames, user names, secrets or display text.

## 11. Tests

Required evidence:
- Successful human finalization and immutable/versioned persistence.
- Each unmet v2/D4 condition, zero rows, missing confirmation and valid 0% transport.
- Strict v2 schema: missing/extra keys, non-boolean flags, non-finite/non-numeric prices, invalid `source_row_number`/`quantity`.
- Tenant/project isolation, invalid mapping/source lineage and digest/version mismatch.
- Unauthorized/inactive actors and prohibited non-human confirmation.
- Idempotent replay, conflicting reuse and concurrent finalization.
- Branch A: v1-shaped requests are superseded before DB lookup; existing v1 snapshots remain readable but block neither v2 finalization nor artifact generation.
- Source/mapping changes during finalization; no mixed-lineage snapshot.
- Audit-failure rollback and no unrelated data mutation.
- Digest determinism, immutability and migration integrity.

SQLite service tests cover functional/authorization/idempotency/Branch A cases. PostgreSQL tests cover concurrency/lock-order/rollback evidence.

## 12. Runtime exit gate

This slice closes the `PreliminaryAnalysisSnapshot` source-fact implementation gate. It does **not** close:
- `PreliminaryResultArtifact` generation pipeline;
- projection providers `preliminary_request_v1`, `preliminary_analysis_v1`, `preliminary_ready_v1`;
- case-state/current_stage publication.

Those remain blocked until separately authorized.

## 13. Stop conditions observed

- Branch/HEAD/staged match the packet.
- Only allowlisted files are modified.
- Five protected closeout files remain byte-for-byte unchanged.
- No projection runtime, endpoint, frontend, migration edit of existing revisions, or predicate expansion is implemented.
