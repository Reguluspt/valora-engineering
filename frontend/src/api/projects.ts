import { request } from "./client";

export interface ProjectResolutionResponse {
  project_id: string;
  display_name: string;
  matched_by: string;
}

export async function resolveProjectReference(ref: string): Promise<ProjectResolutionResponse> {
  return request<ProjectResolutionResponse>(`/api/v1/projects/resolve?ref=${encodeURIComponent(ref)}`);
}
