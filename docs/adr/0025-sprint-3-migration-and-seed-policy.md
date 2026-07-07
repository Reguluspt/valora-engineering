# ADR 0025 - Sprint 3 Migration and Seed Policy

## Status
Proposed

## Context
Implementing the full Sprint 3 persistence layer requires coordinating several migrations. We need to plan the sequence, restrict what seeding is allowed, and address the PostgreSQL local connection limits.

## Decision
1. **Migration Sequence**:
   - **Migration 1 (Evidence Core)**: `evidence_sources`, `evidence_files`, `evidence_links`, and `evidence_access_logs`.
   - **Migration 2 (Specialized Evidence)**: Specialized sub-tables (`supplier_quote_evidences`, etc.), `evidence_extraction_results`, and `evidence_review_decisions`.
   - **Migration 3 (Knowledge Core)**: `technical_specifications`, `technical_specification_versions`, `quote_batches`, `quote_lines`, `market_quotes`, `appraised_price_decisions`, `knowledge_versions`, `knowledge_lineages`, `knowledge_queue_items`, `knowledge_conflicts`, and `knowledge_confidence`.
   - **Migration 4 (Project Line Linkage)**: Columns mapping on `project_asset_lines`.
2. **Seeding Boundaries**:
   - **Allowed Seed Data**: Reference source types, classification level enums, default confidence weight parameters, and price threshold configuration settings.
   - **Forbidden Seed Data**: Fake supplier quote details, mockup appraised prices, mock PDF files, or simulated historical lineage rows.
3. **Local Infrastructure Constraint**:
   - Due to the local PostgreSQL connection timeout limitation, migrations will be built using Alembic but tested locally against SQLite in-memory configurations. PostgreSQL production upgrade scripts remain unrun locally but will be validated for syntax.

## Consequences
- Clean execution of relational foreign key mappings.
- Prevents database pollution from invalid mockup catalog data.

## Design References
- `valora-design-book-v1.2-gamma-knowledge-evidence-completed/16_MIGRATION_AND_SEED_PLAN.md`

## Sprint 3 Scope Impact
- Controls directory organization and schema execution order of migrations in `backend/alembic/versions`.

## What Is Explicitly Not Implemented Yet
- Running migrations on a real local PostgreSQL container.

## Risks / Follow-up
- Validate that SQLite in-memory database connections execute foreign key check constraints (`PRAGMA foreign_keys = ON;`) to capture link errors during test cycles.
