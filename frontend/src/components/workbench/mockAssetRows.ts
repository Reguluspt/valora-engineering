import { AssetLineGridRow } from "./AssetGridTypes";

export const MOCK_ASSET_ROWS: AssetLineGridRow[] = [
  {
    project_asset_line_id: "uuid-1",
    line_no: 1,
    raw_name: "Đèn đường LED Rạng Đông CSD08 100W",
    normalized_name: "Đèn đường LED 100W",
    canonical_asset: { id: "c-1", standard_name: "Đèn đường LED Rạng Đông CSD08" },
    asset_variant: { id: "v-1", display_name: "100W" },
    taxonomy_node: { id: "t-1", path: "Thiết bị điện > Đèn > Đèn LED > Đèn đường LED" },
    quantity: 15,
    unit: { id: "u-1", code: "cai", name_vi: "cái" },
    quote_batch_status: "active",
    supplier_quote_1: 850000,
    supplier_quote_2: 900000,
    supplier_quote_3: 880000,
    appraised_price: 850000,
    currency: { id: "cur-1", code: "VND" },
    validation_status: "valid",
    review_status: "approved",
    row_version: 1
  },
  {
    project_asset_line_id: "uuid-2",
    line_no: 2,
    raw_name: "Đèn đường LED Rạng Đông CSD10 150W",
    normalized_name: "Đèn đường LED 150W",
    canonical_asset: { id: "c-2", standard_name: "Đèn đường LED Rạng Đông CSD10" },
    asset_variant: { id: "v-2", display_name: "150W" },
    taxonomy_node: { id: "t-1", path: "Thiết bị điện > Đèn > Đèn LED > Đèn đường LED" },
    quantity: 10,
    unit: { id: "u-1", code: "cai", name_vi: "cái" },
    quote_batch_status: "active",
    supplier_quote_1: 1000000,
    supplier_quote_2: 980000,
    supplier_quote_3: 1050000,
    appraised_price: 950000,
    currency: { id: "cur-1", code: "VND" },
    validation_status: "warning",
    review_status: "ready_for_review" as any, // fallback matching wireframe status
    row_version: 3
  },
  {
    project_asset_line_id: "uuid-3",
    line_no: 3,
    raw_name: "Cáp đồng treo cách điện PVC 25mm2",
    normalized_name: "Cáp đồng PVC 25mm2",
    canonical_asset: { id: "c-3", standard_name: "Cáp đồng treo PVC Cadivi" },
    asset_variant: { id: "v-3", display_name: "25mm2" },
    taxonomy_node: { id: "t-2", path: "Vật tư cáp > Cáp treo > Cáp đồng" },
    quantity: 200,
    unit: { id: "u-2", code: "m", name_vi: "mét" },
    quote_batch_status: "active",
    supplier_quote_1: 45000,
    supplier_quote_2: 43000,
    supplier_quote_3: 47000,
    appraised_price: 44000,
    currency: { id: "cur-1", code: "VND" },
    validation_status: "error",
    review_status: "identity_suggested",
    row_version: 2
  },
  {
    project_asset_line_id: "uuid-4",
    line_no: 4,
    raw_name: "Ống nhựa HDPE Sino D50 luồn dây cáp",
    normalized_name: "Ống HDPE D50 luồn cáp",
    canonical_asset: { id: "c-4", standard_name: "Ống nhựa luồn cáp HDPE Sino" },
    asset_variant: { id: "v-4", display_name: "D50" },
    taxonomy_node: { id: "t-3", path: "Vật tư cáp > Ống luồn > Ống HDPE" },
    quantity: 150,
    unit: { id: "u-2", code: "m", name_vi: "mét" },
    quote_batch_status: "active",
    supplier_quote_1: 28000,
    supplier_quote_2: 29000,
    supplier_quote_3: 27500,
    appraised_price: 28000,
    currency: { id: "cur-1", code: "VND" },
    validation_status: "blocking",
    review_status: "raw",
    row_version: 1
  }
];

// Generate 200 items to test virtualization
export function generateLargeMockSet(): AssetLineGridRow[] {
  const dataset = [...MOCK_ASSET_ROWS];
  for (let i = 5; i <= 250; i++) {
    dataset.push({
      project_asset_line_id: `uuid-${i}`,
      line_no: i,
      raw_name: `Thiết bị phụ trợ xây lắp đường điện Mã số ${1000 + i}`,
      normalized_name: `Thiết bị phụ trợ #${i}`,
      canonical_asset: { id: `c-${i}`, standard_name: `Thiết bị Curated standard #${i}` },
      asset_variant: { id: `v-${i}`, display_name: `Type-${i}` },
      taxonomy_node: { id: "t-4", path: "Thiết bị điện > Phụ kiện > Khác" },
      quantity: 5 * i,
      unit: { id: "u-1", code: "cai", name_vi: "cái" },
      quote_batch_status: "active",
      supplier_quote_1: 10000 + i * 100,
      supplier_quote_2: 10500 + i * 100,
      supplier_quote_3: 9800 + i * 100,
      appraised_price: 10000 + i * 100,
      currency: { id: "cur-1", code: "VND" },
      validation_status: i % 4 === 0 ? "warning" : i % 7 === 0 ? "error" : "valid",
      review_status: i % 5 === 0 ? "approved" : "parsed",
      row_version: 1
    });
  }
  return dataset;
}
