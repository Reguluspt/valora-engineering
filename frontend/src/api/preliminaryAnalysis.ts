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

export interface PreliminaryAnalysisAttemptClaim {
  command_id: string;
  expected_analysis_version: number;
  expected_project_version: number;
  import_batch_id: string;
  source_artifact_id: string;
  source_generation: number;
  source_checksum_sha256: string;
  structure_snapshot_id: string;
  mapping_decision_id: string;
  mapping_profile_usage_id: string;
  selection_revision: number;
  mapping_decision_digest_sha256: string;
  profile_usage_mapping_digest_sha256: string;
}

export interface PreliminaryAnalysisAttempt {
  attempt_id: string;
  status: "RECEIVED" | "IN_PROGRESS" | "UNKNOWN" | "COMMITTED" | "REJECTED_TERMINAL";
  state_version: number;
  execution_generation: number;
  committed_snapshot_id: string | null;
}

export interface PreliminaryAnalysisAttemptState {
  blocked: boolean;
  base_analysis_version?: number;
  active_attempt?: PreliminaryAnalysisAttempt;
}

export interface PreliminaryAnalysisFinalizeRequest {
  attempt_id: string;
  expected_analysis_version: number;
  expected_project_version: number;
  import_batch_id: string;
  source_artifact_id: string;
  structure_snapshot_id: string;
  mapping_decision_id: string;
  mapping_profile_usage_id: string;
  mapping_decision_digest_sha256: string;
  profile_usage_mapping_digest_sha256: string;
  line_manifest: (PreliminaryAnalysisLineItem & { staging_row_id: string })[];
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

const projectPath = (projectId: string) => `/api/v1/projects/${encodeURIComponent(projectId)}`;
const attemptPath = (projectId: string) => `${projectPath(projectId)}/preliminary-analysis-attempts`;
const sessionHeaders = (sessionIncarnation: string) => ({ "X-Valora-Session-Incarnation": sessionIncarnation });

export function claimPreliminaryAnalysisAttempt(
  projectId: string, payload: PreliminaryAnalysisAttemptClaim, sessionIncarnation: string,
) {
  return request<PreliminaryAnalysisAttempt>(attemptPath(projectId), {
    method: "POST", body: JSON.stringify(payload), headers: sessionHeaders(sessionIncarnation),
  }, true);
}

export function getPreliminaryAnalysisAttemptState(projectId: string, sessionIncarnation: string) {
  return request<PreliminaryAnalysisAttemptState>(attemptPath(projectId), {
    headers: sessionHeaders(sessionIncarnation),
  }, true);
}

export function getPreliminaryAnalysisAttempt(projectId: string, attemptId: string, sessionIncarnation: string) {
  return request<PreliminaryAnalysisAttempt>(`${attemptPath(projectId)}/${encodeURIComponent(attemptId)}`, {
    headers: sessionHeaders(sessionIncarnation),
  }, true);
}

export function reconcilePreliminaryAnalysisAttempt(
  projectId: string, attempt: PreliminaryAnalysisAttempt, sessionIncarnation: string,
  reason: "request_abandoned" | "executor_unresponsive",
) {
  return request<PreliminaryAnalysisAttempt>(`${attemptPath(projectId)}/${encodeURIComponent(attempt.attempt_id)}/reconcile`, {
    method: "POST",
    body: JSON.stringify({
      expected_state_version: attempt.state_version,
      expected_execution_generation: attempt.execution_generation,
      reason,
    }),
    headers: sessionHeaders(sessionIncarnation),
  }, true);
}

export function finalizePreliminaryAnalysis(
  projectId: string, payload: PreliminaryAnalysisFinalizeRequest, sessionIncarnation: string,
): Promise<PreliminaryAnalysisCommandResponse> {
  return request<PreliminaryAnalysisCommandResponse>(`${projectPath(projectId)}/preliminary-analyses`, {
    method: "POST", body: JSON.stringify(payload), headers: sessionHeaders(sessionIncarnation),
  }, true);
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
