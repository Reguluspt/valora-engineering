import { request } from "./client";

export interface ProjectAssetImportBatchResponse {
  id: string;
  project_id: string;
  status: "created" | "parsing" | "parsed" | "validation_failed" | "ready_for_review" | "applied" | "failed";
  source_filename: string;
  source_sheet_name: string | null;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  warning_rows: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectAssetImportBatchCreate {
  source_filename: string;
  source_sheet_name?: string;
}

export interface ProjectAssetImportValidationMessage {
  field?: string;
  message_key: string;
  message?: string;
}

export interface ProjectAssetImportStagingRowResponse {
  id: string;
  import_batch_id: string;
  source_row_number: number;
  validation_status: "pending" | "valid" | "invalid" | "warning";
  validation_errors: ProjectAssetImportValidationMessage[];
  validation_warnings: ProjectAssetImportValidationMessage[];
  proposed_asset_name?: string;
  proposed_description?: string;
  proposed_quantity?: string;
  proposed_unit?: string;
  proposed_raw_price?: string;
  proposed_currency?: string;
  proposed_appraised_unit_price?: string;
  proposed_review_status?: string;
  proposed_validation_status?: string;
}

export interface ProjectAssetImportStagingRowPaginationResponse {
  project_id: string;
  import_batch_id: string;
  items: ProjectAssetImportStagingRowResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface FetchAssetImportRowsParams {
  limit?: number;
  offset?: number;
  validation_status?: "pending" | "valid" | "invalid" | "warning";
}

export async function createAssetImportBatch(
  projectId: string,
  payload: ProjectAssetImportBatchCreate
): Promise<ProjectAssetImportBatchResponse> {
  return request<ProjectAssetImportBatchResponse>(
    `/api/v1/projects/${projectId}/asset-imports`,
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function fetchAssetImportBatches(
  projectId: string
): Promise<ProjectAssetImportBatchResponse[]> {
  return request<ProjectAssetImportBatchResponse[]>(
    `/api/v1/projects/${projectId}/asset-imports`
  );
}

export async function fetchAssetImportRows(
  projectId: string,
  batchId: string,
  params: FetchAssetImportRowsParams = {}
): Promise<ProjectAssetImportStagingRowPaginationResponse> {
  const query = new URLSearchParams();
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.offset !== undefined) query.set("offset", String(params.offset));
  if (params.validation_status !== undefined) query.set("validation_status", params.validation_status);

  const queryString = query.toString();
  const path = `/api/v1/projects/${projectId}/asset-imports/${batchId}/rows${queryString ? `?${queryString}` : ""}`;
  return request<ProjectAssetImportStagingRowPaginationResponse>(path);
}

export async function uploadAssetImportWorkbook(
  projectId: string,
  batchId: string,
  file: File
): Promise<ProjectAssetImportBatchResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return request<ProjectAssetImportBatchResponse>(
    `/api/v1/projects/${projectId}/asset-imports/${batchId}/upload`,
    {
      method: "POST",
      body: formData
    }
  );
}

