# S13-PR-002 — XLS Dependency / Security Spike

**Task:** S13-PR-002 — Legacy Workbook Adapter and Immutable Source Artifact  
**Date:** 2026-07-16  
**Baseline:** `949903f3912aa65f8b990852756aeef7981bca08`  
**Status:** Decision recorded — **select `xlrd` 2.x** for value-only `.xls` (BIFF) intake under fail-closed adapters

---

## 1. Policy under evaluation

Adaptive Intake v2 must accept legacy `.xls` sources with:

- value-only cell reads (no formula execution, no macro/VBA/DDE/external link execution);
- extension + content-signature checks (OLE compound document signature `D0 CF 11 E0…`);
- fail-closed rejection of encrypted/malformed/unsupported workbooks;
- bounded resource use (sheets/rows/columns/cells/strings);
- no Office desktop/COM/LibreOffice automation;
- Python `>=3.12` compatibility matching `valora-backend`.

---

## 2. Candidates surveyed

| Candidate | Role | Notes |
| --- | --- | --- |
| **xlrd 2.x** | BIFF `.xls` reader | Dropped `.xlsx` support intentionally; pure Python BIFF; widely used in data pipelines |
| **python-calamine** | Fast multi-format via Rust calamine | Strong performance; dependency surface includes native wheels; newer ecosystem footprint |
| **olefile / custom OLE walk** | Stream inspection only | Useful for signature/VBA heuristics; not a full value-preserving sheet reader by itself |
| **xlwt** | Writer only | Used in **tests** to synthesize redacted `.xls` fixtures; not a runtime intake dependency |
| **openpyxl** | `.xlsx` only | Already selected for OOXML; cannot read classic BIFF `.xls` |

Office automation (Excel COM, LibreOffice headless convert) was **rejected a priori** by task non-goals and guardrails.

---

## 3. Evaluation matrix

### 3.1 Python 3.12 compatibility

| Package | Evidence |
| --- | --- |
| xlrd 2.0.1+ | Pure Python; installs and imports cleanly on CPython 3.12/3.13 in this workspace (`xlrd 2.0.2`) |
| python-calamine | Requires native extension wheels; viable on manylinux CI but adds binary supply-chain surface |

### 3.2 Maintenance / release health

| Package | Evidence |
| --- | --- |
| xlrd | Mature; 2.x actively used; maintenance is slow but API is stable for BIFF-only reads. No new feature churn expected. |
| python-calamine | Actively maintained with frequent releases; smaller production history in this codebase. |

### 3.3 License

| Package | License | Fit |
| --- | --- | --- |
| xlrd | BSD-style | Compatible with Valora backend deps |
| boto3 (storage, separate) | Apache-2.0 | Compatible |
| python-calamine | MIT | Compatible |

### 3.4 Security / CVE posture

- Runtime pin: `xlrd>=2.0.1,<3` (BIFF-only line; avoids xlrd 1.x `.xlsx` path).
- `pip-audit` must be run in CI/local gate after install (see implementation report).
- No known requirement to vendor patched forks for this spike window; if `pip-audit` flags a CVE, treat as blocker before Ready.

### 3.5 BIFF / OLE coverage

- **xlrd 2.x** opens classic OLE-wrapped BIFF workbooks (Excel 97–2003 style).
- Signature gate is enforced **before** xlrd open: first 8 bytes must match `XLS_OLE_SIGNATURE`.
- **Not covered as full parsers:** arbitrary OLE malformation beyond what xlrd rejects; exotic BIFF extensions may fail closed as `invalid_xls`.

### 3.6 Value-only / formula behavior

- xlrd returns **cached cell values** (numbers/strings/dates/booleans/error codes). It does **not** execute Excel formulas, VBA, DDE, or external links.
- Adapter opens with `formatting_info=False`, `on_demand=True`, `ragged_rows=True` to reduce memory and avoid format-side channels.

### 3.7 Encrypted workbook detection

