# S2-PR-015: Candidate + Review API Contract Tests Audit

## Files Changed
- `backend/tests/test_candidate_review_api.py` (Fully rewritten and expanded with comprehensive contract tests)

## Endpoints Tested
- `GET /api/v1/asset-identity/candidates`
- `GET /api/v1/asset-identity/candidates/{candidate_id}`
- `PATCH /api/v1/asset-identity/candidates/{candidate_id}`
- `GET /api/v1/asset-identity/review-items`
- `GET /api/v1/asset-identity/review-items/{review_item_id}`
- `PATCH /api/v1/asset-identity/review-items/{review_item_id}`
- `POST /api/v1/asset-identity/review-items/{review_item_id}/resolve`
- `GET /openapi.json`
- `GET /health`

## RBAC Coverage
- Verified deny-by-default where requests without credentials return `401 Unauthorized`.
- Verified requests with valid credentials but empty roles return `403 Forbidden` for all candidate and review queue endpoints.
- Verified viewer role (`asset_identity:candidate:read` and `asset_identity:review:read`) permits GET lists and GET details of candidates and review items, but returns `403 Forbidden` on candidate PATCH, review item PATCH, and review item resolve POST.
- Verified admin/review update role (`asset_identity:review:update` and `asset_identity:candidate:update`) permits mutations.

## Candidate Coverage
- Verified that candidate PATCH only processes the Pydantic-defined fields (`status` and `row_version`).
- Verified that sending extra payload fields (e.g., `confidence_score` or `match_method`) does not mutate the database record (extra fields are ignored).
- Verified that sending an invalid status code results in `422 Unprocessable Entity` validation error.
- Verified that stale `row_version` values result in `409 Conflict`.
- Verified candidate GET list/detail returns the record correctly and doesn't recompute scores.

## SimilarityScore Read-Only Coverage
- Verified that retrieving candidate details returns `similarity_scores` as nested details.
- Verified that candidate PATCH mutations do not create, update, or remove associated `SimilarityScore` entries.
- Verified that no score recomputation occurs during GET requests (seeded values are preserved exactly).

## Review Item Coverage
- Verified review item PATCH only updates metadata (`assigned_to`, `reviewer_note`, `review_status`, and `row_version`).
- Verified that sending extra fields (e.g. `reviewed_by`) does not mutate database columns (extra fields are ignored).
- Verified that stale `row_version` results in `409 Conflict`.

## IdentityDecisionLog Append-Only Coverage
- Verified that resolving a review item appends a new decision log in the database with matching details and actor attributes.
- Verified that there are no mutation endpoints for `IdentityDecisionLog` (POST/PATCH/PUT/DELETE to `/api/v1/asset-identity/decision-logs` return 404).

## Audit Event Coverage
- Verified that resolving a review item triggers a database log in the `AuditEvent` table under the name `IDENTITY_REVIEW_ITEM_RESOLVE`.
- Verified that patching candidates and review items logs `IDENTITY_CANDIDATE_UPDATE` and `IDENTITY_REVIEW_ITEM_UPDATE` respectively.

## ProjectAssetLine Non-Mutation Coverage
- Verified that patching candidate status, patching review items, or resolving review items does *not* mutate suggested or approved identity columns on `ProjectAssetLine`.

## Forbidden Route Coverage
- **Unimplemented Paths**:
  - `GET/POST /api/v1/asset-identity/duplicates` -> `404 Not Found`
  - `GET/POST /api/v1/asset-identity/merge-decisions` -> `404 Not Found`
- **Overlap Paths**:
  - `POST /api/v1/asset-identity/assets/merge` -> `405 Method Not Allowed`
  - `POST /api/v1/asset-identity/candidates/batch-approve` -> `405 Method Not Allowed`
  - `POST /api/v1/asset-identity/candidates/generate-bulk` -> `405 Method Not Allowed`
- **404 vs 405 Explanation**:
  - `404 Not Found` is returned for paths `/duplicates` and `/merge-decisions` because they do not match any configured route in the application router.
  - `405 Method Not Allowed` is returned for `/assets/merge`, `/candidates/batch-approve`, and `/candidates/generate-bulk` because the FastAPI/Starlette router captures `merge`, `batch-approve`, and `generate-bulk` as path parameters under `/assets/{asset_id}` and `/candidates/{candidate_id}` respectively. Since POST is not allowed on these path parameter endpoints, it correctly yields `405 Method Not Allowed` instead of `404 Not Found`.

## OpenAPI Result
- Verified `/openapi.json` loads successfully with a status of 200 and parses as valid JSON containing standard `paths` and `openapi` structure tags.

## Tests/Checks Run
- Executed `python -m pytest` in backend module. All 79 tests passed successfully (including 6 new comprehensive contract test blocks).
- Validated health check client response body and HTTP 200 status code.

## Scope Compliance
- Confirmed zero modifications to frontend code or worker code.
- Confirmed no duplicate detection algorithms, merge executions, batch approvals, or candidate auto-matching algorithms were implemented.

## Forbidden duplicate/merge/generation/future-sprint scan result
- Git diff check confirmed zero new business models, migrations, or route structures added.
- All forbidden routes return 404 or 405.

## Missing or Recommended Fixes
- None. The current API successfully rejects unauthorized operations and ignores invalid fields correctly.

## Final Result
- **Result**: PASS
- **Recommendation**: Ready for S2-PR-016 Duplicate/Merge Decision API Foundation.
