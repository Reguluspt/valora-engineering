# Sprint 3 Implementation Plan — Knowledge + Evidence

This document outlines the scope, entity designs, database schemas, APIs, security parameters, and testing boundaries for Sprint 3.

---

## 1. Sprint 3 Scope Summary
Sprint 3 implements the **Knowledge Context** and the **Evidence Context**. This introduces the logical split between official catalog standard specs (Knowledge) and the unstructured or external support records (Evidence). It also covers Quote Batches, Quote Lines, and Appraised Price Decisions to separate supplier pricing from the finalized appraised price records.

## 2. Entities to Implement

### Evidence Context
- **EvidenceFile**: Container for uploaded document metadata (name, MIME type, size, path/hash, and sensitivity level).
- **EvidenceLink**: Connects an `EvidenceFile` to a target domain entity (e.g. `TechnicalSpecificationVersion`, `QuoteBatch`, `AppraisedPriceDecision`).
- **EvidenceSource**: Tracks source providers/catalog origins.
- **SupplierQuoteEvidence / CatalogueEvidence / InternetEvidence / ImageEvidence / EmailEvidence**: Domain-specific context schemas.
- **EvidenceExtractionResult**: Records metadata extracted by system parses.
- **EvidenceReviewDecision**: Audit of reviewer actions on parsed evidence.
- **EvidenceAccessLog**: Logs sensitive file reads/downloads.

### Knowledge Context
- **TechnicalSpecification**: Standard description folder of standard asset parameters.
- **TechnicalSpecificationVersion**: Holds the specific active, candidate, or draft technical attribute mappings and references `EvidenceFile` sources.
- **QuoteBatch**: Consolidation of vendor quote options (revisions supported).
- **QuoteLine**: Individual quote items (unit price, supplier, currency, unit).
- **AppraisedPriceDecision**: Rationale and finalized appraisal values.
- **KnowledgeVersion**: Registry mapping active version indices across technical spec, quote batch, and appraised price.
- **KnowledgeLineage**: Append-only log tracking source files and historical project origins.
- **KnowledgeQueueItem**: Manual verification queue items.
- **KnowledgeConfidence**: Scoring statistics of catalog records.
- **KnowledgeConflict**: Logs discrepancies in specifications or quotes.

## 3. Tables and Migrations Expected

### Migration 1 — Evidence Core Tables
- `evidence_sources`
- `evidence_files` (fields include `sensitivity_level`)
- `evidence_links` (fields include `is_deleted`, `deleted_by`, `deleted_at`, `delete_reason`)
- `evidence_access_logs`

### Migration 2 — Specialized Evidence & Parsing Tables
- `supplier_quote_evidences`, `catalogue_evidences`, `internet_evidences`, `image_evidences`, `email_evidences`
- `evidence_extraction_results`
- `evidence_review_decisions`

### Migration 3 — Knowledge Core Tables
- `technical_specifications`
- `technical_specification_versions`
- `quote_batches` (fields include `revision_number`, `previous_quote_batch_id`, `row_version`)
- `quote_lines`
- `market_quotes`
- `appraised_price_decisions`
- `knowledge_versions`
- `knowledge_lineages`
- `knowledge_queue_items`
- `knowledge_conflicts`

### Migration 4 — Project Asset Line Links
- Confirm or add column links to `project_asset_lines`:
  - `technical_specification_id`
  - `quote_batch_id`
  - `appraised_price_decision_id`
  - `direct_source_project_id`
  - `original_source_project_id`
  - `lineage_path`

## 4. API Endpoints Expected

### Knowledge API
- `GET /api/v1/knowledge/technical-specifications`
- `GET /api/v1/knowledge/technical-specifications/{id}`
- `PATCH /api/v1/knowledge/technical-specifications/versions/{version_id}` (only allowed on drafts/candidates)
- `DELETE /api/v1/knowledge/technical-specifications/versions/{version_id}` (only allowed on unused drafts)
- `GET /api/v1/knowledge/quote-batches`
- `GET /api/v1/knowledge/quote-batches/{quote_batch_id}`
- `PATCH /api/v1/knowledge/quote-batches/{quote_batch_id}` (before approval only)
- `POST /api/v1/knowledge/quote-batches/{quote_batch_id}/revise` (creates v2 candidate revision)
- `DELETE /api/v1/knowledge/quote-batches/{quote_batch_id}` (unused candidates/rejected only)
- `GET /api/v1/knowledge/appraised-price-decisions`
- `GET /api/v1/knowledge/appraised-price-decisions/{decision_id}`
- `PATCH /api/v1/knowledge/appraised-price-decisions/{decision_id}` (draft status only)
- `DELETE /api/v1/knowledge/appraised-price-decisions/{decision_id}` (unused draft decisions only)
- `GET /api/v1/knowledge/queue/{queue_item_id}`
- `POST /api/v1/knowledge/queue/{queue_item_id}/claim`
- `POST /api/v1/knowledge/queue/{queue_item_id}/release`
- `POST /api/v1/knowledge/queue/{queue_item_id}/review` (applies optimistic locking `expected_row_version`)
- `POST /api/v1/knowledge/queue/auto-reject-low-confidence`
- `GET /api/v1/knowledge/conflicts`
- `GET /api/v1/knowledge/conflicts/{conflict_id}`
- `POST /api/v1/knowledge/conflicts/{conflict_id}/resolve`

