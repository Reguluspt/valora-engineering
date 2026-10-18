import { request } from "./client";

export type ImportContext = {
  contract_version: "quotation-txt-import-v1"; project_id: string; project_code: string; project_name: string;
  case_version: string; project_row_version: number; can_import: boolean; blocked_codes: string[];
  extension: ".txt"; encoding: "utf-8"; max_bytes: number; retention_policy_code: string; policy_version: number;
};
export type ImportCommand = {
  contract_version: "quotation-txt-import-v1"; command_id: string; confirm: true;
  expected_case_version: string; expected_project_row_version: number; expected_sha256: string; expected_byte_length: number;
};
export type ImportStatus = {
  contract_version: "quotation-txt-import-v1"; project_id: string; command_id: string; request_id: string;
  intent_id: string; document_id: string; sha256: string; byte_length: number; request_digest: string;
  outcome: "pending" | "finalized"; storage_state: string; storage_state_version: number; recovery_permitted?: boolean;
  receipt_id?: string; revision_id?: string; generation?: number; binding_id?: string; finalized_at?: string;
  retention_policy_code?: string; retention_anchor_at?: string; minimum_retain_until?: string;
  source?: { available: boolean; reason: string | null; observed_at: string };
};
const base = (projectId: string) => `/api/v1/projects/${encodeURIComponent(projectId)}/quotation-documents`;
export const fetchImportContext = (projectId: string) => request<ImportContext>(`${base(projectId)}/import-context`);
export const fetchImportStatus = (projectId: string, commandId: string) =>
  request<ImportStatus>(`${base(projectId)}/import-receipts/${encodeURIComponent(commandId)}`);
export function importQuotationTxt(projectId: string, command: ImportCommand, file: File, recoveryStateVersion?: number) {
  const form = new FormData();
  form.append("metadata", JSON.stringify(recoveryStateVersion === undefined ? command : {
    ...command, expected_storage_state_version: recoveryStateVersion,
  }));
  form.append("file", file);
  const path = recoveryStateVersion === undefined ? "/import" : `/import-receipts/${encodeURIComponent(command.command_id)}/recover`;
  return request<ImportStatus>(`${base(projectId)}${path}`, { method: "POST", body: form }, true);
}
