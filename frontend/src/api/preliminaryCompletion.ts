import { request, requestBlob } from "./client";

const projectPath = (projectId: string) => `/api/v1/projects/${encodeURIComponent(projectId)}`;
const resultPath = (projectId: string, resultId: string) =>
  `${projectPath(projectId)}/preliminary-results/${encodeURIComponent(resultId)}`;

export interface PreliminaryResultRead {
  id: string;
  project_id: string;
  version: number;
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
  content_checksum_sha256: string;
  source_snapshot_sha256: string;
  created_at: string;
}

export interface ResultGenerateRequest {
  preliminary_analysis_snapshot_id: string;
  expected_project_version: number;
  idempotency_key: string;
  confirmed: true;
}

export interface CustomerBindRequest {
  customer_id: string;
  expected_project_version: number;
  idempotency_key: string;
}

export interface OfficialIntakeRequest {
  preliminary_result_artifact_id: string;
  expected_project_version: number;
  expected_preliminary_result_version: number;
  idempotency_key: string;
  confirmed: true;
}

export interface CustomerSummary {
  id: string;
  legal_name: string;
  display_name: string | null;
  tax_code: string | null;
  contact_phone: string | null;
  address: string | null;
  status: string;
}

export function generatePreliminaryResult(projectId: string, payload: ResultGenerateRequest) {
  return request<{ id: string; project_id: string; version: number }>(`${projectPath(projectId)}/preliminary-results`, {
    method: "POST", body: JSON.stringify(payload),
  });
}

export function getPreliminaryResult(projectId: string, resultId: string) {
  return request<PreliminaryResultRead>(resultPath(projectId, resultId));
}

export function downloadPreliminaryResult(projectId: string, resultId: string) {
  return requestBlob(`${resultPath(projectId, resultId)}/content`);
}

export function searchActiveCustomers(query: string) {
  const params = new URLSearchParams({ q: query.trim(), status: "active", page: "1", page_size: "25" });
  return request<CustomerSummary[]>(`/api/v1/master-data/customers?${params}`);
}

export function getCustomer(customerId: string) {
  return request<CustomerSummary>(`/api/v1/master-data/customers/${encodeURIComponent(customerId)}`);
}

export function bindPreliminaryCustomer(projectId: string, payload: CustomerBindRequest) {
  return request<{ receipt_id: string; target_customer_id: string; committed_project_version: number }>(
    `${projectPath(projectId)}/preliminary-customer`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export function commitOfficialIntake(projectId: string, payload: OfficialIntakeRequest) {
  return request<{ id: string; project_id: string; preliminary_result_artifact_id: string; preliminary_result_version: number }>(
    `${projectPath(projectId)}/official-intake`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}
