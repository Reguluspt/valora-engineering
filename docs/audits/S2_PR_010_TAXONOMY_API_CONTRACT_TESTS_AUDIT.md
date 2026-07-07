# S2-PR-010: Taxonomy API Contract + Coverage Hardening Audit

## Files Changed
- `backend/tests/test_taxonomy_api.py` (Greatly expanded test cases validating lifecycles, hierarchy, uniqueness and scope properties)

## Endpoints Tested
- `POST /api/v1/taxonomy/nodes`
- `POST /api/v1/taxonomy/nodes/{node_id}/submit-review`
- `POST /api/v1/taxonomy/nodes/{node_id}/approve`
- `POST /api/v1/taxonomy/nodes/{node_id}/deprecate`
- `POST /api/v1/taxonomy/families`
- `POST /api/v1/taxonomy/dna`
- `POST /api/v1/taxonomy/dna/{dna_id}/activate`
- `POST /api/v1/taxonomy/attribute-definitions`
- `GET /openapi.json`

## RBAC Coverage
- Tested deny-by-default behavior across endpoints by submitting viewer requests lacking permission mappings. Admin operations verify proper access execution.

## Hierarchy Validation Coverage
- Category cannot exist without parent node.
- Domain cannot be created with parent node.
- Level order constraint (e.g. DOMAIN -> CATEGORY -> SUBCATEGORY -> GROUP) strictly tested and enforced.

## Lifecycle/Status Coverage
- Draft nodes transitioned to pending review, then active, then deprecated.
- Statuses updated sequentially with validation rejection on invalid states (e.g. only draft can be submitted).
- Deprecation verified as status-only update, not removing items from DB.

## AssetFamily Coverage
- Validated that family proposals are rejected under draft category nodes.

## AssetDNA Coverage
- Verified only one active DNA schema per family (activating a version deactivates others).

## AttributeDefinition Coverage
- Key casing rule (snake_case) validated and enforced via Pydantic schema validation.
- Scope mismatch rejected (variant-defining key restricted to variant or both).
- Enum key type rejects payloads missing enum values list.

## Audit Event Coverage
- Validated that mutation operations create corresponding AuditEvent records in the database.

## OpenAPI Result
- OpenAPI loads successfully (endpoint `/openapi.json` returns HTTP 200).

## Tests/Checks Run
- Executed `python -m pytest` inside `backend`.
- All 63 tests passed successfully.

## Scope Compliance
- Exclusively covered taxonomy core endpoint groups. No new database models, migrations, or endpoints added.

## Forbidden Asset Identity/Future-Sprint Scan Result
- Verified that no `/api/v1/asset-identity/...` endpoints exist.

## Missing or Recommended Fixes
- None.

## Final Result
- **Result:** PASS
- **Recommendation:** Ready for S2-PR-011 Asset Identity API Foundation.
