# S13-PR-003 Third Corrective Addendum — Atomic Finalization Seal

**Date:** 2026-07-18

**Status:** frozen before third-corrective runtime changes

**Failed audited remote head:** `ed8dad82478920ab2e15300ff1b71043b64035fb`

**Failed audited tree:** `bc69bab19b96d42eaa270040606280a059e14245`

**Exact-head CI:** run `29654287407`, successful but superseded by the independent audit failure

**Branch:** `s13-pr-003-workbook-structure-discovery`

**PR:** `#17`, must remain Draft

This addendum is binding after an independent Sol Max audit returned **FAIL** for the remote head and
tree above. It supplements, and does not replace, the original evidence-gate design and the first and
second corrective addenda. Every previously closed tenant/RBAC, source-integrity, H-03, M-01, M-02,
Unicode, adjacent-table, bounded-history, append-only, no-staging, no-official-line, and whitespace
gate remains a mandatory regression requirement.

## 1. Finding and root cause

The failed implementation verified that a replayed `drift_reference` described an existing,
internally coherent predecessor snapshot. It did not prove that the tuple was the exact predecessor
observation bound when the target snapshot was finalized.

An attacker or corrupted store could therefore alter the target payload and recompute its target
digest so that it:

1. changed a valid predecessor reference to another valid older predecessor snapshot;
2. replaced a complete predecessor snapshot tuple with an all-null tuple; or
3. rebound the target to a predecessor snapshot created after the target was finalized.

Those coherent alterations could pass list/get replay. Comparing against the predecessor's current
latest snapshot is not a valid repair: a later legitimate analysis of the predecessor must not
invalidate an already-finalized target. Comparing `created_at` values is also forbidden because
timestamps are neither the serialization authority nor a reliable finalization order.

## 2. Binding corrective decision

The existing atomic `WorkbookStructureAnalyzed` audit event is the finalization seal for its target
`WorkbookStructureSnapshot`.

- Snapshot creation already inserts the snapshot and event in the same database transaction.
- The event binds the target `analysis_digest_sha256`.
- The target digest binds the complete canonical structure payload, including the exact
  `drift_reference` observed at finalization.
- Replay must require exactly one matching seal for every returned target snapshot.
- Replay must verify the original direct reference, not compare it with a current-latest predecessor
  snapshot and not walk a recursive ancestry chain.

No duplicate copy of `drift_reference` is added to the audit payload. The digest is the single
canonical binding; duplicating the tuple would create a second representation that could diverge.

## 3. Rule-version and schema decision

This corrective changes read-time finalization-integrity verification only. It does not change
workbook discovery, normalization, row classification, candidate ranking, disposition, rule
configuration, canonical payload shape, or digest semantics.

Therefore:

- new writes continue to use `s13-pr-003-v3`;
- the read allowlist remains exactly v1, v2, and v3;
- unknown rule versions continue to fail closed;
- there is no v4 rule bump;
- there is no migration, backfill, payload rewrite, or new seal table; and
- historical valid v1/v2/v3 snapshots and their events remain byte-for-byte unchanged.

Every valid snapshot created by the application since v1 already has the atomic audit event. A row
inserted outside the frozen service contract without that event is not valid historical evidence and
must fail closed.

## 4. Finalization-seal contract

For each target snapshot, exactly one event must satisfy all of the following metadata bindings:

| Event field | Required value |
| --- | --- |
| `organization_id` | target snapshot organization |
| `actor_user_id` | target `created_by_user_id` |
| `event_name` | `WorkbookStructureAnalyzed` |
| `entity_type` | `WorkbookStructureSnapshot` |
| `entity_id` | target snapshot ID |
| `command_name` | `AnalyzeWorkbookStructure` |
| `created_at` | non-null; never used for lineage ordering |

`correlation_id` is optional operational metadata and is not an integrity binding.

The event payload must be an object with the exact historical field set below, and every value must
match the target snapshot or its durable source artifact:

