# S1-PR-007 Project / ProjectAssetLine / ProjectFile Tables Audit

**Task ID:** S1-PR-007  
**Task Name:** Project / ProjectAssetLine / ProjectFile Persistence Tables  
**Audit Date:** 2026-07-06  
**Sprint:** Sprint 1 — Project + Master Data  
**Design Reference:** Valora Design Book v1.2-final  
**Final Result:** PASS  
**Recommendation:** Ready for Sprint 1 API implementation  

---

## 1. Files Changed

### Modified Files
- [backend/app/db/__init__.py](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/db/__init__.py)
- [backend/app/modules/project_master_data/models.py](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/modules/project_master_data/models.py)

### New Files
- [backend/alembic/versions/85f658678b7d_create_project_baseline.py](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/alembic/versions/85f658678b7d_create_project_baseline.py)
- [backend/tests/test_project.py](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/tests/test_project.py)

---

## 2. Design Files Read

Inspected from `valora-design-book-v1.2-alpha-project-master-data-completed.zip`:
- `09_DATA_MODEL/01_PROJECT_MODEL.md` (Project, ProjectAssetLine, and ProjectFile layouts)
- `12_API/03_PROJECT_API.md` (Constraint configurations and code mappings)
- `04_DOMAIN/04A_PROJECT_COMMANDS_EVENTS.md` (State transitions and commands)
- `04_DOMAIN/07A_PROJECT_STATE_MACHINE.md` (Workflow statuses check)
- `14_ACCEPTANCE_TESTS/PROJECT_ACCEPTANCE_TESTS.md` (Constraint expectations and negative value tests)

---

## 3. Models / Tables Added

1. **`Project`** (`projects` table):
   - Tenant-scoped project model storing code, name, description, status, knowledge update status, fee amount, fee currency, signer profile, and audit fields (`created_by`/`updated_by`). Mapped with optimistic locking.
2. **`ProjectAssetLine`** (`project_asset_lines` table):
   - Project asset line items mapping project, asset name, quantity, unit, raw price/currency, appraised unit price/currency, review status, validation status, brand, and manufacturer. Mapped with optimistic locking.
3. **`ProjectFile`** (`project_files` table):
   - Uploaded file metadata storing file name, size, category, mime type, object key, sha256 checksum, processing status, and JSON extracted metadata. Mapped with optimistic locking. No binary blobs are stored in the database.

---

## 4. Enums Added

- `ProjectWorkflowStatus` (draft, submitted, under_review, approved, rejected, archived, cancelled)
- `KnowledgeUpdateStatus` (pending, applied, deferred, ignored)
- `AssetLineReviewStatus` (pending, accepted, flagged, rejected)
- `AssetLineValidationStatus` (unvalidated, valid, invalid, warning)
- `ProjectFileCategory` (input_contract, reference_doc, appraisal_report, support_file, other)
- `FileProcessingStatus` (pending, processing, completed, failed)

---

## 5. Constraints Added

- **Multi-Tenant Project Code Uniqueness:** Unique constraint `uq_project_code_org` on `projects` for `(organization_id, code)`.
- **Non-Negative Database CheckConstraints:**
  - `chk_project_fee_positive` on `projects` for `fee_amount >= 0`.
  - `chk_asset_quantity_positive` on `project_asset_lines` for `quantity >= 0`.
  - `chk_asset_raw_price_positive` on `project_asset_lines` for `raw_price >= 0`.
  - `chk_asset_appraised_price_positive` on `project_asset_lines` for `appraised_unit_price >= 0`.
  - `chk_file_size_positive` on `project_files` for `file_size >= 0`.
- **Cascade Deletes:** Foreign keys on `ProjectAssetLine.project_id` and `ProjectFile.project_id` cascade delete when parent Project is deleted.

---

## 6. Future-Reference Placeholder Policy

- Added nullable UUID placeholders (`matched_asset_id`, `matched_knowledge_id`, `taxonomy_id`) on `ProjectAssetLine` to enable compatibility with future-sprint business modules (Asset Identity, Taxonomy, Knowledge Base) without introducing behavior or stub logic.

---

## 7. Seed Behavior

- No mock projects, file metadata, or audit entries were seeded.
- Only baseline schema tables were created.

---

## 8. Tests and Checks Run

- **Pytest:** Executed `pytest` in `backend/`. All **21/21 tests passed** successfully.
  - Verified project code uniqueness per organization.
  - Verified CheckConstraints reject negative fees, quantities, prices, and file sizes.
  - Verified cascade deletions on project lines and files.
- **Alembic History:** Confirmed migration order:
  `8779d8e2f490 -> 85f658678b7d (head), create_project_baseline`

---

## 9. PostgreSQL Availability Result

- Local PostgreSQL database remains **unavailable**.
- Checked model structure and constraint logic using SQLite in-memory engine during tests.

---

## 10. Scope Compliance

- **No APIs or routers implemented:** No controllers or routes were created.
- **No MinIO storage client/OCR parsing implemented:** No external integrations were added.
- **No frontend/worker changes:** Changes are restricted strictly to backend DB and modules boundary.

---

## 11. Forbidden Future-Sprint / Domain Scan Result

- Confirmed only Project, ProjectAssetLine, and ProjectFile tables were added.
- No future-sprint logic (OCR parsing, document generation, fuzzy index matching, etc.) was added.

---

## 12. Missing or Recommended Fixes

*None.*

---

## 13. Final Result

```text
PASS
```

---

## 14. Recommendation

Ready for next PR (e.g. APIs and routers implementation in Sprint 1).
