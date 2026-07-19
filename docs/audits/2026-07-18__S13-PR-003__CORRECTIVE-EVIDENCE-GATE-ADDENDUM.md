# S13-PR-003 Corrective Evidence-Gate Addendum — Bounded Regions and Serializable Drift

**Date:** 2026-07-18
**Status:** frozen before corrective runtime changes
**Audited remote head:** `420b04bdca54c61ff0343904e8a350619c1e09ed`
**Audited tree:** `60be27e53315dc27a5230961d055bdf844ef3936`
**Branch:** `s13-pr-003-workbook-structure-discovery`

This addendum is binding for the corrective implementation after the independent Sol Max audit.
It supplements, and does not rewrite, `2026-07-18__S13-PR-003__EVIDENCE-GATE-DESIGN.md`.
Where this addendum defines v2 discovery, classification, lineage, or cleanup behavior, it supersedes
the corresponding v1 rule behavior. Persistence, API authorization, tenant isolation, append-only
evidence, audit minimization, and all non-goals in the original design remain binding.

## 1. Corrective findings in scope

The corrective must close all five independently reproduced findings:

| ID | Severity | Binding problem |
| --- | --- | --- |
| H-01 | High | a candidate uses sheet-wide row/column bounds and can absorb another table or remote content |
| H-02 | High | marker rows can be absorbed into a header or emitted as assets |
| H-03 | High | drift can be evaluated before the serialization lock against a stale predecessor snapshot |
| M-01 | Medium | post-I/O artifact revalidation can reuse a stale SQLAlchemy identity-map instance |
| M-02 | Medium | successful copying followed by a stream-close failure can leak the temporary source file |

The PR remains Draft. Neither the implementer nor Codex may issue the independent PASS verdict.

## 2. Deterministic rule contract v2

The corrective changes the versioned rule identifier to:

```text
s13-pr-003-v2
```

No database migration is required for this rule change. Existing v1 snapshots remain readable and
digest-verifiable under their stored rule version; they are never rewritten.

Every v2 snapshot stores the following complete configuration in `rule_config`:

| Parameter | Value |
| --- | ---: |
| header scan rows per sheet | 200 |
| maximum header span | 3 rows |
| data-consistency sample | 24 rows |
| column-evidence sample | 24 rows |
| empty-column separator run | 1 column |
| late blank-header edge extension | 1 adjacent column |
| vertical blank boundary run | 2 rows |
| vertical unresolved boundary run | 2 rows |
| trailing note/unresolved run | 3 rows |
| post-total tail | 3 rows |
| retained ranked candidates | 25 |
| retained row-class preview | 200 rows |
| clear-proposal threshold | 0.62 |
| ambiguity margin | 0.08 |

These constants may not be relaxed to make a fixture pass. A later tuning change requires another
rule version and corpus evidence.

## 3. Candidate table-column contract

`SheetSummary.max_column` is inspection metadata, never a candidate boundary.

For each eligible one-to-three-row header span, column evidence is the union of:

1. non-empty cells in the header span; and
2. non-empty cells in the next 24 physical rows.

One or more consecutive columns empty in both sources is a separator. Each maximal occupied run is
scored as a separate candidate. Scoring, serial/type consistency, header labels, and later row
classification read only that candidate's column slice.

Within a candidate run, positional labels are retained exactly. Blank labels are `null`; duplicate
labels remain separate positions. A blank trailing header column with body evidence inside the
24-row sample is included normally. Evidence first appearing later may extend the right or left edge
by at most one adjacent column, must add `late_blank_header_column_evidence`, and forces
`review_required`. The resolver may never jump across an evidence-empty separator.

Two horizontally adjacent header anchors without an evidence-empty separator are not silently
merged or selected. They add `ambiguous_horizontal_table_boundary` and force review.

Consequences that must hold:

- a note in `Z1` cannot widen an `A:E` table;
- two horizontal tables separated by an empty evidence column become separate candidates;
- internal/trailing blank header positions supported by body evidence remain positional;
- remote content across a separator never enters confidence, bounds, classification, or fingerprint.

## 4. Candidate row-boundary state machine

`SheetSummary.max_row` is inspection metadata, never a candidate boundary. After preliminary header
ranking, the analyzer performs one streaming resolution pass per sheet for all retained candidates
on that sheet. It must not reopen the adapter once per candidate.

The resolver applies these ordered rules to each candidate:

1. A later eligible header span for an overlapping column region with confidence at least `0.62`
   ends the current region immediately before the new header. This rule also applies beyond the
   initial 200-row header scan; such a discovery adds `additional_table_beyond_header_scan` and
   forces review.
2. One blank row is buffered. If followed by a body row, it remains inside the region and classifies
   as `empty`. A second consecutive blank ends the region before the first blank.
3. One unresolved row remains inside the region. A second consecutive unresolved row also remains,
   ends the region at that row, adds `ambiguous_vertical_table_boundary`, and forces review.
