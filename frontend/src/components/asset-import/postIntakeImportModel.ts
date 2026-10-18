import type { CaseStateResponse, PostIntakeImportContext } from "../../api/caseState";
import type { AssetImportApplyResponse, ProjectAssetImportBatchResponse as Batch,
  ProjectAssetImportStagingRowPaginationResponse as Rows } from "../../api/assetImports";

export const APPLY_CONTRACT = "s12-post-intake-guarded-apply-v2";
export const PAGE_SIZE = 25;
export const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const TOKEN = /^[0-9a-f]{64}$/;
const integer = (n: number) => Number.isSafeInteger(n) && n >= 0;

export function importContext(p: CaseStateResponse | null, projectId: string): PostIntakeImportContext | null {
  const action = p?.next_action;
  const c = action?.context as PostIntakeImportContext | undefined;
  if (!p || !c || action?.kind !== "PENDING" || action.stage !== "ASSET_REVIEW" ||
      p.current_stage !== "ASSET_REVIEW" || p.blockers.length || p.stale.length ||
      p.stages.find(s => s.stage === "ASSET_REVIEW")?.result !== "INCOMPLETE" ||
      !p.capabilities.some(cap => cap.stage === "ASSET_REVIEW" && cap.available) ||
      !UUID.test(projectId) || c.project_id !== projectId || !TOKEN.test(p.case_version) ||
      c.case_version !== p.case_version ||
      ![c.official_intake_commit_id, c.result_id, c.batch_id, c.staging_usage_id].every(id => typeof id === "string" && UUID.test(id)) ||
      p.preliminary.project_id !== projectId ||
      c.official_intake_commit_id !== p.preliminary.official_intake_commit_id ||
      c.result_id !== p.preliminary.current_preliminary_result_artifact_id ||
      c.batch_id !== p.preliminary.current_preliminary_import_batch_id) return null;
  if (action.semantic_route_key === "asset_import_validate_pending" && c.kind === "validate" &&
      ["validation_required", "validation_retry"].includes(c.reason_code)) return c;
  if (action.semantic_route_key === "asset_import_apply_confirm" && c.kind === "apply" &&
      c.reason_code === "apply_required" && c.contract_version === APPLY_CONTRACT && c.confirmation_required === true) return c;
  return null;
}

export function targetKey(c: PostIntakeImportContext): string {
  return [c.project_id, c.official_intake_commit_id, c.result_id, c.batch_id,
    c.staging_usage_id, c.case_version, c.kind].join(":");
}

export function sameSelectedSource(p: CaseStateResponse, c: PostIntakeImportContext): boolean {
  const context = p.next_action?.context as (Partial<PostIntakeImportContext> & { batch_id?: string }) | null;
  return p.preliminary.project_id === c.project_id && p.preliminary.current_preliminary_import_batch_id === c.batch_id &&
    p.preliminary.official_intake_commit_id === c.official_intake_commit_id &&
    p.preliminary.current_preliminary_result_artifact_id === c.result_id &&
    context?.project_id === c.project_id && context.case_version === p.case_version &&
    (!context.batch_id || context.batch_id === c.batch_id) &&
    (!context.staging_usage_id || context.staging_usage_id === c.staging_usage_id);
}

export function coherentPage(batch: Batch, rows: Rows, projectId: string, batchId: string, offset: number): boolean {
  return batch.id === batchId && batch.project_id === projectId &&
    [batch.total_rows, batch.valid_rows, batch.invalid_rows, batch.warning_rows].every(integer) &&
    batch.valid_rows + batch.invalid_rows + batch.warning_rows <= batch.total_rows &&
    rows.project_id === projectId && rows.import_batch_id === batchId && rows.total === batch.total_rows &&
    rows.limit === PAGE_SIZE && rows.offset === offset && integer(rows.total) &&
    rows.items.length === Math.min(PAGE_SIZE, Math.max(0, rows.total - offset)) &&
    new Set(rows.items.map(row => row.id)).size === rows.items.length &&
    new Set(rows.items.map(row => row.source_row_number)).size === rows.items.length &&
    rows.items.every(row => UUID.test(row.id) && row.import_batch_id === batchId &&
      Number.isSafeInteger(row.source_row_number) && row.source_row_number > 0 &&
      ["pending", "valid", "invalid", "warning"].includes(row.validation_status) &&
      Array.isArray(row.validation_errors) && Array.isArray(row.validation_warnings));
}

export function allValid(batch: Batch, rows: Rows): boolean {
  return batch.status === "ready_for_review" && batch.total_rows > 0 && batch.valid_rows === batch.total_rows &&
    batch.invalid_rows === 0 && batch.warning_rows === 0 && rows.items.every(row => row.validation_status === "valid");
}

export function validApplyResponse(result: AssetImportApplyResponse, batch: Batch, rows: Rows): boolean {
  return result.project_id === batch.project_id && result.import_batch_id === batch.id && result.status === "applied" &&
    result.created_count === batch.total_rows && Array.isArray(result.created_lines) &&
    result.created_lines.length === result.created_count &&
    new Set(result.created_lines.map(line => line.line_id)).size === result.created_count &&
    new Set(result.created_lines.map(line => line.staging_row_id)).size === result.created_count &&
    new Set(result.created_lines.map(line => line.source_row_number)).size === result.created_count &&
    result.created_lines.every(line => UUID.test(line.line_id) && UUID.test(line.staging_row_id) &&
      Number.isSafeInteger(line.source_row_number) && line.source_row_number > 0) &&
    rows.items.every(row => result.created_lines.some(line => line.staging_row_id === row.id && line.source_row_number === row.source_row_number));
}

// Readback proves an existing promotion, never which interrupted request committed it.
export function promotionProven(p: CaseStateResponse, batch: Batch, target: PostIntakeImportContext): boolean {
  const action = p.next_action, c = action?.context;
  return batch.status === "applied" && batch.id === target.batch_id && batch.project_id === target.project_id &&
    batch.total_rows > 0 && p.preliminary.project_id === target.project_id &&
    p.preliminary.official_intake_commit_id === target.official_intake_commit_id &&
    p.preliminary.current_preliminary_result_artifact_id === target.result_id &&
    p.preliminary.current_preliminary_import_batch_id === target.batch_id && TOKEN.test(p.case_version) &&
    p.capabilities.some(cap => cap.stage === "ASSET_REVIEW" && cap.available) &&
    c?.project_id === target.project_id && c.case_version === p.case_version && action?.stage === "ASSET_REVIEW" &&
    ((action.kind === "PENDING" && c.kind === "line" && UUID.test(c.line_id || "") &&
      Number.isSafeInteger(c.membership_version) && c.membership_version! > 0 &&
      ["asset_review_line_validate_required", "asset_review_line_review_required"].includes(action.semantic_route_key || "")) ||
     (action.kind === "UNAVAILABLE" && c.kind === "permission" && c.reason_code === "session_required"));
}
