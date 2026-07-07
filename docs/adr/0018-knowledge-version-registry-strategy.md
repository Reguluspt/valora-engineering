# ADR 0018 - Knowledge Version Registry Strategy

## Status
Proposed

## Context
Original design defined both `TechnicalSpecificationVersion` and `KnowledgeVersion` without separating their functional boundaries clearly. We need a clear architecture defining how payload versioning differs from index tracing and mapping, how active versions are queried, and how historical project linkages remain immutable.

## Decision
1. **Model Distinction**:
   - `TechnicalSpecificationVersion` stores concrete technical parameters, attribute values (as key-value pairs or JSON payloads), and direct references to source project and evidence file IDs.
   - `KnowledgeVersion` serves as a generic, cross-domain index registry. It traces versions without duplicating data attributes (like technical specs, quote lines, or rationales).
2. **Registry Attributes**:
   - `KnowledgeVersion` maps generic keys: `knowledge_type` (e.g. `technical_spec`, `quote_batch`, `appraised_price`), `target_id`, `concrete_version_id`, `version_number`, and links them to catalog canonical assets or variants.
3. **Active/Current Version Resolution**:
   - Queries look up `KnowledgeVersion` records where `status = active` to determine the active catalog standard for a given `canonical_asset_id` or `asset_variant_id`.
4. **Historical Immutability**:
   - Approved versions remain immutable. Project asset lines link directly to specific `technical_specification_id`, `quote_batch_id`, and `appraised_price_decision_id` records, preserving historical project linkages even when catalog standards are superseded.

## Consequences
- Clean separation of catalog registry indexing from domain payload schemas.
- Prevention of data duplication across indexing models.
- Transparent audit lineage back to original project asset lines.

## Design References
- `valora-design-book-v1.2-gamma-knowledge-evidence-completed/20_AUDIT_PATCH_VERSIONING_MODEL_CLARIFICATION.md`

## Sprint 3 Scope Impact
- Controls schema layout of `KnowledgeVersion` and `TechnicalSpecificationVersion` tables.

## What Is Explicitly Not Implemented Yet
- Automated background synchronization between project approvals and version index status (synchronization triggered via API commands).

## Risks / Follow-up
- Ensure foreign keys prevent cascading deletes of indexed concrete payloads.
