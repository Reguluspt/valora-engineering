# ADR 0015 - Duplicate Merge and Lineage Policy

## Status
Proposed

## Context
When merging duplicate canonical assets, the system must maintain lineage tracking, prevent hard deletes, and migrate aliases and variants to ensure data integrity.

## Decision
1. **Auditable Merges**:
   - Every merge must record a transaction in a `merge_decisions` table tracking `source_asset_id`, `target_asset_id`, `reason`, and configuration flags.
2. **Soft Merge Execution**:
   - The source asset status updates to `merged` and updates `merged_into_asset_id = target_asset_id`. The record is never hard-deleted.
3. **Alias Preservation**:
   - All aliases mapped to the source are re-linked to the target.
   - All variants mapped to the source family are safely re-associated.

## Consequences
- Zero database record deletions during asset resolution.
- Clear audit trails.

## Design References
- `valora-design-book-v1.2-beta-taxonomy-asset-identity-completed/09_DATA_MODEL/04_ASSET_IDENTITY_MODEL.md`

## Sprint 2 Scope Impact
- Dictates API merge endpoint rules and database model triggers.

## What Is Explicitly Not Implemented Yet
- Reversion triggers to restore merged assets.

## Risks / Follow-up
- Ensure cascading updates on linked records do not block concurrent requests.
