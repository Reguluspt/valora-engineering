import { request } from "./client";
import type { CANONICAL_CASE_STAGES } from "../contracts/valoraV23";

export type CaseStage = typeof CANONICAL_CASE_STAGES[number];
export type CaseStageResult =
  | "COMPLETE"
  | "IN_PROGRESS"
  | "INCOMPLETE"
  | "BLOCKED"
  | "STALE"
  | "NOT_APPLICABLE"
  | "NOT_AVAILABLE";

export interface CaseStateStage {
  stage: CaseStage;
  result: CaseStageResult;
  provider_key: string | null;
}

export interface CaseStateNextAction {
  kind: "BLOCKER" | "PENDING" | "UNAVAILABLE" | "NO_AUTHORIZED_DOWNSTREAM_ACTION";
  stage: CaseStage | null;
  semantic_route_key: string | null;
  validation_issue_id: string | null;
}

export interface CaseStateIssue {
  id: string;
  target_type: string;
  target_id: string;
  severity: "blocking" | "warning";
  status: "open";
  row_version: number;
}

export interface CaseStateCapability {
  stage: CaseStage;
  available: boolean;
  provider_key: string | null;
  version: string;
}

export interface PreliminarySelectionResponse {
  project_id: string;
  customer_id: string | null;
  project_row_version: number;
  current_preliminary_import_batch_id: string | null;
  current_source_artifact_id: string | null;
  current_preliminary_analysis_snapshot_id: string | null;
  current_preliminary_analysis_version: number | null;
  current_preliminary_result_artifact_id: string | null;
  current_preliminary_result_version: number | null;
  official_intake_commit_id: string | null;
}

export interface CaseStateResponse {
  case_version: string;
  current_stage: CaseStage;
  next_action: CaseStateNextAction | null;
  stages: CaseStateStage[];
  blockers: CaseStateIssue[];
  warnings: CaseStateIssue[];
  stale: Record<string, unknown>[];
  capabilities: CaseStateCapability[];
  preliminary: PreliminarySelectionResponse;
}

export function fetchCaseState(
  projectId: string,
  signal?: AbortSignal
): Promise<CaseStateResponse> {
  return request<CaseStateResponse>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/case-state`,
    { signal }
  );
}
