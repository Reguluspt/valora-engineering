import { request } from "./client";

export interface WorkbenchPreparation {
  project_id: string;
  case_version: string;
  project_row_version: number;
  seal_id: string | null;
  authoritative_set_sha256: string | null;
  membership_version: number | null;
  line_versions: { line_id: string; row_version: number }[];
  prior_confirmation_id: string | null;
  withdrawn: boolean;
  can_confirm: boolean;
  can_withdraw: boolean;
  can_edit_description: boolean;
}
interface WorkbenchCommandBase {
  command_id: string;
  confirm: true;
  expected_project_row_version: number;
  expected_case_version: string;
  expected_seal_id: string;
  expected_authoritative_set_sha256: string;
  expected_membership_version: number;
  expected_line_versions: WorkbenchPreparation["line_versions"];
}
export type WorkbenchCommand = WorkbenchCommandBase & (
  { contract_version: "asset-workbench-confirmation-v1"; reason_note: string | null; supersedes_confirmation_id: string | null } |
  { contract_version: "asset-workbench-withdrawal-v1"; reason_note: string; expected_confirmation_id: string }
);
export interface WorkbenchReceipt {
  result: { command_id: string; project_id: string; contract_version: WorkbenchCommand["contract_version"];
    confirmation_id: string; reversal_id: string | null; receipt_id: string; project_row_version: number; created_at: string };
  replayed: boolean;
  historical: boolean;
  current_case_version: string;
}
const path = (projectId: string) => `/api/v1/projects/${encodeURIComponent(projectId)}/asset-workbench`;
export const fetchWorkbenchPreparation = (projectId: string) => request<WorkbenchPreparation>(`${path(projectId)}/preparation`);
export const fetchWorkbenchReceipt = (projectId: string, commandId: string) =>
  request<WorkbenchReceipt>(`${path(projectId)}/command-receipts/${encodeURIComponent(commandId)}`);
export const submitWorkbench = (projectId: string, command: WorkbenchCommand) =>
  request<WorkbenchReceipt>(`${path(projectId)}/${command.contract_version === "asset-workbench-confirmation-v1" ? "confirm" : "withdraw"}`,
    { method: "POST", body: JSON.stringify(command) });
