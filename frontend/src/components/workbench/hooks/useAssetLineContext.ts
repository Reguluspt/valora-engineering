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
      const rawFields: Record<string, string> = {};
      if (selectedRow.raw_name) rawFields["raw_name"] = selectedRow.raw_name;

      const data: AssetLineContext = {
        project_asset_line_id: selectedRow.project_asset_line_id,
        knowledge_panel: null,
        price_evidence_panel: null,
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
