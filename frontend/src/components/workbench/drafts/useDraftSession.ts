import { useState, useCallback } from "react";
import { InlineEditDraft, UndoRedoStackEntry, AutosaveCheckpoint } from "./DraftStateTypes";

export function useDraftSession() {
  const [drafts, setDrafts] = useState<Record<string, InlineEditDraft>>({});
  const [undoStack, setUndoStack] = useState<UndoRedoStackEntry[]>([]);
  const [redoStack, setRedoStack] = useState<UndoRedoStackEntry[]>([]);
  const [checkpoint, setCheckpoint] = useState<AutosaveCheckpoint>({
    id: "session-init",
    timestamp: "N/A",
    status: "idle"
  });

  const updateDraft = useCallback((
    project_asset_line_id: string,
    field_key: string,
    draft_value: any,
    base_value: any,
    base_row_version: number
  ) => {
    const draftKey = `${project_asset_line_id}:${field_key}`;
    const beforeValue = drafts[draftKey]?.draft_value ?? base_value;

    if (draft_value === base_value) {
      // Cleaned back to base
      setDrafts((prev) => {
        const next = { ...prev };
        delete next[draftKey];
        return next;
      });
      return;
    }

    const newDraft: InlineEditDraft = {
      project_asset_line_id,
      field_key,
      draft_value,
      base_value,
      base_row_version
    };

    setDrafts((prev) => ({ ...prev, [draftKey]: newDraft }));

    // Record Undo Stack Entry
    const stackEntry: UndoRedoStackEntry = {
      project_asset_line_id,
      field_key,
      before_value: beforeValue,
      after_value: draft_value,
      timestamp: new Date().toLocaleTimeString()
    };

    setUndoStack((prev) => [...prev, stackEntry]);
    setRedoStack([]); // Clear Redo on new action
    setCheckpoint((prev) => ({
      ...prev,
      status: "dirty"
    }));
  }, [drafts]);

  const undo = useCallback(() => {
    if (undoStack.length === 0) return;

    const entry = undoStack[undoStack.length - 1];
    setUndoStack((prev) => prev.slice(0, -1));
    setRedoStack((prev) => [...prev, entry]);

    const draftKey = `${entry.project_asset_line_id}:${entry.field_key}`;
    setDrafts((prev) => {
      const next = { ...prev };
      if (entry.before_value === next[draftKey]?.base_value) {
        delete next[draftKey];
      } else {
        next[draftKey] = {
          ...next[draftKey],
          draft_value: entry.before_value
        };
      }
      return next;
    });

    setCheckpoint((prev) => ({
      ...prev,
      status: "dirty"
    }));
  }, [undoStack]);

  const redo = useCallback(() => {
    if (redoStack.length === 0) return;

    const entry = redoStack[redoStack.length - 1];
    setRedoStack((prev) => prev.slice(0, -1));
    setUndoStack((prev) => [...prev, entry]);

    const draftKey = `${entry.project_asset_line_id}:${entry.field_key}`;
    setDrafts((prev) => {
      const next = { ...prev };
      next[draftKey] = {
        ...next[draftKey],
        draft_value: entry.after_value
      };
      return next;
    });

    setCheckpoint((prev) => ({
      ...prev,
      status: "dirty"
    }));
  }, [redoStack]);

  const triggerAutosaveMock = useCallback(() => {
    setCheckpoint({
      id: Math.random().toString(36).substring(7),
      timestamp: new Date().toLocaleTimeString(),
      status: "checkpointed"
    });
  }, []);

  return {
    drafts,
    undoStack,
    redoStack,
    checkpoint,
    updateDraft,
    undo,
    redo,
    triggerAutosaveMock
  };
}
