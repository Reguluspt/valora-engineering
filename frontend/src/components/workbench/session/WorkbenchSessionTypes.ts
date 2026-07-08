export interface WorkbenchSession {
  id: string;
  user_id: string;
  project_id: string;
  status: "active" | "inactive" | "abandoned";
  row_version: number;
  created_at: string;
  last_active_at: string;
  current_selection: any;
}

export interface WorkbenchSessionCreate {
  project_id: string;
}

export interface WorkbenchSessionHeartbeatRequest {
  expected_row_version: number;
}
