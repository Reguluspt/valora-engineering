# S2-PR-007: Duplicate / Merge / Review Persistence Audit

## Files Changed
- `backend/app/modules/project_master_data/models.py` (Added DuplicateCandidate, MergeDecision, IdentityReviewItem, and IdentityDecisionLog models)
- `backend/app/db/__init__.py` (Registered models in baseline mapping)
- `backend/alembic/versions/a87a9b6da997_create_duplicate_merge_review_tables.py` (Alembic migration script)
- `backend/tests/test_alias_candidate_persistence.py` (Removed obsolete non-existence asserts for duplicate merge tables)
- `backend/tests/test_duplicate_merge_review_persistence.py` (New tests checking check constraints, defaults and relationships)

## Design Files Read
- `09_DATA_MODEL/04_ASSET_IDENTITY_MODEL.md` (beta zip)
- `12_API/07_ASSET_IDENTITY_API.md` (beta zip)
- `16_MIGRATION_AND_SEED_PLAN.md` (beta zip)

## Models/Tables Added
- `DuplicateCandidate` (`duplicate_candidates`)
- `MergeDecision` (`merge_decisions`)
- `IdentityReviewItem` (`identity_review_items`)
- `IdentityDecisionLog` (`identity_decision_logs`)

## Enums Added
- `DuplicateCandidateStatus`
- `MergeDecisionStatus`
- `IdentityReviewStatus`
- `IdentityDecisionType`

## Constraints Added
- `DuplicateCandidate` foreign keys referencing Canonical Assets (ondelete RESTRICT), and `chk_duplicate_diff_assets` check constraint (source != target).
- `MergeDecision` foreign keys referencing Canonical Assets (ondelete RESTRICT), and `chk_merge_diff_assets` check constraint (source != target).
- `IdentityReviewItem` foreign keys referencing project lines, candidates, and users (ondelete RESTRICT / SET NULL).
- `IdentityDecisionLog` foreign keys referencing lines and users (ondelete RESTRICT).

## Lineage Preservation Behavior
- Set `ondelete='RESTRICT'` for all parent/canonical references to protect historical lineages and audit logs against cascading deletes.

## Seed Behavior
- Seeding reference schemas only as dictated by migration setup. No production data populated.

## Tests/Checks Run
- Executed `python -m pytest` inside `backend`.
- All 53 tests passed successfully (including 3 new persistence check tests).

## PostgreSQL Availability Result
- PostgreSQL is unavailable locally (Port 5432 closed). Migration checks run using SQLite database configurations.

## Scope Compliance
- Exclusively implemented Duplicate, Merge, and Review persistence structures.
- Zero APIs, controllers, merge triggers or worker hooks added.

## Forbidden API/Algorithm/Merge-Execution/Future-Sprint Scan Result
- Verified that no merge executor, duplicate scanner, candidate generator or batch approval code was introduced.
- No project asset line fields were modified or extended.

## Missing or Recommended Fixes
- None.

## Final Result
- **Result:** PASS
- **Recommendation:** Ready for S2-PR-008 ProjectAssetLine Identity Extension implementation.
