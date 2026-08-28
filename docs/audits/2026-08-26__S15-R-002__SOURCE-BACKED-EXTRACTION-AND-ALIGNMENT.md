# S15-R-002 — Source-Backed Extraction and Alignment Evidence

Date: 2026-08-26

Branch: `remediation/s15-r-002-source-backed-alignment`

Implementation commit: `10d8dcc`

Publication state: local only; not pushed

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
| Focused S15 dossier/job/extraction/alignment tests | 17 passed before final reliability refinement; final affected slice 12 passed |
| Worker lint and tests | Ruff PASS; 5 passed |
| Full backend test suite | 1007 passed, 68 skipped, 0 failed |
| Backend Ruff | PASS |
| Security policy/secret scan | PASS |
| Backend project dependency audit | no known vulnerabilities |
| Worker project dependency audit | no known vulnerabilities |
| Migration graph | one head at `d2e3f4a5b6c7` |
| S15 migration SQL slice | PostgreSQL offline SQL generation PASS |
| Frontend clean install | `npm ci` PASS; 177 packages audited; 0 vulnerabilities |
| Frontend lint/tests/build | lint PASS; 86 passed; production build PASS; demo-marker assertion PASS |
| PostgreSQL constraint/concurrency tests | BLOCKED locally: no PostgreSQL service on port 5432; CI tests fail closed when `CI=true` lacks the expected head |
| MinIO integration | BLOCKED locally: Docker Desktop Linux engine pipe is absent |
| Docker image/build/runtime | BLOCKED locally: Docker Desktop Linux engine pipe is absent |

The full backend count above was measured immediately before the final small permanent-failure
routing refinement. The directly affected backend and worker slices were rerun after that change.
The same-SHA full suite is repeated after the evidence commit before integration acceptance.

## Exit decision

S15-R-002 is an acceptable local implementation candidate, not a publication or deployment
approval. Final acceptance still requires the exact integration SHA to pass PostgreSQL, MinIO and
Docker gates. Only after those gates are green may the remediation history be reconstructed into
reviewable, scope-correct pull requests.
