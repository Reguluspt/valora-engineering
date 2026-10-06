import { request } from "./client";

export type EvidenceCategory = "internet_survey" | "unit_price_explanation" | "prior_appraisal_result";
export interface ObservedValue {
  amount: string; range_upper: string | null; currency: string; unit_basis: string; quantity_basis: string;
  tax: string; delivery: string; condition: string; locator: string;
}
export interface SourceMaterial {
  category: EvidenceCategory; origin: string; reference: string | null; locator: string;
  effective_date: string | null; unknown_date_reason: string | null; captured_at: string;
  capture_method: "manual_transcription" | "authored_explanation"; retained_text: string; limitations: string;
  value: ObservedValue | null; expires_at: string | null;
  explanation: { method: "sum_of_scaled_source_values"; inputs: { evidence_revision_id: string; coefficient: string }[];
    assumptions: string; calculations: string; units: string; currency: string; proposed_basis_value: string } | null;
  historical: { project_id: string; line_id: string; appraisal_date: string; result_excerpt: string;
    result_locator: string; result_value: ObservedValue } | null;
}
export interface EvidenceDecisionView {
  decision_id: string; relationship_id: string; evidence_revision_id: string; line_id: string;
  outcome: "accepted" | "rejected"; disposition: "qualifying_basis" | "excluded_alternative" | "unresolved_concern";
  qualifying: boolean; withdrawn: boolean; review_due_at: string; review_expired: boolean;
  unresolved_concern: boolean; can_withdraw: boolean;
}
export interface EvidenceSourceView {
  source_id: string; evidence_revision_id: string; revision: number; predecessor_revision_id: string | null;
  category: EvidenceCategory; origin: string; effective_date: string | null; date_unknown: boolean;
  captured_at: string; expires_at: string | null; expired: boolean; current: boolean; withdrawn: boolean; eligible: boolean;
  can_correct: boolean; can_withdraw: boolean; can_accept: boolean; can_reject: boolean;
  explanation_input_eligible: boolean; decision: EvidenceDecisionView | null;
}
export interface EvidenceWorkspace {
  project_id: string; case_version: string; line_id: string | null; covered_count: number | null; sealed_count: number;
  confirmation_id: string | null; confirmation_withdrawn: boolean; confirmation_current: boolean;
  can_withdraw_confirmation: boolean; line_covered: boolean | null; line_hold: boolean; reason_codes: string[];
  sources: EvidenceSourceView[]; offset: number; total: number; next_offset: number | null;
}
export interface EvidencePreparation {
  project_id: string; case_version: string; project_row_version: number; seal_id: string | null;
  authoritative_set_sha256: string | null; membership_version: number | null; workbench_confirmation_id: string | null;
  prior_confirmation_id: string | null; lines: { line_id: string; row_version: number; proof_sha256: string }[];
  sources: { source_id: string; evidence_revision_id: string; withdrawn: boolean }[];
  decisions: { line_id: string; source_id: string; evidence_revision_id: string; relationship_id: string; decision_id: string; withdrawn: boolean }[];
  can_register: boolean; can_decide: boolean; can_confirm: boolean; can_withdraw: boolean;
}
export interface RelevanceFacts {
  source_portion: string; relevance_rationale: string; suitability_rationale: string; limitations: string;
  applicability_date: string; temporal_applicability: string; source_priority_rationale: string;
  higher_priorities_considered: ("internet_survey" | "unit_price_explanation")[];
  outcome: EvidenceDecisionView["outcome"]; disposition: EvidenceDecisionView["disposition"]; review_due_at: string;
}
export type EvidenceIntent =
  | { operation: "register"; source_id: string; predecessor_revision_id: string | null; material: SourceMaterial; reason_note: string | null }
  | { operation: "decide"; line_id: string; evidence_revision_id: string; predecessor_relationship_id: string | null;
      prior_decision_id: string | null; expected_line_proof_sha256: string; facts: RelevanceFacts; reason_note: string | null }
  | { operation: "withdraw"; target_kind: "source" | "relationship" | "decision"; target_id: string; reason_note: string }
  | { operation: "confirm"; supersedes_confirmation_id: string | null; reason_note: string | null }
  | { operation: "withdraw-confirmation"; expected_confirmation_id: string; reason_note: string };
