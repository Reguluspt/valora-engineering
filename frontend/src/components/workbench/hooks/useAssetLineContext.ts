import { useState, useEffect } from "react";
import { AssetLineGridRow } from "../AssetGridTypes";
import { AssetLineContext } from "../panels/ContextPanelTypes";

export function useAssetLineContext(
  _projectId: string,
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
      const attrs: Record<string, string> = {};
      if (selectedRow.raw_name) attrs["Tên gốc"] = selectedRow.raw_name;

      const data: AssetLineContext = {
        project_asset_line_id: selectedRow.project_asset_line_id,
        knowledge_panel: {
          current_spec: {
            technical_specification_id: `spec-${selectedRow.project_asset_line_id}`,
            version_id: "v-1",
            status: "active",
            attribute_values: attrs,
          },
          suggestions: [],
          conflicts: []
        },
        price_evidence_panel: {
          quote_batch: null,
          quote_lines: [],
          appraised_price_decision: selectedRow.appraised_price != null ? {
            id: `apd-${selectedRow.project_asset_line_id}`,
            selected_unit_price: selectedRow.appraised_price,
            rationale: null,
            status: selectedRow.review_status as string,
          } : null,
        },
        lineage: null,
        validation_issues: null,
      };

      setContextData(data);
    } catch (err: any) {
      setErrorMsg(err.message || "Không thể tạo dữ liệu ngữ cảnh");
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
