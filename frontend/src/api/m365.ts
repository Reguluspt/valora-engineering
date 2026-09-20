import { request } from "./client";

export type OneDriveConnectionStatus = "not_connected" | "active" | "error" | "revoked";
export type RevalidationClassification =
  | "no_change"
  | "external_change_outside_managed"
  | "external_change_in_managed"
  | "file_replaced_or_moved"
  | "access_unavailable";

export interface OneDriveConnection {
  connection_id: string | null;
  drive_id: string | null;
  status: OneDriveConnectionStatus;
  last_verified_at: string | null;
  capability_state: "read-only" | "exchange-write-ready" | "reconsent-required";
  read_available: boolean;
  appfolder_write_available: boolean;
}

export interface AdoptionTemplate {
  template_version_id: string;
  template_name: string;
  document_type: string;
  version_number: number;
}

export interface OneDriveEntry {
  drive_item_id: string;
  kind: "folder" | "docx";
  name: string;
  size_bytes: number | null;
  last_modified_at: string | null;
  web_url: string | null;
}

export interface AdoptionOptions {
  project_id: string;
  project_code: string;
  project_name: string;
  connection_id: string;
  drive_id: string;
  parent_item_id: string | null;
  data_snapshot: Record<string, unknown>;
  templates: AdoptionTemplate[];
  items: OneDriveEntry[];
  truncated: boolean;
}

export interface RevalidationReadiness {
  document_id: string;
  document_revision_id: string;
  document_revision: number;
  binding_id: string;
  drive_id: string;
  drive_item_id: string;
  file_name: string;
  file_path: string | null;
  web_url: string;
  baseline_eligible: boolean;
  recovery_code: string | null;
  classification: RevalidationClassification | null;
  completed_at: string | null;
  affected_region_keys: string[];
  is_fresh: boolean;
  is_safe_for_freshness_required_action: boolean;
  stale_reason: string | null;
  blocking_reason: string | null;
  next_action: string | null;
  retryable: boolean;
}

export interface OperationalDocument {
  document_id: string;
  title: string;
  document_type: string;
  readiness: RevalidationReadiness;
}

export interface ProvisionDocumentRequest {
  template_version_id: string;
  connection_id: string;
  drive_item_id: string;
  title: string;
  data_snapshot: Record<string, unknown>;
  idempotency_key: string;
}

export interface ProvisionDocumentResponse {
  document_id: string;
  document_revision_id: string;
  document_revision: number;
  binding_id: string;
  baseline_id: string;
  document_type: string;
  title: string;
  file_name: string;
  web_url: string;
}

export async function getOneDriveConnection(): Promise<OneDriveConnection> {
  return request<OneDriveConnection>("/api/v1/m365/onedrive/connection");
}

export async function beginOneDriveAuthorization(
  scopeProfile: "read_only" | "exchange_write" = "read_only",
): Promise<string> {
  const result = await request<{ authorization_url: string }>(
    `/api/v1/m365/onedrive/authorize?scope_profile=${scopeProfile}`,
    { method: "POST" },
  );
  return result.authorization_url;
}

export async function getAdoptionOptions(
  projectId: string,
  parentItemId?: string,
): Promise<AdoptionOptions> {
  const query = parentItemId ? `?parent_item_id=${encodeURIComponent(parentItemId)}` : "";
  return request<AdoptionOptions>(
    `/api/v1/m365/onedrive/projects/${projectId}/adoption-options${query}`,
  );
}

export async function listOperationalDocuments(
  projectId: string,
): Promise<OperationalDocument[]> {
  return request<OperationalDocument[]>(
    `/api/v1/m365/onedrive/projects/${projectId}/documents`,
  );
}

export async function provisionOperationalDocument(
  projectId: string,
  payload: ProvisionDocumentRequest,
): Promise<ProvisionDocumentResponse> {
  return request<ProvisionDocumentResponse>(
    `/api/v1/m365/onedrive/projects/${projectId}/documents/provision`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export async function revalidateOperationalDocument(
  projectId: string,
  readiness: RevalidationReadiness,
  trigger: "explicit_refresh" | "reconnect" = "explicit_refresh",
): Promise<void> {
  await request(
    `/api/v1/m365/onedrive/projects/${projectId}/documents/${readiness.document_id}/revalidation`,
    {
      method: "POST",
      body: JSON.stringify({
        expected_document_revision_id: readiness.document_revision_id,
        expected_document_revision: readiness.document_revision,
        trigger,
        idempotency_key: createIdempotencyKey("revalidation"),
      }),
    },
  );
}

export function createIdempotencyKey(prefix: string): string {
  const random = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
  return `${prefix}-${random}`;
}
