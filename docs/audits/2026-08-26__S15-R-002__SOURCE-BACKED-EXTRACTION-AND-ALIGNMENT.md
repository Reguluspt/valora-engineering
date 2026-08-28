# S15-R-002 — Source-Backed Extraction and Alignment Evidence

Date: 2026-08-26; PostgreSQL/MinIO/Docker closure: 2026-08-27; stack rebase verification: 2026-08-28

Branch: `release/r-gate-001-final-acceptance`

Audited implementation commits: `10d8dcc`, `b9094d2`

Evidence baseline commit: `002d0626b0d40f34801640bcd58e42070793ac4f`
PR #26 exact review head is recorded in the PR body. This document is deliberately
self-reference-safe: changing it changes the Git head, so dynamic exact-head values are
recorded in the PR body and audit comment for the resulting SHA.
Review base: `main` at `b5b476d1ac8144d102214f0dc240c9c1bbda9c64`

Publication state: PR #26 remains `OPEN / DRAFT` until the exact-head audit and CI gate pass;
no merge or deployment approval

Evidence-sync note: this document records the audited implementation head. A documentation-only
successor may update the file, but cannot embed its own final SHA without changing that SHA;
the current PR head and same-head CI run are recorded in the PR body.

## Authority and scope

This slice implements the next bounded part of ADR 0032 and ADR 0034. It replaces the
unreleased S15 placeholder extraction/alignment behavior; it does not promote bootstrap
knowledge, activate S16 automation, publish a branch, or modify the original nineteen local
commits.

The repository contains no customer DOCX/XLS/XLSX fixture. Verification therefore uses newly
generated, valid binary DOCX and XLSX test artifacts with reordered report rows and a deliberate
unit conflict. Production execution reads the verified object identified by the dossier source
record; it does not substitute the test artifacts or any fabricated row set.

## Source-backed extraction boundary

- The worker reads the exact object-storage key owned by the tenant-qualified dossier source.
- Object metadata size, streamed byte count and SHA-256 are checked against the immutable source
  record before parsing.
- XLS/XLSX files use the fail-closed S13 workbook adapters. DOCX files are validated as bounded,
  non-encrypted Open XML archives and parsed with `python-docx`.
- PDF extraction fails explicitly with `pdf_extraction_not_implemented`; it is not replaced by
  demonstration data.
- Extraction preserves raw cell values, normalized matching fields, source checksums, parser and
  schema versions, and cell/row/table locators. DOCX page numbers are labeled as rendered-break
  estimates rather than claimed as authoritative pagination.
- Immutable extraction snapshots are idempotent only for the exact source checksum, parser,
  parser version and extraction schema version.
- Snapshot/table/row writes and `DossierSourceExtracted` audit evidence commit atomically after
  a second source fingerprint check and an exact live lease/generation check.

## Content-based paired alignment

- Alignment is bound to one exact Excel extraction snapshot and one exact DOCX report snapshot
  from the same organization and dossier.
- Candidate selection uses STT, asset name, unit, quantity, technical attributes and a weak order
  tie-break. Order is evaluated only after an STT or name identity signal exists.
- Reordered technical rows are matched by content. Unit, quantity/rounding and ambiguous-match
  conditions are retained as review conflicts.
- Technical, quote-comparison and final-result candidates remain separate and retain their own
  locators and score basis.
- The engine creates only `candidate`, `review_required` or `unresolved` rows. It never writes
  `confirmed` or `rejected`, never marks the dossier aligned, and never promotes active knowledge.
- Exact snapshot-pair reruns are idempotent and write only one alignment run/audit record.

## Tenant, ownership and database integrity

- New extraction and alignment records carry organization and dossier ownership.
- Composite foreign keys bind source, snapshot, table, row, job, alignment run and human reviewer
  to the same tenant/dossier boundary.
- Database checks enforce source/table roles, checksums, generation tokens, counts, confidence,
  review state and reviewer/timestamp shape.
- PostgreSQL JSONB is used for raw cells, normalized fields, locators, score basis and conflicts.
- The migration chain is linear:
  `b0c1d2e3f4a5 -> c1d2e3f4a5b6 -> d2e3f4a5b6c7`.
- The model-required `updated_at` columns and check constraints are reconciled directly in the
  origin module migrations (`e7f8a9b0c1d2` and `f8a9b0c1d2e3`) with non-null server defaults,
  preserving a clean single linear head at `d2e3f4a5b6c7`.

## Reliable consumer

