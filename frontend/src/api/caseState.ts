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

export interface CaseStateResponse {
  case_version: string;
  current_stage: CaseStage;
  next_action: CaseStateNextAction | null;
  stages: CaseStateStage[];
  blockers: CaseStateIssue[];
  warnings: CaseStateIssue[];
  stale: Record<string, unknown>[];
  capabilities: CaseStateCapability[];
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