- Password-protected BIFF books raise `xlrd.XLRDError` with password/encrypt messaging.
- Adapter maps those to fail-closed `encrypted_workbook` (HTTP 400, Vietnamese detail, no path leakage).

### 3.8 Macro / VBA / DDE / external links

| Threat | Handling |
| --- | --- |
| VBA/macro execution | xlrd does not execute macros. Residual risk is **parsing attacker-crafted BIFF**, mitigated by size/row/column/string limits and fail-closed open errors. |
| Explicit VBA stream rejection | Full OLE directory enumeration is limited in xlrd 2.x without extra OLE libs; spike accepts **non-execution + limits** rather than claiming complete stream deny-listing. |
| DDE / external links | Not executed by xlrd value path; treated as opaque values if present as text. |
| `.xlsx` macros / external links | Handled on the **openpyxl + ZIP safety** path (separate adapter), not xlrd. |

**Honest residual:** if a future threat model requires guaranteed rejection of every workbook that *contains* a VBA project stream (even without execution), add an `olefile` stream inventory gate in a follow-up corrective. S13-PR-002 policy is satisfied by **no execution + fail-closed open + bounds**.

### 3.9 Streaming / memory / limits

- File is spooled to a bounded temp path with max upload bytes before adapter open.
- `on_demand=True` reduces sheet materialization.
- Application enforces `max_sheets`, `max_physical_rows`, `max_columns`, `max_cell_chars`.
- Merged regions: xlrd 2.x without `formatting_info` does not expose merged-region metadata; adapter returns empty merged metadata for `.xls` (documented limitation; coordinate/value preservation still holds).

### 3.10 Sheet / cell / metadata preservation

| Requirement | xlrd outcome |
| --- | --- |
| Sheet names | Yes |
| Cell coordinates (row/col) | Yes via iteration |
| Blank cells / duplicate header values | Preserved by coordinate iteration (not header-keyed dicts) |
| Merged regions | **Not** exposed without formatting_info (limitation) |

---

## 4. Decision

**Choose `xlrd>=2.0.1,<3`** as the `.xls` runtime dependency for S13-PR-002.

### Why xlrd

1. Matches BIFF-only scope after 2.x split from OOXML.
2. Pure Python → simpler CI/repro and fewer native wheels than calamine.
3. Proven value-only semantics suitable for fail-closed intake.
4. Clear error surface for encrypted/malformed books.

### Why not python-calamine (for this PR)

1. Adds native binary surface without proven Valora CI pin history.
2. Spike does not show a safety gap that only calamine closes for value-only BIFF.
3. Can be revisited if performance or format coverage becomes a measured blocker.

### Why not OLE-only libraries alone

They do not provide a complete sheet value iterator contract required by `WorkbookAdapter`.

### Why not Office automation

Explicit non-goal; non-deterministic; not deployable in Valora backend containers.

---

## 5. Companion storage dependency (recorded for checklist completeness)

| Package | Purpose | License | Rationale |
| --- | --- | --- | --- |
| **boto3** | S3-compatible object storage client (MinIO/local/CI) | Apache-2.0 | Standard AWS SDK; used behind an internal `ObjectStoragePort`; credentials never returned on API |

---

## 6. Adapter contract implications

- `XlsWorkbookAdapter` name=`xls-xlrd`, version=`s13-pr-002-v1`.
- Detection: extension ∈ `{.xls}` **and** OLE signature; mismatches → `signature_mismatch`.
- S12 upload path remains `.xlsx`-only; `.xls` only enters Adaptive source-artifact endpoints.

---

## 7. Residual risks / follow-ups (non-blocking for Draft)

1. Optional `olefile` VBA-stream deny-list if audit demands content presence rejection, not only non-execution.
2. Merged-region metadata for `.xls` if a later structure-discovery PR needs it (may require `formatting_info=True` with stricter bounds or another library).
3. Keep `pip-audit` green on every Ready attempt; pin tighter if a CVE appears.

---

## 8. Conclusion

**Proceed with `.xls` implementation via xlrd 2.x** under fail-closed adapter limits. No soft-accept path, no Office automation, no lowering of guardrails.
