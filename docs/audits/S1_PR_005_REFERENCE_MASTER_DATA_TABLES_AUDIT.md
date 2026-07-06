# S1-PR-005 Reference Master Data Tables Baseline Audit

**Task ID:** S1-PR-005  
**Task Name:** Reference Master Data Tables Baseline  
**Audit Date:** 2026-07-06  
**Sprint:** Sprint 1 — Project + Master Data  
**Design Reference:** Valora Design Book v1.2-final  
**Final Result:** PASS  
**Recommendation:** Ready for S1-PR-006  

---

## 1. Files Changed

### Modified Files
- [backend/app/db/__init__.py](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/db/__init__.py)
- [backend/app/modules/project_master_data/models.py](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/modules/project_master_data/models.py)

### New Files
- [backend/alembic/versions/318f6d7d13e8_create_reference_data_baseline.py](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/alembic/versions/318f6d7d13e8_create_reference_data_baseline.py)
- [backend/tests/test_reference_data.py](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/tests/test_reference_data.py)

---

## 2. Design Files Read

Inspected from `valora-design-book-v1.2-alpha-project-master-data-completed.zip`:
- `09_DATA_MODEL/02_MASTER_DATA_MODEL.md` (Country, Province, Unit, and Currency table layouts)
- `12_API/05_MASTER_DATA_API.md` (Constraint configurations and code mappings)
- `14_ACCEPTANCE_TESTS/MASTER_DATA_ACCEPTANCE_TESTS.md` (Reference lookup creation checks)

---

## 3. Models / Tables Added

1. **`Country`** (`countries` table):
   - Stores country code lookups including ISO2 (unique, nullable), ISO3 (unique, nullable), Vietnamese name (`name_vi`), English name (`name_en`), and active status.
2. **`Province`** (`provinces` table):
   - Stores regions linked to a parent country, mapped via `country_id` foreign key.
3. **`Unit`** (`units` table):
   - Stores measurement unit lookups containing code (unique), display name, symbol, type (Enum: quantity, length, area, weight, other), and status.
4. **`Currency`** (`currencies` table):
   - Stores monetary currencies containing code (unique, 3 chars), display name, symbol, decimal places count, and status.

---

## 4. Constraints Added

- **Country Unique Codes:** Unique constraints on `countries` table for `iso2` and `iso3` (unique when not null).
- **Province Foreign Key:** Foreign key constraint `country_id` pointing to `countries.id` on delete CASCADE.
- **Unit Unique Code:** Unique constraint on `units.code`.
- **Currency Unique Code:** Unique constraint on `currencies.code`.

---

## 5. Seed Behavior

- Seeding was explicitly deferred in this PR as standard database lookup lists (e.g., full ISO lists) are not required by the current sprint sequence to start. Seeding is left to standard import scripts or test fixtures.
- Only schema baseline structures were generated. No real customer, supplier, project, or user data was seeded.

---

## 6. Tests and Checks Run

- **Pytest:** Executed `pytest` in `backend/`. All **12/12 tests passed** successfully.
  - Verified Country/Province back-populates relationship mappings.
  - Verified duplicate Country ISO code rejections.
  - Verified duplicate Unit code and Currency code rejections.
  - Verified UnitType and ReferenceStatus Enum mappings.
- **Alembic History:** Confirmed migration order:
  `7519c3d1f364 -> 318f6d7d13e8 (head), create_reference_data_baseline`

---

## 7. PostgreSQL Availability Result

- Local PostgreSQL database remains **unavailable**.
- Checked model structure and constraint logic using SQLite in-memory engine during tests.

---

## 8. Scope Compliance

- **No forbidden models implemented:** Did not create Customer, CustomerAlias, Supplier, SupplierAlias, Brand, Manufacturer, SignerProfile, or Project models.
- **No APIs or CRUD endpoints implemented:** Only database schema definitions and Alembic files were created.
- **No frontend/worker changes:** Changes are restricted strictly to backend DB and modules boundary.

---

## 9. Forbidden Domain / Business Scan Result

- Confirmed only Country, Province, Unit, and Currency models were added.
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

Ready for next PR (e.g., **S1-PR-006 — Customer / Supplier Persistence Tables** or Project baseline).
