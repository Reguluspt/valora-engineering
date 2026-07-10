import { request } from "./client";

export interface ProjectResolutionResponse {
  project_id: string;
  display_name: string;
  matched_by: string;
}

export async function resolveProjectReference(ref: string): Promise<ProjectResolutionResponse> {
  return request<ProjectResolutionResponse>(`/api/v1/projects/resolve?ref=${encodeURIComponent(ref)}`);
}

export interface AssetLineDraftState {
  asset_line_id: string;
  has_saved_draft: boolean;
  has_unsaved_changes: boolean;
  is_locked: boolean;
  is_stale: boolean;
  draft_status: string;
  changed_fields: string[];
  last_saved_at: string | null;
  last_saved_by: string | null;
}

export interface ProjectDraftStateResponse {
  project_id: string;
  items: AssetLineDraftState[];
  total: number;
}

export async function fetchProjectDraftState(projectId: string): Promise<ProjectDraftStateResponse> {
  return request<ProjectDraftStateResponse>(`/api/v1/projects/${projectId}/asset-lines/draft-state`);
}
