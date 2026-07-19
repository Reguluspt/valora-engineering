# S13-PR-003 Second Corrective Evidence-Gate Addendum — Unicode, Adjacent Tables, and Bounded History

**Date:** 2026-07-18
**Status:** frozen before second-corrective runtime changes
**Failed audited remote head:** `abd8556794d8599dd2ed27c4fdd4ca93924b27f7`
**Failed audited tree:** `1440ceac50f4b79be488ef747fef0ed280d8acd1`
**Branch:** `s13-pr-003-workbook-structure-discovery`

This addendum is binding after the independent Sol Max audit returned **FAIL** for the head above. It
supplements the original design and the first corrective addendum. All previously closed H-03, M-01,
M-02, tenant/RBAC, append-only, no-staging, no-official-line, source-integrity, and PostgreSQL
serialization gates remain binding regression requirements.

## 1. Findings in scope

The second corrective must close every finding from the failed audit:

1. adjacent horizontal tables without an empty separator can be merged and proposed when a later
   table starts with `Mã tài sản` rather than a repeated `STT`;
2. accent folding collides `TỔNG CỘNG TỶ LỆ` with the `Tổng công ty` non-marker exception;
3. `đ/Đ` does not fold to `d`, losing common Vietnamese header vocabulary;
4. snapshot-history listing reads, returns, and integrity-verifies an unbounded history; and
5. committed trailing spaces contradicted the claimed `git diff --check` evidence.

No semantic column mapping, staging materialization, Apply behavior, asset identity, pricing, UI, or
S13-PR-004 work is authorized.

## 2. Version and compatibility contract

The analysis rule version changes from `s13-pr-003-v2` to `s13-pr-003-v3`. This bump is mandatory
because normalization, marker classification, header vocabulary, horizontal partitioning,
disposition, and canonical digest may change for the same workbook.

The explicit read allowlist is:

```text
s13-pr-003-v1
s13-pr-003-v2
s13-pr-003-v3
```

- New analysis creates only v3 snapshots.
- Valid v1 and v2 snapshots remain byte-for-byte replayable; no rewrite or backfill is allowed.
- V1 does not require a `drift_reference`.
- V2 and v3 require the version-appropriate drift-reference contract.
- An unknown rule version fails closed as `structure_snapshot_integrity_failure`.
- A v1 or v2 predecessor used by a v3 analysis forces
  `structure_rule_version_changed/review_required`.
- No database migration is required.

The v3 stored rule configuration adds:

| Parameter | Value |
| --- | ---: |
| `header_group_min_families` | 3 |
| `header_group_min_columns` | 3 |
| `header_group_start_lookback` | 2 |
| `repeated_core_family_threshold` | 2 |

All v2 bounded-region parameters remain unchanged and stored.

## 3. Two-channel Unicode normalization

### Surface channel

`surface_normalized` applies NFKC, `casefold()`, and whitespace collapse while preserving Vietnamese
diacritics and `đ`. It is authoritative for marker semantics and must distinguish:

```text
tổng cộng tỷ lệ
tổng công ty
```

### Search channel

`search_normalized` starts from the surface channel, applies NFD, removes combining marks, maps
`đ → d`, and collapses whitespace. It is used for header vocabulary, header role families,
serial/outline matching, and accent-insensitive fallback evidence.

Required results include:

```text
ĐVT         → dvt
Đặc điểm    → dac diem
Đơn giá     → don gia
Đơn vị tính → don vi tinh
```

Phrase matching uses token boundaries. Punctuation such as `:`, `-`, `–`, and `—` is a boundary;
arbitrary substring matches are forbidden.

## 4. Marker evidence and classification

Marker evaluation is tri-state:

```text
recognized marker | no marker | ambiguous folded marker
```

Classification precedence is:

```text
EMPTY → recognized marker → ambiguous marker as UNRESOLVED
→ strong serial-led ASSET → other UNRESOLVED
```

Header eligibility rejects both recognized and ambiguous markers.

