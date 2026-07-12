import { useState, useEffect, useCallback } from "react";
import { fetchProjectAssetLines, ProjectAssetLineResponse } from "../../../api/assetLines";
import { AssetLineGridRow } from "../AssetGridTypes";
import { getFriendlyErrorFromUnknown } from "../../../errors/errorRegistry";

const PAGE_SIZE = 50;

function toIntSafe(val: string | undefined): number | null {
  if (val === undefined || val === null) return null;
  const parsed = parseInt(val, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export function mapAssetLinesToGridRows(items: ProjectAssetLineResponse[]): AssetLineGridRow[] {
  return items.map((item, idx) => ({
    project_asset_line_id: item.id,
    line_no: idx + 1,
    raw_name: item.asset_name,
    normalized_name: null,
    canonical_asset: null,
    asset_variant: null,
    taxonomy_node: null,
    quantity: item.quantity,
    unit: null,
    quote_batch_status: null,
    supplier_quote_1: null,
    supplier_quote_2: null,
    supplier_quote_3: null,
    appraised_price: item.appraised_unit_price ?? null,
    currency: null,
    validation_status: (item.validation_status as any) === "needs_review" ? "warning" : (item.validation_status as any),
    review_status: (item.review_status as any),
    row_version: toIntSafe(item.version_token) ?? null,
  }));
}

export function useProjectAssetLines(projectId: string) {
  const [rows, setRows] = useState<AssetLineGridRow[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadingMore, setLoadingMore] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [friendlyError, setFriendlyError] = useState<{ title: string; message: string; nextAction: string } | null>(null);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [hasMore, setHasMore] = useState<boolean>(false);

  const loadFirstPage = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setErrorMsg(null);
    setFriendlyError(null);

    try {
      const res = await fetchProjectAssetLines(projectId, { limit: PAGE_SIZE, offset: 0 });
      const mappedRows = mapAssetLinesToGridRows(res.items);
      setRows(mappedRows);
      setTotalCount(res.total);
      setHasMore(res.total > PAGE_SIZE);
    } catch (err: any) {
      setErrorMsg(err.message || "Không thể tải danh sách tài sản");
      setFriendlyError(getFriendlyErrorFromUnknown(err));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  const loadMore = useCallback(async () => {
    if (!projectId || loadingMore || !hasMore) return;
    setLoadingMore(true);

    try {
      const res = await fetchProjectAssetLines(projectId, { limit: PAGE_SIZE, offset: rows.length });
      const mappedRows = mapAssetLinesToGridRows(res.items);
      setRows((prev) => {
        const existingIds = new Set(prev.map((r) => r.project_asset_line_id));
        const newRows = mappedRows.filter((r) => !existingIds.has(r.project_asset_line_id));
        return [...prev, ...newRows];
      });
      setTotalCount(res.total);
      setHasMore(rows.length + mappedRows.length < res.total);
    } catch (err: any) {
      setErrorMsg(err.message || "Không thể tải thêm dữ liệu");
    } finally {
      setLoadingMore(false);
    }
  }, [projectId, loadingMore, hasMore, rows.length]);

  useEffect(() => {
    loadFirstPage();
  }, [loadFirstPage]);

  return {
    rows,
    loading,
    loadingMore,
    errorMsg,
    friendlyError,
    loadMore,
    hasMore,
    loadedCount: rows.length,
    totalCount,
    retry: loadFirstPage,
  };
}
