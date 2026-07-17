# S13-PR-002 Implementation Report (Corrective)

**Task ID:** S13-PR-002  
**PR:** #15  
**Branch:** `s13-pr-002-legacy-workbook-source-artifact`  
**Base:** `949903f3912aa65f8b990852756aeef7981bca08`  
**Pre-corrective audited head:** `eb0fc0de7eb0b6843e9a79ec0f14abd092bd5374`  
**Status:** **DRAFT — NOT READY / NOT MERGED** (await independent re-audit)

---

## Corrective scope (B-01 … B-07)

| ID | Blocker | Closure |
| --- | --- | --- |
| B-01 | `.xls` fail-closed presence | `xls_safety.py` olefile inventory + BIFF FILEPASS/SUPBOOK/EXTERNNAME; tests for VBA name, FILEPASS, external SUPBOOK |
| B-02 | Merged regions both formats | OOXML `xlsx_merge.py`; xlrd formatting_info + BIFF MERGEDCELLS; max_merged limits; malformed ref reject |
| B-03 | Full bounded inspection | `inspect()` exhausts rows/cells for char/row/total cell limits; reject before reserve/object write (`test_reject_oversized_cell_before_object_write`) |
| B-04 | Blank/duplicate positional | `ragged_rows=False`; full sheet width; xlsx pad to max_column; production-like header/data tests |
| B-05 | DB immutability / tenant | RESTRICT FKs; composite tenant FK; state/format/generation/size/checksum checks; batch unique (org,project,id); model FK on `current_source_artifact_id` |
| B-06 | Storage/reconciler truth | head/delete distinguish NotFound vs error; tenant+actor required; available terminal; residual failed→orphan; audit only after verified delete; errors counter |
| B-07 | Executable proof matrix | Expanded `test_s13_pr_002_source_artifacts.py` |

---

## Dependencies

- `xlrd>=2.0.1,<3`
- `olefile>=0.46`
- `boto3>=1.34.0`
- `xlwt` (dev fixtures)

Migration: `f2a3b4c5d6e7` (revised in place pre-merge) ← `e1f2a3b4c5d6`

---

## API / S12 boundary

Unchanged: S12 upload remains `.xlsx` staging v1; source-artifact path is separate; no staging/`ProjectAssetLine` mutation.

---

## Known limitations (true non-goals only)

- No Sprint 15 job scheduler for reconciler
- No signed download URLs
- No S13-PR-003 mapping/discovery
- Not a general malware sandbox beyond presence + bounds + no execution

---

## Gates

Local focused S13 suite green; full suite + exact-head CI recorded after push.
