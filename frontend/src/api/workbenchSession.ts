import { request } from "./client";
import { WorkbenchSession, WorkbenchSessionCreate, WorkbenchSessionHeartbeatRequest } from "../components/workbench/session/WorkbenchSessionTypes";

export async function createSession(data: WorkbenchSessionCreate): Promise<WorkbenchSession> {
  return request<WorkbenchSession>("/api/v1/workbench/sessions", {
    method: "POST",
    body: JSON.stringify(data)
  });
}

export async function getSession(sessionId: string): Promise<WorkbenchSession> {
  return request<WorkbenchSession>(`/api/v1/workbench/sessions/${sessionId}`);
}

export async function sendHeartbeat(
  sessionId: string,
  data: WorkbenchSessionHeartbeatRequest
): Promise<WorkbenchSession> {
  return request<WorkbenchSession>(`/api/v1/workbench/sessions/${sessionId}/heartbeat`, {
    method: "POST",
    body: JSON.stringify(data)
  });
}