- The production registry now owns real `document_extraction` and `dossier_alignment` handlers.
- Handlers use the same injected session factory as the worker and an explicit object-storage
  dependency, preserving production configuration while allowing end-to-end proof.
- Jobs remain protected by claim/attempt/generation fencing and heartbeat lease renewal.
- Typed permanent failures, including checksum and contract failures, go directly to dead letter;
  retryable storage failures and unexpected runtime failures follow bounded retry/backoff.
- The end-to-end worker test claims and completes two real-binary extraction jobs, enqueues the
  resulting exact snapshot pair, runs alignment, and verifies audit and no-auto-confirm behavior.

## Local verification

| Gate | Result |
| --- | --- |
| Initial real-service failure set | 11 PostgreSQL failures reproduced; all 11 corrected and rerun successfully |
| Worker lint and tests | Ruff PASS; 5 passed |
| Full backend test suite | 1075 passed, 0 failed on PostgreSQL/MinIO (`CI=true`) |
| Backend Ruff | PASS |
| Security policy/secret scan | PASS |
| Backend project dependency audit | clean runner environment: no known vulnerabilities |
| Worker project dependency audit | clean runner environment: no known vulnerabilities |
| Migration graph and fresh upgrade | one head at `d2e3f4a5b6c7`; empty PostgreSQL upgraded through the full chain |
| Frontend clean install | `npm ci` PASS; 177 packages audited; 0 vulnerabilities |
| Frontend lint/tests/build | lint PASS; 86 passed; production build PASS; demo-marker assertion PASS |
| PostgreSQL constraint/concurrency tests | PASS at head `d2e3f4a5b6c7`, including mapping, identity and SKIP LOCKED claim proofs |
| MinIO integration | PASS; bucket `valora-local` verified and real XLSX/DOCX objects streamed and checksummed |
| Docker exact-revision build | Prior clean build artifact (source/Docker context unchanged by subsequent documentation-only commits): backend `sha256:9a4f88b29b2554e1c6b14af2d641da11727783ce1923a10a6832ce04147925d9`, worker `sha256:e9eff4a5b0657d1dd8a9299024fd40bb3d7ecc3bd8984b3ba74dbe58d58e7724`, frontend `sha256:773d4287e79830bfc47e861f044592c4298ede71e7a3fdb80e0ae5ea2748dbdb`; each carried `org.opencontainers.image.revision=a8972d12816b1f6ba4c7e35f8bdacce724c3562a` and was rebuilt from the identical Docker context |
| Docker exact-head label protocol | The Dockerfiles and Compose args bind `org.opencontainers.image.revision` to `VALORA_IMAGE_REVISION`; exact-head rebuild is required when the daemon is available. The PR body records the exact reviewed Git SHA and the prior artifact provenance; no digest is relabeled or represented as a build of a different SHA |
| Docker isolated runtime | Prior clean run used Compose project `valora-docker-audit`, fresh project-scoped PostgreSQL/MinIO volumes and an isolated network; backend/frontend HTTP 200, zero schema drift and registered production worker handlers; the existing `valora_postgres_data` volume was not modified |
| Container worker smoke | two extraction jobs plus one paired-alignment job completed; one attempt and generation per job; all attempts succeeded |
| Container business output | Excel and DOCX snapshots created; one `paired-content-v1` candidate at confidence `1.0000`; no automatic review confirmation |
| Container audit output | 3 each of `TaskJobQueued`, `TaskJobClaimed`, `TaskJobCompleted`; 2 `DossierSourceExtracted`; 1 alignment audit |

The project-wide `pip-audit` command must be run from the clean CI environment. The shared host
Python installation contains unrelated applications and reports unrelated packages such as Flask,
GitPython and Pillow; a clean environment recreated from the backend and worker project metadata
reported no known vulnerabilities for either job.

ADR 0035 (Proposed) records the separate baseline reconciliation. The prior clean run upgraded a
fresh PostgreSQL database to `d2e3f4a5b6c7` and `alembic check` reported no new upgrade operations;
the exact-head CI/audit decision remains authoritative for PR #26. The PR body carries the exact
head, CI run, prior image IDs, labels, migration current/check output, health checks and worker
smoke output without pretending that a documentation-only commit rebuilt those images.

## Exit decision

S15-R-002 satisfies the repository CI workflow and PostgreSQL/MinIO application gates as a Draft
implementation candidate at the audited implementation head. Exact-revision Docker acceptance is
recorded on PR #26. This is not a merge or deployment approval; ADR 0035 remains Proposed until
the owner accepts it.
