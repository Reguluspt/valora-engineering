# S13-S16 Local Remediation Design and Assignment Packet

**Status:** Owner-authorized for local implementation on 2026-08-26. No push, Draft PR, Ready, merge, or deployment is authorized by this packet.

**Archive evidence:** `archive/local-s13-s16-e826a8c` at `e826a8cfe09000f1a28750cd00c99b325e2744af` preserves the original 19 local commits unchanged.

**Coordination baseline:** `remediation/s13-s16-integration` starts from accepted `origin/main` `d09662c95edfd3515d405e468d215159b46fbf1f`.

**S13-PR-004 baseline rule:** Any S13-PR-004 implementation or correction must remain attributable to the assigned baseline `2af753520ab6b7885555adc5b7945a28d32ee311`. The coordination branch does not supersede that exact-baseline requirement.

## 1. Objective

Preserve the unreviewed S14-S16 work as local evidence while rebuilding only approved, Design Book-aligned slices from a clean baseline. Remove fabricated production data, restore tenant and audit invariants, implement a durable job/worker boundary, replace invented dossier alignment with source-backed DOCX-Excel processing, repair frontend dependency gates, and produce exact-SHA acceptance evidence.

## 2. Design authority

The canonical reading order is:

1. `CODEX.md` and `ENGINEERING_GUARDRAILS.md`.
2. `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md`.
3. Design Book v1.2-final package for core domain, security, Asset Identity, and Document Intelligence boundaries.
4. Design Book v1.3 for Vietnamese-first UX, Astryx, and friendly error presentation.
5. Design Book v1.4 for Adaptive Intake, Asset Identity Memory, paired dossiers, reliable jobs, and bounded automation.
6. ADR 0031-0034 and the S13-S16 remediation plan.

ADR 0031-0034 already define the required domain boundaries. This packet authorizes remediation work; it does not invent a new domain rule or promote an R2 capability. Any required deviation stops for a new owner decision and ADR assessment.

## 3. Local branch architecture

```text
e826a8c original local history
  -> archive/local-s13-s16-e826a8c (frozen, local only)

d09662c accepted origin/main
  -> remediation/s13-s16-integration (local coordination)
       -> R-FE-001
       -> S14-R-001
       -> S15-R-001
       -> S15-R-002
       -> R-GATE-001
```

Mixed commits from the archive are not cherry-picked wholesale. Each slice ports only the necessary files or hunks, begins with a focused failing test where practical, and records its own evidence. Release branches may be created only after all gates pass. Push still requires separate owner authorization.

## 4. Runtime contracts

### R-FE-001 - Production data integrity and frontend dependency gate

- Production API adapters return server data or a typed error. They never substitute fixtures after an authentication, authorization, not-found, network, or server failure.
- Demo data lives behind a separate demo-mode adapter and entry point. Every demo surface displays a permanent Vietnamese demonstration-data banner.
- Production builds must not include demo datasets in their dependency graph.
- Backend HTTP semantics remain accurate, while the UI translates them into actionable Vietnamese messages without exposing status codes, ORM details, identifiers, or stack traces.
- React, React DOM, Astryx, and StyleX versions must have a valid peer graph. Clean `npm ci` is mandatory without `--legacy-peer-deps`; High/Critical dependency findings block the slice.

### S14-R-001 - Tenant-safe identity decisions

- Organization and actor are derived from authenticated server context, never trusted from a client payload.
- Every referenced project, customer, observation, canonical asset, variant, alias, decision, and feedback target is loaded through tenant-scoped access.
- Actor active state, permission, target ownership, workflow state, and expected version are checked before mutation.
- Mutation, authoritative decision, feedback, and required `AuditEvent` commit or roll back in one transaction.
- Database foreign keys, unique constraints, and tenant-compatible constraints protect relationships that can be expressed structurally.
- High-risk cross-tenant attempts are blocked and create the required `SecurityEvent`/`SecurityAuditLog` without leaking protected resource existence.

### S15-R-001 - Reliable job and worker boundary

- Source state and transactional outbox request commit atomically.
- PostgreSQL claim uses an atomic row-lock/compare-and-set boundary, a lease token, expiry, generation, and a unique attempt number.
- Complete/fail/cancel requires the current job state, generation, worker identity, and lease token. Expired or superseded attempts cannot publish a result.
- Delivery is at-least-once; every registered handler is idempotent and duplicate delivery cannot duplicate a domain result.
- Retry/backoff, timeout, cancellation, dead-letter/exception review, correlation, and causation are bounded and auditable.
- Public commands start, cancel, and retry jobs. Parse, extract, map, complete, and fail pipeline commands remain worker-only.

