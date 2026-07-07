# S2-PR-006: Asset Alias + Identity Candidate Persistence Audit

## Files Changed
- `backend/app/modules/project_master_data/models.py` (Added AssetAlias, IdentityCandidate, SimilarityScore models and normalize_alias_helper)
- `backend/app/db/__init__.py` (Registered models in baseline mapping)
- `backend/alembic/versions/a87a9b6da996_create_alias_candidate_tables.py` (Alembic migration script)
- `backend/tests/test_asset_variant_persistence.py` (Removed obsolete non-existence asserts for asset alias table)
- `backend/tests/test_alias_candidate_persistence.py` (New tests verifying relationships, uniqueness and normalization helpers)

## Design Files Read
- `09_DATA_MODEL/04_ASSET_IDENTITY_MODEL.md` (beta zip)
- `12_API/07_ASSET_IDENTITY_API.md` (beta zip)
- `16_MIGRATION_AND_SEED_PLAN.md` (beta zip)

## Models/Tables Added
- `AssetAlias` (`asset_aliases`)
- `IdentityCandidate` (`identity_candidates`)
- `SimilarityScore` (`similarity_scores`)

## Enums Added
- `AssetAliasScope`
- `AssetAliasStatus`
- `IdentityCandidateStatus`

## Constraints Added
- `AssetAlias` unique constraints `uq_alias_normalized_canonical` and `uq_alias_normalized_variant` on `(normalized_alias, canonical_asset_id / asset_variant_id)`.
- `AssetAlias` foreign keys configured to use `ondelete='RESTRICT'` to protect data lineage.
- `IdentityCandidate` foreign keys referencing parent project asset lines, proposed targets (ondelete RESTRICT).
- `SimilarityScore` references candidate with `ondelete='CASCADE'`.

## Normalization Behavior
- Implemented `normalize_alias_helper` which downcases input strings, strips punctuation/non-alphanumeric chars, collapses extra spaces, and trims edges.

## Seed Behavior
- Seeding reference schemas only as dictated by migration setup. No production data populated.

## Tests/Checks Run
- Executed `python -m pytest` inside `backend`.
- All 51 tests passed successfully.

## PostgreSQL Availability Result
- PostgreSQL is unavailable locally (Port 5432 closed). Migration checks run using SQLite database configurations.

## Scope Compliance
- Exclusively implemented AssetAlias and IdentityCandidate baseline tables.
- Zero APIs, matchers, AI providers, or worker jobs introduced.

## Forbidden Merge/API/Approval/Future-Sprint Scan Result
- Verified that `duplicate_candidates` and `merge_decisions` are completely non-existent and unregistered in database metadata.
- No ProjectAssetLine extensions, candidate generation triggers or batch approval endpoints were added.

## Missing or Recommended Fixes
- None.

## Final Result
- **Result:** PASS
- **Recommendation:** Ready for S2-PR-007 Duplicate/Merge/Review Persistence implementation.
