export interface WorkbenchLayoutSave {
  layout_name: string;
  layout_payload: any;
  is_default: boolean;
}

export interface AssetGridViewSave {
  view_name: string;
  columns: string[];
  filters: any;
  sort: any;
  is_default: boolean;
}

export interface WorkbenchSelectionSave {
  selected_target_type: string;
  selected_target_ids: string[];
}

export interface PanelStateSave {
  panel_type: string;
  is_expanded: boolean;
  width: number;
}
