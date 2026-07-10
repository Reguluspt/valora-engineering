import { useState, useEffect, useCallback } from "react";
import { fetchProjectAssetLines, ProjectAssetLineResponse } from "../../../api/assetLines";
import { AssetLineGridRow } from "../AssetGridTypes";
import { getFriendlyErrorFromUnknown } from "../../../errors/errorRegistry";

export function mapAssetLinesToGridRows(items: ProjectAssetLineResponse[]): AssetLineGridRow[] {
  return items.map((item, idx) => ({
    project_asset_line_id: item.id,
    line_no: idx + 1,
    raw_name: item.asset_name,
    normalized_name: item.asset_name,
    canonical_asset: {
      id: item.brand_id || `c-${item.id}`,
      standard_name: item.description || item.asset_name,
    },
    asset_variant: {
      id: item.manufacturer_id || `v-${item.id}`,
      display_name: item.description || "N/A",
    },
    taxonomy_node: {
      id: `t-${item.id}`,
      path: "Thiết bị điện > Chưa phân loại",
    },
    quantity: item.quantity,
    unit: {
      id: item.unit_id || "u-1",
      code: "cai",
      name_vi: "cái",
    },
    quote_batch_status: "active",
    supplier_quote_1: item.raw_price || 0,
    supplier_quote_2: 0,
    supplier_quote_3: 0,
    appraised_price: item.appraised_unit_price || 0,
    currency: {
      id: item.appraised_currency_id || "cur-1",
      code: "VND",
    },
    validation_status: (item.validation_status as any) === "needs_review" ? "warning" : item.validation_status as any,
    review_status: item.review_status as any,
    row_version: parseInt(item.version_token) || 1,
  }));
}

export function useProjectAssetLines(projectId: string) {
  const [rows, setRows] = useState<AssetLineGridRow[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [friendlyError, setFriendlyError] = useState<{ title: string; message: string; nextAction: string } | null>(null);

  const loadAssetLines = useCallback(async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      setFriendlyError(null);

      // Validate project UUID format (do not use hardcoded dummy fallbacks)
      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      if (!uuidRegex.test(projectId)) {
        setRows([]);
        setFriendlyError({
          title: "Chưa xác định được mã hồ sơ",
          message: "Chưa xác định được mã hồ sơ để tải danh sách tài sản.",
          nextAction: "Vui lòng mở hồ sơ từ danh sách hồ sơ hoặc thử tải lại."
        });
        setLoading(false);
        return;
      }

      const res = await fetchProjectAssetLines(projectId);
      const mappedRows = mapAssetLinesToGridRows(res.items);
      setRows(mappedRows);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load asset lines");
      const friendly = getFriendlyErrorFromUnknown(err);
      setFriendlyError(friendly);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadAssetLines();
  }, [loadAssetLines]);

  return {
    rows,
    loading,
    errorMsg,
    friendlyError,
    retry: loadAssetLines,
  };
}
