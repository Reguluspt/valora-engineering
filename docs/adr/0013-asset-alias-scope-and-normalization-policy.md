# ADR 0013 - Asset Alias Scope and Normalization Policy

## Status
Proposed

## Context
Raw names extracted from documents or catalogs vary heavily. We need an alias matching table to map raw names to canonical assets or specific variants.

## Decision
1. **Alias Scoping**:
   - `AssetAlias` can have `alias_scope = canonical` or `alias_scope = variant`.
   - If `variant`, the target must define a valid `asset_variant_id`.
2. **Normalization Rules**:
   - The field `normalized_alias` is automatically populated during saves by downcasing, stripping special characters, collapsing extra spaces, and removing punctuation.
3. **Lineage Preservation**:
   - On asset merge, aliases must be preserved and moved onto the target canonical asset.

## Consequences
- Fast database indexing and lookup against `normalized_alias`.
- Clear lineage mapping of historical catalog entries.

## Design References
- `valora-design-book-v1.2-beta-taxonomy-asset-identity-completed/09_DATA_MODEL/04_ASSET_IDENTITY_MODEL.md`

## Sprint 2 Scope Impact
- Outlines the `asset_aliases` table structure and normalization functions.

## What Is Explicitly Not Implemented Yet
- Semantic embedding vectors for aliases (deferred to later AI sprint).

## Risks / Follow-up
- Prevent collision of duplicate normalized alias strings within the same scope.
