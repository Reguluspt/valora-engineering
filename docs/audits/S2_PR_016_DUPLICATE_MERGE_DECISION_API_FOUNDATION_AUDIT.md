# S2-PR-016: Duplicate / Merge Decision API Foundation Audit

## Files Changed
- `backend/app/api/asset_identity.py` (Implemented endpoints for DuplicateCandidate and MergeDecision)
- `backend/app/modules/project_master_data/candidate_review_schemas.py` (Added Pydantic schemas for DuplicateCandidate and MergeDecision)
- `backend/tests/test_candidate_review_api.py` (Added tests for duplicate and merge endpoints)

## Design Files Read
- `09_DATA_MODEL/04_ASSET_IDENTITY_MODEL.md` (beta zip)
- `12_API/07_ASSET_IDENTITY_API.md` (beta zip)
- `13_SECURITY/04_TAXONOMY_ASSET_IDENTITY_SECURITY.md` (beta zip)
- `14_ACCEPTANCE_TESTS/ASSET_IDENTITY_ACCEPTANCE_TESTS.md` (beta zip)
- `15_CROSS_REFERENCE_MAP.md` (beta zip)
- `16_MIGRATION_AND_SEED_PLAN.md` (beta zip)

## Endpoints Added
- `GET /api/v1/asset-identity/duplicates` (List suspected duplicate assets)
- `GET /api/v1/asset-identity/duplicates/{duplicate_id}` (Get duplicate candidate details)
- `PATCH /api/v1/asset-identity/duplicates/{duplicate_id}` (Update duplicate candidate status/metadata)
- `POST /api/v1/asset-identity/merge-decisions` (Create a proposed merge decision metadata record)
- `GET /api/v1/asset-identity/merge-decisions` (List historical/pending merge decisions)
- `GET /api/v1/asset-identity/merge-decisions/{decision_id}` (Get merge decision details)

## Schemas Added
- `DuplicateCandidateUpdate` / `DuplicateCandidateResponse`
- `MergeDecisionCreate` / `MergeDecisionResponse`

## Permission Checks Applied
- `asset_identity:duplicate:read` (List/get duplicates)
- `asset_identity:duplicate:update` (Update duplicate candidate status)
- `asset_identity:merge:create` (Create merge decision record)
- `asset_identity:merge:read` (View merge records)

## DuplicateCandidate Behavior
- proposal-only structure.
- status transitions update via PATCH. Hard deletes are forbidden.
- row_version optimistic locking check applied on updates.
- constraint check prevents registering a duplicate mapping an asset to itself (`source_asset_id != target_asset_id`).

## MergeDecision Behavior
- proposal-only structure. Creating a `MergeDecision` records decision metadata only.
- Validation rejects source == target.
- Validation rejects request if source or target canonical asset does not exist.
- Required `reason` parameter validated.

## Audit Event Behavior
- PATCH `/duplicates` logs `DUPLICATE_CANDIDATE_UPDATE` with updated status.
- POST `/merge-decisions` logs `MERGE_DECISION_CREATE` with source and target asset IDs.

## No-Merge-Execution Confirmation
- Confirmed that creating a `MergeDecision` does NOT execute any database merges.
- Confirmed no updates to CanonicalAsset `status` or `merged_into_asset_id` fields occur on POST.
- Confirmed no relinking of `AssetAlias` or `AssetVariant` records happens.

## ProjectAssetLine Non-Mutation Confirmation
- Confirmed that duplicate or merge decision actions do NOT write values to the suggested or approved identity columns on `ProjectAssetLine` table rows.

## Tests/Checks Run
- Executed `python -m pytest` inside `backend`.
- All 81 tests passed successfully (including duplicate & merge api foundation test blocks).
- Validated health check client response.
- Confirmed OpenAPI schema loads successfully.

## PostgreSQL Availability Result
- PostgreSQL is unavailable locally. All checks executed against SQLite in-memory configurations.

## Scope Compliance
- Exclusively implemented Duplicate and Merge API boundaries. No execution logic added.
- Confirmed zero modifications to frontend code or worker code.

## Forbidden generation/execution/future-sprint scan result
- All forbidden routes return `405 Method Not Allowed` or `404 Not Found`.
- No background workers, auto-match scanners, or AI providers are configured.

## Missing or Recommended Fixes
- None.

## Final Result
- **Result:** PASS
- **Recommendation:** Ready for S2-PR-017 Duplicate/Merge Contract Tests.