export const EVIDENCE_CONTRACTS = {
  register: "price-evidence-registration-v1", decide: "price-evidence-relevance-v1", withdraw: "price-evidence-withdrawal-v1",
  confirm: "price-evidence-confirmation-v1", "withdraw-confirmation": "price-evidence-confirmation-withdrawal-v1",
} as const;
export interface EvidenceReceipt {
  result: { command_id: string; receipt_id: string; project_id: string; contract_version: string;
    record_id: string; relationship_id: string | null; project_row_version: number; created_at: string };
  replayed: boolean; historical: boolean; current_case_version: string;
}
export interface EvidenceSourceRead {
  project_id: string; source_id: string; evidence_revision_id: string; predecessor_revision_id: string | null;
  revision: number; registrar_id: string; registered_at: string; material: SourceMaterial;
}
const path = (id: string) => `/api/v1/projects/${encodeURIComponent(id)}/price-evidence`;
export const fetchEvidencePreparation = (id: string) => request<EvidencePreparation>(`${path(id)}/preparation`);
export const fetchEvidenceWorkspace = (id: string, lineId: string | null, offset = 0) =>
  request<EvidenceWorkspace>(`${path(id)}/workspace?offset=${offset}${lineId ? `&line_id=${encodeURIComponent(lineId)}` : ""}`);
export const fetchEvidenceSource = (id: string, revision: string) =>
  request<EvidenceSourceRead>(`${path(id)}/sources/${encodeURIComponent(revision)}`);
export const fetchEvidenceReceipt = (id: string, commandId: string) =>
  request<EvidenceReceipt>(`${path(id)}/command-receipts/${encodeURIComponent(commandId)}`);

export function evidenceCommand(snapshot: EvidencePreparation, intent: EvidenceIntent, commandId: string) {
  const base = { command_id: commandId, contract_version: EVIDENCE_CONTRACTS[intent.operation], confirm: true,
    expected_project_row_version: snapshot.project_row_version, expected_case_version: snapshot.case_version,
    expected_seal_id: snapshot.seal_id, expected_authoritative_set_sha256: snapshot.authoritative_set_sha256,
    expected_membership_version: snapshot.membership_version, expected_workbench_confirmation_id: snapshot.workbench_confirmation_id,
    expected_line_versions: snapshot.lines.map(({ line_id, row_version }) => ({ line_id, row_version })), reason_note: intent.reason_note };
  switch (intent.operation) {
    case "register": return { ...base, source_id: intent.source_id, predecessor_revision_id: intent.predecessor_revision_id, material: intent.material };
    case "decide": return { ...base, ...intent.facts, line_id: intent.line_id, evidence_revision_id: intent.evidence_revision_id,
      predecessor_relationship_id: intent.predecessor_relationship_id, prior_decision_id: intent.prior_decision_id,
      expected_line_proof_sha256: intent.expected_line_proof_sha256 };
    case "withdraw": return { ...base, target_kind: intent.target_kind, target_id: intent.target_id };
    case "confirm": return { ...base, supersedes_confirmation_id: intent.supersedes_confirmation_id };
    case "withdraw-confirmation": return { ...base, expected_confirmation_id: intent.expected_confirmation_id };
  }
}
export const submitEvidence = (id: string, intent: EvidenceIntent, snapshot: EvidencePreparation, commandId: string) =>
  request<EvidenceReceipt>(`${path(id)}/${intent.operation}`, { method: "POST", body: JSON.stringify(evidenceCommand(snapshot, intent, commandId)) });
