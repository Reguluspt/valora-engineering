# S3-PR-002: Knowledge + Evidence ADR / Gap Resolution Audit Report

This report documents the ADR intake and gap resolution phase for Sprint 3 (Knowledge + Evidence) of Project Valora.

## Final Result
- **Result:** PASS
- **Recommendation:** Ready for S3-PR-003 Evidence Library Persistence.

## ADRs Created
- `docs/adr/0018-knowledge-version-registry-strategy.md` (Proposed)
- `docs/adr/0019-quote-price-conflict-formulas.md` (Proposed)
- `docs/adr/0020-evidence-immutability-unlink-cleanup-policy.md` (Proposed)
- `docs/adr/0021-sensitive-evidence-access-log-policy.md` (Proposed)
- `docs/adr/0022-quote-batch-line-appraised-price-boundary.md` (Proposed)
- `docs/adr/0023-ai-knowledge-queue-auto-reject-policy.md` (Proposed)
- `docs/adr/0024-knowledge-evidence-rbac-and-review-policy.md` (Proposed)
- `docs/adr/0025-sprint-3-migration-and-seed-policy.md` (Proposed)

## Scope Compliance
- Confirmed that only documentation files under `docs/adr/` and `docs/audits/` have been changed.
- Verified that zero modifications were made to backend app source code, tests, frontend, worker, or reference packages.
- Confirmed no migrations, database schemas, models, or endpoints were implemented.

## Gap Resolution Verification
1. **Version Registry Boundary**: Resolved in ADR 0018. Technical specification versions contain concrete payloads, whereas knowledge version registry entries index targets.
2. **Quote Price Formula**: Resolved in ADR 0019. Defined deterministic formula for spread and median deviation.
3. **Unlinking/Cleanup Policy**: Resolved in ADR 0020. Unlinking acts as soft delete on `EvidenceLink` records. Hard deletes are restricted to unused drafts/candidates.
4. **Sensitive Ingestion Tracing**: Resolved in ADR 0021. Established sensitivity classifications (`normal`, `sensitive`, `restricted`). Downloading a sensitive/restricted file triggers a write to `EvidenceAccessLog`.
5. **Quote Batch/Appraised Boundary**: Resolved in ADR 0022. Market quotes and appraised price decisions are separated. Appraised decisions cannot be silently modified.
6. **Low-Confidence Auto-Rejection**: Resolved in ADR 0023. Suggestions below `0.50` confidence are marked rejected and filtered out of standard queue views. No external AI APIs are integrated.
7. **RBAC Rules**: Resolved in ADR 0024. Mapped all 5 knowledge and 7 evidence permissions.
8. **Infrastructure Limitations**: Resolved in ADR 0025. Tracked local PostgreSQL timeout limit; tests will run on in-memory SQLite configurations.
