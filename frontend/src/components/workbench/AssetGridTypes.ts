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
  normalized_name: string | null;
  canonical_asset: CanonicalAsset | null;
  asset_variant: AssetVariant | null;
  taxonomy_node: TaxonomyNode | null;
  quantity: number;
  unit: Unit | null;
  quote_batch_status: string | null;
  supplier_quote_1: number | null;
  supplier_quote_2: number | null;
  supplier_quote_3: number | null;
  appraised_price: number | null;
  currency: Currency | null;
  validation_status: "valid" | "warning" | "error" | "blocking";
  review_status: "raw" | "parsed" | "identity_suggested" | "identity_approved" | "taxonomy_approved" | "knowledge_matched" | "price_reviewed" | "approved" | "locked" | "excluded";
  row_version: number | null;
}

export type SortField = "line_no" | "raw_name" | "quantity" | "appraised_price";
export type SortOrder = "asc" | "desc";

export interface GridSortState {
  field: SortField;
  order: SortOrder;
}
