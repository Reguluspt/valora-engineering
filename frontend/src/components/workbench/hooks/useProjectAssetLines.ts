import { useState, useEffect, useCallback } from "react";
import { fetchProjectAssetLines, ProjectAssetLineResponse } from "../../../api/assetLines";
import { resolveProjectReference } from "../../../api/projects";
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
  const [resolvedUuid, setResolvedUuid] = useState<string | null>(null);

  // Validate and resolve project ID
  useEffect(() => {
    let active = true;
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

    if (uuidRegex.test(projectId)) {
      setResolvedUuid(projectId);
      return;
    }

    async function resolve() {
      try {
        setLoading(true);
        setErrorMsg(null);
        setFriendlyError(null);

        const res = await resolveProjectReference(projectId);
        if (active) {
          setResolvedUuid(res.project_id);
        }
      } catch (err: any) {
        if (!active) return;
        setErrorMsg(err.message || "Failed to resolve project reference");
        
        if (err.status === 404) {
          setFriendlyError({
            title: "Không tìm thấy hồ sơ",
            message: "Không tìm thấy hồ sơ tương ứng với mã cung cấp.",
            nextAction: "Vui lòng mở hồ sơ từ danh sách hồ sơ hoặc thử tải lại."
          });
        } else if (err.status === 409) {
          setFriendlyError({
            title: "Trùng lặp hồ sơ",
            message: "Có nhiều hồ sơ trùng thông tin, vui lòng chọn từ danh sách hồ sơ.",
            nextAction: "Vui lòng liên hệ quản trị viên hoặc chọn chính xác mã ID."
          });
        } else if (err.status === 403) {
          setFriendlyError({
            title: "Không có quyền truy cập",
            message: "Hồ sơ không thuộc phạm vi truy cập của tài khoản này.",
            nextAction: "Vui lòng liên hệ quản trị viên để đăng ký vai trò phù hợp."
          });
        } else {
          setFriendlyError(getFriendlyErrorFromUnknown(err));
        }
        setLoading(false);
      }
    }

    resolve();

    return () => {
      active = false;
    };
  }, [projectId]);

  const loadAssetLines = useCallback(async () => {
    if (!resolvedUuid) return;

    try {
      setLoading(true);
      setErrorMsg(null);
      setFriendlyError(null);

      const res = await fetchProjectAssetLines(resolvedUuid);
      const mappedRows = mapAssetLinesToGridRows(res.items);
      setRows(mappedRows);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load asset lines");
      setFriendlyError(getFriendlyErrorFromUnknown(err));
    } finally {
      setLoading(false);
    }
  }, [resolvedUuid]);

  useEffect(() => {
    loadAssetLines();
  }, [loadAssetLines]);

  return {
    rows,
    loading,
    errorMsg,
    friendlyError,
    retry: resolvedUuid ? loadAssetLines : () => {
      // Re-trigger resolution
      setResolvedUuid(null);
      setLoading(true);
    },
  };
}
