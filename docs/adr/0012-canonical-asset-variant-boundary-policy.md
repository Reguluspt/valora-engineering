# ADR 0012 - Canonical Asset vs. Asset Variant Boundary Policy

## Status
Proposed

## Context
When comparing raw catalog names, assets that differ only by capacity, dimensions, size, or output capacity should not become separate `CanonicalAsset` master records. They must represent different `AssetVariant` records referencing the same `CanonicalAsset`.

## Decision
1. **Separation**:
   - `CanonicalAsset` contains standard details: brand, manufacturer, short name, model category code.
   - `AssetVariant` contains variant-specific parameters (e.g. 150W, 100W, 5HP).
2. **Project Integration**:
   - `ProjectAssetLine` is extended with four nullable fields: `suggested_canonical_asset_id`, `approved_canonical_asset_id`, `suggested_asset_variant_id`, `approved_asset_variant_id`.
3. **Approval Flow**:
   - Creating/Updating a variant requires explicit state changes: `draft` -> `pending_review` -> `active`.

## Consequences
- Prevents database inflation of duplicate canonical records.
- Standardizes equipment names.

## Design References
- `valora-design-book-v1.2-beta-taxonomy-asset-identity-completed/01_SCOPE_AND_COMPLETION_GATE.md`
- `valora-design-book-v1.2-beta-taxonomy-asset-identity-completed/09_DATA_MODEL/03_TAXONOMY_MODEL.md`

## Sprint 2 Scope Impact
- Defines table schemas for canonical assets and variants.

## What Is Explicitly Not Implemented Yet
- Automated variant recommendation pipeline based on string extraction (deferred to AI/OCR workers).

## Risks / Follow-up
- Ensure matching rules strictly check parent-child constraints during lookup.
