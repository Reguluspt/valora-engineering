# VALORA UI/UX v2.3 — PR-01 PreliminaryResultArtifact Generation Contract

**Status:** IMPLEMENTED HISTORICAL SLICE — generation fact later consumed by accepted Case State providers
**Scope:** Atomic generation of one immutable `PreliminaryResultArtifact` per project from a v2 `PreliminaryAnalysisSnapshot`. Includes authorization, lineage verification, deterministic XLSX transformation, object storage, idempotency and audit. Does not include HTTP endpoints, projection providers, case-state/current_stage publication, frontend or deployment.
**Authority:** ADR 0038 D1–D10, ADR 0037/OFFICIAL_INTAKE commit pattern, Case State Projection Contract §5.

> **2026-09-23 current disposition:** The scope/exit-gate text below records this generation slice at implementation time. The separately authorized preliminary providers and Case State endpoint were later implemented/wired; later implementation contracts/audits govern current runtime status.

## 1. Schema

Table: `preliminary_result_artifacts` (hardened by migration `c159fab13c3a`)

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK, deterministic UUIDv5 |
| `organization_id` | UUID | NOT NULL, composite tenant FK to `projects` |
| `customer_id` | UUID | NOT NULL, composite tenant FK to `projects` |
| `project_id` | UUID | NOT NULL, composite tenant FK to `projects` |
| `version` | integer | NOT NULL, `> 0`, starts at `1` |
| `original_filename` | varchar | NOT NULL |
| `content_type` | varchar | NOT NULL |
| `file_size_bytes` | integer | NOT NULL, `> 0` |
| `content_checksum_sha256` | char(64) | NOT NULL, lowercase hex |
| `storage_object_key` | varchar | NOT NULL, deterministic path |
| `source_snapshot_sha256` | char(64) | NOT NULL, lowercase hex |
| `lineage_manifest` | JSONB | NOT NULL, full generation lineage |
| `created_by_user_id` | UUID | NOT NULL, composite tenant FK to `users` |
| `created_at` | timestamptz | NOT NULL, default `now()` |
| `idempotency_key` | varchar(128) | nullable; non-empty after trim when present |
| `request_digest_sha256` | char(64) | nullable; lowercase hex when present |

Indexes:
- `idx_preliminary_result_project` on `(organization_id, project_id)`.
- Partial unique index `uq_preliminary_result_idempotency` on `(organization_id, idempotency_key)` WHERE `idempotency_key IS NOT NULL`.

Checks:
- All SHA-256 columns match `^[0-9a-f]{64}$` and are lowercase.
- `version > 0` and `file_size_bytes > 0`.
- `idempotency_key` non-empty after trim when present, max 128 chars.
- Pairing: `(idempotency_key IS NULL) = (request_digest_sha256 IS NULL)`. NULL is only allowed for pre-hardening legacy rows; new rows always populate both fields.

Uniqueness:
- One row per `(organization_id, idempotency_key)` where the key is not NULL (partial unique index).
- One row per project (enforced by application-level race resolution, not a DB unique constraint).

## 2. Authorization

Permission identifier: `project:preliminary_result:generate`

- Actor must be an active `User` in an active `OrganizationProfile`.
- Actor must hold the permission through an active, non-revoked `UserRole` binding on every invocation, including replay.
- Identity and organization come from trusted server context; they are never read from request-owned fields.
- This slice does not seed the permission into any role.

## 3. Input contract

Command parameters:

| Parameter | Type | Notes |
|---|---|---|
| `actor` | `User` | server-trusted authenticated human |
| `org_id` | UUID | server-trusted organization |
| `project_id` | UUID | target project |
| `preliminary_analysis_snapshot_id` | UUID | v2 snapshot to materialize |
| `expected_project_version` | int | optimistic version check |
| `idempotency_key` | string | non-empty, max 128 chars after trim |
| `confirmed` | boolean | exactly `true`; command requires explicit confirmation |
| `correlation_id` | string | optional audit correlation |

## 4. Lineage validation

The command validates, in tenant/project scope:

