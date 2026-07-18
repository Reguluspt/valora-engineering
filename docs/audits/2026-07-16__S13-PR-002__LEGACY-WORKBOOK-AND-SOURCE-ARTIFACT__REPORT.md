# S13-PR-002 Implementation Report (Second Corrective)

**Task ID:** S13-PR-002  
**PR:** #15 (Draft)  
**Branch:** `s13-pr-002-legacy-workbook-source-artifact`  
**Base:** `949903f3912aa65f8b990852756aeef7981bca08`  
**Pre-corrective head:** `eb0fc0de7eb0b6843e9a79ec0f14abd092bd5374`  
**First corrective head:** `1c098f21766a380239bae5bac620ab7221c59fb7` (CI `29577487790` PASS; re-audit FAIL)  
**Second corrective head:** `994d6fdd9df73ad1fb4075e08ebff1bad8bcc9f1`  
**Exact tip:** `dcd9ac944cea3870bc71123cd5697855bf042775` (docs CI evidence only after code `994d6fd`)  
**CI on code+docs tip `d0880aa`:** run `29579039489` PASS (backend/frontend/worker; includes second corrective suite)  
**Local S13 suites:** 40 passed, 2 skipped (local MinIO; local PG constraint when no TEST_DATABASE_URL)  
**Status:** **DRAFT — NOT READY / NOT MERGED**

---

## R-01 … R-09 closure (second corrective)

| ID | Issue | Closure | Tests |
| --- | --- | --- | --- |
| R-01 | 4-byte add-in SUPBOOK accepted | Allow only `len==4` and `payload[2:4]==01 04` | `test_supbook_internal_accepted_addin_rejected`, `test_e2e_threat_xls_upload_rejected[addin_supbook]` |
| R-02 | Macro/DCON not scanned | BOUNDSHEET dt, NAME flags, DCON/DCONNAME/DCONREF | `test_biff_macro_and_dcon_rejected`, e2e macro/dconref |
| R-03 | Threat tests not E2E | Synthetic OLE fixtures via `ole_builder` → source-artifact POST | `test_e2e_threat_xls_upload_rejected[*]` |
| R-04 | BIFF merge fallback wrong | Removed fallback; require `formatting_info=True` sheet-local merges | `test_xls_multi_sheet_merges_independent`, `test_xls_merged_limit` |
| R-05 | Cross-batch current pointer | Composite FK `(batch.id, current_id) → (artifact.import_batch_id, artifact.id)` | `test_pg_same_batch_current_pointer_enforced` (PG/CI) |
| R-06 | Checksum not verified on reconcile | Stream SHA-256 pending objects | `test_reconciler_pending_checksum_mismatch` |
| R-07 | NoSuchBucket as not-found | Excluded from `_is_not_found_error` | `test_nosuchbucket_not_object_not_found` |
| R-08 | Ref-check incomplete | Early `if ref_check: continue` + re-check under lock before delete | `test_reconciler_ref_check_blocks` |
| R-09 | Incomplete matrix | Expanded second corrective suite | `test_s13_pr_002_second_corrective.py` + prior suite |

---

## Dependencies

- xlrd + **olefile** (presence detection)
- boto3; xlwt (dev)

Claims limited to what tests prove: presence reject for listed BIFF forms; pending reconcile **does** SHA-256 stream verify.

---

## Non-goals

- S15 job scheduler  
- Signed download URLs  
- S13-PR-003 mapping  
- Full malware sandbox beyond listed presence + bounds  

---

## Gates

Local S13 suites green; full suite + exact-head CI after push.
