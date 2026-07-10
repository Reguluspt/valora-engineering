import { request } from "./client";

export interface ProjectAssetLineResponse {
  id: string;
  project_id: string;
  asset_name: string;
  description: string | null;
  quantity: number;
  unit_id: string | null;
  raw_price: number | null;
  raw_price_currency_id: string | null;
  appraised_unit_price: number | null;
  appraised_currency_id: string | null;
  review_status: string;
  validation_status: string;
  brand_id: string | null;
  manufacturer_id: string | null;
  version_token: string;
}

export interface ProjectAssetLinePaginationResponse {
  project_id: string;
  items: ProjectAssetLineResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface FetchAssetLinesParams {
  limit?: number;
  offset?: number;
  search?: string;
  validation_status?: string;
  valuation_status?: string;
}

export async function fetchProjectAssetLines(
  projectId: string,
  params: FetchAssetLinesParams = {}
): Promise<ProjectAssetLinePaginationResponse> {
  const query = new URLSearchParams();
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.offset !== undefined) query.set("offset", String(params.offset));
  if (params.search !== undefined) query.set("search", params.search);
  if (params.validation_status !== undefined) query.set("validation_status", params.validation_status);
  if (params.valuation_status !== undefined) query.set("valuation_status", params.valuation_status);

  const queryString = query.toString();
  const path = `/api/v1/projects/${projectId}/asset-lines${queryString ? `?${queryString}` : ""}`;
  return request<ProjectAssetLinePaginationResponse>(path);
}