1. `Project` exists in the actor's organization.
2. `PreliminaryAnalysisSnapshot` exists for the project and is locked `FOR UPDATE`.
3. The stored snapshot's `line_manifest` satisfies the strict v2 shape (exactly nine keys, valid `source_row_number`/`quantity`, no duplicates).
4. `ImportSourceArtifact` is `AVAILABLE`, belongs to the project, and `detected_format == "xlsx"`.
5. `ProjectAssetImportBatch` belongs to the project and its `current_source_artifact_id` equals the snapshot's source artifact.
6. `WorkbookStructureSnapshot` belongs to the requested source artifact.
7. `ColumnMappingDecision` and `ColumnMappingProfileUsage` link the same source artifact, structure snapshot and import batch.
8. Snapshot digests match the stored `mapping_digest_sha256` of the decision and usage.
9. Cross-check lineage checksums: artifact checksum matches `usage.source_checksum_sha256`; structure digest matches `usage.structure_digest_sha256`.
10. Expected `Project.row_version` matches.

Missing, foreign, superseded, non-xlsx or inconsistent lineage fails closed with a typed 409 (or 404 for missing entities).

## 5. Two-phase generation flow

### Phase 1 — Validate, lock and compute (inside DB transaction)

1. Validate confirmation and idempotency key shape.
2. Reload active actor + org and derive effective permissions.
3. `Project FOR UPDATE` scoped by `(organization_id, project_id)`.
4. `PreliminaryAnalysisSnapshot FOR UPDATE` scoped by tenant/project and verify v2 shape.
5. `ImportSourceArtifact FOR UPDATE` scoped by tenant/project and verify state/format.
6. Resolve `ProjectAssetImportBatch`, `WorkbookStructureSnapshot`, `ColumnMappingDecision`, `ColumnMappingProfileUsage` and verify digests/lineage.
7. Compute canonical snapshot digest and request digest.
8. Resolve idempotency key:
   - Same key + same artifact id, request digest, actor and snapshot digest → replay existing artifact.
   - Same key + any mismatch → `409 preliminary_result_idempotency_key_reused`.
9. Check that no artifact already exists for the project; if so → `409 preliminary_result_already_generated`.
10. Compute deterministic artifact id, output filename and storage key.
11. `commit()` to release locks before object IO.

### Phase 2 — Build and store object (outside DB transaction)

1. Open the source workbook bytes from object storage.
2. Verify source checksum against `artifact.checksum_sha256`.
3. Load workbook with `data_only=True`.
4. Resolve the unique quantity field from the mapping snapshot; target columns are `max_column + 1` (price) and `max_column + 2` (amount).
5. Geometry checks:
   - Target columns are within worksheet limits.
   - Every `source_row_number` lies inside the candidate data region.
   - Target cells do not intersect merged ranges and are empty.
6. Write vertically-merged headers:
   - Column `price_col`: "Đơn giá đề xuất"
   - Column `amount_col`: "Thành tiền"
7. Write one row per manifest line at `source_row_number`:
   - Price = `proposed_unit_price`
   - Amount = `quantity * proposed_unit_price`, rounded to 2 decimal places with `ROUND_HALF_UP`.
8. Save output workbook and compute its SHA-256.
9. Put object to the deterministic storage key with no-overwrite semantics; if the key exists, verify size + SHA-256 match.

### Phase 3 — Insert artifact (new DB transaction)

1. Reload active actor + org and permissions.
2. `Project FOR UPDATE` and `PreliminaryAnalysisSnapshot FOR UPDATE`.
3. Recheck `project.row_version` and snapshot canonical digest; reject if either changed.
4. Recheck idempotency and project-level uniqueness.
5. Build `lineage_manifest` (see §6).
6. Insert `PreliminaryResultArtifact` with deterministic id.
7. Insert `AuditEvent` atomically.
8. `commit()`.

Unexpected failures roll back the DB transaction. If the object was stored but the artifact insert fails, a best-effort `storage.delete()` is attempted on the deterministic key.

## 6. Determinism

### Artifact id

```text
uuid5(
  NAMESPACE_URL = "https://valora.internal/pr01/preliminary-result/v1",
  "org={org_id}|key={normalized_key}|digest={request_digest}"
)
```

### Storage key

```text
org/{org_id}/project/{project_id}/preliminary-results/{artifact_id}.xlsx
```

### Output filename

```text
ket-qua-so-bo-v1-{artifact_id}.xlsx
```

### Snapshot canonical digest

Canonical JSON payload:

```json
{
  "contract": "preliminary-analysis-canonical-digest-v1",
  "import_batch_id": "<UUID>",
  "line_manifest_digest_sha256": "<hex>",
  "mapping_decision_digest_sha256": "<hex>",
  "mapping_decision_id": "<UUID>",
  "mapping_profile_usage_id": "<UUID>",
  "organization_id": "<UUID>",
  "profile_usage_mapping_digest_sha256": "<hex>",
  "project_id": "<UUID>",
  "snapshot_id": "<UUID>",
  "source_artifact_generation": <int>,
  "source_artifact_id": "<UUID>",
  "structure_snapshot_id": "<UUID>",
  "version": <int>
}
```

