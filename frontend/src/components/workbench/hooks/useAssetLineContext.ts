import { useState, useEffect } from "react";
import { AssetLineGridRow } from "../AssetGridTypes";
import { AssetLineContext } from "../panels/ContextPanelTypes";

export function useAssetLineContext(
  projectId: string,
  selectedRow: AssetLineGridRow | null
) {
  const [contextData, setContextData] = useState<AssetLineContext | undefined>(undefined);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedRow) {
      setContextData(undefined);
      return;
    }

    setLoading(true);
    setErrorMsg(null);

    try {
      // Map selected grid row attributes safely to structural panels without leaking version_token
      const data: AssetLineContext = {
        project_asset_line_id: selectedRow.project_asset_line_id,
        knowledge_panel: {
          current_spec: {
            technical_specification_id: `spec-${selectedRow.project_asset_line_id}`,
            version_id: "v-1",
            status: "active",
            attribute_values: {
              "Tên chuẩn hóa": selectedRow.normalized_name,
              "Tên chuẩn": selectedRow.canonical_asset.standard_name,
              "Hãng sản xuất/Model": selectedRow.asset_variant.display_name,
              "Nhóm phân loại": selectedRow.taxonomy_node.path
            }
          },
          suggestions: [],
          conflicts: []
        },
        price_evidence_panel: {
          quote_batch: {
            id: `qb-${selectedRow.project_asset_line_id}`,
            display_name: "Thông tin báo giá tài sản",
            status: "active",
            conflict_status: "valid",
            spread_percent: 0
          },
          quote_lines: [
            {
              id: `ql-1-${selectedRow.project_asset_line_id}`,
              quote_label: "Báo giá 1",
              supplier_name: "Báo giá tham chiếu 1",
              quoted_unit_price: selectedRow.supplier_quote_1,
              currency_code: selectedRow.currency.code,
              evidence_id: `ev-1-${selectedRow.project_asset_line_id}`,
              status: "active"
            }
          ],
          appraised_price_decision: {
            id: `apd-${selectedRow.project_asset_line_id}`,
            selected_unit_price: selectedRow.appraised_price,
            rationale: "Bản nháp thẩm định tự động tham chiếu từ báo giá gốc.",
            status: selectedRow.review_status
          }
        },
        lineage: {
          original_source_project: { id: "p-org", project_code: "PRJ-ORG" },
          direct_source_project: { id: "p-dir", project_code: "PRJ-DIR" },
          lineage_path: ["p-org", "p-dir"]
        },
        validation_issues: []
      };

      setContextData(data);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to parse context data");
    } finally {
      setLoading(false);
    }
  }, [selectedRow]);

  return {
    contextData,
    loading,
    errorMsg
  };
}
