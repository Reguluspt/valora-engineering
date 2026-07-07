# S2-PR-012: Asset Identity API Contract + Coverage Hardening Audit

## Files Changed
- `backend/app/api/asset_identity.py` (Added require_permission hooks to all GET/read endpoints)
- `backend/tests/test_asset_identity_api.py` (Expanded test cases to cover list, get, and patch routes for canonical assets, variants, and aliases)

## Endpoints Tested
- `POST /api/v1/asset-identity/assets`
- `GET /api/v1/asset-identity/assets`
- `GET /api/v1/asset-identity/assets/{asset_id}`
- `PATCH /api/v1/asset-identity/assets/{asset_id}`
- `POST /api/v1/asset-identity/assets/{asset_id}/variants`
- `GET /api/v1/asset-identity/assets/{asset_id}/variants`
- `GET /api/v1/asset-identity/variants/{variant_id}`
- `PATCH /api/v1/asset-identity/variants/{variant_id}`
- `POST /api/v1/asset-identity/assets/{asset_id}/aliases`
- `GET /api/v1/asset-identity/aliases`
- `GET /api/v1/asset-identity/aliases/{alias_id}`
- `PATCH /api/v1/asset-identity/aliases/{alias_id}`
- `GET /openapi.json`

## RBAC Coverage
- Verified deny-by-default behavior across GET, POST, and PATCH endpoints using unauthorized credentials. Verified read-only access (GET endpoints pass; PATCH/POST endpoints reject with HTTP 403) using viewer credentials.

## CanonicalAsset Coverage
- Non-existent family ID references rejected (returns HTTP 422).
- Non-existent primary taxonomy node ID references rejected (returns HTTP 422).
- Validated standard name modifications (PATCH) under correct admin permissions.

## AssetVariant Coverage
- Variant creation rejected under non-existent parent assets (returns HTTP 404).
- Unique code per canonical asset boundary constraint checked and verified (returns HTTP 409).
- Shared code across different canonical assets accepted (returns HTTP 201).
- Validated list, detail, and PATCH operations.

## AssetAlias Coverage
- Checked raw name normalization.
- Verified scope checks (canonical scope requires variant target to be null, variant scope requires valid variant target).
- Duplicate normalized name conflicts rejected (returns HTTP 409).
- Validated list, detail, and status updates (PATCH).

## Alias Normalization Coverage
- Confirmed raw strings (e.g. `"MBA ABB 110kV"`) are successfully written and read as normalized strings (e.g. `"mba abb 110kv"`).

## Audit Event Coverage
- Mutation endpoints verified to record `CANONICAL_ASSET_CREATE`, `CANONICAL_ASSET_UPDATE`, `ASSET_VARIANT_CREATE`, and `ASSET_ALIAS_CREATE` AuditEvent records in the database.

## OpenAPI Result
- OpenAPI loads successfully (returns HTTP 200).

## Tests/Checks Run
- Executed `python -m pytest` inside `backend`.
- All 70 tests passed successfully.

## Scope Compliance
- Restricted completely to Layer 1 Asset Identity. No new databases, router dependencies, or migrations introduced.

## Forbidden candidate/review/merge/future-sprint scan result
- Verified `/api/v1/asset-identity/candidates` and `/api/v1/asset-identity/assets/merge` do not exist.

## Missing or Recommended Fixes
- None.

## Final Result
- **Result:** PASS
- **Recommendation:** Ready for S2-PR-013 Candidate/Review API Planning.
