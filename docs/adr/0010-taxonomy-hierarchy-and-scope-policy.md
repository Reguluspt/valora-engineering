# ADR 0010 - Taxonomy Hierarchy and Scope Policy

## Status
Proposed

## Context
Sprint 2 introduces the hierarchical taxonomy data structure (`TaxonomyNode`). We need to establish the levels, parent-child inheritance constraints, lifecycle status transitions, and scope boundaries.

## Decision
1. **Taxonomy Levels**: The system enforces four strict enum levels: `domain`, `category`, `subcategory`, and `group`.
2. **Hierarchy Rules**:
   - A root node has no `parent_id` and must be at the `domain` level.
   - Any non-root node must specify a valid `parent_id`.
   - The hierarchy is strictly checked: parent nodes must be active. An active child node cannot have a deprecated, rejected, or draft parent.
3. **Lifecycle Statuses**: We support `draft`, `pending_review`, `active`, `deprecated`, `rejected`, and `merged` statuses.
4. **Scoping**: Taxonomy nodes are globally proposed but can be system-wide seed data (`is_system_seed = true`) or organization-proposed drafts.

## Consequences
- Clean structural grouping of equipment families under specific subcategories and groups.
- Safe lifecycle tracking of deprecated nodes to prevent assignment to new projects.

## Design References
- `valora-design-book-v1.2-beta-taxonomy-asset-identity-completed/09_DATA_MODEL/03_TAXONOMY_MODEL.md`

## Sprint 2 Scope Impact
- Unblocks database schema definition for `taxonomy_nodes`.

## What Is Explicitly Not Implemented Yet
- Automated parent validation checking for recursive loops (deferred to future API hardening).

## Risks / Follow-up
- Ensure migration scripts correctly handle hierarchical root parent checks.
