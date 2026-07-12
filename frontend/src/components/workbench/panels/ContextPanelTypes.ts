export interface SpecVersion {
  technical_specification_id: string;
  version_id: string;
  status: string;
  attribute_values: Record<string, string>;
}

export interface SpecSuggestion {
  suggestion_id: string;
  source_type: string;
  confidence_score: number;
  summary: string;
  attribute_values: Record<string, string>;
  evidence_ids: string[];
  warnings: string[];
}

export interface KnowledgePanelData {
  current_spec: SpecVersion | null;
  suggestions: SpecSuggestion[];
  conflicts: string[];
}

export interface QuoteBatch {
  id: string;
  display_name: string;
  status: string;
  conflict_status: string;
  spread_percent: number;
}

export interface QuoteLine {
  id: string;
  quote_label: string;
  supplier_name: string;
  quoted_unit_price: number;
  currency_code: string;
  evidence_id: string;
  status: string;
}

export interface AppraisedPriceDecision {
  id: string;
  selected_unit_price: number | null;
  rationale: string | null;
  status: string | null;
}

export interface PriceEvidencePanelData {
  quote_batch: QuoteBatch | null;
  quote_lines: QuoteLine[];
  appraised_price_decision: AppraisedPriceDecision | null;
}

export interface LineageData {
  original_source_project: { id: string; project_code: string } | null;
  direct_source_project: { id: string; project_code: string } | null;
  lineage_path: string[];
}

export interface ValidationIssue {
  id: string;
  severity: "info" | "warning" | "error" | "blocking";
  category: string;
  message: string;
  is_blocking: boolean;
}

export interface AssetLineContext {
  project_asset_line_id: string;
  knowledge_panel: KnowledgePanelData | null;
  price_evidence_panel: PriceEvidencePanelData | null;
  lineage: LineageData | null;
  validation_issues: ValidationIssue[] | null;
}
