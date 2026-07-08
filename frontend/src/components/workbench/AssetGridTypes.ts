export interface CanonicalAsset {
  id: string;
  standard_name: string;
}

export interface AssetVariant {
  id: string;
  display_name: string;
}

export interface TaxonomyNode {
  id: string;
  path: string;
}

export interface Unit {
  id: string;
  code: string;
  name_vi: string;
}

export interface Currency {
  id: string;
  code: string;
}

export interface AssetLineGridRow {
  project_asset_line_id: string;
  line_no: number;
  raw_name: string;
  normalized_name: string;
  canonical_asset: CanonicalAsset;
  asset_variant: AssetVariant;
  taxonomy_node: TaxonomyNode;
  quantity: number;
  unit: Unit;
  quote_batch_status: string;
  supplier_quote_1: number;
  supplier_quote_2: number;
  supplier_quote_3: number;
  appraised_price: number;
  currency: Currency;
  validation_status: "valid" | "warning" | "error" | "blocking";
  review_status: "raw" | "parsed" | "identity_suggested" | "identity_approved" | "taxonomy_approved" | "knowledge_matched" | "price_reviewed" | "approved" | "locked" | "excluded";
  row_version: number;
}

export type SortField = "line_no" | "raw_name" | "quantity" | "appraised_price";
export type SortOrder = "asc" | "desc";

export interface GridSortState {
  field: SortField;
  order: SortOrder;
}
