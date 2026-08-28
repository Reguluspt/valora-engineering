# Schema and Alembic Drift Reconciliation Evidence

**Date:** 2026-08-27
**Authority:** ADR 0035 (Proposed)
**Status:** Resolved and Verified

## 1. Summary of Identified Drift & Resolutions

| Item | Classification | Source of Truth | Remediation Action | Verification Result |
|---|---|---|---|---|
| `dummy_model` | Legacy test artifact in local DB | No migration ever created it; defined in `test_db.py` on `Base` | Switched `test_db.py` to `TestBase(DeclarativeBase)`; dropped from DB volume | Not present in fresh migration; not in `Base.metadata` |
| `idx_audit_event_*` | Metadata drift | Migration `a87a9b6da992` | Added 3 index declarations to `AuditEvent.__table_args__` | `alembic check` PASS |
| `dossier_extraction_snapshots` scalar FKs | Metadata drift / redundant scalar FKs | Migration `c1d2e3f4a5b6` composite FKs | Removed redundant scalar `ForeignKey` on columns; kept composite FKs | `alembic check` PASS; composite tenant FK intact |
| `generated_documents.file_size_bytes` | Metadata drift | Migration `a87a9b6da9a2` (`BigInteger`) | Changed mapped type to `BigInteger().with_variant(Integer, "sqlite")` | `alembic check` PASS |
| `uq_active_session_per_user_project` | Metadata drift | Migration `db5977424e7b` (partial unique index) | Added partial `Index` with `postgresql_where` / `sqlite_where` to `WorkbenchSession.__table_args__` | `alembic check` PASS |
| `updated_at` / check constraints | Source migration alignment | Migrations `e7f8a9b0c1d2`, `f8a9b0c1d2e3` | Added `updated_at` and check constraints directly to module migrations | `alembic check` PASS; single linear head `d2e3f4a5b6c7` |

## 2. PostgreSQL Throwaway Lifecycle Verification

- **Database:** `valora_throwaway` created on PostgreSQL 16.
- **Upgrade Chain:** 38 linear migrations from base `632247f5fd32` to `d2e3f4a5b6c7` applied cleanly.
- **Total Tables:** 117 tables.
- **Alembic Check:** `No new upgrade operations detected.`
- **Downgrade / Upgrade Cycle:** `downgrade -1` -> `c1d2e3f4a5b6` -> `upgrade head` -> `d2e3f4a5b6c7` executed cleanly.

## 3. Exact-Revision Container Evidence Protocol

- The prior identical-context backend, worker and frontend artifact carries the OCI label
  `org.opencontainers.image.revision=a8972d12816b1f6ba4c7e35f8bdacce724c3562a`; it is not
  represented as a build of the later documentation-only PR #26 head.
- The images are built only after the final source/evidence commit exists.
- Runtime verification uses a separate Compose project, new PostgreSQL/MinIO volumes and an
  isolated network; it never reuses or deletes the existing `valora_postgres_data` volume.
- Dynamic image IDs, the exact revision label, `alembic current`, `alembic check`, HTTP health and
  production worker-handler outputs are recorded in PR #26. Keeping these dynamic values outside
  this committed file prevents the evidence update itself from changing the verified SHA.