Surface Vietnamese vocabulary:

- total: `tổng`, `tổng cộng`, `tổng giá trị`, `tổng thành tiền`, `total`;
- subtotal: `cộng phần`, `cộng mục`, `tạm tính`, `subtotal`;
- note: `ghi chú`, `chú thích`, `note`, or leading `*`;
- section: `phần`, `chương`, `mục`, `hạng mục`.

Required behavior:

| Row | Class |
| --- | --- |
| `[99, "TỔNG CỘNG TỶ LỆ", 100]` | `total` |
| `[99, "TỔNG CỘNG TỶ TRỌNG", 100]` | `total` |
| `[1, "Tổng công ty ABC", 100]` | `asset` |
| `[1, "TONG CONG TY ABC", 100]` | `unresolved/ambiguous_folded_marker` |
| `["TONG CONG"]` | `total` |

The accented `Tổng công ty` exception is decided only through the surface channel. The folded prefix
`tong cong ty` is insufficient to choose between corporation text and `tổng cộng tỷ...`; if surface
evidence cannot disambiguate it, the row is unresolved and may not fall through to asset.

## 5. Adjacent horizontal header groups

V3 assigns exact token-phrase header roles:

| Family | Phrases |
| --- | --- |
| `START_INDEX` | `stt`, `số thứ tự` |
| `START_ID` | `mã tài sản`, `mã vật tư`, `mã hàng hóa` |
| `NAME` | `tên tài sản`, `tên vật tư`, `tên hàng hóa` |
| `DESCRIPTION` | `đặc điểm`, `quy cách`, `mô tả` |
| `UNIT` | `đvt`, `đơn vị tính` |
| `MEASURE` | `số lượng`, `khối lượng` |
| `VALUE` | `đơn giá`, `thành tiền`, `giá tđ`, `giá thẩm định` |
| `NOTE` | `ghi chú` |

Bare `mã` is not a start anchor.

A complete header group:

1. starts at a `START_INDEX` or `START_ID` anchor;
2. contains at least one `NAME`;
3. contains at least one of `MEASURE|UNIT|VALUE|DESCRIPTION`; and
4. spans at least three header-evidence columns.

For every occupied column run:

1. collect positional role families and start anchors;
2. segment from each start anchor to the column before the next start anchor;
3. when at least two segments are complete groups, discard the covering candidate;
4. emit one candidate per complete segment;
5. attach `multiple_horizontal_table_groups` to every emitted child; and
6. force `review_required`.

A single table `STT | Mã tài sản | Tên tài sản | Số lượng` is not split: the `STT`-only first
segment is incomplete, so only one complete group exists.

If confident partitioning is impossible but two non-overlapping
`NAME + (MEASURE|UNIT|VALUE)` bundles repeat, each with non-empty header evidence no more than two
columns before it, do not guess bounds. Attach `ambiguous_horizontal_table_boundary` and force review.

Required attack result:

```text
A:C = STT | Tên tài sản | Số lượng
D:F = Mã tài sản | Tên tài sản | Số lượng

candidate A:C + candidate D:F
no covering proposed candidate A:F
disposition = review_required
reason = multiple_horizontal_table_groups
```

Candidates are deduplicated by sheet, header start/end, and min/max columns. The retained candidate
uses the greatest confidence and the union of boundary flags.

## 6. Bounded snapshot-history API

The list response body remains `list[WorkbookStructureSnapshotResponse]`; no response envelope or
item-schema change is allowed.

Query parameters:

| Parameter | Contract |
| --- | --- |
| `limit` | default 20, minimum 1, maximum 50 |
| `cursor` | optional non-negative last-seen `snapshot_version` |

The scoped query is stable and append-safe:

```sql
WHERE snapshot_version > :cursor
ORDER BY snapshot_version ASC
LIMIT :limit_plus_one
```

At most `limit` items are returned. Response headers are:

- `X-Valora-Page-Limit: <effective limit>`;
- `X-Valora-Next-Cursor: <last returned version>` only when another item exists.

