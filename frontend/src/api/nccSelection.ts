import { request } from "./client";

export interface NccSelectionEvidence {
  evidence_file_id: string;
  filename: string | null;
  status: string | null;
}

export interface NccSelectionCandidate {
  quote_line_id: string;
  quote_batch_id: string;
  quote_batch_revision_number: number;
  supplier_id: string;
  supplier_name: string;
  quoted_unit_price: number;
  currency: string;
  quantity: number | null;
  unit_of_measure: string | null;
  quote_date: string | null;
  evidence: NccSelectionEvidence;
  difference_amount: number | null;
  difference_percent: number | null;
  warnings: string[];
  eligible: boolean;
}

export interface NccSelectionCurrent {
  selection_id: string;
  selection_revision: number;
  quote_line_id: string;
  quote_batch_id: string;
  quote_batch_revision_number: number;
  supplier_id: string;
  supplier_name: string;
  quoted_unit_price: number;
  currency: string;
  quantity: number | null;
  unit_of_measure: string | null;
  quote_date: string | null;
  evidence: NccSelectionEvidence;
  current_unit_price: number | null;
  current_unit_price_currency_id: string | null;
  difference_amount: number | null;
  difference_percent: number | null;
  warnings: string[];
  acknowledged_warning_codes: string[];
  confirmed_by_user_id: string;
  confirmed_at: string;
  stale: boolean;
}

export interface NccSelectionHistoryItem {
  selection_revision: number;
  quote_line_id: string;
  supplier_name: string;
  quoted_unit_price: number;
  currency: string;
  difference_amount: number | null;
  difference_percent: number | null;
  warnings: string[];
  confirmed_by_user_id: string;
  confirmed_at: string;
}

export type NccSelectionState = "unselected" | "selected" | "stale";

export interface NccSelectionAssetLine {
  asset_line_id: string;
  asset_name: string;
  unit_id: string | null;
  unit_name: string | null;
  quantity: number;
  appraised_unit_price: number | null;
  appraised_currency_id: string | null;
  current_selection: NccSelectionCurrent | null;
  candidates: NccSelectionCandidate[];
  history: NccSelectionHistoryItem[];
  state: NccSelectionState;
}

export interface NccSelectionKpis {
  total_asset_lines: number;
  selected: number;
  unselected: number;
  stale: number;
  eligible_quotes: number;
}

export interface NccSelectionAggregateResponse {
  project_id: string;
  kpis: NccSelectionKpis;
  asset_lines: NccSelectionAssetLine[];
}

export interface NccSelectionConfirmPayload {
  quote_line_id: string;
  expected_selection_revision: number;
  acknowledged_warning_codes: string[];
  idempotency_key: string;
  confirmed: boolean;
}

export function fetchNccSelections(
  projectId: string,
  signal?: AbortSignal
): Promise<NccSelectionAggregateResponse> {
  return request<NccSelectionAggregateResponse>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/ncc-selections`,
    { signal }
  );
}

export function confirmNccSelection(
  projectId: string,
  lineId: string,
  payload: NccSelectionConfirmPayload
): Promise<NccSelectionCurrent> {
  return request<NccSelectionCurrent>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/asset-lines/${encodeURIComponent(lineId)}/ncc-selection`,
    { method: "POST", body: JSON.stringify(payload) }
  );
}
