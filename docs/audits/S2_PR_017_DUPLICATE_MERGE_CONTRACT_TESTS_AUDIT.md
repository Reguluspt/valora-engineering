# S2-PR-017: Duplicate / Merge Decision API Contract Tests Audit

## Files Changed
- `backend/tests/test_candidate_review_api.py` (Seeded AssetAlias and added validations checking reason fields, delete methods, and alias/variant linkages)

## Endpoints Tested
- `GET /api/v1/asset-identity/duplicates`
- `GET /api/v1/asset-identity/duplicates/{duplicate_id}`
- `PATCH /api/v1/asset-identity/duplicates/{duplicate_id}`
- `POST /api/v1/asset-identity/merge-decisions`
- `GET /api/v1/asset-identity/merge-decisions`
- `GET /api/v1/asset-identity/merge-decisions/{decision_id}`
- `GET /openapi.json`
- `GET /health`

## RBAC Coverage
- Verified deny-by-default where requests without credentials return `401 Unauthorized` for all duplicate and merge endpoints.
- Verified requests with valid credentials but empty roles return `403 Forbidden` for all duplicate and merge endpoints.
- Verified viewer role can query list and details of duplicates and merge decisions, but returns `403 Forbidden` on duplicate PATCH and merge decision POST.
- Verified admin/read-write role permits duplicate PATCH and merge decision POST.

## DuplicateCandidate Coverage
- Verified GET list and detail returns seeded duplicate records.
- Verified PATCH updates only allowed fields (`status`, `metadata_info`, and `row_version`), while other fields like `confidence_score` are ignored.
- Verified invalid status is rejected with `422 Unprocessable Entity`.
- Verified stale `row_version` returns `409 Conflict`.
- Verified that registering a duplicate candidate mapping an asset to itself throws database constraints errors.

## MergeDecision Coverage
- Verified POST creates a metadata merge decision record with status `PROPOSED`.
- Verified POST rejects source == target.
- Verified POST rejects requests referencing nonexistent source or target canonical assets.
- Verified POST rejects empty `reason` string and missing `reason` field with `422 Unprocessable Entity`.
- Verified GET list and detail endpoints return merge decision entries.

## Audit Event Coverage
- Verified that PATCH duplicates creates an `AuditEvent` with event_name `DUPLICATE_CANDIDATE_UPDATE`.
- Verified that POST merge decisions creates an `AuditEvent` with event_name `MERGE_DECISION_CREATE`.

## No-Merge-Execution Coverage
- Verified that creating a merge decision does NOT run any execution scripts.
- Verified that the source/target canonical assets remain active/draft with no status modifications.
- Verified that the source canonical asset `merged_into_asset_id` column remains null.

## Alias/Variant Non-Relink Coverage
- Verified that after posting a merge decision, all associated variants and aliases remain mapped to their original source canonical assets and are not moved or relinked.

## ProjectAssetLine Non-Mutation Coverage
- Verified that duplicate and merge decision actions do NOT modify suggested or approved identity fields on `ProjectAssetLine`.

## Forbidden Route Coverage
- **Unimplemented Paths**:
  - Direct deletion or edit endpoints for merge decisions (`DELETE/PATCH /merge-decisions/{id}`) return `405 Method Not Allowed` because the paths match registered GET route parameters.
  - Direct deletion endpoints for duplicates (`DELETE /duplicates/{id}`) return `405 Method Not Allowed` because the path matches the registered GET route.
- **Overlap Paths**:
  - `POST /api/v1/asset-identity/assets/merge` -> `405 Method Not Allowed`
  - `POST /api/v1/asset-identity/candidates/batch-approve` -> `405 Method Not Allowed`
  - `POST /api/v1/asset-identity/candidates/generate-bulk` -> `405 Method Not Allowed`
- **404 vs 405 Explanation**:
  - `405 Method Not Allowed` is returned for `/assets/merge`, `/candidates/batch-approve`, and `/candidates/generate-bulk` because the FastAPI/Starlette router captures `merge`, `batch-approve`, and `generate-bulk` as path parameters under `/assets/{asset_id}` and `/candidates/{candidate_id}` respectively. Since POST is not allowed on these path parameter endpoints, it correctly yields `405 Method Not Allowed` instead of `404 Not Found`.

## OpenAPI Result
- Verified `/openapi.json` loads successfully.

## Tests/Checks Run
- Executed `python -m pytest`. All 81 tests passed successfully.
- Validated `/health` response status code 200.

## Scope Compliance
- Confirmed zero modifications to frontend code or worker code.
- Confirmed no duplicate detection algorithms, merge executions, batch approvals, or candidate auto-matching algorithms were implemented.

## Forbidden generation/execution/future-sprint scan result
- Git diff check confirmed zero new business models, migrations, or route structures added.
- All forbidden routes return 405.

## Missing or Recommended Fixes
- None.

## Final Result
- **Result:** PASS
- **Recommendation:** Ready for S2-PR-018 Sprint 2 Final Acceptance Audit.