`cursor` beyond the latest version returns `[]`. Invalid bounds return 422. Existing callers that
omit parameters still receive the same JSON array shape, now bounded to the first 20 records. OpenAPI
documents both response headers.

## 7. Bounded bulk integrity verification

Per-item database queries are forbidden in list verification.

Verification is separated into:

1. pure core verification: digest, rule/disposition/count, source binding, supported rule version,
   rule-specific drift-reference shape and syntax;
2. one bounded context load for the requested page; and
3. pure in-memory link verification.

For a page of one through fifty snapshots, the maximum query budget is:

| Query | Maximum |
| --- | ---: |
| target artifact | 1 |
| page `limit + 1` | 1 |
| immediate durable predecessor | 1 |
| referenced artifacts, one scoped `IN` query | 1 |
| referenced snapshots, one scoped `IN` query | 1 |
| total | 5 |

Referenced snapshot validation is direct; it must not recursively walk an unbounded generation chain.
Only returned page items are verified. Any corrupt item in the page fails the entire request with the
stable integrity error; corruption outside the page is not read during that page request. Get-one
uses the same bounded verifier with a one-item page.

## 8. Required evidence

Tests must prove:

- two and three adjacent complete header groups partition and force review;
- the single-table `STT | Mã tài sản | Tên tài sản | Số lượng` does not split;
- repeated value labels alone do not split;
- an unknown second start with repeated core bundles fails closed;
- empty separators and v2 trailing-header/vertical/remote-note behavior do not regress;
- both Unicode channels and every required marker collision case above;
- `ĐVT`, `Đặc điểm`, `Đơn giá`, and `Đơn vị tính` regain vocabulary evidence;
- two v3 executions are deterministic, while v2/v3 digest differences are expected;
- 55 valid snapshots paginate as 20/20/15 without duplicates or loss;
- explicit limit 50, invalid parameters, cursor past end, append-between-pages, tenant-safe 404, headers,
  and unchanged item/body schema;
- page-local corruption fails while off-page corruption is not read;
- one-item and fifty-item referenced pages each stay within five SQL statements;
- valid v1 and v2 replay, unknown versions fail, and legacy evidence is never rewritten;
- H-03, M-01, M-02, PostgreSQL version serialization, source cleanup, no-staging, and
  no-`ProjectAssetLine` mutation remain green.

## 9. Process correction

The first corrective addendum's four Markdown hard-break spaces are removed without semantic change.
Audit trail:

- prior blob: `d02c79c82a8c8b6f19f204c85dc8ee77b026c404`;
- sanitized blob: `89e4d3756774844de2ad67a6f8daac3856301f18`.

CI adds a committed-content hygiene gate:

- pull request: `git diff --check BASE_SHA...HEAD_SHA` with full history available;
- push: `git show --check --format= HEAD_SHA`.

Bare worktree-only `git diff --check` is not acceptable PR evidence. Before an audit request, both:

```text
git diff --check 137f8c527422b656974e569c924dafa8150b8b22..CORRECTIVE_HEAD
git show --check --oneline CORRECTIVE_HEAD
```

must exit zero without whitespace errors.

## 10. Commit and audit order

1. `docs(S13-PR-003): freeze second corrective evidence gate`;
2. `fix(S13-PR-003): separate adjacent header groups and harden Unicode semantics`;
3. `fix(S13-PR-003): bound snapshot listing and batch integrity verification`;
4. `ci(S13-PR-003): enforce committed whitespace hygiene`.

Before independent audit: focused and full backend suites, Ruff, security/dependency gates, Alembic
single-head/live upgrade, PostgreSQL/MinIO, worker/frontend, pagination query budget, and committed
whitespace hygiene must pass on the exact published head.

The PR remains Draft. A fresh Sol Max auditor evaluates the new exact head/tree after exact-head CI.
Only a Sol Max PASS may open Antigravity audit on that same head/tree. Codex and implementers do not
self-issue PASS, mark Ready, or merge.
