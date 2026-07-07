# ADR 0024 - Knowledge and Evidence RBAC and Review Policy

## Status
Proposed

## Context
Catalog integrity requires strict RBAC validation. We need to formalize roles, define manual review gates, and ensure all updates generate immutable audit logs.

## Decision
1. **Permission Mapping**:
   - **Knowledge Scopes**:
     - `knowledge:read`: List and read specs, quotes, appraised prices, and queue details.
     - `knowledge:create`: Submit draft specs or appraised price proposals.
     - `knowledge:update`: Modify draft/candidate metadata and claim queue items.
     - `knowledge:approve`: Activate and approve specification versions and appraised price decisions.
     - `knowledge:cleanup`: Archive/delete unused drafts.
   - **Evidence Scopes**:
     - `evidence:file:create`: Upload document metadata.
     - `evidence:file:update`: Update non-content metadata.
     - `evidence:file:download_sensitive`: Access and download sensitive/restricted documents.
     - `evidence:link:create`: Associate evidence to catalog records.
     - `evidence:link:delete`: Unlink evidence links.
     - `evidence:source:update`: Modify source provider entries.
     - `evidence:cleanup`: Clean up unreferenced evidence drafts.
2. **Review Gate**:
   - Technical specifications and appraised prices can only be activated as official catalog standards via manual review and approval by an authorized user (`knowledge:approve`).
3. **Curator/Admin Override**:
   - Unlinking evidence supporting active standards requires the Curator/Admin role override check.
4. **Audit Log Hook**:
   - All mutations write an audit event entry.
   - Downloading sensitive documents logs metadata to `EvidenceAccessLog` and triggers a `EVIDENCE_FILE_DOWNLOAD_SENSITIVE` audit trail entry.

## Consequences
- Guarantees strict access control limits.
- Complete history trace of all catalog adjustments.

## Design References
- `valora-design-book-v1.2-gamma-knowledge-evidence-completed/21_AUDIT_PATCH_SECURITY_AND_CLEANUP.md`

## Sprint 3 Scope Impact
- Mandates security authorization decorators on all Sprint 3 API endpoints.

## What Is Explicitly Not Implemented Yet
- Dynamic permission snapshot assignment (currently statically checked).

## Risks / Follow-up
- Enforcing access logs on sensitive downloads requires validating real-time user header bindings correctly.
