# PR-07 app-owned immutable storage policy decision

**Start time:** 2026-09-19, Asia/Saigon
**Status:** complete — action recorded in ADR 0043
**Supersedes:** [initial storage fallback research](pr07-storage-fallback-options.md)

## Initial purpose

Resolve the initial fallback research after the Product Owner approved app-owned immutable document
storage, then record the smallest policy baseline required before provider-neutral validation. This
decision must preserve ADR 0042/D6 as historical authority for the blocked OneDrive direct-write path
and must not select or call a production cloud provider.

## Strategy

1. Separate the OneDrive G3 closeout from the new authoritative-storage direction.
2. Lock user-copy, retention, deletion, encryption and recovery policy without inventing a provider.
3. Reconcile the policy with existing `DocumentRevision`/CurrentHead capability and the proposed
   `DocumentBlobStore` contract.
4. Authorize only the reversible local fake validation needed before an isolated provider spike.

## Checklist

- [x] Select the OneDrive export interaction model.
- [x] Set finalized-revision retention, legal-hold and purge rules.
- [x] Set encryption/key-ownership and environment-separation targets.
- [x] Set architecture RPO/RTO targets.
- [x] Preserve AWS S3 as spike-only and leave production provider/residency unselected.
- [x] Reconcile ADR 0042, ADR 0043, the storage contract, plan and acceptance matrix.
- [x] Keep real customer data, cloud credentials and live requests outside the next task.

## Result

The Product Owner accepted this baseline:

- **OneDrive Model A:** an export is a derived artifact/external working copy. External edits do not
  automatically change CurrentHead, create a revision or start bidirectional sync.
- **Retention:** finalized valuation-document revisions retain for at least ten years from the
  applicable record/release business milestone. Legal hold blocks purge.
- **Deletion:** finalized revisions have no ordinary hard-delete path. Any post-retention physical
  purge is explicit, authorized, audited and policy-driven. Unfinalized candidates use a separate
  lifecycle.
- **Encryption:** production uses server-side encryption with VALORA-controlled customer-managed
  keys and separate production/non-production boundaries. The AWS reference is SSE-KMS; per-tenant
  keys are not required by this task.
- **Recovery targets:** architecture target `RPO <= 15 minutes`; `RTO <= 4 hours`.
- **Provider scope:** AWS S3 is only the later isolated technical-spike candidate. Production provider
  and data-residency region are not selected.
- **Data boundary:** local fake validation and the future spike use no real customer document or
  valuation record.

### Verification

The baseline was cross-checked against the repository's implemented models. `DocumentRecord`,
append-only `DocumentRevision` and explicit `DocumentRevisionCurrentHead` exist. The
`DocumentBlobStore`, storage intent/candidate/event/state/binding and N+1 storage finalizer remain
proposed and are not described as implemented.

The accepted documents preserve ADR 0042/D6 and G3 Option A for direct OneDrive replacement. They
open no AWS credential, request, adapter, production migration, PR-08, deployment or release.

### Corroborating links

- [ADR 0042](../adr/0042-onedrive-personal-protected-values-and-sync-write-transactions.md)
- [Accepted ADR 0043](../adr/0043-app-owned-immutable-document-storage.md)
- [Document Blob Storage contract](../implementation/VALORA_DOCUMENT_BLOB_STORAGE_CONTRACT.md)
- [Completed architecture task](../plan/done/valora-storage-arch-001.md)
- [Provider comparison](valora-storage-provider-selection.md)
- [G3 decision](../plan/done/pr07-g3-architecture-decision.md)

## Decision

**Action:** close `VALORA-STORAGE-ARCH-001` with the accepted baseline above and open bounded local
task `VALORA-STORAGE-FAKE-001`. That task may implement only the provider-neutral port, smallest
supporting persistence/service flow, deterministic fake and T1–T14 tests. It may not call AWS or any
other cloud, use real customer data, select production provider/residency, implement OneDrive write,
perform a production rollout/migration, open PR-08, deploy or release.

The next cloud gate remains `VALORA-STORAGE-S3-SPIKE-001`, which can only be proposed after T1–T14
and independent review pass. No live spike is authorized by this decision.

Cross-references:

- [Initial research record](pr07-storage-fallback-options.md)
- [Acceptance matrix](../implementation/VALORA_UIUX_V2_3_PR00_PR13_FEATURE_ACCEPTANCE_MATRIX.md)