4. Outside the post-total state, at most three consecutive `note|unresolved` rows without an
   `asset|section|subtotal` anchor remain in the region. A fourth is excluded, ends the region, adds
   `trailing_non_asset_boundary`, and forces review.
5. The first `total` is terminal. At most three following `note|empty|unresolved` rows remain.
   A fourth tail row is excluded and adds `post_total_tail_exceeded`. Any later
   `asset|section|subtotal` row is excluded and adds `content_after_terminal_total`. Either flag
   forces review.
6. Normal sheet end after accepted content ends the region without adding an ambiguity flag. A
   single final unresolved row remains accepted evidence and does not alone force review.

Two vertical tables with zero or one intervening blank row therefore remain distinct when the
second header is eligible. If their scores differ by less than `0.08`, the existing
`competing_candidates` review gate applies.

Every retained candidate includes stable boundary evidence:

```json
{
  "candidate_table_bounds": {
    "min_row": 5,
    "max_row": 15,
    "min_column": 1,
    "max_column": 9
  },
  "boundary_reason": "next_header|blank_run|sheet_end|terminal_total|ambiguous",
  "boundary_flags": []
}
```

The primary candidate's counts and preview are computed only from:

```text
[min_column, max_column] × [data_start_row, max_row]
```

No row or cell outside this rectangle may affect the classification evidence.

## 5. Row-marker and header eligibility contract

Classification precedence is fixed:

```text
EMPTY → TOTAL → SUBTOTAL → NOTE → SECTION → ASSET → UNRESOLVED
```

Marker matching uses normalized Unicode, case, and whitespace. It inspects the first non-empty text
cell, optionally after one outline/serial cell. Known anchored forms are:

| Class | Anchored forms |
| --- | --- |
| total | exact `tong`/`total`, or prefix `tong cong`, `tong gia tri`, `tong thanh tien` |
| subtotal | prefix `cong phan`, `cong muc`, `tam tinh`, `subtotal` |
| note | prefix `ghi chu`, `chu thich`, `note`, or leading `*` |
| section | prefix `phan`, `chuong`, `muc`, `hang muc` |

An exact marker after an outline/serial cell wins over the asset rule. Thus
`[99, "TỔNG CỘNG", 100]` is `total`. A non-marker business name such as
`[1, "Tổng công ty ABC", 100]` does not match the anchored total vocabulary and remains eligible for
`asset`. Generic uppercase text or an uppercase code/name pair is not sufficient section evidence;
when no explicit section anchor exists it is `unresolved`.

Confidence is fixed:

| Result | Confidence |
| --- | ---: |
| empty | 1.00 |
| explicit marker | 0.98 |
| serial-led asset with other content | 0.94 |
| mixed text/numeric without serial, unresolved | 0.40 |
| other unresolved | 0.35 |

The mixed-text-plus-numeric heuristic no longer authorizes an asset classification. Only a first
non-empty serial cell plus at least one other content cell is a strong v2 asset signature.

A physical row may participate in a header span only when all of the following hold:

- it is non-empty;
- it is not any marker class;
- it has no strong asset signature;
- it contains no physical numeric, boolean, or datetime value; and
- the complete span yields at least two positional header labels.

These checks prohibit a section immediately below the true header from being absorbed into a
multi-row header. Uncertain rows fail closed as `unresolved`; they do not receive high confidence.

## 6. Serializable drift and source-authority contract

Object I/O and adapter analysis occur before any database row lock. Before I/O, the service freezes
an immutable primitive artifact fingerprint containing at least:

```text
id, organization_id, project_id, import_batch_id, generation, state,
checksum_sha256, file_size_bytes, detected_format, storage_object_key
```

Database finalization then follows this exact order:

```text
batch FOR UPDATE + populate_existing
→ target artifact FOR UPDATE + populate_existing
→ compare fresh artifact with frozen fingerprint
→ resolve immediate prior available artifact in the same tenant/project/batch
→ resolve and verify the latest snapshot of exactly that predecessor
→ bind drift reference and apply drift/review rules
→ calculate canonical digest
→ allocate target snapshot version
→ insert snapshot and success audit
→ commit
```

The service may not acquire a project lock after the batch lock. Adapter or object-storage work may
not be moved into the lock window.

Artifact comparison never compares two ORM variables that can share one identity-map object. Any
fingerprint difference, including state, generation, checksum, size, format, or object key, returns
`409/source_artifact_changed` with no snapshot or success audit.

The predecessor is the `available` artifact with the greatest generation lower than the target.
There is no fallback past that artifact:

- no predecessor: bind a null drift reference;
- predecessor without a snapshot: bind its identity, add `prior_generation_snapshot_missing`, and
  force review;
- predecessor with a snapshot: verify and bind its artifact ID/generation plus snapshot
  ID/version/rule/digest;
