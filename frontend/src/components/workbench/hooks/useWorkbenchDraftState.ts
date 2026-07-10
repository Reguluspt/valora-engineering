import { useState, useEffect, useCallback } from "react";
import { fetchProjectDraftState, AssetLineDraftState } from "../../../api/projects";
import { getFriendlyErrorFromUnknown } from "../../../errors/errorRegistry";

export function getDraftStatusLabelVi(status: string, hasUnsaved: boolean): string {
  if (status === "stale") return "Cần cập nhật mới";
  if (status === "locked") return "Đang khóa";
  if (hasUnsaved) return "Chưa lưu";
  if (status === "saved_draft") return "Đã lưu nháp";
  return "Không có thay đổi";
}

export function getDraftStatusBadge(status: string, hasUnsaved: boolean): "draft" | "review" | "approved" | "warning" | "error" | "blocking" {
  if (status === "stale") return "warning";
  if (status === "locked") return "blocking";
  if (hasUnsaved) return "draft";
  if (status === "saved_draft") return "review";
  return "approved";
}

export function useWorkbenchDraftState(projectId: string) {
  const [draftStates, setDraftStates] = useState<Record<string, AssetLineDraftState>>({});
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [friendlyError, setFriendlyError] = useState<{ title: string; message: string; nextAction: string } | null>(null);

  const loadDraftStates = useCallback(async () => {
    if (!projectId || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(projectId)) {
      return;
    }

    try {
      setLoading(true);
      setErrorMsg(null);
      setFriendlyError(null);

      const res = await fetchProjectDraftState(projectId);
      const mapped: Record<string, AssetLineDraftState> = {};
      res.items.forEach((item) => {
        mapped[item.asset_line_id] = item;
      });
      setDraftStates(mapped);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load draft states");
      setFriendlyError(getFriendlyErrorFromUnknown(err));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadDraftStates();
  }, [loadDraftStates]);

  return {
    draftStates,
    loading,
    errorMsg,
    friendlyError,
    reload: loadDraftStates
  };
}
