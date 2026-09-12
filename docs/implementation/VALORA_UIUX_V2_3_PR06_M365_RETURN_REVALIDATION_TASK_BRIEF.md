# VALORA UI/UX v2.3 — PR-06 M365 Return/Revalidation Task Brief

**Task:** `VALORA-PR06-IMPL-001` **Status:** IMPLEMENTED — LIVE ONEDRIVE PERSONAL ACCEPTANCE COMPLETE **Date:** 2026-09-12 **Branch:** `integration/phase1d-pr06-m365-revalidation` **Baseline:** `81c6dc987933235b70f50d5e2a29818c01242ba8`

## Objective

Implement the smallest truthful OneDrive Personal Return/Revalidation slice, including the owner-authorized canonical producer needed to create a real eligible first revision/binding/baseline lineage. Revalidation appends a tenant-safe observation and derives exactly one accepted semantic result without mutating the Document Revision, its immutable binding, or the OneDrive file.

## Goal chain

```text
Sealed bind-time DOCX + Managed Region baseline
→ provider-backed return observation
→ five-way canonical classification
→ computed freshness/readiness
→ safe PR-07 sync/conflict input without silent overwrite
```

For live acceptance, the prerequisite path is:

```text
Active template/version + bounded Data Snapshot + existing OneDrive DOCX
→ atomic RenderJob/GeneratedDocument/canonical revision/binding/baseline lineage
→ provider-backed revalidation
```

## Authority

- `CODEX.md`
- `ENGINEERING_GUARDRAILS.md`
- `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md`
- `docs/design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.3.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.3_M365_RETURN_REVALIDATION_CONTRACT_ADDENDUM.md`
- `docs/design/VALORA_UIUX_HANDOFF_v2.3_M365_RETURN_REVALIDATION_VISUAL_BASELINE_ADDENDUM.md`
- `docs/adr/0040-onedrive-delegated-integration-and-file-binding.md`
- accepted `docs/adr/0041-onedrive-personal-return-revalidation-observations.md`

Repository authority outranks recall, provider suggestions, visual shorthand, and legacy endpoint behavior.

## Multi-provider execution plan

The Product Owner fixed the provider roster for PR-06 on 2026-09-12:

| Gate | Provider route | Mode | Required output |
| --- | --- | --- | --- |
| Independent repository survey | OpenCode Go `opencode-go/deepseek-v4.1-flash` | read-only | file map, architecture gaps, risks, and `READY` or `BLOCKED` |
| Architecture/security challenge | AGY `gemini-3.1-pro-high` | plan/read-only | ADR 0041 findings classified P0-P2 |
| Runtime implementation | Codex | sole writer | bounded diff inside the owner-accepted allowlist |
| Independent implementation review | OpenCode Go `opencode-go/deepseek-v4.1-flash` | read-only | exact file/line findings classified P0-P2 |
| Final acceptance | Codex | gate | one `PASS`, `FAIL`, or `BLOCKED` verdict with command evidence |

No Claude or Kimi model may be used for PR-06. DeepSeek V4 Flash is superseded for new work by DeepSeek V4.1 Flash. Gemini must run through AGY. Provider liveness or quota failure is reported honestly; it must not be hidden by silently substituting a prohibited provider. External providers do not write repository files, approve their own output, or replace command/test evidence.

## Survey result

DeepSeek V4.1 Flash completed a read-only survey against `81c6dc987933235b70f50d5e2a29818c01242ba8`.

### Verified repository facts

1. PR-05 provides canonical `DocumentRecord`, immutable `DocumentRevision`, explicit current head, encrypted credential vault, OneDrive Personal connection, stable drive/item identity, and immutable `M365RevisionBinding`.
2. The Graph port and adapter currently read drive/item metadata only; current observations set `graph_version_id` to `None` and do not download content.
3. No Managed Region definition, baseline, extraction, fingerprint, comparison, revalidation observation, or document readiness runtime exists.
4. The accepted authority requires exactly five semantic results and forbids treating provider failure as no change.
5. Metadata alone cannot distinguish `EXTERNAL_CHANGE_OUTSIDE_MANAGED` from `EXTERNAL_CHANGE_IN_MANAGED`.
6. Revalidation must not create or mutate a Document Revision or overwrite its immutable M365 binding.
7. External Graph reads must finish before the short locked transaction; actor, tenant, current head, binding, baseline, and idempotency must be rechecked before commit.
8. The current Alembic head is `f4c8d2a1b7e9`.
9. Live `origin/main` is `93f50f9ac81ab93e2361fffa8b71fc3bcfca57f6`; PR-06 intentionally starts from the local PR-05 commit because it is the required foundation.

