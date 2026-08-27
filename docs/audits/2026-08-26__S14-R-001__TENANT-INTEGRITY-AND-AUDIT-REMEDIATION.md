# S14-R-001 — Tenant Integrity and Audit Remediation

## Status

- Local-only implementation SHA: `b2d2785264f118d51b29fc9adf632abbb19bd228`
- Branch: `remediation/s14-r-001-tenant-integrity`
- GitHub push/release: **not authorized and not performed**
- Release acceptance: **pending PostgreSQL and final same-SHA CI gates**

## Authority crosswalk

The remediation was checked against:

- `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md`
- `docs/adr/0031-contextual-asset-identity-memory-and-human-confirmed-feedback.md`
- `docs/remediation/2026-08-26__S13-S16__LOCAL-REMEDIATION-DESIGN.md`
- Design Book v1.2 Beta Taxonomy / Asset Identity security rules
- Design Book v1.2 Zeta Data Isolation and Security Hardening records

The protected command uses `asset_identity:approve`. Human confirmation remains
mandatory. Raw wording is preserved, contextual memory is tenant/customer
scoped, and only committed human decisions generate feedback.

## Corrective implementation

### Actor, permission, tenant, and ownership

- Replaced caller-supplied `actor_id` with a trusted `User` authentication
  context that is reloaded from persistence.
- Requires an active organization, active same-organization actor, and the
  Design Book permission `asset_identity:approve`.
- Locks and validates project, customer, and raw observation ownership before
  any business mutation.
- Cross-tenant and invalid actor contexts return non-disclosing responses.
- Authorization denials and tenant failures are persisted before the command is
  rejected; no business mutation is committed with them.

### Database integrity

Migration `e7f8a9b0c1d2` adds:

- composite tenant/customer/project/observation/actor foreign keys;
- composite lineage foreign keys for batch, source artifact, workbook snapshot,
  and optional staging row;
- real foreign keys for canonical asset, variant, curated alias, source decision,
  and contextual-alias targets;
- exact target-shape, decision-type, rejection-reason, feedback-type, and status
  checks;
- one feedback event per source decision;
- fail-closed preflight for incomplete local-only S14 ownership rows.

### Audit and security records

- Success writes `AuditEvent` atomically with the decision, contextual alias,
  and learning feedback.
- Added only the approved Design Book primitives required by this mutation path:
  `TenantBoundaryCheck`, `SecurityEvent`, and `SecurityAuditLog`.
- Passing high-risk boundary checks are recorded in the success transaction.
- Failed boundary checks create durable high-severity security evidence without
  exposing protected resource contents to the caller.

### Idempotency and feedback

- Exact command replay returns the same decision and same feedback event.
- Reuse of a command ID with different intent returns `409`.
- Accepted/corrected targets must be active and valid.
- Rejected decisions require a non-empty reason.
- Deferred decisions cannot carry a target and never create feedback.
- Contextual aliases can be created only by accepted/corrected human decisions.

## Verification evidence

| Gate | Result |
|---|---|
| Ruff over changed backend/migration/tests | PASS |
| S14 + identity focused suite | PASS — 29 tests |
| S14-R-001 service suite | PASS — 12 tests |
| PostgreSQL-only S14-R-001 tests without PostgreSQL runtime | SKIP — 2 tests, intentionally fail in CI if PostgreSQL is absent or not at head |
| Alembic graph | PASS — one head: `e7f8a9b0c1d2` |
| S14 migration offline PostgreSQL SQL generation, upgrade and downgrade slice | PASS |
| Backend broad run before stale-head assertion update | 988 passed, 65 skipped, 2 failed only because two older tests expected the prior S13 head |
| Two corrected Alembic-head assertions | PASS — 2 tests |

The complete backend suite will be rerun on the final integration SHA. This
document does not convert the skipped PostgreSQL tests into acceptance evidence.

## Remaining release blockers

- Docker Desktop daemon is not running on the current host.
- PostgreSQL and MinIO are not listening locally.
- The new migration has not yet been applied to a real PostgreSQL database.
- The PostgreSQL concurrency/constraint tests have not yet executed.
- S15 reliable job, paired DOCX/Excel alignment, and the final same-SHA CI gates
  remain pending.
