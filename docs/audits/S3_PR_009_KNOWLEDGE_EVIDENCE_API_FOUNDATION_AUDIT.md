# S3-PR-009: Knowledge + Evidence API Foundation Audit Report

This report documents the audit for S3-PR-009 (Knowledge + Evidence API Foundation) of Project Valora.

## Files Changed
- `backend/app/main.py` (Registered `evidence` and `knowledge` API routers)
- `backend/app/api/evidence.py` (Created Evidence library API routes)
- `backend/app/api/knowledge.py` (Created Knowledge library and queue API routes)
- `backend/app/modules/project_master_data/evidence_schemas.py` (Created Pydantic validation schemas for Evidence)
- `backend/app/modules/project_master_data/knowledge_schemas.py` (Created Pydantic validation schemas for Knowledge)
- `backend/tests/test_knowledge_evidence_api.py` (Created integration/contract tests for API endpoints)

## Design Files Read
- `01_SCOPE_AND_COMPLETION_GATE.md`
- `15_CROSS_REFERENCE_MAP.md`
- `18_AUDIT_PATCH_CRUD_APIS.md`
- `20_AUDIT_PATCH_VERSIONING_MODEL_CLARIFICATION.md`
- `21_AUDIT_PATCH_SECURITY_AND_CLEANUP.md`
- `docs/adr/0004-rbac-enforcement-and-permission-snapshot.md`
- `docs/adr/0020-evidence-immutability-unlink-cleanup-policy.md`
- `docs/adr/0021-sensitive-evidence-access-log-policy.md`
- `docs/adr/0024-knowledge-evidence-rbac-and-review-policy.md`

## Endpoints Added
- **Evidence API:**
  - `GET /api/v1/evidence/sources`
  - `GET /api/v1/evidence/sources/{source_id}`
  - `PATCH /api/v1/evidence/sources/{source_id}`
  - `GET /api/v1/evidence/files/{evidence_file_id}`
  - `PATCH /api/v1/evidence/files/{evidence_file_id}`
  - `DELETE /api/v1/evidence/files/{evidence_file_id}` (soft-delete status)
  - `GET /api/v1/evidence/links`
  - `POST /api/v1/evidence/links`
  - `DELETE /api/v1/evidence/links/{link_id}` (soft-unlink)
  - `GET /api/v1/evidence/access-logs`
- **Knowledge API:**
  - `GET /api/v1/knowledge/technical-specifications`
  - `GET /api/v1/knowledge/technical-specifications/{id}`
  - `PATCH /api/v1/knowledge/technical-specifications/versions/{version_id}`
  - `GET /api/v1/knowledge/quote-batches`
  - `GET /api/v1/knowledge/quote-batches/{quote_batch_id}`
  - `PATCH /api/v1/knowledge/quote-batches/{quote_batch_id}`
  - `POST /api/v1/knowledge/quote-batches/{quote_batch_id}/revise`
  - `GET /api/v1/knowledge/appraised-price-decisions`
  - `GET /api/v1/knowledge/appraised-price-decisions/{decision_id}`
  - `PATCH /api/v1/knowledge/appraised-price-decisions/{decision_id}`
  - `GET /api/v1/knowledge/queue`
  - `GET /api/v1/knowledge/queue/{queue_item_id}`
  - `POST /api/v1/knowledge/queue/{queue_item_id}/claim`
  - `POST /api/v1/knowledge/queue/{queue_item_id}/release`
  - `POST /api/v1/knowledge/queue/{queue_item_id}/review`
  - `GET /api/v1/knowledge/conflicts`
  - `GET /api/v1/knowledge/conflicts/{conflict_id}`
  - `POST /api/v1/knowledge/conflicts/{conflict_id}/resolve`

## Schemas Added
- `EvidenceSourceCreate`, `EvidenceSourceUpdate`, `EvidenceSourceResponse`
- `EvidenceFileUpdate`, `EvidenceFileResponse`
- `EvidenceLinkCreate`, `EvidenceLinkResponse`
- `EvidenceAccessLogResponse`
- `TechnicalSpecificationResponse`, `TechnicalSpecificationVersionUpdate`, `TechnicalSpecificationVersionResponse`
- `QuoteBatchUpdate`, `QuoteLineResponse`, `QuoteBatchResponse`
- `AppraisedPriceDecisionUpdate`, `AppraisedPriceDecisionResponse`
- `KnowledgeQueueItemResponse`, `KnowledgeConflictResponse`

## Permission Checks Applied
- Checked via `require_permission(...)` dependency:
  - Read endpoints require `knowledge:read`.
  - Mutation endpoints require specific perms like `evidence:source:update`, `evidence:file:update`, `evidence:link:create`, `evidence:link:delete`, `evidence:cleanup`, `knowledge:update`, `knowledge:approve`.

## Evidence API Behavior
- Returns clean JSON structures of sources and file metadata.

## Evidence Immutability Behavior
- Blocked mutations of `object_key`, `checksum`, `file_size`, and `filename` in PATCH metadata endpoint.

## EvidenceLink Soft-Unlink Behavior
- Verified that `DELETE /api/v1/evidence/links/{link_id}` flags the target as `is_deleted = True` and sets user/timestamp attributes without purging physical database rows.

## Knowledge Technical Spec API Behavior
- Disallows updating spec versions marked as `active` or `superseded`. Updates restricted to `draft` or `candidate` statuses.

## QuoteBatch/QuoteLine API Behavior
- PATCH restricted to draft/candidate statuses. Active quote batches revised exclusively through `POST /api/v1/knowledge/quote-batches/{id}/revise` to preserve lineage.

## AppraisedPriceDecision API Behavior
- Blocked mutations on approved catalog decisions. Rationale/pricing edits restricted to draft stages.

## Queue/Conflict API Behavior
- Queue endpoints claim/release/review queue item attributes safely.
- Resolving conflicts marks conflict status resolved without altering referenced quotes.

## Audit Event Behavior
- Verified that `log_audit_event(...)` is invoked for all mutations. All payload schemas sanitize UUID structures recursively to plain strings to bypass SQLite serialization issues.

## Official Knowledge Non-Mutation Confirmation
- Confirmed that review operations on candidate queues modify queue log states but do not automatically publish/activate official catalog assets.

## ProjectAssetLine Non-Mutation Confirmation
- Confirmed no changes to `project_asset_lines` columns or logic.

## Tests/Checks Run
- Executed `python -m pytest` in `backend`. All 128 tests passed successfully (including newly added `test_knowledge_evidence_api.py` suite).
- Checked `/health`: healthy.

## PostgreSQL Availability Result
- PostgreSQL is unavailable locally. Database actions were validated against SQLite configurations.

## Scope Compliance
- Confirmed no database schema modifications or migrations were added.
- No actual file streaming, MinIO integration, AI providers, vector embeddings, crawlers, or background processors were implemented.

## Forbidden upload/download/OCR/AI/worker/calculation/future-sprint scan result
- Checked endpoint routes for object file byte stream interfaces; confirmed all file operations return metadata structures only.

## Missing or Recommended Fixes
- None.

## Final Result
- **Result:** PASS
- **Recommendation:** Ready for S3-PR-010 API Contract & Concurrency Coverage Hardening.
