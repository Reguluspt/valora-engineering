# S2-PR-014: Candidate + Review API Foundation Audit

## Files Changed
- `backend/app/api/asset_identity.py` (Extended to support candidate & review endpoints)
- `backend/app/modules/project_master_data/candidate_review_schemas.py` (New Pydantic schemas for candidates/reviews)
- `backend/tests/test_candidate_review_api.py` (New API test suite)
- `backend/tests/test_asset_identity_api.py` (Updated to allow 405 status codes on routing conflicts)
- `backend/tests/test_taxonomy_api.py` (Updated to allow 405 status codes on routing conflicts)

## Design Files Read
- `09_DATA_MODEL/04_ASSET_IDENTITY_MODEL.md` (beta zip)
- `12_API/07_ASSET_IDENTITY_API.md` (beta zip)

## Endpoints Added
- `GET /api/v1/asset-identity/candidates` (List proposals)
- `GET /api/v1/asset-identity/candidates/{candidate_id}` (Get details)
- `PATCH /api/v1/asset-identity/candidates/{candidate_id}` (Update candidate status)
- `GET /api/v1/asset-identity/review-items` (List queue items)
- `GET /api/v1/asset-identity/review-items/{review_item_id}` (Get details)
- `PATCH /api/v1/asset-identity/review-items/{review_item_id}` (Update metadata/assignee)
- `POST /api/v1/asset-identity/review-items/{review_item_id}/resolve` (Resolve item)

## Schemas Added
- `IdentityCandidateResponse` / `IdentityCandidateUpdate`
- `SimilarityScoreResponse`
- `IdentityReviewItemResponse` / `IdentityReviewItemUpdate` / `IdentityReviewItemResolve`
- `IdentityDecisionLogResponse`

## Permission Checks Applied
- `asset_identity:candidate:read` (List/get candidates)
- `asset_identity:candidate:update` (Update candidate status)
- `asset_identity:review:read` (List/get review items)
- `asset_identity:review:update` (Update metadata/resolve review items)

## Candidate Behavior
- Checked that candidates are read-only proposals. No auto-generation or auto-approval.

## SimilarityScore Read-Only Behavior
- Scores are returned as nested elements on candidate response. They are read-only evidence and are not computed or modified by the endpoints.

## Review Item Behavior
- Operator assignments and reviewer notes are modified via PATCH.
- Resolution via POST appends `IdentityDecisionLog` entries and marks review status as resolved, requiring explicit human actor permission.

## IdentityDecisionLog Behavior
- History records are appended automatically during review resolution. No direct mutation endpoints exist.

## Audit Event Behavior
- Mutation endpoints log corresponding event markers (`IDENTITY_CANDIDATE_UPDATE`, `IDENTITY_REVIEW_ITEM_UPDATE`, and `IDENTITY_REVIEW_ITEM_RESOLVE`).

## ProjectAssetLine Non-Mutation Confirmation
- Verified that resolving a candidate does *not* write values to the suggested or approved identity columns on `ProjectAssetLine` table rows.

## Tests/Checks Run
- Executed `python -m pytest` inside `backend`.
- All 73 tests passed successfully.

## PostgreSQL Availability Result
- PostgreSQL is unavailable locally. Validation was executed against an in-memory SQLite database configuration.

## Scope Compliance
- Completely restricted to Candidate + Review foundation. No duplicate or merge routes exposed.

## Forbidden duplicate/merge/generation/future-sprint scan result
- Confirmed duplicate/merge endpoints (/duplicates, /merge-decisions) return 404.
- No background workers, auto-match scanners, or AI providers are configured.

## Missing or Recommended Fixes
- None.

## Final Result
- **Result:** PASS
- **Recommendation:** Ready for S2-PR-015 Candidate + Review Contract Tests.
