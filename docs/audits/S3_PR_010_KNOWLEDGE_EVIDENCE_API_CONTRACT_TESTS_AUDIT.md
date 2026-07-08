# S3-PR-010: Knowledge + Evidence API Contract & Concurrency Coverage Hardening Audit Report

This report documents the audit for S3-PR-010 (API Contract & Concurrency Hardening) of Project Valora.

## Files Changed
- `backend/tests/test_knowledge_evidence_api.py` (Updated to explicitly cover all 28 foundational API endpoints)
- `backend/tests/test_knowledge_evidence_api_hardening.py` (Created API contract and concurrency hardening test suite)

## Complete Endpoint Matrix

### Evidence API Endpoint Coverage

| Method | Endpoint | Tested / Status | Notes |
|---|---|---|---|
| GET | `/api/v1/evidence/sources` | **Tested** | Verifies source listing permissions |
| GET | `/api/v1/evidence/sources/{source_id}` | **Tested** | Verifies detailed retrieval |
| PATCH | `/api/v1/evidence/sources/{source_id}` | **Tested** | Updates source metadata |
| GET | `/api/v1/evidence/files/{evidence_file_id}` | **Tested** | Retrieves evidence file |
| PATCH | `/api/v1/evidence/files/{evidence_file_id}` | **Tested** | Verifies optimistic lock and immutable field ignores |
| DELETE | `/api/v1/evidence/files/{evidence_file_id}` | **Tested** | Performs status archiving |
| GET | `/api/v1/evidence/links` | **Tested** | Lists link registry |
| POST | `/api/v1/evidence/links` | **Tested** | Connects file to target spec |
| DELETE | `/api/v1/evidence/links/{link_id}` | **Tested** | Triggers soft-unlink deletion |
| GET | `/api/v1/evidence/access-logs` | **Tested** | Lists download access log lists |
| POST | `/api/v1/evidence/upload` | **Not Applicable** | Forbidden: upload streaming deferred to future integration |
| GET | `/api/v1/evidence/download` | **Not Applicable** | Forbidden: file streaming download deferred to future integration |

### Knowledge API Endpoint Coverage

| Method | Endpoint | Tested / Status | Notes |
|---|---|---|---|
| GET | `/api/v1/knowledge/technical-specifications` | **Tested** | Lists standard specifications |
| GET | `/api/v1/knowledge/technical-specifications/{id}` | **Tested** | Retrieves detailed specification |
| PATCH | `/api/v1/knowledge/technical-specifications/versions/{version_id}` | **Tested** | Patches spec version; blocks active edits |
| GET | `/api/v1/knowledge/quote-batches` | **Tested** | Lists quote batches |
| GET | `/api/v1/knowledge/quote-batches/{quote_batch_id}` | **Tested** | Retrieves detailed quote batch |
| PATCH | `/api/v1/knowledge/quote-batches/{quote_batch_id}` | **Tested** | Patches batch metadata |
| POST | `/api/v1/knowledge/quote-batches/{quote_batch_id}/revise` | **Tested** | Creates new revision; preserves active batch |
| GET | `/api/v1/knowledge/appraised-price-decisions` | **Tested** | Lists appraised price decisions |
| GET | `/api/v1/knowledge/appraised-price-decisions/{decision_id}` | **Tested** | Retrieves detailed price decision |
| PATCH | `/api/v1/knowledge/appraised-price-decisions/{decision_id}` | **Tested** | Updates appraised decision |
| GET | `/api/v1/knowledge/queue` | **Tested** | Lists queue candidates |
| GET | `/api/v1/knowledge/queue/{queue_item_id}` | **Tested** | Retrieves queue metadata details |
| POST | `/api/v1/knowledge/queue/{queue_item_id}/claim` | **Tested** | Claims queue item |
| POST | `/api/v1/knowledge/queue/{queue_item_id}/release` | **Tested** | Releases claimed item |
| POST | `/api/v1/knowledge/queue/{queue_item_id}/review` | **Tested** | Reviews/rejects items without auto-approval |
| GET | `/api/v1/knowledge/conflicts` | **Tested** | Lists pricing conflict anomalies |
| GET | `/api/v1/knowledge/conflicts/{conflict_id}` | **Tested** | Retrieves detailed conflict |
| POST | `/api/v1/knowledge/conflicts/{conflict_id}/resolve` | **Tested** | Resolves conflict logs without quote mutation |

## RBAC Coverage
- Verified deny-by-default on all endpoints when authorization header `X-User-Id` is missing or invalid (raises 401).
- Verified viewer role lacks mutation permission (raises 403) on POST/PATCH/DELETE actions.
- Evidence metadata read permission boundary utilizes standard `knowledge:read` roles by design because Evidence acts as the validation ground backing the Knowledge registry.

## Evidence Immutability Coverage
- Asserted that PATCH operations on files ignore and discard changes to immutable fields (`object_key`, `checksum`, `file_size`, `filename`, and `mime_type`) preserving database records intact.

## EvidenceLink Soft-Unlink Coverage
- Verified delete link actions set `is_deleted = True` and populate metadata fields without deleting the parent `EvidenceFile` row.

## Row_version/Concurrency Coverage
- Verified that sending a stale `expected_row_version` raises an HTTP 409 conflict error for:
  - `EvidenceFile`
  - `TechnicalSpecificationVersion`
  - `QuoteBatch`
  - `AppraisedPriceDecision`
  - `KnowledgeQueueItem`
  - `KnowledgeConflict`

## Official Knowledge Non-Mutation Confirmation
- Asserted queue operations do not write or auto-publish official specs.

## ProjectAssetLine Non-Mutation Confirmation
- Confirmed no changes to `project_asset_lines` columns or logic.

## Forbidden Route/Behavior Coverage
- Verified byte-stream upload/download routes are missing and return HTTP 404.

## OpenAPI Result
- Confirmed schema loads.

## Tests/Checks Run
- Executed `python -m pytest` in `backend`. All 133 tests passed successfully.
- Checked `/health`: healthy.

## PostgreSQL Availability Result
- PostgreSQL is unavailable locally. Database actions were validated against SQLite configurations.

## Scope Compliance
- Confirmed no database schema modifications, migrations, or application code changes were added.
- Only unit test coverage was added.

## Final Result
- **Result:** PASS
- **Recommendation:** Ready for S3-PR-011 Sprint 3 Final Acceptance Audit.
