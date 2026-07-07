# S3-PR-003: Evidence Library Persistence Audit Report

This report documents the audit for S3-PR-003 (Evidence Library core persistence) of Project Valora.

## Files Changed
- `backend/app/modules/project_master_data/models.py` (Appended core Evidence models and enums)
- `backend/alembic/versions/a87a9b6da999_create_evidence_core_tables.py` (Manually created Alembic migration script)
- `backend/tests/test_evidence_library_persistence.py` (Added core persistence tests)

## Design Files Read
- `01_SCOPE_AND_COMPLETION_GATE.md`
- `15_CROSS_REFERENCE_MAP.md`
- `16_MIGRATION_AND_SEED_PLAN.md`
- `18_AUDIT_PATCH_CRUD_APIS.md`
- `21_AUDIT_PATCH_SECURITY_AND_CLEANUP.md`
- `docs/adr/0020-evidence-immutability-unlink-cleanup-policy.md`
- `docs/adr/0021-sensitive-evidence-access-log-policy.md`

## Models/Tables Added
- `EvidenceSource` (`evidence_sources`)
- `EvidenceFile` (`evidence_files`)
- `EvidenceLink` (`evidence_links`)
- `EvidenceAccessLog` (`evidence_access_logs`)

## Enums Added
- `EvidenceSourceType` (catalogue / supplier / internet / manual / ai / system)
- `EvidenceFileStatus` (pending / active / archived)
- `EvidenceSensitivityLevel` (normal / sensitive / restricted)
- `EvidenceAccessType` (view / download / metadata)

## Constraints Added
- Foreign key referencing `users.id` with `RESTRICT` on delete for all audit and link dependencies.
- Foreign key `evidence_file_id` referencing `evidence_files.id` with `RESTRICT` on delete to protect evidence deletion cascade.
- Index `idx_evidence_link_target` covering `target_type` and `target_id`.

## Evidence Immutability Behavior
- Fields `filename`, `mime_type`, `file_size`, `object_key`, and `checksum` are preserved as immutable parameters.
- Mutative edits are limited to description and status meta columns.

## EvidenceLink Soft-Delete Behavior
- Link removals do not hard delete rows. Unlinking modifies `is_deleted = true` while logging the deleting user, timestamp, and justification reason.
- The associated `EvidenceFile` remains in the library unmodified.

## EvidenceAccessLog Behavior
- Append-only structure verified. Access logs track file, user, IP, agent, and reasons for accesses to sensitive metadata or download operations.

## Seed Behavior
- Confirmed no mockup quote data or PDF byte files are seeded. Seeding is limited to enum reference maps.

## Tests/Checks Run
- Executed `python -m pytest` in `backend`. All 88 tests passed successfully (including newly added `test_evidence_library_persistence.py` suite).
- Validated health check client is healthy.

## PostgreSQL Availability Result
- PostgreSQL is unavailable locally. Migrations and check constraints were validated using the SQLite in-memory engine.

## Scope Compliance
- Confirmed that only core evidence persistence structures were implemented.
- No specialized evidence tables (`supplier_quote_evidences`, etc.) or knowledge tables (`technical_specifications`, etc.) were added.
- No API routers, file upload handlers, or background parsing jobs were added.
- Confirmed no changes to frontend or worker modules.

## Forbidden specialized-evidence/knowledge/API/future-sprint scan result
- Git diff check confirmed zero new route registrations.
- Verification tests assert that forbidden tables are NOT registered in metadata.

## Missing or Recommended Fixes
- None.

## Final Result
- **Result:** PASS
- **Recommendation:** Ready for S3-PR-004 Reference & Specialized Evidence Persistence.