### Evidence API
- `GET /api/v1/evidence/files/{evidence_file_id}`
- `GET /api/v1/evidence/files/{evidence_file_id}/download` (sensitive read check & audit log trigger)
- `PATCH /api/v1/evidence/files/{evidence_file_id}` (metadata only)
- `DELETE /api/v1/evidence/files/{evidence_file_id}` (unused soft delete only)
- `GET /api/v1/evidence/links` (query by target_type & target_id)
- `POST /api/v1/evidence/links`
- `DELETE /api/v1/evidence/links/{link_id}` (unlink / soft delete only)
- `GET /api/v1/evidence/sources`
- `GET /api/v1/evidence/sources/{source_id}`
- `PATCH /api/v1/evidence/sources/{source_id}`
- `GET /api/v1/evidence/extractions/{extraction_id}`
- `POST /api/v1/evidence/extractions/{extraction_id}/review`
- `POST /api/v1/evidence/extractions/auto-reject-low-confidence`

## 5. RBAC Permissions
- `knowledge:read` / `knowledge:create` / `knowledge:update` / `knowledge:approve` / `knowledge:cleanup`
- `evidence:file:create` / `evidence:file:update` / `evidence:file:download_sensitive` / `evidence:link:create` / `evidence:link:delete` / `evidence:source:update` / `evidence:cleanup`

## 6. Audit Events
All mutative actions must write records to the append-only `AuditEvent` table:
- `TECHNICAL_SPECIFICATION_VERSION_UPDATE` / `TECHNICAL_SPECIFICATION_VERSION_DELETE`
- `QUOTE_BATCH_UPDATE` / `QUOTE_BATCH_REVISE` / `QUOTE_BATCH_DELETE`
- `APPRAISED_PRICE_DECISION_UPDATE` / `APPRAISED_PRICE_DECISION_DELETE`
- `KNOWLEDGE_QUEUE_CLAIM` / `KNOWLEDGE_QUEUE_RELEASE` / `KNOWLEDGE_QUEUE_REVIEW`
- `KNOWLEDGE_CONFLICT_RESOLVE`
- `EVIDENCE_FILE_DOWNLOAD_SENSITIVE` (logs to `EvidenceAccessLog` as well)
- `EVIDENCE_LINK_DELETE`
- `UNUSED_DRAFT_CLEANUP`
- `AUTO_REJECT_LOW_CONFIDENCE`

## 7. Evidence Immutability / Append-Only Rules
- Original uploaded files and bytes are completely immutable. Metadata updates (like descriptions) are allowed.
- Evidence deletions represent soft deletes. Unlinking an evidence file updates `EvidenceLink.is_deleted = true` with reason and actor fields.
- Unlinking evidence that supports an approved appraised price or active knowledge version requires Curator/Admin override permissions.

## 8. Knowledge Versioning Rules
- Active catalog standard records are immutable. Corrections or updates create a new version of `TechnicalSpecificationVersion` which starts as a draft/candidate.
- `KnowledgeVersion` indexes and traces version history across domains without duplicating data payloads.
- Lineage pathways are tracked sequentially.

## 9. Quote Batch / Quote Line / Price Evidence Boundary
- **Market Quote vs Appraised Price**: A QuoteBatch logs multiple vendor lines (supplier quote 1/2/3). AppraisedPriceDecision records the professional choice selecting a pricing standard with a written reason.
- Approved QuoteBatch is immutable. Revisions increment `revision_number` and link to `previous_quote_batch_id`.

## 10. AI Suggestion Queue Boundary
- Suggestions remain in the manual review queue and cannot write to official knowledge tables directly.
- The `AutoRejectLowConfidenceKnowledgeCandidates` command automatically flags candidates with a confidence score `< 0.50` as rejected. They are hidden from standard queue lists.

## 11. Cleanup/Delete/Unlink Rules
- Active or approved items (TechnicalSpecificationVersion, QuoteBatch, AppraisedPriceDecision) linked to active catalog listings cannot be deleted.
- Only unused candidate, draft, or auto-rejected items are eligible for cleanup.

## 12. Acceptance Tests to Implement
- Test auto-rejection on low-confidence AI suggestions.
- Test min/max spread and median deviation quote price conflict formulas.
- Test row-version optimistic concurrency.
- Test sensitive evidence audit logging on downloads.
- Test unlinking restrictions on approved decisions.

## 13. Suggested PR Sequence
1. S3-PR-002: Knowledge + Evidence ADR / Gap Resolution
2. S3-PR-003: Evidence Library & Access Log Persistence
3. S3-PR-004: Reference & Specialized Evidence Persistence
4. S3-PR-005: Knowledge Technical Spec & Version Registry Persistence
5. S3-PR-006: Quote Batch & Line Revision Persistence
6. S3-PR-007: Appraised Price Decision Persistence
7. S3-PR-008: AI Auto-Reject Queue & Conflict Policy Persistence
8. S3-PR-009: Knowledge + Evidence API Foundation
9. S3-PR-010: API Contract & Concurrency Coverage Hardening
10. S3-PR-011: Sprint 3 Final Acceptance Audit

## 14. Risks and Ambiguities
- **SQLite Concurrency Limitation**: Optimistic locking checks (`row_version`) will run in-memory. Under SQLite in-memory, thread locks must be monitored to avoid transaction failures.
- **Sensitivity level assignment**: Boundary between normal/restricted needs to be explicitly defined.

## 15. ADRs Needed Before Coding
- **ADR 0018: Knowledge Version Registry Mapping Strategy** (mapping concrete versions without payload duplication).
- **ADR 0019: Quote Price Conflict Verification Formulas** (specifying floating-point calculations for spread percentages).

## 16. What is Explicitly Out of Scope in Sprint 3
- Full workbench UI panels, PDF/Excel rendering engines, background web scrapers, OCR scanner parsing workers, and accounting ledgers.
