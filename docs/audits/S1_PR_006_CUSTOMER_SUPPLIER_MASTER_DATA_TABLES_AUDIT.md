# S1-PR-006 Customer / Supplier / Brand / Manufacturer / SignerProfile Tables Audit

**Task ID:** S1-PR-006  
**Task Name:** Customer / Supplier / Brand / Manufacturer / SignerProfile Persistence Tables  
**Audit Date:** 2026-07-06  
**Sprint:** Sprint 1 — Project + Master Data  
**Design Reference:** Valora Design Book v1.2-final  
**Final Result:** PASS  
**Recommendation:** Ready for Sprint 1 Project Model implementation  

---

## 1. Files Changed

### Modified Files
- [backend/app/db/__init__.py](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/db/__init__.py)
- [backend/app/modules/project_master_data/models.py](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/modules/project_master_data/models.py)

### New Files
- [backend/alembic/versions/8779d8e2f490_create_master_data_baseline.py](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/alembic/versions/8779d8e2f490_create_master_data_baseline.py)
- [backend/tests/test_master_data.py](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/tests/test_master_data.py)

---

## 2. Design Files Read

Inspected from `valora-design-book-v1.2-alpha-project-master-data-completed.zip`:
- `09_DATA_MODEL/02_MASTER_DATA_MODEL.md` (Customer, Supplier, Brand, Manufacturer, SignerProfile layouts)
- `12_API/05_MASTER_DATA_API.md` (Merging states, deactivation fields, tax code unique constraints)
- `04_DOMAIN/04B_MASTER_DATA_COMMANDS_EVENTS.md` (Merge event data structures)
- `14_ACCEPTANCE_TESTS/MASTER_DATA_ACCEPTANCE_TESTS.md` (Uniqueness and cascade tests)

---

## 3. Models / Tables Added

1. **`Customer`** (`customers` table):
   - Tenant-scoped customer model storing legal name, display name, tax code, address, province, status, self-referential merge target, and auditor tracking (`created_by`/`updated_by`). Mapped with optimistic locking.
2. **`CustomerAlias`** (`customer_aliases` table):
   - Mapped name aliases for fuzzy logic with confidence score. Cascade deletes on Customer.
3. **`Supplier`** (`suppliers` table):
   - Tenant-scoped supplier model with legal name, display name, tax code, address, province, status, self-referential merge target, reliability score, and auditor tracking. Mapped with optimistic locking.
4. **`SupplierAlias`** (`supplier_aliases` table):
   - Mapped name aliases for fuzzy logic. Cascade deletes on Supplier.
5. **`Manufacturer`** (`manufacturers` table):
   - Brand manufacturer profile with country and website mapping.
6. **`Brand`** (`brands` table):
   - Brand name lookup with country and manufacturer links. Mapped with optimistic locking.
7. **`SignerProfile`** (`signer_profiles` table):
   - Authorized signers for valuations with default flag. Mapped with optimistic locking.

---

## 4. Constraints Added

- **Multi-Tenant Tax Code Uniqueness:**
  - Unique constraint `uq_customer_tax_org` on `customers` for `(organization_id, tax_code)`.
  - Unique constraint `uq_supplier_tax_org` on `suppliers` for `(organization_id, tax_code)`.
- **Foreign Keys:**
  - Cascade deletes on `CustomerAlias.customer_id` and `SupplierAlias.supplier_id`.
  - `SET NULL` on `province_id`, `country_id`, `manufacturer_id`, and merge self-referential fields.
- **Brand Case-Insensitive Uniqueness:**
  - Unique index `uq_brand_name_lower` on `lower(name)`.

---

## 5. Seed Behavior

- No production master data, organizations, users, or passwords were seeded in the migration.
- Only baseline schema tables were created.

---

## 6. Tests and Checks Run

- **Pytest:** Executed `pytest` in `backend/`. All **17/17 tests passed** successfully.
  - Verified tax code uniqueness per organization for Customers and Suppliers.
  - Verified case-insensitive name uniqueness for Brands.
  - Verified alias relationships and cascade deletions.
  - Verified optimistic version locking increments.
- **Alembic History:** Confirmed migration order:
  `318f6d7d13e8 -> 8779d8e2f490 (head), create_master_data_baseline`

---

## 7. PostgreSQL Availability Result

- Local PostgreSQL database remains **unavailable**.
- Checked model structure and constraint logic using SQLite in-memory engine during tests.

---

## 8. Scope Compliance

- **No Project models implemented:** Did not create Project, ProjectAssetLine, or ProjectFile.
- **No APIs or CRUD endpoints implemented:** Only database schema definitions and Alembic files were created.
- **No frontend/worker changes:** Changes are restricted strictly to backend DB and modules boundary.

---

## 9. Forbidden Domain / Business Scan Result

- Confirmed only core master data tables were added.
- No other business models exist.

---

## 10. Missing or Recommended Fixes

*None.*

---

## 11. Final Result

```text
PASS
```

---

## 12. Recommendation

Ready for next PR (e.g., **S1-PR-007 — Project / Asset / File Persistence Tables** baseline implementation).
