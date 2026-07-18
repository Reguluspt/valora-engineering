# S13-PR-003 Fourth Corrective Addendum — Canonical Payload Object Gate

**Date:** 2026-07-18

**Status:** frozen before fourth-corrective runtime changes

**Failed audited remote head:** `4511dfe41e6616274db4bd0c6e9645ebd7246bb3`

**Failed audited tree:** `16b7072401f79f08601f27cfd18daf06500c0c3d`

**Exact-head CI:** run `29656717823`, successful with 976 passed and 0 skipped, but superseded by the
independent audit failure

**Branch:** `s13-pr-003-workbook-structure-discovery`

**PR:** `#17`, must remain Draft

This addendum is binding after the independent Sol Max acceptance audit returned **FAIL** for the
head and tree above. It supplements every earlier frozen S13-PR-003 design. All finalization-seal,
lineage, tenant/RBAC, five-SELECT, source-integrity, Unicode, adjacent-table, pagination,
append-only, no-staging, no-official-line, and committed-whitespace gates remain mandatory
regression requirements.

## 1. Finding and root cause

`WorkbookStructureSnapshot.structure_payload` is stored in PostgreSQL JSONB. JSONB can persist any
JSON top-level value, including an object, array, string, number, boolean, or JSON null.

The failed implementation checked the supported scalar rule version and canonical digest, then
assumed the payload was a dictionary and called `payload.get(...)`. When a non-object JSON value had
a matching recomputed digest, both list and get could raise an unhandled `AttributeError` before the
finalization-seal query. Evidence remained fail-closed, but the API did not return the frozen stable
integrity response.

The Lead independently reproduced the exception for all five non-object JSON categories:

```text
array | string | number | boolean | null
```

The previous coherent-payload test covered only dictionary-shaped alteration and therefore did not
exercise this boundary.

## 2. Binding validation order

`_verify_snapshot_core` must follow this order:

1. verify the scalar `snapshot.rule_version` is in the explicit v1/v2/v3 allowlist;
2. assign `payload = snapshot.structure_payload`;
3. require `isinstance(payload, dict)`;
4. verify the canonical payload digest;
5. verify payload/scalar/source/rule-specific drift-reference bindings; and
6. continue to the unchanged exact finalization-seal and direct-lineage verifier.

Step 3 must run before digest evaluation and before any payload field access. Every non-object JSON
value fails through:

```text
HTTP 500
error_code = structure_snapshot_integrity_failure
```

The object-shape and digest-failure paths must use the same generic public detail so callers cannot
distinguish internal corruption shape from digest mismatch. The response may not echo the stored
payload, Python exception, database type, or any cell data.

Keeping the supported-version check first preserves the existing unknown-rule precedence. An unknown
rule fails closed through the same stable error code even if its payload is also malformed.

## 3. Scope boundary

This corrective covers only the top-level canonical payload object gate.

- `source` already has an explicit dictionary check before field access.
- `drift_reference` already has an explicit dictionary check and complete/null tuple validation.
- replay does not dereference arbitrary `rule_config` or candidate substructure; their bytes are
  already bound by the target digest and unchanged finalization seal.
- no adjacent malformed-shape exception has been demonstrated that authorizes broader validation.

This corrective must not introduce speculative schema validation, rewrite historical payloads, or
change discovery semantics.

## 4. Compatibility, version, and persistence decision

The change is a read-time integrity boundary only. It does not change normalization, discovery,
classification, ranking, disposition, rule configuration, canonical serialization, payload content,
or digest calculation for any valid object payload.

Therefore:

- new writes remain `s13-pr-003-v3`;
- the read allowlist remains exactly v1, v2, and v3;
- there is no v4 rule bump;
- there is no model or Alembic migration;
- there is no backfill, rewrite, repair, or synthetic audit event;
- valid historical v1/v2/v3 snapshots and audit events remain byte-for-byte unchanged; and
- the finalization-seal payload and query remain unchanged.

PostgreSQL JSONB object values, SQLite JSON object values, and ORM-loaded dictionaries receive the
same behavior. JSON arrays and scalars are corruption evidence, not legacy compatibility cases.

## 5. List, get, locality, and query contract