### Survey disposition

The initial survey returned `BLOCKED` pending Product Owner acceptance of ADR 0041 and the exact PR-06 contract. The Product Owner accepted both on 2026-09-12 and later authorized D9, closing that historical blocker before runtime implementation began.

## Authorized implementation boundary

PR-06 may add:

- immutable sealed content-baseline and Managed Region fingerprint persistence attached to a PR-05 binding;
- proof-based enrollment for an existing binding and atomic baseline creation for new supported bindings;
- bounded DOCX acquisition, package validation, Managed Region extraction, canonicalization, and digest ports/adapters;
- Graph metadata/content read support using existing delegated `Files.Read` access;
- append-only `M365RevalidationObservation` persistence;
- a tenant-safe explicit revalidation application service and read aggregate;
- computed freshness/readiness facts scoped to the current Document Revision and binding;
- internal/public API endpoints only as required for explicit `Kiểm tra thay đổi` and readback;
- sanitized audit, idempotency, concurrency, migration, parser, service, API, and PostgreSQL proofs;
- current-state authority updates only after owner acceptance and implementation evidence.
- one strict OneDrive adoption producer that creates first canonical document lineage atomically after provider verification, without Graph write.

## Proposed implementation allowlist

- `backend/alembic/versions/<pr06_revision>_create_m365_revalidation_observations.py`
- `backend/app/db/__init__.py`
- `backend/app/modules/document_workspace/**` only if needed to expose current immutable revision facts; no revision mutation semantics
- `backend/app/modules/m365_integration/domain/graph_gateway.py`
- `backend/app/modules/m365_integration/domain/managed_regions.py`
- `backend/app/modules/m365_integration/infrastructure/graph_adapter.py`
- `backend/app/modules/m365_integration/infrastructure/docx_managed_regions.py`
- `backend/app/modules/m365_integration/application/bind_document_service.py` only for accepted atomic baseline sealing on new bindings
- `backend/app/modules/m365_integration/application/revalidation_service.py`, including the proof-based enrollment recovery command for existing PR-05 bindings
- `backend/app/modules/m365_integration/application/provision_document_service.py`
- `backend/app/modules/m365_integration/models.py`
- `backend/app/api/m365.py`
- `backend/app/main.py` only if bounded route registration is required
- `backend/tests/test_pr06_m365_revalidation.py`
- `backend/tests/test_pr06_m365_revalidation_api.py`
- `backend/tests/test_pr06_m365_postgresql.py`
- `backend/tests/test_pr06_m365_document_provision.py`
- `backend/tests/fixtures/pr06_m365/**`
- `backend/tests/test_s13_pr_004_column_mapping_postgresql.py` only to register PR-06 tables as later-schema artifacts in the isolated prior-migration parity test
- `backend/pyproject.toml` only if an accepted bounded DOCX/XML dependency is strictly necessary after dependency review
- `docs/adr/0041-onedrive-personal-return-revalidation-observations.md`
- `docs/implementation/VALORA_UIUX_V2_3_PR06_M365_RETURN_REVALIDATION_TASK_BRIEF.md`
- `docs/implementation/VALORA_UIUX_V2_3_PR06_M365_RETURN_REVALIDATION_CONTRACT.md`
- `docs/audits/2026-09-12__PR-06__M365_RETURN_REVALIDATION_AUDIT.md`
- current-state authority files only when needed to record the exact accepted and verified PR-06 disposition

Any other production or test file requires coordinator review before edit.

## Required implementation semantics

- OneDrive Personal and delegated `Files.Read` remain the only provider/account boundary.
- Revalidation starts only for the actor's tenant-safe current Document Revision, exact immutable binding, active connection, and eligible sealed content baseline.
- Missing/foreign identifiers fail closed without leaking existence.
- New supported bindings seal exact DOCX and versioned Managed Region fingerprints atomically with the binding after external reads.
- Existing bindings may be enrolled only with exact checksum, metadata, manifest, and parser-safety proof; no current-file-as-history shortcut.
- Metadata may short-circuit a trustworthy no-change result but may not localize content changes.
- Changed/ambiguous metadata requires bounded content download and canonical Managed Region comparison.
- Exactly five terminal classifications are exposed; eligibility and in-flight processing remain separate technical states.
- Every terminal attempt appends one immutable observation and one sanitized audit fact atomically.
- Latest/current revalidation is selected by current revision and binding lineage, not timestamp alone.
- Readiness is computed from authoritative current facts; no mutable readiness projection is introduced.
- External token/Graph/content work finishes before the database transaction; the transaction rechecks permission, tenant, head, binding, baseline, and idempotency.
- Enrollment and revalidation never create or mutate a VALORA Document Revision. The separately authorized canonical producer may create revision `#1` only together with its RenderJob, GeneratedDocument, current head, immutable binding, sealed baseline/regions, and audit facts in one transaction.
- Revalidation never writes, renames, moves, deletes, shares, or rebinds a OneDrive file.

