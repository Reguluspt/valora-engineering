import { request } from "./client";
import {
  InlineEditDraftCreate,
  AutosaveCheckpointCreate
} from "../components/workbench/session/WorkbenchDraftSyncTypes";

export async function saveInlineEdit(sessionId: string, data: InlineEditDraftCreate): Promise<any> {
  return request<any>(`/api/v1/workbench/sessions/${sessionId}/inline-edit`, {
    method: "POST",
    body: JSON.stringify(data)
  });
}

export async function listInlineEdits(sessionId: string): Promise<any[]> {
  return request<any[]>(`/api/v1/workbench/sessions/${sessionId}/inline-edits`);
}

export async function saveCheckpoint(sessionId: string, data: AutosaveCheckpointCreate): Promise<any> {
  return request<any>(`/api/v1/workbench/sessions/${sessionId}/checkpoint`, {
    method: "POST",
    body: JSON.stringify(data)
  });
}

export async function executeUndo(sessionId: string): Promise<any> {
  return request<any>(`/api/v1/workbench/sessions/${sessionId}/undo`, {
    method: "POST"
  });
}

export async function executeRedo(sessionId: string): Promise<any> {
  return request<any>(`/api/v1/workbench/sessions/${sessionId}/redo`, {
    method: "POST"
  });
}
