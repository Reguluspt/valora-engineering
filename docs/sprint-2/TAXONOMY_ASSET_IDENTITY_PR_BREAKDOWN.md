# PR Breakdown - Sprint 2: Taxonomy + Asset Identity

This document defines the sequential PR breakdown for Sprint 2 to manage development increments cleanly.

## PR Sequence

### S2-PR-002: Taxonomy ADR / Gap Resolution
- **Goal**: Establish core constraints, design decisions, and clarify similarities matching requirements.
- **Deliverables**: Focus on architectural documentation and edge-case resolution ADRs.

### S2-PR-003: Taxonomy Core Persistence Tables
- **Goal**: Implement primary database schemas and migrations.
- **Deliverables**: Alembic migrations for `taxonomy_nodes`, `asset_families`, `asset_dna`, and `asset_attribute_definitions`.

### S2-PR-004: Asset Variant Persistence Tables
- **Goal**: Implement variant schema and validation layer.
- **Deliverables**: Schema migrations for `asset_variants` and `asset_variant_attribute_values`.

### S2-PR-005: Canonical Asset Persistence Tables
- **Goal**: Implement canonical asset schema and attribute values.
- **Deliverables**: Schema migrations for `canonical_assets` and `canonical_asset_attribute_values`.

### S2-PR-006: Asset Alias & Identity Candidate Persistence Tables
- **Goal**: Implement identity matching data structures.
- **Deliverables**: Schema migrations for `asset_aliases`, `identity_candidates`, `similarity_scores`, `duplicate_candidates`, and `merge_decisions`.

### S2-PR-007: Taxonomy API Foundation
- **Goal**: Implement node proposals, updates, reviews, and variant creation endpoints.
- **Deliverables**: Taxonomy routers, Pydantic schemas, validation filters, and corresponding unit tests.

### S2-PR-008: Asset Identity API Foundation
- **Goal**: Implement similarity matcher pipelines, alias attachments, bulk approval queues, and merges.
- **Deliverables**: Asset identity routers, batch validation rules, and merge lineage tracking logic.

### S2-PR-009: Contract + Coverage Hardening
- **Goal**: Hardening tests across all endpoint routes.
- **Deliverables**: Comprehensive unit and integration test suite verification.

### S2-PR-010: Sprint 2 Final Acceptance Audit
- **Goal**: Perform comprehensive code quality and scope compliance verification.
- **Deliverables**: Final Sprint 2 audit report.
