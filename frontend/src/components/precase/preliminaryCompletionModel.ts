import type { CaseStateResponse } from "../../api/caseState";
import type {
  CustomerBindRequest, OfficialIntakeRequest, ResultGenerateRequest,
} from "../../api/preliminaryCompletion";

export type CompletionAttempt =
  | { kind: "result"; payload: ResultGenerateRequest }
  | { kind: "customer"; payload: CustomerBindRequest }
  | { kind: "intake"; payload: OfficialIntakeRequest };

const stageResult = (state: CaseStateResponse, stage: string) =>
  state.stages.find((item) => item.stage === stage)?.result;

const pendingRoute = (state: CaseStateResponse, key: string) =>
  state.next_action?.kind === "PENDING" && state.next_action.semantic_route_key === key;

export function canGenerateResult(state: CaseStateResponse): boolean {
  const selected = state.preliminary;
  return Boolean(!selected.official_intake_commit_id && selected.current_preliminary_analysis_snapshot_id &&
    !selected.current_preliminary_result_artifact_id && state.blockers.length === 0 &&
    stageResult(state, "PRELIMINARY_READY") === "INCOMPLETE" &&
    pendingRoute(state, "preliminary_ready_pending"));
}

export function canBindCustomer(state: CaseStateResponse): boolean {
  const selected = state.preliminary;
  return Boolean(!selected.official_intake_commit_id && selected.current_preliminary_result_artifact_id &&
    !selected.customer_id);
}

export function canCommitIntake(state: CaseStateResponse, customerActive: boolean): boolean {
  const selected = state.preliminary;
  return Boolean(!selected.official_intake_commit_id && selected.current_preliminary_result_artifact_id &&
    selected.current_preliminary_result_version && selected.customer_id && customerActive &&
    state.blockers.length === 0 && stageResult(state, "OFFICIAL_INTAKE") === "INCOMPLETE" &&
    pendingRoute(state, "official_intake_pending"));
}

export function attemptCommitted(state: CaseStateResponse, attempt: CompletionAttempt): boolean {
  const selected = state.preliminary;
  if (attempt.kind === "result") return Boolean(selected.current_preliminary_result_artifact_id &&
    selected.current_preliminary_analysis_snapshot_id === attempt.payload.preliminary_analysis_snapshot_id);
  if (attempt.kind === "customer") return selected.customer_id === attempt.payload.customer_id;
  return Boolean(selected.official_intake_commit_id);
}

export function attemptRetryable(state: CaseStateResponse, attempt: CompletionAttempt, customerActive: boolean): boolean {
  const selected = state.preliminary;
  if (selected.project_row_version !== attempt.payload.expected_project_version) return false;
  if (attempt.kind === "result") return canGenerateResult(state) &&
    selected.current_preliminary_analysis_snapshot_id === attempt.payload.preliminary_analysis_snapshot_id;
  if (attempt.kind === "customer") return canBindCustomer(state) && customerActive;
  return canCommitIntake(state, customerActive) &&
    selected.current_preliminary_result_artifact_id === attempt.payload.preliminary_result_artifact_id &&
    selected.current_preliminary_result_version === attempt.payload.expected_preliminary_result_version;
}
