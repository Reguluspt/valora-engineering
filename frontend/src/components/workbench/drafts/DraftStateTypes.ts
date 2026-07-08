export interface UndoRedoStackEntry {
  project_asset_line_id: string;
  field_key: string;
  before_value: any;
  after_value: any;
  timestamp: string;
}

export interface InlineEditDraft {
  project_asset_line_id: string;
  field_key: string;
  draft_value: any;
  base_value: any;
  base_row_version: number;
}

export interface AutosaveCheckpoint {
  id: string;
  timestamp: string;
  status: "idle" | "dirty" | "checkpointed" | "conflict";
}
