import { request } from "./client";

export interface PreliminaryAnalysisLineItem {
  identity: string;
  accepted_price_basis: string;
  confirmed_reference_price: number;
  transport_percentage: number;
  proposed_unit_price: number;
  human_line_confirmed: boolean;
  has_unresolved_blocking_line: boolean;
  source_row_number: number;
  quantity: number;
}

export interface PreliminaryAnalysisFinalizeRequest {
  expected_project_version: number;
  import_batch_id: string;
  source_artifact_id: string;
  structure_snapshot_id: string;
  mapping_decision_id: string;
  mapping_profile_usage_id: string;
  mapping_decision_digest_sha256: string;
  profile_usage_mapping_digest_sha256: string;
  line_manifest: PreliminaryAnalysisLineItem[];
  idempotency_key: string;
  confirmed: boolean;
}

export interface PreliminaryAnalysisCommandResponse {
  id: string;
  project_id: string;
  version: number;
  expected_project_version: number;
  import_batch_id: string;
  source_artifact_id: string;
}

export interface PreliminaryAnalysisReadResponse {
  id: string;
  project_id: string;
  version: number;
  import_batch_id: string;
  source_artifact_id: string;
  structure_snapshot_id: string;
  mapping_decision_id: string;
  mapping_profile_usage_id: string;
  mapping_decision_digest_sha256: string;
  profile_usage_mapping_digest_sha256: string;
  line_manifest: PreliminaryAnalysisLineItem[];
  line_manifest_digest_sha256: string;
  finalized_by_user_id: string;
  finalized_at: string;
}

export function finalizePreliminaryAnalysis(
  projectId: string,
  payload: PreliminaryAnalysisFinalizeRequest
): Promise<PreliminaryAnalysisCommandResponse> {
  return request<PreliminaryAnalysisCommandResponse>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/preliminary-analyses`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export function getPreliminaryAnalysis(
  projectId: string,
  analysisId: string,
  signal?: AbortSignal
): Promise<PreliminaryAnalysisReadResponse> {
  return request<PreliminaryAnalysisReadResponse>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/preliminary-analyses/${encodeURIComponent(analysisId)}`,
    { signal }
  );
}