- a predecessor rule version different from v2 adds `structure_rule_version_changed` and forces
  review;
- a changed primary structural signature adds `structure_drift_from_previous_generation` and forces
  review.

The v2 structural signature contains sheet, header start/end, data start, min/max columns, and
positional header labels. `max_row` is excluded because ordinary data-row growth is not template
drift. Boundary ambiguity remains independently fail-closed through `boundary_flags`.

`drift_reference` is part of the canonical payload and integrity verification. Reproducibility means:

```text
same target artifact + same verified bytes + same rule version/config
+ same drift reference => same canonical digest
```

Different source identity or lineage evidence may correctly produce a different digest.

## 7. Verified temporary-source ownership

The materializer owns the temporary path until the caller's adapter work finishes. It must be a
managed context (or an equivalent ownership construct) with these properties:

1. open/read/size/checksum failures retain their existing stable error and take precedence over a
   secondary close failure;
2. a successful copy followed by close failure returns
   `503/source_stream_close_failed`;
3. the temporary path is unlinked on open, read, verification, close, adapter, and normal-success
   paths;
4. no failure creates a snapshot or success audit; and
5. adapter close failure cannot bypass temporary-path cleanup.

Ownership may transfer to adapter analysis only after source-stream close and checksum/size
verification both succeed.

## 8. Required corrective evidence

### Domain and adversarial matrix

- true header followed immediately by `PHẦN ĐIỆN` does not absorb the section;
- section/total/subtotal/note markers with outline and numeric side cells remain non-assets;
- `X01 / MÁY BƠM` and mixed text/numeric without a serial fail closed as unresolved;
- a serial-led non-marker business row remains asset;
- two vertical tables, two horizontal tables, a remote `Z1` note, a far-below note, and a repeated
  header anchor obey the v2 bounds and review flags;
- a supported blank trailing header column is retained with a terminal `null` label;
- late adjacent blank-header evidence extends exactly one column and forces review;
- one versus two blank rows, two unresolved rows, terminal-total tails, and a fourth trailing
  non-asset row exercise every state transition;
- classification preview and counts contain no row or column outside the primary rectangle;
- candidate retention and row-provider passes stay bounded and every iterator closes.

### Service and API matrix

- `.xlsx` and `.xls` PD-001-shaped fixtures still propose row 5 and classify the required markers;
- the multi-row header remains rows 5–6;
- same artifact/config/lineage replays the same digest;
- drift reference is payload- and digest-bound; tampering fails closed;
- an immediate predecessor without a snapshot forces review;
- reordered/inserted header evidence forces review against the exact predecessor;
- caller overrides, cross-tenant access, append-only behavior, and no-staging/no-official-line mutation
  retain their existing proofs;
- a two-session identity-map probe changes durable artifact authority between initial read and lock,
  and the service must return `source_artifact_changed`;
- successful read plus failing close returns `source_stream_close_failed`, leaks no file, and writes no
  snapshot/audit;
- short read plus failing close preserves `source_size_mismatch` and also leaks no file.

### PostgreSQL concurrency gate

A deterministic, no-sleep two-session test must prove:

1. transaction A holds the batch lock and creates a valid immediate-predecessor snapshot without
   committing;
2. generation N+1 analysis reaches and waits on that lock;
3. PostgreSQL lock evidence confirms the wait;
4. after A commits, N+1 re-queries under the lock and binds A's exact snapshot;
5. a changed structure becomes `review_required/structure_drift_from_previous_generation`;
6. an unchanged structure may be proposed but still binds A's exact snapshot; and
7. concurrent analyses of one artifact allocate distinct versions without a unique violation.

The PostgreSQL test may skip only in a declared local non-PostgreSQL environment. GitHub CI must fail
if its PostgreSQL URL is absent or if this test skips.

## 9. Commit and completion gates

Implementation order is binding:

1. `docs(S13-PR-003): freeze corrective evidence-gate addendum`;
2. bounded-region and row-classification runtime plus adversarial tests;
3. source fingerprint, lock ordering, drift lineage, and integration tests;
4. managed temporary-source cleanup and failure tests;
5. PostgreSQL serialization proof.

The corrective is not ready for independent audit until:

- focused corrective tests, the complete backend suite, Ruff, dependency audit, and security scan pass;
- Alembic still has exactly one head and upgrade/downgrade smoke passes;
- exact published-head GitHub CI passes with PostgreSQL/MinIO and the concurrency proof executed;
- the diff contains no staging, Apply, or official-line mutation;
- the PR remains Draft;
- a fresh Sol Max auditor evaluates the exact corrective head without participating in planning or
  implementation; and
- Antigravity independently audits that same exact head after the Sol Max audit.

Review rate may intentionally increase under v2. No threshold or boundary rule may be loosened
without an anonymized corpus, versioned evidence, and owner-approved design change.
