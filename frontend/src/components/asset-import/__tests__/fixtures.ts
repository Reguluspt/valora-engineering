import type { CaseStateResponse, PostIntakeImportContext } from "../../../api/caseState";
import type { ProjectAssetImportBatchResponse as Batch, ProjectAssetImportStagingRowPaginationResponse as Rows } from "../../../api/assetImports";
import { CANONICAL_CASE_STAGES } from "../../../contracts/valoraV23";
export const id = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
export const target = (kind: "validate" | "apply" = "validate"): PostIntakeImportContext => ({
  project_id: id(1), batch_id: id(2), result_id: id(3), official_intake_commit_id: id(4), staging_usage_id: id(5),
  case_version: (kind === "validate" ? "a" : "b").repeat(64),
  ...(kind === "validate" ? { kind, reason_code: "validation_required" } :
    { kind, reason_code: "apply_required", confirmation_required: true, contract_version: "s12-post-intake-guarded-apply-v2" }),
});
export function projection(kind: "validate" | "apply" = "validate"): CaseStateResponse {
  const context = target(kind);
  return { case_version: context.case_version, current_stage: "ASSET_REVIEW",
    next_action: { kind: "PENDING", stage: "ASSET_REVIEW", semantic_route_key: kind === "validate" ? "asset_import_validate_pending" : "asset_import_apply_confirm",
      validation_issue_id: null, context },
    stages: CANONICAL_CASE_STAGES.map(stage => ({ stage, result: "INCOMPLETE", provider_key: "asset_review_line_decision_v1" })),
    blockers: [], warnings: [], stale: [], capabilities: [{ stage: "ASSET_REVIEW", available: true, provider_key: "asset_review_line_decision_v1", version: "v1" }],
    preliminary: { project_id: id(1), customer_id: id(8), project_row_version: 4, current_preliminary_import_batch_id: id(2),
      current_source_artifact_id: id(6), current_preliminary_analysis_snapshot_id: id(7), current_preliminary_analysis_version: 1,
      current_preliminary_result_artifact_id: id(3), current_preliminary_result_version: 1, official_intake_commit_id: id(4) } };
}
export const batch = (valid = false): Batch => ({ id: id(2), project_id: id(1), status: valid ? "ready_for_review" : "parsed",
  source_filename: "Tài sản.xlsx", source_sheet_name: "Danh mục", total_rows: 3, valid_rows: valid ? 3 : 0,
  invalid_rows: 0, warning_rows: 0, created_at: "2026-10-18", updated_at: "2026-10-18" });
export const rows = (valid = false): Rows => ({ project_id: id(1), import_batch_id: id(2), total: 3, limit: 25, offset: 0,
  items: [11, 12, 13].map(n => ({ id: id(n), import_batch_id: id(2), source_row_number: n,
    validation_status: valid ? "valid" : "pending", validation_errors: [], validation_warnings: [], proposed_asset_name: `Tài sản ${n}`, proposed_quantity: "1.00" })) });
export const applied = () => {
  const p = projection("apply"); p.case_version = "c".repeat(64);
  p.next_action = { kind: "UNAVAILABLE", stage: "ASSET_REVIEW", semantic_route_key: null, validation_issue_id: null,
    context: { kind: "permission", project_id: id(1), case_version: p.case_version, reason_code: "session_required" } };
  return p;
};