## Forbidden scope

- no OneDrive for Business, work/school-account flow, SharePoint site, document library, or `Sites.Selected` integration;
- no Graph application permissions, tenant-wide access, or delegated write consent;
- no file upload, overwrite, rename, move, delete, sharing, restore, or version mutation;
- no automatic rebind by filename/path and no mutation of an immutable binding;
- no PR-07 sync write, three-way conflict decision, conflict-resolution UI, or protected value snapshot;
- no polling scheduler, webhook, delta query, or change-notification processing;
- no focus-return frontend orchestration, visual redesign, fake Word editor, or Export PDF;
- no mutable document-readiness source of truth and no new workflow checkpoint;
- no automatic Document Revision creation outside the explicit D9 producer, release mutation, publishing, or completion increase;
- no unrestricted DOCX text, raw Managed Region values, access/refresh token, client secret, provider exception, or short-lived download URL in database, API, audit, or logs;
- no invented Managed Region ownership convention when an authoritative definition set is absent;
- no unrelated refactor, dependency upgrade, legacy document endpoint rewrite, or scope expansion;
- no commit, push, pull request publication, merge, deploy, tag, or release without separate authorization.

## Required verification after implementation

- focused classification matrix for all five canonical outcomes, including outside-only, inside-managed, mixed changes, rename/path drift with stable identity, replacement/unresolved identity, and access failure;
- proof that changed tags cannot directly select either managed-change class;
- baseline-enrollment tests for exact checksum/metadata equality and fail-closed legacy mismatch;
- adversarial DOCX fixtures for duplicate/missing region keys, malformed XML, external relationships, path traversal, decompression bombs, oversize content, parser-contract mismatch, and unsupported structures;
- tenant isolation and permission tests before any provider call;
- Graph timeout, throttling, expired consent, missing item, metadata/content race, partial download, and checksum mismatch tests;
- idempotent replay, conflicting key reuse, concurrent equivalent attempts, current-head race, binding race, and stale-lineage rejection;
- proof that observation plus AuditEvent commits atomically and that commit failure leaves neither partial fact;
- proof that no terminal/provider failure mutates Document Revision, binding, baseline, OneDrive content, or workflow completion;
- PostgreSQL migration upgrade/downgrade/upgrade with zero skips, constraints, uniqueness, and concurrent writer coverage;
- API serialization and log/audit redaction tests for tokens, URLs, raw content, raw region values, and provider exceptions;
- full relevant backend suite, Ruff, Python compilation, Alembic single-head check, dependency/security review, and `git diff --check`;
- independent review of the exact final delta and a final `PASS`, `FAIL`, or `BLOCKED` gate;
- live OneDrive Personal acceptance only after a real binding has a provable eligible baseline; live testing remains read-only.

## Stop conditions

Stop runtime edits when any of these becomes unresolved:

- ADR 0041 or the implementation contract is not owner-accepted;
- no authoritative Managed Region definition/normalization contract exists for the target document;
- an existing binding cannot prove equality with its immutable Document Revision and bind-time observation;
- classification would require inferring managed/outside scope from Graph metadata alone;
- provider/content/parser failure would need to be represented as success or `NO_CHANGE`;
- safe bounded DOCX parsing cannot be implemented without unaccepted dependency or storage expansion;
- implementation requires OneDrive write permission, OneDrive Business, SharePoint, PR-07 conflict/value snapshots, or any Document Revision outside the explicit atomic D9 producer;
- sensitive content or credential material would enter persistence, API, logs, or audit;
- transaction correctness would require holding a database lock across Graph/content I/O.

## Current disposition

`PASS — LIVE ONEDRIVE PERSONAL ACCEPTANCE COMPLETE`. DeepSeek V4.1 Flash challenged the extension and identified the missing `RenderJob`/`GeneratedDocument` lineage and superseded scope clauses; both were resolved by ADR 0041 D9 and this amended brief. Gemini 3.1 Pro High returned `READY` subject to pre-download size and pre-provider idempotency gates, both implemented and verified. The D9 producer created authoritative revision/binding/baseline lineage for a real OneDrive Personal DOCX, and provider-backed revalidation returned `NO_CHANGE` with fresh/safe readiness. Acceptance resources and the PR-06 Entra secret were cleaned after evidence capture. Commit, push, publication, deployment, and release remain separately gated.
