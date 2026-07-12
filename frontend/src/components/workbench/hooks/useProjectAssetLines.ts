import { useState, useEffect, useCallback, useRef } from "react";
import { fetchProjectAssetLines, ProjectAssetLineResponse } from "../../../api/assetLines";
import { AssetLineGridRow } from "../AssetGridTypes";
import { getFriendlyErrorFromUnknown } from "../../../errors/errorRegistry";

const PAGE_SIZE = 50;

function parseVersionToken(val: string | undefined): number | null {
  if (val === undefined || val === null) return null;
  if (typeof val !== "string") return null;
  if (val === "") return null;
  if (!/^[1-9]\d*$/.test(val)) return null;
  const parsed = Number(val);
  if (!Number.isSafeInteger(parsed)) return null;
  return parsed;
}

export function mapAssetLinesToGridRows(items: ProjectAssetLineResponse[], offset: number): AssetLineGridRow[] {
  return items.map((item, idx) => ({
    project_asset_line_id: item.id,
    line_no: offset + idx + 1,
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
    row_version: parseVersionToken(item.version_token),
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
  const loadingMoreRef = useRef(false);
  const projectGen = useRef(0);
  const consumedOffsetRef = useRef(0);

  const resetState = useCallback(() => {
    setRows([]);
    setLoading(true);
    setLoadingMore(false);
    loadingMoreRef.current = false;
    consumedOffsetRef.current = 0;
    setErrorMsg(null);
    setFriendlyError(null);
    setTotalCount(0);
    setHasMore(false);
  }, []);

  const appendRows = useCallback((items: AssetLineGridRow[]) => {
    setRows((prev) => {
      const existingIds = new Set(prev.map((r) => r.project_asset_line_id));
      const newRows = items.filter((r) => !existingIds.has(r.project_asset_line_id));
      return [...prev, ...newRows];
    });
  }, []);

  const loadPage = useCallback(async (offset: number) => {
    if (!projectId) return;
    const gen = projectGen.current;

    try {
      const res = await fetchProjectAssetLines(projectId, { limit: PAGE_SIZE, offset });
      if (gen !== projectGen.current) return;

      const mappedRows = mapAssetLinesToGridRows(res.items, offset);
      if (offset === 0) {
        setRows(mappedRows);
      } else {
        appendRows(mappedRows);
      }
      consumedOffsetRef.current = offset + res.items.length;
      setTotalCount(res.total);
      setHasMore(consumedOffsetRef.current < res.total);
    } catch (err: any) {
      if (gen !== projectGen.current) return;
      setErrorMsg(err.message || "Không thể tải danh sách tài sản");
      setFriendlyError(getFriendlyErrorFromUnknown(err));
    } finally {
      if (gen === projectGen.current) {
        setLoading(false);
        setLoadingMore(false);
        loadingMoreRef.current = false;
      }
    }
  }, [projectId, appendRows]);

  useEffect(() => {
    resetState();
    projectGen.current += 1;

    setLoading(true);
    loadPage(0);

    return () => {
      projectGen.current += 1;
    };
  }, [projectId, loadPage, resetState]);

  const loadMore = useCallback(async () => {
    if (!projectId || loadingMoreRef.current || !hasMore) return;
    loadingMoreRef.current = true;
    setLoadingMore(true);
    await loadPage(consumedOffsetRef.current);
  }, [projectId, hasMore, loadPage]);

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
    retry: () => {
      resetState();
      projectGen.current += 1;
      setLoading(true);
      loadPage(0);
    },
  };
}
