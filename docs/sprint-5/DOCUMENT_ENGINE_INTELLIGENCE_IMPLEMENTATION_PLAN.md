# Document Engine & Intelligence Implementation Plan

This plan details the database schema modeling, API contract endpoints, and rules engine implementation for the Document Engine & Intelligence modules (Sprint 5).

## Proposed Changes

### Component 1: Document Engine Persistence
- Create/modify SQLAlchemy models in `backend/app/modules/project_master_data/models.py`:
  - `DocumentTemplate` (id, code, name, status, created_at)
  - `TemplateVersion` (id, template_id, version_no, template_payload, is_active, is_deprecated, deprecated_at)
  - `TemplatePlaceholder` (id, version_id, placeholder_key, placeholder_type)
  - `PlaceholderBinding` (id, job_id, placeholder_key, bound_value)
  - `ComputedPlaceholderExpression` (id, version_id, placeholder_key, expression_payload)
  - `RenderJob` (id, session_id, template_version_id, status, error_message, created_at)
  - `GeneratedDocument` (id, job_id, file_path, data_snapshot_payload, created_at)
  - `DocumentPackage` (id, project_id, name, created_at)
  - `DocumentPackageItem` (id, package_id, generated_document_id, order_no)

### Component 2: Document Intelligence Persistence
- Create/modify SQLAlchemy models in `backend/app/modules/project_master_data/models.py`:
  - `ParsedDocument` (id, original_filename, parsed_text, status, file_size)
  - `ExtractedField` (id, parsed_document_id, field_key, field_value, confidence, status)
  - `DocumentDiff` (id, source_doc_id, target_doc_id, diff_payload)
  - `DocumentCorrection` (id, parsed_document_id, field_key, corrected_value, reviewed_by, is_committed)

### Component 3: API Controllers
- Create `backend/app/api/document_engine.py` router registered under `/api/v1/document-engine`:
  - `POST /templates` (Create template)
  - `POST /templates/{id}/versions` (Add version)
  - `POST /templates/versions/{version_id}/deprecate` (Deprecate version)
  - `POST /render-jobs` (Trigger render job)
  - `GET /render-jobs/{id}` (Read render status)
- Create `backend/app/api/document_intelligence.py` router registered under `/api/v1/document-intelligence`:
  - `POST /parse` (Initiate parse metadata job)
  - `GET /parsed-documents/{id}` (Read parsed text/fields)
  - `POST /parsed-documents/{id}/corrections` (Submit correction draft)
  - `POST /parsed-documents/{id}/corrections/{corr_id}/commit` (Human-confirmed commit)

## Verification Plan

### Automated Integration Tests
- Verify CRUD operations, validation expressions, and draft corrections.
- Verify that AI suggestions do not auto-commit without manual review.
