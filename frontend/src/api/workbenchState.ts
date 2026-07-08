import { request } from "./client";
import {
  WorkbenchLayoutSave,
  AssetGridViewSave,
  WorkbenchSelectionSave,
  PanelStateSave
} from "../components/workbench/session/WorkbenchStateTypes";

export async function saveLayout(sessionId: string, data: WorkbenchLayoutSave): Promise<any> {
  return request<any>(`/api/v1/workbench/sessions/${sessionId}/layout`, {
    method: "POST",
    body: JSON.stringify(data)
  });
}

export async function listGridViews(sessionId: string): Promise<any[]> {
  return request<any[]>(`/api/v1/workbench/sessions/${sessionId}/grid-view`);
}

export async function saveGridView(sessionId: string, data: AssetGridViewSave): Promise<any> {
  return request<any>(`/api/v1/workbench/sessions/${sessionId}/grid-view`, {
    method: "POST",
    body: JSON.stringify(data)
  });
}

export async function saveSelection(sessionId: string, data: WorkbenchSelectionSave): Promise<any> {
  return request<any>(`/api/v1/workbench/sessions/${sessionId}/selection`, {
    method: "POST",
    body: JSON.stringify(data)
  });
}

export async function getSelection(sessionId: string): Promise<any[]> {
  return request<any[]>(`/api/v1/workbench/sessions/${sessionId}/selection`);
}

export async function savePanelState(sessionId: string, data: PanelStateSave): Promise<any> {
  return request<any>(`/api/v1/workbench/sessions/${sessionId}/panel-state`, {
    method: "POST",
    body: JSON.stringify(data)
  });
}

export async function listPanelStates(sessionId: string): Promise<any[]> {
  return request<any[]>(`/api/v1/workbench/sessions/${sessionId}/panel-state`);
}

export async function listNotifications(sessionId: string): Promise<any[]> {
  return request<any[]>(`/api/v1/workbench/sessions/${sessionId}/notifications`);
}
