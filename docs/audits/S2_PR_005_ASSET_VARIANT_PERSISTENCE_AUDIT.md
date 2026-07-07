# S2-PR-005: Asset Variant Persistence Audit

## Files Changed
- `backend/app/modules/project_master_data/models.py` (Added AssetVariant and AssetVariantAttributeValue ORM models)
- `backend/app/db/__init__.py` (Registered models in baseline mapping)
- `backend/alembic/versions/a87a9b6da995_create_asset_variant_tables.py` (Alembic migration script)
- `backend/tests/test_canonical_asset_persistence.py` (Removed now-invalid asset variants non-existence assert test)
- `backend/tests/test_asset_variant_persistence.py` (New tests verifying relationships and unique code per canonical asset)

## Design Files Read
- `09_DATA_MODEL/03_TAXONOMY_MODEL.md` (beta zip)
- `09_DATA_MODEL/04_ASSET_IDENTITY_MODEL.md` (beta zip)
- `16_MIGRATION_AND_SEED_PLAN.md` (beta zip)

## Models/Tables Added
- `AssetVariant` (`asset_variants`)
- `AssetVariantAttributeValue` (`asset_variant_attribute_values`)

## Enums Added
- `AssetVariantStatus`

## Constraints Added
- `AssetVariant` foreign keys to `AssetFamily` (ondelete RESTRICT) and `CanonicalAsset` (ondelete RESTRICT) to preserve data lineage. (Corrected under S2-PR-005-FIX-2).
- `AssetVariant` unique constraint: `uq_asset_variant_canonical_code` on `(canonical_asset_id, code)`. (Corrected under S2-PR-005-FIX to scope variant uniqueness to the parent CanonicalAsset).
- `AssetVariant` retains direct `asset_family_id` as explicitly required by the beta design model to support unlinked/draft variants.
- `AssetVariantAttributeValue` foreign keys referencing parent variant and attribute definition schemas (ondelete CASCADE is kept on attribute values since they represent sub-components of the variant itself).

## Seed Behavior
- Seeding reference schemas only as dictated by migration setup. No production data populated.

## Tests/Checks Run
- Executed `python -m pytest` inside `backend`.
- All 49 tests passed successfully.

## PostgreSQL Availability Result
- PostgreSQL is unavailable locally (Port 5432 closed). Migration checks run using SQLite database configurations.

## Scope Compliance
- Exclusively implemented AssetVariant baseline tables.
- Zero APIs, endpoints, matchers, or workers added.

## Forbidden Alias/Identity/Future-Sprint Scan Result
- Verified that `asset_aliases` and matching tables are completely non-existent and unregistered in database metadata.
- No ProjectAssetLine extensions or AI matches introduced.

## Missing or Recommended Fixes
- None.

## Final Result
- **Result:** PASS
- **Recommendation:** Ready for S2-PR-006 Asset Alias and Identity Candidate Persistence implementation.
