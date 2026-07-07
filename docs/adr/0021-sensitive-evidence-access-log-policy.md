# ADR 0021 - Sensitive Evidence Access Log Policy

## Status
Proposed

## Context
Evidence files may contain proprietary pricing or manufacturer data. We need to implement classification levels and audit sensitive data access without leaking secrets in the audit log payload.

## Decision
1. **Sensitivity Classification**:
   - `EvidenceFile` records are classified into three levels: `normal`, `sensitive`, or `restricted`.
2. **Audit Trigger**:
   - Querying metadata (e.g. GET `/evidence/files/{id}`) does not trigger an access log.
   - Downloading or viewing the actual document payload (e.g. GET `/evidence/files/{id}/download`) for files classified as `sensitive` or `restricted` triggers a mandatory row insertion in the `EvidenceAccessLog` table.
3. **Access Log Schema**:
   - Fields: `evidence_file_id`, `accessed_by` (User UUID), `access_type` (`view` | `download` | `metadata`), `access_reason` (optional parameter supplied by caller), `ip_address`, `user_agent`, and `accessed_at`.
4. **Guard Rails**:
   - Downloading `restricted` files requires the `evidence:file:download_sensitive` RBAC permission.
   - Secrets, access tokens, or raw credentials must never be written to `EvidenceAccessLog` payload parameters.

## Consequences
- Guarantees trace visibility for sensitive documents.
- Minimizes log volume by auditing file reads only.

## Design References
- `valora-design-book-v1.2-gamma-knowledge-evidence-completed/21_AUDIT_PATCH_SECURITY_AND_CLEANUP.md`

## Sprint 3 Scope Impact
- Mandates access check filters and database hooks in the evidence controller module.

## What Is Explicitly Not Implemented Yet
- Automated IP geolocation tracing or suspicious request rate alerts.

## Risks / Follow-up
- Ensure proxy IP headers (`X-Forwarded-For`) are validated to log the real client IP.
