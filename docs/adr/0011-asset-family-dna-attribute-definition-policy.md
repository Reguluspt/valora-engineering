# ADR 0011 - Asset Family, DNA, and Attribute Definition Policy

## Status
Proposed

## Context
Each `AssetFamily` needs technical attribute validation schemas. Previously, data scopes for canonical assets and variants were combined, creating validation confusion.

## Decision
1. **Relationships**:
   - `AssetFamily` belongs to a `TaxonomyNode`.
   - `AssetDNA` represents a versioned validation schema linked 1-to-1 to an `AssetFamily`.
   - `AssetAttributeDefinition` belongs to a versioned `AssetDNA` schema.
2. **Scopes**:
   - Attribute definitions have a `scope` parameter: `canonical`, `variant`, or `both`.
   - `canonical`: common properties defining overall identity (e.g., standard_name, brand).
   - `variant`: technical specifications defining model variants (e.g., horsepower, size).
3. **Data Types**: Enforce enums: `string`, `number`, `boolean`, `enum`, and `date`.
4. **Lifecycle**: Only one active DNA schema is allowed per family. Required attributes must be filled before variant approval.

## Consequences
- Clean separation between base canonical identity attributes and variant technical attributes.
- Version-controlled schema updates per family.

## Design References
- `valora-design-book-v1.2-beta-taxonomy-asset-identity-completed/09_DATA_MODEL/03_TAXONOMY_MODEL.md`

## Sprint 2 Scope Impact
- Dictates table mappings for family, DNA, definition, and value storage tables.

## What Is Explicitly Not Implemented Yet
- Dynamic client-side form rendering from definitions (deferred to frontend).

## Risks / Follow-up
- Validate version numbers strictly on DNA creation.
