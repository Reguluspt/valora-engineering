---
name: valora-postgresql-proof
description: Plan and verify PostgreSQL evidence for Valora locking, concurrency, migrations, tenant isolation, rollback and version or CAS gates.
---

# PostgreSQL proof

Read live scoped implementation/authority after bootstrap. Where the gate requires PostgreSQL, use real PostgreSQL with recorded server version, command, exact HEAD and raw results. SQLite is not a substitute. Local PostgreSQL skips are not PASS; no required test may skip in CI.

Choose proof that distinguishes correct behavior from the named failure:

- Lock/concurrency: real separate transactions/connections, deterministic barriers or lock observations; assert committed rows/audit/receipts, not timing alone. Prove both meaningful race orders when the invariant depends on winner order.
- Migration round trip: upgrade → exercise affected state → downgrade → upgrade, at exact migration revisions. Downgrade must remove only owned/provenance-proven grants or objects; preserve pre-existing state.
- Tenant fail-closed: missing identity, inactive principals and cross-tenant identifiers fail without mutation or leakage.
- Atomic rollback: inject the relevant failure and prove all business/audit/receipt writes roll back together.
- Version/CAS: record exact expected/actual versions, stale rejection, winner increment and replay behavior required by the contract.

Use synthetic fixtures; never upload credentials, customer payloads or real appraisal values to OpenViking. Record limitations and raw skip counts. This skill supplies evidence patterns, not permission to modify domain behavior or run production operations. Follow the [profile](../../../docs/plan/VALORA_OPENVIKING_OPERATING_PROFILE_V1.md).