### Request digest

Canonical JSON payload:

```json
{
  "actor_id": "<UUID>",
  "contract": "preliminary-result-generate-v1",
  "expected_project_version": <int>,
  "preliminary_analysis_snapshot_digest_sha256": "<hex>",
  "preliminary_analysis_snapshot_id": "<UUID>",
  "project_id": "<UUID>"
}
```

Serialization for all canonical digests: `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"))`, then SHA-256.

## 7. Lineage manifest

`lineage_manifest` is a deterministic JSON object containing:

- `generation_contract`: `"preliminary-result-generate-v1"`
- `project_id`, `organization_id`, `customer_id`, `import_batch_id`
- `source_workbook`: artifact id, generation, checksum, detected format
- `structure_snapshot`: id, version, rule version, analysis digest
- `mapping`: decision id, decision digest, profile usage id, usage digest, template fingerprint, mapping contract version
- `analysis_snapshot`: id, version, canonical digest, line manifest digest, finalized by/at
- `mapped_region`: sheet name, header/data rows, min/max rows/columns
- `quantity_column`: source column index and letter
- `output_layout`: price/amount column indexes, headers, merge rule, amount calculation rule
- `line_locator_count`: number of manifest lines

No raw workbook content, user names or secrets are stored.

## 8. Idempotency and race behavior

- Same `(organization_id, idempotency_key)` + same request digest + same actor + same project + same snapshot digest → replay existing artifact.
- Same key + different request digest (different snapshot, actor or project version) → `409 preliminary_result_idempotency_key_reused`.
- Any artifact already exists for the project under any key → `409 preliminary_result_already_generated`.
- Concurrent generate-vs-generate and generate-vs-official-intake races are serialized by `Project FOR UPDATE` and the unique `(organization_id, idempotency_key)` constraint.

## 9. Output layout rules

- Header row(s) are merged vertically across `header_start_row`..`header_end_row` for the two new columns.
- Data rows are addressed by `source_row_number` from the v2 manifest, not by sequential offset.
- Amount formula is static: `quantity * proposed_unit_price`, rounded half-up to 2 decimal places.
- Existing source cells are never overwritten; target cells must be empty and unmerged.

## 10. Audit

Successful command writes one atomic `AuditEvent`:

```text
command_name = "GeneratePreliminaryResultArtifact"
event_name = "PreliminaryResultArtifactGenerated"
entity_type = "PreliminaryResultArtifact"
entity_id = <artifact id>
organization_id = <server-scoped organization>
actor_user_id = <authenticated human>
correlation_id = <request correlation>
```

Payload contains only IDs, versions, digests and file metadata. No raw workbook content, filenames, user names, secrets or display text.

## 11. Tests

Required evidence:
- Successful generation from a v2 snapshot and immutable persistence.
- Deterministic artifact id, storage key and output checksum for identical requests.
- Strict v2 line manifest rejection (missing/extra keys, invalid `source_row_number`/`quantity`, duplicates).
- Source workbook checksum mismatch, missing source object, non-xlsx format.
- Target geometry violations (out-of-region locators, merged cells, non-empty target cells).
- Tenant/project isolation and missing lineage entities.
- Unauthorized/inactive actors.
- Idempotent replay, conflicting key reuse and project-level already-generated.
- Project version conflict and snapshot digest change between Phase 1 and Phase 3.
- Audit-failure rollback and object-storage cleanup on DB failure.
- PostgreSQL concurrency: double generate, same-key different digest, different keys, generate-vs-official-intake interleave.
- Migration upgrade/downgrade integrity on SQLite and PostgreSQL.

## 12. Runtime exit gate

This slice closes the `PreliminaryResultArtifact` generation pipeline gate. It does **not** close:
- projection providers `preliminary_request_v1`, `preliminary_analysis_v1`, `preliminary_ready_v1`;
- case-state/current_stage publication;
- HTTP endpoints or frontend workflows.

Those remain blocked until separately authorized.

## 13. Stop conditions observed

- Branch/HEAD/staged match the packet.
- Only allowlisted files are modified.
- Five protected closeout files remain byte-for-byte unchanged.
- No projection runtime, endpoint, frontend, migration edit of existing revisions, or predicate expansion is implemented.