### S15-R-002 - Source-backed DOCX-Excel extraction and alignment

- Immutable, checksummed Excel and DOCX artifacts enter one tenant-scoped `DossierBundle` with explicit source roles.
- Document Intelligence preserves the canonical pipeline: `uploaded -> classified -> parsed -> fields/tables_extracted -> mapped -> review_ready -> reviewed -> committed`.
- Extracted table, row, and cell records keep source locators and parser/extraction versions.
- Alignment compares actual Excel and DOCX rows using STT, section, name, unit, quantity, attributes, and explicit transformations. Order alone is never sufficient.
- Missing, inserted, split, merged, reordered, ambiguous, or conflicting rows become `review_required` or `unresolved`; counts and confidence are never fabricated.
- Supplier quotes, raw working price, proposal price, and final appraised-price candidates remain separate.
- Extraction and alignment create reviewable candidates only. Human-confirmed domain commands control feedback and promotion.

## 5. Non-functional assumptions

- Correctness, tenant isolation, lineage, and auditability take priority over throughput.
- Initial execution may use bounded polling; the contract must remain safe with multiple workers.
- Raw documents and extracted source observations are immutable/versioned.
- Public fixtures are synthetic or anonymized; real customer files are not committed.
- SQLite is development evidence only. PostgreSQL is mandatory for concurrency and constraint acceptance.
- The deterministic/manual path remains complete when AI is unavailable.

## 6. Verification gates

### Slice gates

- R-FE-001: production failure tests, demo-boundary tests, Vietnamese error tests, lint, component tests, production build, clean `npm ci`, and dependency audit with zero High/Critical findings.
- S14-R-001: inactive actor, missing permission, cross-tenant, wrong ownership, stale version, duplicate command, transaction rollback, PostgreSQL FK/constraint, and security-event tests.
- S15-R-001: competing claims, reclaim after expiry, stale-lease rejection, duplicate delivery, unique attempts, cancellation, timeout, retry, dead-letter, stale-generation, and end-to-end worker tests.
- S15-R-002: real parser fixture, source-locator assertions, missing/inserted/split/merged/reordered rows, unit/rounding transformations, no order-only match, no fixed confidence/count, and mandatory review tests. PD-001 counts may be asserted only from the actual approved fixture, never manufactured.

### Final gate

One exact SHA must pass backend/frontend/worker tests, Ruff/lint/build, Alembic head/history, PostgreSQL integration/concurrency, MinIO/object-storage integration, Docker image/Compose smoke, dependency audit, secret/security scan, and `git diff --check`. Target integration tests may not be skipped. Every remaining skip and limitation is reported explicitly and is not called PASS.

## 7. Decision log

- **D-001:** Keep S14-S16 locally but do not release them until remediation and evidence gates pass.
- **D-002:** Do not push the original 19 commits.
- **D-003:** Use a clean baseline and selectively rebuild scoped slices.
- **D-004:** ADR 0031-0034 remain authoritative; use this assignment/evidence packet rather than inventing replacement ADRs.
- **D-005:** Freeze the original 19 commits as immutable local evidence.
- **D-006:** Fail closed and display the real state; never turn a failure into fabricated success data.
- **D-007:** Only test evidence executed on the exact reported SHA is release evidence.
- **D-008:** Apply the Design Book corrections: exact S13-PR-004 baseline, Vietnamese-friendly UI error masking, security logging for high-risk tenant violations, and the canonical Document Intelligence pipeline.

## 8. Explicit non-goals

- No external AI provider integration or R2 capability promotion.
- No AI/system approval, active-knowledge activation, final price, QC, signature, or report release.
- No bulk SQL into active knowledge.
- No unrelated refactor or visual redesign.
- No push, PR state change, merge, deployment, credential change, or production-data operation.

## 9. Known starting limitations

- The local Docker daemon was unavailable during the initial audit; PostgreSQL, MinIO, container build, and Compose evidence must be rerun when the daemon is available.
- The archived frontend currently has two stale AppShell tests, an invalid peer-dependency graph, and two High dependency advisories.
- The archived backend test suite passes locally with PostgreSQL/MinIO skips; those skips are not acceptance evidence.
