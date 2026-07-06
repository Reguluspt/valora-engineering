# S1-PR-004 Organization / User / Role Baseline Audit

**Task ID:** S1-PR-004  
**Task Name:** Organization / User / Role Baseline  
**Audit Date:** 2026-07-06  
**Sprint:** Sprint 1 — Project + Master Data  
**Design Reference:** Valora Design Book v1.2-final  
**Final Result:** PASS  
**Recommendation:** Ready for S1-PR-005  

---

## 1. Files Changed

### Modified Files
- [backend/app/db/__init__.py](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/db/__init__.py)

### New Files
- [backend/app/modules/project_master_data/models.py](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/modules/project_master_data/models.py)
- [backend/alembic/versions/7519c3d1f364_create_identity_baseline.py](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/alembic/versions/7519c3d1f364_create_identity_baseline.py)
- [backend/tests/test_identity.py](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/tests/test_identity.py)

---

## 2. Design Files Read

Inspected from `valora-design-book-v1.2-alpha-project-master-data-completed.zip`:
- `09_DATA_MODEL/02_MASTER_DATA_MODEL.md` (OrganizationProfile, User, Role, and UserRole definitions)
- `13_SECURITY/02_AUTHENTICATION.md` (Login identity format and password storage rules)
- `13_SECURITY/03_AUTHORIZATION_RBAC.md` (Permission tables and role-permission matrices)
- `14_ACCEPTANCE_TESTS/MASTER_DATA_ACCEPTANCE_TESTS.md` (UserRole login permissions and revocation criteria)

---

## 3. Models / Tables Added

1. **`OrganizationProfile`** (`organization_profiles` table):
   - Tenant baseline storing slug, legal name, display name, contact info, and status (active/inactive).
2. **`User`** (`users` table):
   - User account mapped to `organization_profiles`, storing email, name, password hash, status (active/inactive/invited/locked), and last login time.
3. **`Role`** (`roles` table):
   - System roles storing code, display name, description, and list of permissions.
4. **`UserRole`** (`user_roles` table):
   - Join table mapping users to roles, tracking assignments and revocations via `is_active` status flag.

*Note on Deferral:* The `UserPermissionSnapshot` table is deferred as it is an optional cached structure and is not required for the Sprint 1 identity schema baseline.

---

## 4. Constraints Added

- **Multi-Tenant Unique Login:** Unique constraint `uq_user_org_email` on `users` table for `(organization_id, email)`.
- **Tenant Slug Uniqueness:** Unique constraint on `organization_profiles` for `organization_slug`.
- **Role Code Uniqueness:** Unique constraint on `roles` for `code`.
- **Active Role Uniqueness:** Partial unique index `uq_active_user_role` on `user_roles` for `(user_id, role_id)` where `is_active = True`. Handled via `postgresql_where` and `sqlite_where` for cross-backend testing compatibility.

---

## 5. Seed Behavior

Seeded the 6 standard roles and their design permissions inside the Alembic migration [7519c3d1f364_create_identity_baseline.py](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/alembic/versions/7519c3d1f364_create_identity_baseline.py):
- `owner`: full administrative and valuation permissions.
- `admin`: identical permissions to `owner` for tenant management.
- `appraiser`: project creation, metadata updating, and valuation reviews.
- `reviewer`: QC submissions, approvals, and rejection permissions.
- `knowledge_curator`: knowledge base update and customer/supplier merge permissions.
- `viewer`: read-only access to projects and master data.

No users, passwords, or production data were seeded.

---

## 6. Tests and Checks Run

- **Pytest:** Executed `pytest` in `backend/`. All **8/8 tests passed** successfully.
  - Verified uniqueness constraints on organization slugs and tenant emails.
  - Verified partial active index behaviour (allowing duplicate inactive roles but blocking duplicate active roles).
  - Verified relationship cascades and back-populates.
- **Alembic History:** Ran `alembic history` and verified correct migration ordering:
  `632247f5fd32 -> 7519c3d1f364 (head), create_identity_baseline`

---

## 7. PostgreSQL Availability Result

- Local PostgreSQL is **not available** (timed out as expected).
- Verified ORM model structure and migration metadata offline using SQLite in-memory engine during pytest execution.

---

## 8. Scope Compliance

- **No auth APIs implemented:** Endpoints like `/login` or `/logout` were not created.
- **No password hashing packages added:** Plaintext passwords are not used; `password_hash` stores string values only.
- **No business domain models added:** No Customer, Supplier, Project, or reference tables were implemented.
- **No frontend/worker changes:** Edits remain constrained within backend/app/db and backend/app/modules.

---

## 9. Forbidden Domain / Business Scan Result

- Verified `backend/app/modules/project_master_data/models.py` only contains standard identity entities (`OrganizationProfile`, `User`, `Role`, `UserRole`).
- No mention of `Customer`, `Supplier`, or `Project` tables exists.

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

Ready for **S1-PR-005 — Master Data Reference Tables** (or Customer/Supplier tables) implementation.