| Payload field | Required value |
| --- | --- |
| `import_batch_id` | target import batch ID |
| `source_artifact_id` | target source artifact ID |
| `source_generation` | durable target artifact generation |
| `snapshot_version` | target snapshot version |
| `rule_version` | target rule version |
| `disposition` | target disposition |
| `candidate_count` | target candidate count |
| `analysis_digest_sha256` | target canonical analysis digest |

The verifier must use the stable `structure_snapshot_integrity_failure` response for every seal
failure. Zero matching events, two or more events, missing or extra payload fields, non-object
payload, changed metadata, or any value mismatch all fail closed. If a changed organization, event
name, entity type, entity ID, or command makes an event fall outside the scoped query, it is treated
as a missing seal.

Duplicate detection must remain bounded. For a page of `N` target snapshots, load at most `N + 1`
candidate event rows in stable order, then group by target ID and require exactly one per target. This
materializes at most 51 rows for the maximum page.

## 5. Creation-time lineage contract

The existing batch-lock serialization remains authoritative:

1. analyze verified object bytes outside the lock;
2. lock the import batch `FOR UPDATE`;
3. reload and lock the target artifact with `populate_existing`;
4. compare its complete frozen fingerprint;
5. select the exact immediate earlier `available` source artifact by generation;
6. select that artifact's greatest `snapshot_version`, never by `created_at`;
7. integrity-verify the selected predecessor snapshot without falling back to an older row;
8. bind the observed tuple into `drift_reference` and compute the target digest;
9. insert the target snapshot and exactly one finalization event; and
10. commit both atomically.

A PostgreSQL concurrency test must prove that if another transaction finalizes a newer predecessor
snapshot while holding the same batch lock, target creation waits and then binds the newly committed
greatest predecessor version.

## 6. Replay lineage semantics

Core target digest, scalar, rule, source, and seal verification runs before accepting lineage links.

For v2 and v3:

- the referenced artifact must be the exact immediate earlier durable `available` artifact by
  generation;
- no predecessor requires `drift_reference = null`;
- a predecessor with no snapshot at target finalization uses the correct artifact ID/generation and
  an all-null snapshot subtuple;
- an observed predecessor snapshot uses a complete ID/version/rule/digest subtuple;
- partial-null tuples always fail; and
- a complete tuple must direct-match a tenant/project/batch-scoped durable snapshot belonging to the
  referenced artifact, after which that referenced snapshot receives non-recursive core verification.

The following historical cases must remain valid:

- a target originally bound predecessor version 1, then that predecessor legitimately acquired
  versions 2 or 3; and
- a target originally bound an all-null predecessor snapshot tuple, then that predecessor was
  analyzed for the first time.

Replay must not query the current maximum predecessor snapshot version, compare target/reference
timestamps, forbid later-created predecessor observations, or recursively traverse ancestors. A
coherent rebind to an older, null, or later tuple changes the target digest and is rejected by the
unchanged finalization seal.

V1 compatibility remains rule-specific:

- an absent `drift_reference` is valid;
- an explicitly null `drift_reference` is valid when core and seal bindings match; and
- an optional non-null v1 reference must pass its frozen shape, backward-generation, tenant-scoped
  artifact, and direct snapshot checks, without imposing the v2/v3 immediate-predecessor invariant.

No valid replay may rewrite a snapshot or event.

## 7. Bounded query contract

List/get verification must remain page-local, non-recursive, tenant-scoped, and free of N+1 queries.
For one through fifty returned snapshots, the total request budget remains at most five `SELECT`
statements:

| Query | Maximum |
| --- | ---: |
| scoped target artifact | 1 |
| page `limit + 1`, or get target snapshot | 1 |
| immediate durable predecessor context when required | 1 |
| bounded combined referenced-artifact/direct-snapshot context | 1 |
| bounded finalization seals, capped at `N + 1` | 1 |
| **total** | **5** |

The implementation may combine predecessor and referenced context more tightly and use fewer
queries, but it may not exceed this ceiling. The combined reference query must be bounded by IDs from
the current page, source-scoped, and able to retain v1 optional-reference compatibility. An empty page
may stop after the target-artifact and page queries. Corruption outside the requested page must not be
read or affect the current response.

