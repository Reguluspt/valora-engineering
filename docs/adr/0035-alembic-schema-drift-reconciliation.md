# ADR 0035 — Alembic and ORM Schema Drift Reconciliation

**Status:** Proposed
**Date:** 2026-08-27
**Context:** Sprint 13–16 remediation closure and production release readiness
**Deciders:** Core Engineering Team, Lead Reviewer

## Context

Running `alembic check` against PostgreSQL head `d2e3f4a5b6c7` revealed differences between the physical PostgreSQL schema (derived from linear migrations `632247f5fd32` through `d2e3f4a5b6c7`) and SQLAlchemy ORM metadata declarations:

1. **Table `dummy_model`:** Flagged as removed table. Investigation showed it was a test artifact defined in `backend/tests/test_db.py` inheriting from `Base`. When test runs executed `Base.metadata.create_all()`, the table was created in the local PostgreSQL volume, but no migration ever defined `dummy_model`.
2. **Indexes on `audit_events`:** `idx_audit_event_org`, `idx_audit_event_actor`, and `idx_audit_event_entity` were created in migration `a87a9b6da992_create_audit_events_table.py` for performance, but omitted from `AuditEvent.__table_args__`.
3. **Scalar FKs on `dossier_extraction_snapshots`:** In `backend/app/modules/excel_import/models.py`, `DossierExtractionSnapshot` declared scalar `ForeignKey(...)` on `organization_id`, `dossier_bundle_id`, and `source_file_id`, while simultaneously defining composite tenant FKs in `__table_args__`. Migration `c1d2e3f4a5b6` intentionally enforces composite foreign keys (`fk_dossier_extraction_source_tenant` and `fk_dossier_extraction_job_tenant`) rather than scalar keys.
4. **Column type in `generated_documents`:** Migration `a87a9b6da9a2_create_document_engine_tables.py` declared `file_size_bytes` as `sa.BigInteger()`. The ORM model mapped `int` without specifying `BigInteger`, defaulting to 32-bit `Integer`.
5. **Partial unique index in `workbench_sessions`:** Migration `db5977424e7b_create_active_session_unique_index.py` created `uq_active_session_per_user_project` with `WHERE status = 'active'`. The ORM model lacked the corresponding partial index definition in `__table_args__`.
6. **Timestamp columns and check constraints:** Missing `updated_at` columns and check constraints were reconciled directly into the respective source module migrations (`e7f8a9b0c1d2_harden_identity_tenant_and_security_audit.py` and `f8a9b0c1d2e3_create_dossier_bundle_tables.py`) rather than introducing auxiliary hotfix migrations, preserving the pristine single linear migration head at `d2e3f4a5b6c7`.

## Decision

1. **Source of Truth:**
   - The linear Alembic migration graph (`632247f5fd32` -> `d2e3f4a5b6c7`) is the definitive schema source of truth for PostgreSQL DDL.
   - No blind Alembic autogenerate DDL is permitted.
   - Composite tenant foreign keys are authoritative and must not be weakened.

2. **Remediation Actions:**
   - **Isolation of Test Models:** `backend/tests/test_db.py` now uses an isolated `TestBase(DeclarativeBase)` so `Base.metadata` remains strictly reserved for production domain models. Legacy `dummy_model` was removed from the local database volume.
   - **Audit Indexes:** Added `idx_audit_event_org`, `idx_audit_event_actor`, and `idx_audit_event_entity` to `AuditEvent.__table_args__`.
   - **Composite FK Purity:** Removed redundant scalar `ForeignKey` annotations from `DossierExtractionSnapshot`, relying on the authoritative `ForeignKeyConstraint` in `__table_args__`.
   - **BigInteger Alignment:** Specified `BigInteger().with_variant(Integer, "sqlite")` on `GeneratedDocument.file_size_bytes`.
   - **Partial Unique Index:** Added `uq_active_session_per_user_project` to `WorkbenchSession.__table_args__` with `postgresql_where=text("status = 'active'")` and `sqlite_where=text("status = 'active'")`.
   - **Source Migration Normalization:** Reconciled `updated_at` timestamp columns and check constraints directly in module migrations (`e7f8a9b0c1d2`, `f8a9b0c1d2e3`).

3. **Validation Criteria:**
   - Fresh throwaway PostgreSQL database upgraded from base to `d2e3f4a5b6c7` must pass `alembic check` with zero new upgrade operations.
   - Linear upgrade / downgrade / upgrade cycles must execute without error.
   - All backend, worker, and frontend tests must pass against PostgreSQL.

## Consequences

- Zero schema drift between PostgreSQL DDL and SQLAlchemy metadata.
- Clean `alembic check` in CI and local environments.
- Multi-tenant foreign key constraints and index optimizations are preserved intact.
