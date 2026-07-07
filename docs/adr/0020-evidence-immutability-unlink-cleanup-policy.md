# ADR 0020 - Evidence Immutability, Unlink, and Cleanup Policy

## Status
Proposed

## Context
Evidence files act as legal and audit provenance for Valora catalog standards. We need strict policies to prevent raw document alteration, define how relationships are disconnected, and limit hard deletes.

## Decision
1. **Evidence File Immutability**:
   - Original file bytes, object paths/keys, and checksum hashes are immutable after upload.
   - Non-content metadata (e.g. description labels) may be updated.
2. **Soft-Unlinking**:
   - Disconnecting an evidence file from a catalog version or quote batch is performed via soft delete on the link table (`EvidenceLink`).
   - Fields populated on unlink: `is_deleted = true`, `deleted_by = user_id`, `deleted_at = timestamp`, and `delete_reason = reason_text`.
   - The underlying `EvidenceFile` row remains unmodified in the library.
3. **Guard Constraints**:
   - Unlinking evidence that supports an approved appraised price decision or active knowledge version requires Curator/Admin override permissions and a mandatory justification reason.
4. **Cleanup Thresholds**:
   - Hard deletes are forbidden for active or linked database records.
   - Hard deletes are only permitted for unused candidate technical specification versions, unused candidate quote batches, unused draft appraised price decisions, or auto-rejected queue items.

## Consequences
- Preserves absolute historical audit trail of document files.
- Prevents deletion of documents actively supporting active or approved standards.

## Design References
- `valora-design-book-v1.2-gamma-knowledge-evidence-completed/21_AUDIT_PATCH_SECURITY_AND_CLEANUP.md`

## Sprint 3 Scope Impact
- Restricts DELETE routes and controls soft-unlink logic in `EvidenceLink`.

## What Is Explicitly Not Implemented Yet
- Automated physical object storage garbage collection.

## Risks / Follow-up
- Soft-deleted links must be filtered out of standard frontend view queries.
