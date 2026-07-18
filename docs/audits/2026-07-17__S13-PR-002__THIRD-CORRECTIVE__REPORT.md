# S13-PR-002 Third Corrective Report

**PR:** #15 Draft  
**Branch:** `s13-pr-002-legacy-workbook-source-artifact`  
**Baseline:** `dd477089407ee9bc3e0b258b386fa417d8016532`  
**Status:** **DRAFT — NOT READY / NOT MERGED**

## B-01…B-08 closure

| ID | Fix | Tests |
| --- | --- | --- |
| B-01 | `iter_rows()` total-cell counter both adapters | `test_xlsx_iter_rows_total_cells_exact_and_max_plus_one`, `test_xls_iter_rows_total_cells_exact_and_max_plus_one` |
| B-02 | Only completed digest → checksum_mismatch; infra → ObjectStorageError | `test_reconciler_stream_timeout_not_checksum_mismatch`, `test_reconciler_true_checksum_mismatch` |
| B-03 | Per-item commit; counters after durable success | `test_reconciler_later_error_preserves_earlier_commit` |
| B-04 | Threat HTTP with prior current + staging field equality | `test_threat_upload_preserves_prior_staging_and_lines` |
| B-05 | Real PG DML same-batch OK / cross-batch IntegrityError | `test_pg_same_batch_pointer_dml_enforcement` |
| B-06 | Flip ref-check late before delete | `test_reconciler_late_ref_check_before_delete` |
| B-07 | Exact+max+1 samples, formula data_only, zip limits | third corrective suite |
| B-08 | CI full suite + MinIO required when CI=true | `test_s3_minio_required_in_ci` |

## Non-goals

S13-PR-003, AI, S12 Apply changes, Office automation.
