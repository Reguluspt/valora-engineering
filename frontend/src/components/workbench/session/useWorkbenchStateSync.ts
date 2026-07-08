import { useCallback } from "react";
import {
  saveLayout,
  saveGridView,
  saveSelection,
  savePanelState
} from "../../../api/workbenchState";
import { ApiError } from "../../../api/client";

export function useWorkbenchStateSync(sessionId: string | undefined, onError?: (msg: string) => void) {
  const syncLayout = useCallback(async (name: string, payload: any, isDefault = false) => {
    if (!sessionId) return;
    try {
      await saveLayout(sessionId, {
        layout_name: name,
        layout_payload: payload,
        is_default: isDefault
      });
    } catch (err: any) {
      if (onError && err instanceof ApiError) onError(err.message);
    }
  }, [sessionId, onError]);

  const syncGridView = useCallback(async (name: string, columns: string[], filters: any, sort: any, isDefault = false) => {
    if (!sessionId) return;
    try {
      await saveGridView(sessionId, {
        view_name: name,
        columns,
        filters,
        sort,
        is_default: isDefault
      });
    } catch (err: any) {
      if (onError && err instanceof ApiError) onError(err.message);
    }
  }, [sessionId, onError]);

  const syncSelection = useCallback(async (targetType: string, ids: string[]) => {
    if (!sessionId) return;
    try {
      await saveSelection(sessionId, {
        selected_target_type: targetType,
        selected_target_ids: ids
      });
    } catch (err: any) {
      if (onError && err instanceof ApiError) onError(err.message);
    }
  }, [sessionId, onError]);

  const syncPanelState = useCallback(async (panelType: string, isExpanded: boolean, width: number) => {
    if (!sessionId) return;
    try {
      await savePanelState(sessionId, {
        panel_type: panelType,
        is_expanded: isExpanded,
        width
      });
    } catch (err: any) {
      if (onError && err instanceof ApiError) onError(err.message);
    }
  }, [sessionId, onError]);

  return {
    syncLayout,
    syncGridView,
    syncSelection,
    syncPanelState
  };
}
