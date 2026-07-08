export interface InlineEditDraftCreate {
  target_type: string;
  target_id: string;
  field_key: string;
  draft_value: any;
  base_value: any;
  base_row_version: number;
}

export interface AutosaveCheckpointCreate {
  checkpoint_payload: any;
}
