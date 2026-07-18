# S13-PR-003 Evidence-Gate Design — Workbook Structure Discovery and Row Classification

**Date:** 2026-07-18
**Owner assignment:** explicit, 2026-07-18
**Baseline:** `137f8c527422b656974e569c924dafa8150b8b22`
**Branch:** `s13-pr-003-workbook-structure-discovery`
**Status:** frozen before runtime implementation

## 1. Binding authority

- `CODEX.md` and `ENGINEERING_GUARDRAILS.md` permanent tenant, mutation, evidence and review gates.
- Design Book v1.4 §§5.2–5.7 and §6.2.
- ADR 0030 decisions 1–5 and the `WorkbookStructureSnapshot` concept.
- S13–S16 remediation plan, S13-PR-003 only.

No new ADR is required. This task implements the already accepted deterministic structure-discovery
and row-classification slice. It does not change S12 Apply v1.

## 2. Scope and non-goals

S13-PR-003 shall:

1. analyze an `available` immutable `ImportSourceArtifact` through the real `.xls`/`.xlsx` adapter;
2. rank bounded sheet/table/header-span candidates without using the first non-empty row rule;
3. support title rows and one-to-three-row header spans;
4. classify physical data rows as `asset`, `section`, `subtotal`, `total`, `note`, `empty` or `unresolved`;
5. persist an immutable, versioned `WorkbookStructureSnapshot` with rule version, candidate evidence,
   row-classification summary/preview and canonical digest;
6. expose authenticated analyze/list/get APIs with explanations and confidence;
7. return `review_required` for low confidence, competing candidates or structural drift;
8. reproduce a prior result by returning and digest-verifying the stored snapshot.

Non-goals:

- no semantic column-role assignment or `ColumnMappingProfile` (S13-PR-004);
- no mapping confirmation UI/API (S13-PR-005);
- no staging materialization, validation or Apply change;
- no asset-identity, pricing, AI/provider or Office-desktop behavior;
- no raw cell values in general audit payloads.

## 3. Frozen deterministic rule contract

Rule version: `s13-pr-003-v1`.

Bounded configuration, stored in each snapshot:

| Parameter | Value |
| --- | ---: |
| header scan rows per sheet | 200 |
| maximum header span | 3 rows |
| data-consistency sample | 24 rows |
| retained ranked candidates | 25 |
| retained row-class preview | 200 non-header rows |
| clear-proposal threshold | 0.62 |
| ambiguity margin | 0.08 |

These values are versioned heuristic defaults, not capability-promotion thresholds. They cannot
confirm mapping, materialize staging or approve official data.

Candidate scoring uses multiple independent signals allowed by v1.4: density/non-empty width,
business-header vocabulary, text/type patterns, subsequent-row consistency, serial-number patterns,
merged title regions and section/total markers. Sheet names such as `PD-001` are not hard-coded as a
positive score.

Disposition is fail-closed:

- `proposed` only when the top candidate reaches the threshold, is separated by the ambiguity margin
  and does not drift from the latest prior-generation snapshot;
- `review_required` otherwise, with stable reason codes.

## 4. Persistence contract

`WorkbookStructureSnapshot` is append-only in application behavior:

- tenant/project/batch/source-artifact composite scope;
- positive `snapshot_version`, unique per source artifact;
- source checksum and adapter identity;
- `rule_version` and full bounded rule configuration;
- `proposed` or `review_required` disposition;
- candidate count, canonical JSON payload and lowercase SHA-256 digest;
- authenticated creator and creation timestamp;
- no update/delete endpoint.

Database constraints enforce tenant/source linkage, version uniqueness, disposition, count and digest
shape. List/get reads re-compute the digest and fail closed if stored evidence was altered.

## 5. Authority-to-evidence binding

| Plane | Independent source | Required binding proof |
| --- | --- | --- |
| A — source authority | persisted artifact identity, state, size and checksum | object bytes are streamed with bounds and re-hashed before analysis |
| B — executed analysis | actual format adapter rows/merged regions | candidates and row classes derive only from adapter output for those verified bytes |
| C — durable observation | database snapshot + API response | canonical payload digest, rule version, actor and source IDs match the executed analysis |

The analyzer may not accept caller-supplied sheet/header/classification results. API clients supply only
the route-scoped artifact identity.

## 6. Required positive evidence

- anonymized PD-001-shaped `.xlsx` and `.xls` fixtures propose sheet `PD-001`, header row 5;
- A1 report title is not a header candidate;
- multi-row header span is detected without collapsing blank/duplicate column positions;
- `PHẦN ĐIỆN` and `PHẦN NƯỚC` classify as `section`;
- subtotal/total/note/empty/unresolved remain non-asset classes;
- same bytes + same rule version produce the same canonical digest;
- list/get return the stored snapshot unchanged after digest verification;
- version creation is tenant-scoped and append-only;
- audit event contains identifiers, versions, counts, disposition and digest only;
- staging rows and `ProjectAssetLine` counts/content remain unchanged.

## 7. Required negative/adversarial evidence

1. First non-empty title attack cannot win header discovery.
2. Two near-equal table candidates force `review_required`.
3. Inserted/reordered title/header rows versus a prior-generation snapshot force
   `review_required` instead of silent drift.
4. Section/total/subtotal/note markers cannot be emitted as `asset` merely because the row is non-empty.
5. Cross-tenant project/batch/artifact/snapshot access returns safe not-found.
6. Missing/non-available artifact, missing object, short read, size mismatch or checksum mismatch creates
   no snapshot and no success audit.
7. Tampered persisted payload/digest fails closed on read.
8. Caller cannot provide or override candidate, confidence, row class, rule version or digest.
9. Analysis performs no staging or official-line mutation on success or failure.
10. Candidate scan and retained preview remain bounded; adapters/resources close in `finally` paths.

## 8. API contract

Under the existing project/import/source-artifact route:

- `POST .../source-artifacts/{artifact_id}/structure-snapshots` — execute analysis and append snapshot;
- `GET .../source-artifacts/{artifact_id}/structure-snapshots` — list verified versions;
- `GET .../source-artifacts/{artifact_id}/structure-snapshots/{snapshot_id}` — replay one verified snapshot.

POST requires `workbench:edit`; reads require `project:read`. All scope is server-derived from the
authenticated user and route identifiers.

## 9. Completion gate

- focused unit/API/adversarial tests pass;
- full backend suite and Ruff pass;
- Alembic has exactly one head and migration upgrade/downgrade smoke passes;
- exact-head GitHub CI passes with PostgreSQL/MinIO tests executed;
- diff stays within S13-PR-003 scope;
- Antigravity audits the exact published head; Codex does not self-issue independent PASS.