## 8. Mandatory adversarial evidence

The focused corrective suite must prove all of the following.

### Finalization and coherent-tamper probes

- predecessor versions 1 and 2 exist before target creation; the target binds version 2;
- the PostgreSQL batch-lock race binds the snapshot committed before the target obtains the lock;
- changing a target from its original tuple to an older valid tuple and recomputing its target digest
  fails because the seal remains unchanged;
- changing a complete tuple to all-null and recomputing the target digest fails;
- after target finalization, adding a predecessor snapshot and coherently rebinding the target to it
  fails;
- coherently changing target payload, digest, and scalar columns still fails against the seal;
- missing and duplicate seals fail;
- mismatched organization, actor, event name/type/entity/command, timestamp, payload shape, source
  generation, snapshot version, rule, disposition, count, or digest fails; and
- missing or wrong referenced snapshot ID/version/rule/digest/source/tenant fails.

### Valid-history and bounds probes

- an originally bound predecessor remains replayable after later predecessor snapshots are appended;
- an originally all-null tuple remains replayable after the predecessor is first analyzed;
- genuine v1 absent/null/optional references and genuine v2/v3 rows replay byte-for-byte without
  rewrite;
- an unknown rule still fails even when accompanied by an otherwise plausible event;
- page sizes 1 and 50, plus get-one, remain within five `SELECT` statements;
- the event query proves its `N + 1` cap and materializes at most 51 rows;
- fifty direct references create no N+1 behavior;
- a broken seal outside the page does not affect the current page, but fails when its page is read;
- cross-tenant routes preserve safe 404 behavior and cross-organization events cannot satisfy a seal;
  and
- no staging row, `ProjectAssetLine`, mapping, Apply, or official-data mutation is introduced.

All prior focused and full regression gates remain mandatory, including full backend tests, Ruff,
security/dependency checks, Alembic single-head and live-upgrade smoke, PostgreSQL/MinIO integration,
worker/frontend CI, range `git diff --check`, and per-commit `git show --check`.

## 9. Authorized file scope and commit order

Authorized changes are limited to:

- this frozen addendum;
- `backend/app/modules/excel_import/application/workbook_structure_service.py`; and
- focused S13-PR-003 tests, preferably
  `backend/tests/test_s13_pr_003_workbook_structure.py` unless a small dedicated corrective test file
  materially improves fixture isolation.

No domain analyzer, API/schema, model, Alembic, frontend, staging, Apply, or CI-workflow change is
authorized by this addendum.

Required evidence order:

1. publish this design-only commit through the GitHub App and verify its exact tree;
2. implement runtime verification and tests against the frozen design;
3. run focused gates, then full local gates;
4. publish the exact runtime/test head through the GitHub App and verify blobs, tree, and commit range;
5. require exact-head CI PASS;
6. commission a fresh independent Sol Max audit of that exact SHA/tree; and
7. only after Sol Max returns PASS, hand the same unchanged SHA/tree to Antigravity.

PR #17 remains Draft throughout these steps. A prior CI success is not acceptance evidence for a
superseded head, and neither the implementation agent nor the Lead may self-declare final PASS.

## 10. Residual risk and deployment preflight

This seal closes the audited threat in which the target snapshot is coherently altered while the
durable audit event remains intact. `AuditEvent` is not a general WORM or cryptographically signed
store: append-only behavior is an application policy, `entity_id` is not a foreign key to the
snapshot, and a privileged database actor could alter both the snapshot and its event.

If the threat model expands to coordinated database rewriting, a separate ADR must evaluate an
immutable seal table, database trigger/privilege boundary, or signed external/WORM log. That larger
security architecture is outside this corrective and must not be smuggled into it.

Before deployment, run a read-only inventory for workbook snapshots whose matching finalization-event
count is not exactly one. Any result is a release blocker requiring owner review. Do not fabricate or
automatically backfill historical seals.