List and get share `_verify_snapshot_page`, so both must exercise the same core object gate.

- A malformed item inside the requested page fails the entire page with the stable integrity error.
- A malformed item outside the requested page is not loaded and cannot affect the current response.
- Get-one fails only when its requested target is malformed.
- Core rejection occurs before the seal/context queries and therefore cannot add a `SELECT`.
- Valid pages of 1 through 50 items and get-one must remain within the frozen five-SELECT ceiling.
- Seal loading remains tenant-scoped, stable ordered, and capped at `N + 1`; direct lineage remains
  bounded and non-recursive.

No identity-map-only proof is sufficient. Tests must commit malformed JSON and expire or expunge ORM
state before replay so the value crosses the durable JSON serialization boundary.

## 6. Mandatory adversarial evidence

For each top-level value below, store it as `structure_payload`, compute and store its matching
canonical digest, leave the original finalization event unchanged, commit, reload, and call both list
and get:

| JSON category | Representative value | Required result |
| --- | --- | --- |
| array | `[]` or `[{}]` | stable integrity failure |
| string | `"scalar"` | stable integrity failure |
| number | `7` | stable integrity failure |
| boolean | `true` | stable integrity failure |
| JSON null | `null` | stable integrity failure |

Every response must be HTTP 500 with exactly
`detail.error_code = structure_snapshot_integrity_failure`; no Python exception may escape.

Additional controls must prove:

- a non-object payload with a stale/mismatched digest follows the same public integrity response,
  demonstrating object-shape-before-digest ordering without information leakage;
- malformed item 21 does not affect the first 20-item page but fails the page beginning at cursor 20;
- get-one and list reject the same malformed target;
- valid object payloads for v1 absent/null/optional references and v2/v3 replay byte-for-byte without
  snapshot or event mutation;
- unknown rule versions remain fail-closed;
- coherent older/null/later lineage alteration and every finalization-seal negative probe remain
  green;
- list limits 1 and 50 plus get-one retain the five-SELECT ceiling; and
- no staging row, mapping, Apply path, `ProjectAssetLine`, or official-data mutation is introduced.

The focused suite must include both route-level responses and a narrow pure-core negative control so
an API exception-handler artifact cannot hide the exact guard order.

## 7. Authorized file scope

Only these changes are authorized:

- this frozen addendum;
- `backend/app/modules/excel_import/application/workbook_structure_service.py`; and
- `backend/tests/test_s13_pr_003_workbook_structure.py`, unless a very small dedicated fourth-
  corrective test file materially improves isolation.

No domain analyzer, model, migration, API/schema, CORS, frontend, worker, CI workflow, staging,
mapping, Apply, or official-data file is authorized.

## 8. Evidence and publication order

1. Publish this design-only addendum through the GitHub App and verify its exact blob/tree.
2. Implement the object guard and adversarial tests against the frozen design.
3. Run focused tests, full backend regression, Ruff, security, warning-as-error compile, Alembic
   single-head, and per-commit/range whitespace gates.
4. Obtain independent pre-commit red-team QA of the uncommitted runtime/test diff.
5. Publish the exact runtime/test tree through the GitHub App by non-force fast-forward and verify
   every blob, tree, parent, and design-to-head file list.
6. Require a new exact-head CI run with PostgreSQL/MinIO and zero skipped tests.
7. Commission a fresh independent Sol Max acceptance auditor who did not plan or implement this
   corrective.
8. Only after Sol Max returns PASS may the same unchanged SHA/tree be handed to Antigravity.

PR #17 remains Draft throughout. The successful CI run and passing gates for a superseded failed
head are historical evidence only; they cannot be reused as acceptance evidence for the next head.

## 9. Residual threat and process note

The third-corrective residual threat remains unchanged: a privileged database actor capable of
coherently rewriting both a snapshot and its audit event is outside this corrective and requires a
separate immutable/signed evidence architecture.

The failed Sol Max auditor reported one process deviation: it removed only the untracked
`backend/pytest-of-root/` directory generated by its own completed tests before receiving the Lead's
instruction to leave residue untouched. No tracked file or audited tree changed. This deviation is
recorded for transparency and is not accepted as authority to mutate future audit targets.
