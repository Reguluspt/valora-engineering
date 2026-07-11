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

export interface AssetLineDraftSaveRequest {
  field_key: string;
  draft_value: any;
  base_value?: any;
  version_token: string;
}

export interface AssetLineDraftSaveResponse {
  project_id: string;
  asset_line_id: string;
  draft_status: "saved_draft" | "stale" | "locked";
  field_key: string;
  has_saved_draft: boolean;
  has_unsaved_changes: boolean;
  is_stale: boolean;
  changed_fields: string[];
  saved_at?: string | null;
}

export async function saveAssetLineDraft(
  projectId: string,
  assetLineId: string,
  payload: AssetLineDraftSaveRequest
): Promise<AssetLineDraftSaveResponse> {
  return request<AssetLineDraftSaveResponse>(
    `/api/v1/projects/${projectId}/asset-lines/${assetLineId}/draft`,
    {
      method: "PATCH",
      body: JSON.stringify(payload)
    }
  );
}

export interface AssetLineDraftCommitRequest {
  field_keys: string[];
  confirm: boolean;
  version_token: string;
}

export interface AssetLineDraftCommitResponse {
  project_id: string;
  asset_line_id: string;
  committed_fields: string[];
  draft_status: "clean";
  has_saved_draft: boolean;
  has_unsaved_changes: boolean;
  is_stale: boolean;
  committed_at?: string | null;
}

export async function commitAssetLineDraft(
  projectId: string,
  assetLineId: string,
  payload: AssetLineDraftCommitRequest
): Promise<AssetLineDraftCommitResponse> {
  return request<AssetLineDraftCommitResponse>(
    `/api/v1/projects/${projectId}/asset-lines/${assetLineId}/draft/commit`,
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}
