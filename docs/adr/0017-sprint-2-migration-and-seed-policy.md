# ADR 0017 - Sprint 2 Migration and Seed Policy

## Status
Proposed

## Context
Adding the taxonomy and identity schemas requires database modifications. We need to define the migration sequencing, seed modes, and scope boundaries.

## Decision
1. **Migration Sequence**:
   - **Migration 1 (Taxonomy)**: `taxonomy_nodes`, `asset_families`, `asset_dna`, `asset_attribute_definitions`, `asset_variants`, `canonical_asset_attribute_values`, `asset_variant_attribute_values`, `taxonomy_change_requests`.
   - **Migration 2 (Identity)**: `canonical_assets`, `asset_aliases`, `identity_candidates`, `similarity_scores`, `duplicate_candidates`, `merge_decisions`, `identity_review_items`, `identity_decision_logs`.
   - **Migration 3 (Project Line)**: Extend `project_asset_lines` with suggested/approved IDs and statuses.
2. **Seed Policy**:
   - Only static, approved reference taxonomies are seeded (`is_system_seed = true`, `status = active`).
   - No mock supplier quotes, appraised prices, or fake lineage histories are seeded.

## Consequences
- Predictable and orderly deployment sequence.
- Safe testing of relationships during integrations.

## Design References
- `valora-design-book-v1.2-beta-taxonomy-asset-identity-completed/16_MIGRATION_AND_SEED_PLAN.md`

## Sprint 2 Scope Impact
- Organizes migration generation during the implementation sprint.

## What Is Explicitly Not Implemented Yet
- Automated cleanup of unreferenced taxonomy drafts.

## Risks / Follow-up
- Validate foreign key constraints on SQLite during migration testing.
