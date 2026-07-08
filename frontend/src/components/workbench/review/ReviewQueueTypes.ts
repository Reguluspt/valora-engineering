export interface ReviewQueueItem {
  id: string;
  project_code: string;
  project_name: string;
  line_no: number;
  asset_summary: string;
  review_type: "identity" | "taxonomy" | "appraised_price" | "evidence" | "qc";
  priority: "high" | "normal" | "low";
  validation_status: "valid" | "warning" | "error" | "blocking";
  assigned_to: string | null;
  status: "open" | "in_review" | "completed";
  row_version: number;
}

export type MockRole = "owner" | "admin" | "appraiser" | "reviewer" | "knowledge_curator" | "viewer";
