# Schema and Alembic Drift Reconciliation Evidence

**Date:** 2026-08-27
**Authority:** ADR 0035 (Approved by User on 2026-08-27)
**Status:** Resolved and Verified

## 1. Summary of Identified Drift & Resolutions

| Item | Classification | Source of Truth | Remediation Action | Verification Result |
|---|---|---|---|---|
| `dummy_model` | Legacy test artifact in local DB | No migration ever created it; defined in `test_db.py` on `Base` | Switched `test_db.py` to `TestBase(DeclarativeBase)`; dropped from DB volume | Not present in fresh migration; not in `Base.metadata` |
| `idx_audit_event_*` | Metadata drift | Migration `a87a9b6da992` | Added 3 index declarations to `AuditEvent.__table_args__` | `alembic check` PASS |
| `dossier_extraction_snapshots` scalar FKs | Metadata drift / redundant scalar FKs | Migration `c1d2e3f4a5b6` composite FKs | Removed redundant scalar `ForeignKey` on columns; kept composite FKs | `alembic check` PASS; composite tenant FK intact |
| `generated_documents.file_size_bytes` | Metadata drift | Migration `a87a9b6da9a2` (`BigInteger`) | Changed mapped type to `BigInteger().with_variant(Integer, "sqlite")` | `alembic check` PASS |
| `uq_active_session_per_user_project` | Metadata drift | Migration `db5977424e7b` (partial unique index) | Added partial `Index` with `postgresql_where` / `sqlite_where` to `WorkbenchSession.__table_args__` | `alembic check` PASS |

## 2. PostgreSQL Throwaway Lifecycle Verification

- **Database:** `valora_throwaway` created on PostgreSQL 16.
- **Upgrade Chain:** 39 linear migrations from base `632247f5fd32` to `e3f4a5b6c7d8` applied cleanly.
- **Total Tables:** 117 tables.
- **Alembic Check:** `No new upgrade operations detected.`
- **Downgrade / Upgrade Cycle:** `downgrade -1` -> `d2e3f4a5b6c7` -> `upgrade head` -> `e3f4a5b6c7d8` executed cleanly.
