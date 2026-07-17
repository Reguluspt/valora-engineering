# S13-PR-002 — XLS Dependency / Security Spike (Corrective)

**Task:** S13-PR-002 — Legacy Workbook Adapter and Immutable Source Artifact  
**Date:** 2026-07-16 (corrective 2026-07-17)  
**Baseline:** `949903f3912aa65f8b990852756aeef7981bca08`  
**Audited draft head (pre-corrective):** `eb0fc0de7eb0b6843e9a79ec0f14abd092bd5374`  
**Status:** Decision — **`xlrd` 2.x + `olefile`** for value-only BIFF with **presence-based** fail-closed gates

---

## 1. Policy

Adaptive Intake v2 must **detect and reject presence** of:

- encrypted/FILEPASS;
- VBA/macro project streams;
- external workbook links (SUPBOOK > internal self-ref);
- EXTERNNAME / DCONNAME external naming;
- malformed/unsupported OLE/BIFF.

Non-execution alone is **not** sufficient.

---

## 2. Selected stack

| Package | Pin | Role | License |
| --- | --- | --- | --- |
| **xlrd** | `>=2.0.1,<3` | BIFF value-only cells + optional merged_cells | BSD |
| **olefile** | `>=0.46` | OLE stream inventory + Workbook stream read | BSD |
| openpyxl | existing | `.xlsx` only | MIT |

Python: `>=3.12` (verified on 3.12 CI / 3.13 local).

### Why not python-calamine

Native wheels add supply-chain surface without proving better presence detection for this PR. Revisit only if BIFF coverage blocks a measured case.

### Why not Office automation

Explicit non-goal.

---

## 3. Presence detection design

1. **OLE signature** `D0 CF 11 E0…`
2. **`olefile.listdir()`** — reject stream/storage names matching VBA/macro patterns (`_VBA_PROJECT_CUR`, `vba`, `macrosheet`, …)
3. **Bounded BIFF scan** of Workbook/Book stream:
   - `FILEPASS (0x002F)` → `encrypted_workbook`
   - `SUPBOOK (0x01AE)` with length **> 4** → `external_link_not_allowed` (internal self-ref is 4 bytes)
   - `EXTERNNAME` / `DCONNAME` non-empty → `external_link_not_allowed`
4. **xlrd open** after presence gates; map password errors → `encrypted_workbook`
5. **Merged cells:** `formatting_info=True` when supported; else parse `MERGEDCELLS (0x00E5)` from BIFF
6. **Positional cells:** `ragged_rows=False`; emit full sheet width including trailing blanks

Error codes (stable): `encrypted_workbook`, `macro_not_allowed`, `external_link_not_allowed`, `invalid_xls`, `signature_mismatch`, limit codes.

Vietnamese details; no internal paths.

---

## 4. CVE / pip-audit

CI runs `pip-audit` after install. Block Ready if critical findings on xlrd/olefile/boto3.

---

## 5. Residual (non-goal honesty)

- Not a full antivirus/OLE exploit sandbox — resource bounds + presence reject + no code execution.
- Exotic BIFF extensions fail closed as `invalid_xls` when unreadable.
- Full CFB malicious polyglot corpus is out of scope; synthetic BIFF/OLE name fixtures prove policy paths.

---

## 6. Conclusion

**Proceed** with xlrd + olefile presence-based fail-closed `.xls` intake. Corrective closes independent audit B-01 for presence detection.
