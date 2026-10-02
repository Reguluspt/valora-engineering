import { request } from "./client";

export type ReviewDecision = "accepted" | "flagged" | "rejected";
export interface LineCommandRequest {
  command_id: string;
  confirm: true;
  expected_row_version: number;
  expected_case_version: string;
  contract_version: "asset-line-validation-v1" | "asset-line-human-review-v1";
  target_review_status?: ReviewDecision;
  reason_note?: string | null;
  supersedes_decision_id?: string | null;
}
export interface LineFinding {
  code: string;
  field: string;
  severity: "error" | "advisory";
  reference_id: string | null;
}
export interface LineCommandResponse {
  result: {
    command_id: string;
    receipt_id: string;
    project_id: string;
    line_id: string;
    proof_id: string;
    contract_version: LineCommandRequest["contract_version"];
    line_row_version: number;
    created_at: string;
    validation_outcome: "valid" | "invalid" | "warning" | null;
    validation_generation: number | null;
    target_review_status: ReviewDecision | null;
    decision_version: number | null;
    reversal_id: string | null;
    findings: LineFinding[];
  };
  replayed: boolean;
  historical: boolean;
  current_case_version: string;
}
const linePath = (projectId: string, lineId: string) =>
  `/api/v1/projects/${encodeURIComponent(projectId)}/asset-lines/${encodeURIComponent(lineId)}`;

export function submitAssetReview(projectId: string, lineId: string, payload: LineCommandRequest) {
  return request<LineCommandResponse>(`${linePath(projectId, lineId)}/${
    payload.contract_version === "asset-line-validation-v1" ? "validate" : "review-decision"
  }`, { method: "POST", body: JSON.stringify(payload) });
}
export function fetchAssetReviewReceipt(projectId: string, lineId: string, commandId: string) {
  return request<LineCommandResponse>(`${linePath(projectId, lineId)}/command-receipts/${encodeURIComponent(commandId)}`);
}
