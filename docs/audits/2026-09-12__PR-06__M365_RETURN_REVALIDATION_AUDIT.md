# PR-06 OneDrive Personal return/revalidation runtime audit

**Task:** `VALORA-PR06-IMPL-001`
**Date:** 2026-09-12
**Branch:** `integration/phase1d-pr06-m365-revalidation`
**Baseline:** `81c6dc987933235b70f50d5e2a29818c01242ba8`
**Disposition:** PASS — LIVE ONEDRIVE PERSONAL ACCEPTANCE COMPLETE

## Outcome

The accepted ADR 0041 and PR-06 implementation contract are implemented for OneDrive Personal delegated `Files.Read`. The runtime now has immutable sealed content/Managed Region baselines, bounded DOCX acquisition and parsing, append-only revalidation observations, exactly five terminal classifications, tenant-safe API boundaries, computed readiness, idempotency, race checks, and PostgreSQL migration/concurrency proof. The D9 canonical adoption producer is production-reachable and live acceptance completed against a real Microsoft Personal account and OneDrive file.

No commit, push, publication, deployment, SharePoint, OneDrive for Business, Graph write scope, PR-07 synchronization, or conflict-resolution behavior was performed.

## Closed residual gaps

1. XML parser hardening rejects NUL-bearing non-UTF-8 OOXML before ElementTree parsing. Regression coverage proves UTF-16, UTF-16LE without BOM, and UTF-16BE without BOM cannot bypass the DTD/entity guard.
2. Existing-binding baseline enrollment is production-reachable through the registered HTTP route. Its server authority resolves an organization-scoped active Document Template and Template Version, a strict `valora-managed-regions-v1` manifest, and project/document lineage through `GeneratedDocument.data_snapshot_hash == DocumentRevision.data_snapshot_digest_sha256`. Exact downloaded DOCX bytes are independently checked against `DocumentRevision.content_checksum_sha256`. The HTTP integration test exercises the real resolver and seal service without monkeypatching authority.
3. Revalidation fails closed when a persisted parser or fingerprint contract version does not match the running implementation.

## Verification evidence

| Gate | Evidence | Result |
|---|---|---|
| Focused PR-05/PR-06 service and API | `python -m pytest tests/test_pr06_m365_revalidation.py tests/test_pr06_m365_revalidation_api.py tests/test_pr06_m365_document_provision.py tests/test_pr05_m365_foundation.py -q` | 64 passed; 13 pre-existing Pydantic deprecation warnings |
| PR-06 PostgreSQL migration/concurrency | isolated temporary databases; `python -m pytest tests/test_pr06_m365_postgresql.py -q` | 3 passed; upgrade/downgrade/upgrade, same-key revalidation concurrency, and same-key producer concurrency proven |
| Prior-schema PostgreSQL regression | PR-05 PostgreSQL plus S13 PR-004 migration checks | 8 passed |
| Repository lint | `python -m ruff check .` | passed |
| Alembic topology | `python -m alembic heads` | single head `a6d9e4c2b8f1` |
| Patch hygiene | `git diff --check` | passed |
| Full backend regression | initial full run | 1,388 passed; 12 environment failures caused by stopped MinIO and a stale shared database revision |
| Failure reconciliation | isolated database plus healthy MinIO, with migration subprocess variables pointed to the same database | all initially failing selections reconciled; no PR-06 regression remained |
| Architecture challenge | AGY `gemini-3.1-pro-high` | READY; no P0, corrections incorporated before implementation |
| Final independent code review | `opencode-go/deepseek-v4.1-flash` | FINAL READY; no unresolved P0/P1 |
| Live OneDrive Personal producer | real delegated connection and `VALORA-PR06-LIVE-20260912.docx` (36,957 bytes) | revision `#1`, immutable binding, sealed baseline, and one Managed Region created atomically |
| Live provider-backed revalidation | Graph stable identity and `eTag` fast path at `2026-09-12T14:00:23.795587Z` | `no_change`; affected regions `[]`; fresh and safe |
| Live PostgreSQL lineage/audit verification | dedicated migrated database `valora_pr06_live_20260912` | nine lineage nodes linked; exact generated/revision/baseline checksum chain; four expected audit events; raw-value/secret scan passed |
| Ephemeral acceptance cleanup | Entra credential list, Graph item lookup, and local resource teardown | PR-06 secret removed while PR-05 secret remained; fixture returned Graph `404`; dedicated database, temporary credentials/artifacts, server, PostgreSQL, and MinIO removed or stopped |

The full-suite result is reported as a split evidence chain rather than misrepresented as one clean rerun: the expensive initial run exposed only local infrastructure contamination, and each failed selection was then rerun under corrected isolated dependencies.

## Live OneDrive Personal disposition

Live acceptance used the Product Owner's Microsoft Personal account, the registered personal-account-only application, delegated `Files.Read`, and a real DOCX synchronized to OneDrive. An active Template Version supplied the strict `valora-managed-regions-v1` authority for the `appraised-value` content control. The authorized D9 producer downloaded the exact provider bytes and atomically created `RenderJob → GeneratedDocument → DocumentRecord → DocumentRevision #1 → CurrentHead → M365RevisionBinding → M365ManagedContentBaseline → ManagedRegion` lineage and three mutation audit facts.

The subsequent provider-backed revalidation observed the same stable drive/item identity and `eTag`, persisted one append-only `no_change` observation plus its audit fact, and computed readiness as fresh and safe. No OneDrive content was written or mutated by the API. The live evidence therefore closes the former eligible-document blocker without fabricating a historical baseline.

## Non-blocking follow-up register

- Freshness TTL scheduling, browser focus-return orchestration, polling, and webhooks remain explicitly deferred by ADR 0041 D7.
- A later hardening slice may normalize volatile content-control properties, constrain bearer-free download redirects to a provider host policy, and make external-relationship `TargetMode` comparison case-insensitive.
- Internal persistence/API enum values use lowercase wire strings while authority documents name the same five semantics in uppercase constants; no sixth value exists.
- Delegated readiness is intentionally connection-owner scoped until a cross-user connection-sharing policy is accepted.

## Gate conclusion

PR-06 engineering and live OneDrive Personal acceptance are complete. The implementation is ready for local commit review. Commit and push remain separately gated by the Product Owner.
