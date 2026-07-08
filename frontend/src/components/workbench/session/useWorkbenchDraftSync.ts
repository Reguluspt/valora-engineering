import { useCallback } from "react";
import {
  saveInlineEdit,
  saveCheckpoint,
  executeUndo,
  executeRedo
} from "../../../api/workbenchDrafts";
import { ApiError } from "../../../api/client";

export function useWorkbenchDraftSync(
  sessionId: string | undefined,
  onError?: (msg: string) => void,
  onConflict?: () => void
) {
  const syncInlineEdit = useCallback(async (
    targetType: string,
    targetId: string,
    fieldKey: string,
    draftValue: any,
    baseValue: any,
    baseRowVersion: number
  ) => {
    if (!sessionId) return;
    try {
      await saveInlineEdit(sessionId, {
        target_type: targetType,
        target_id: targetId,
        field_key: fieldKey,
        draft_value: draftValue,
        base_value: baseValue,
        base_row_version: baseRowVersion
      });
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 409 && onConflict) {
          onConflict();
        } else if (onError) {
          onError(err.message);
        }
      }
    }
  }, [sessionId, onError, onConflict]);

  const syncCheckpoint = useCallback(async (payload: any) => {
    if (!sessionId) return;
    try {
      await saveCheckpoint(sessionId, {
        checkpoint_payload: payload
      });
    } catch (err: any) {
      if (onError && err instanceof ApiError) onError(err.message);
    }
  }, [sessionId, onError]);

  const syncUndo = useCallback(async () => {
    if (!sessionId) return;
    try {
      await executeUndo(sessionId);
    } catch (err: any) {
      if (onError && err instanceof ApiError) onError(err.message);
    }
  }, [sessionId, onError]);

  const syncRedo = useCallback(async () => {
    if (!sessionId) return;
    try {
      await executeRedo(sessionId);
    } catch (err: any) {
      if (onError && err instanceof ApiError) onError(err.message);
    }
  }, [sessionId, onError]);

  return {
    syncInlineEdit,
    syncCheckpoint,
    syncUndo,
    syncRedo
  };
}
