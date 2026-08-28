# S15-R-001 — Dossier and Reliable Job Remediation Evidence

Date: 2026-08-26; PR #24 rebase verification: 2026-08-28

Branch: `release/s15-r-001-reliable-jobs`

Audited implementation head: `65e206a5d3f12192bd8cce0a6ccd422a223986a0`

Evidence-sync state: this document is maintained by a documentation-only successor commit;
the current PR head and same-head CI run are recorded in the PR body because a commit cannot
embed its own SHA without changing that SHA.

Review base: `main` at `2f95920cb48bd260b4235f883361cc0e4b4fe9d3`

Publication state: PR #24 is `OPEN / DRAFT`; no merge or deployment approval

## Authority and scope

This slice is bounded by:

- ADR 0032 for the paired dossier aggregate, immutable source roles and source locators;
- ADR 0034 for durable jobs, append-only attempts, lease expiry, retry, cancellation,
  stale-generation rejection and idempotent consumers;
- the Design Book v1.4 requirement that long-running extraction work use a reliable job
  boundary before production automation;
- the local S13-S16 remediation design and the instruction not to publish the original
  nineteen local commits.

The worker business-handler registry remains intentionally empty in this slice. The runtime is
real and tested, but this commit must not be deployed by itself: source-backed DOCX/Excel
handlers are registered only in the following S15 extraction/alignment slice. This prevents a
placeholder handler or fabricated result from entering the production path.

## Corrected dossier invariants

- Replaced invented `excel_workbook` / `word_report` roles with ADR 0032 roles.
- Requires exactly one `customer_asset_list` and one `final_appraisal_report`; supporting
  evidence roles may repeat where the domain permits it.
- Requires a customer and permits an optional project only when it belongs to the same customer
  and tenant.
- Reloads the active actor and organization from persistence and requires
  `document_intelligence:job:create`.
- Rejects client-shaped source dictionaries; the command accepts bounded verified-source
  metadata with positive size, lowercase SHA-256, safe object key and role-compatible extension.
- Compares the complete command intent on bundle-code replay and returns `409` on mismatch.
- Adds tenant-qualified customer, project, creator and bundle/source foreign keys plus database
  checks and partial uniqueness for the primary pair.
- Writes the successful `DossierBundleCreated` audit event atomically and durably records denied
  tenant/authorization checks.

## Corrected reliable-job invariants

- Enqueue reloads and authorizes the actor, validates the dossier/source ownership target,
  rejects client tenant/actor fields and stages job plus audit in the caller-owned transaction.
- Idempotency compares actor, type, normalized payload, retry policy and correlation/causation
  metadata; a reused key with different intent returns `409`.
- PostgreSQL claims use row locking with `SKIP LOCKED`; claims create one append-only attempt and
  increment a generation token.
- Active leases fence other workers, same-worker claim replay returns the current attempt, and
  expired attempts are closed as `timed_out` before reclaim.
- Completion and failure require an exact organization, worker, attempt, generation and live
  lease match. Exact completion/failure replay is idempotent; conflicting or stale replay is
  rejected and audited.
- Failure schedules deterministic exponential backoff or transitions to dead letter at the
  bounded maximum-attempt count.
- Lease renewal and authorized cancellation are implemented; cancellation fences an in-flight
  attempt.
- Job payload/result use PostgreSQL JSONB, and the schema enforces status, lease, completion,
  cancellation, attempt bounds and tenant-qualified ownership.

## Worker and build path

- Replaced the Sprint 0 log-only worker with a database-backed claim/dispatch/heartbeat/finalize
  loop.
- Each handler receives immutable job/attempt/generation context; a background heartbeat renews
  long-running leases through a separate session.
- Unsupported or failing handlers are recorded through the reliable failure path rather than
  acknowledged or supplied with placeholder results.
- Added a worker image, Compose service, pinned MinIO image, backend/worker package discovery and
  CI installation of the backend contract into the worker environment.
- Repaired the backend Dockerfile so package installation occurs after source is present and uses
  the CI-supported Python 3.12 runtime.

## Migration graph

- Renamed the colliding S15 migrations so the local chain is linear:
  `e7f8a9b0c1d2 -> f8a9b0c1d2e3 -> a9b0c1d2e3f4 -> b0c1d2e3f4a5`.
- The corrective migration refuses to reinterpret any existing unreleased dossier/job rows. It
  must run only while those new S15 tables are empty; otherwise it fails and requires explicit
  export/review.
- `alembic heads`: exactly one head, `b0c1d2e3f4a5`.
- Offline SQL generation for `a9b0c1d2e3f4:b0c1d2e3f4a5`: PASS.
- Full-chain offline SQL still stops in the historical migration `7519c3d1f364` because its JSON
  seed has no literal renderer. Online PostgreSQL migration is the authoritative CI gate and was
  not available locally.

## Local verification

| Gate | Result |
| --- | --- |
| Focused dossier/job tests | 11 passed |
| PostgreSQL-only S15 tests | 2 skipped locally; configured to fail, not skip, when `CI=true` lacks PostgreSQL or the expected head |
| Worker lint and tests | Ruff PASS; 3 passed |
| Full backend test suite | 1001 passed, 67 skipped, 0 failed |
| Backend Ruff | PASS |
| Security policy/secret scan | PASS |
| Migration graph | one head at `b0c1d2e3f4a5` |
| S15 migration SQL slice | PASS |
| Compose configuration parse | PASS |
| Docker build/runtime | BLOCKED locally: Docker Desktop Linux engine pipe is absent |
| PostgreSQL concurrency/constraint evidence | BLOCKED locally: no PostgreSQL service; tests are committed for CI |
| MinIO integration | BLOCKED locally with Docker daemon; remains a same-SHA CI gate |

## PR #24 rebase verification

- The branch was rebased onto the newly merged `main` commit shown above and force-pushed
  with `--force-with-lease`.
- GitHub Actions run `33160232110` passed all four jobs (`committed-whitespace`, `backend`,
  `worker`, `frontend`) at the audited implementation head. The documentation-only successor
  must also pass the same four gates before Ready review.
- A focused rerun on the rebased stack tip (`release/r-gate-001-final-acceptance`) reports
  `10 passed, 3 skipped`; the three skips are PostgreSQL-only tests in the local environment.
  The implementation-head PR #24 CI run executed the PostgreSQL migration, constraint and concurrency
  gates successfully.
- PR #24 remains intentionally Draft; source-backed extraction/alignment handlers are supplied
  by downstream PRs #25 and #26, not this branch.

## Exit decision

At the audited implementation head plus its documentation-only evidence successor, S15-R-001 is
a Draft implementation candidate. The current PR head must retain green same-head CI before
Ready review. This is not a merge or deployment approval. Source-backed document extraction and
paired alignment remain explicitly bounded to downstream PRs #25 and #26.
