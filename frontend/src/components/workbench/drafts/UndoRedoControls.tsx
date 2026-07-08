import React from "react";

interface UndoRedoControlsProps {
  undoDisabled: boolean;
  redoDisabled: boolean;
  onUndo: () => void;
  onRedo: () => void;
}

export function UndoRedoControls({
  undoDisabled,
  redoDisabled,
  onUndo,
  onRedo
}: UndoRedoControlsProps) {
  return (
    <div style={{ display: "flex", gap: "var(--space-sm)" }}>
      <button
        className="action-btn"
        onClick={onUndo}
        disabled={undoDisabled}
        title={undoDisabled ? "Undo stack empty" : "Undo last local draft change"}
      >
        ⎌ Undo
      </button>
      <button
        className="action-btn"
        onClick={onRedo}
        disabled={redoDisabled}
        title={redoDisabled ? "Redo stack empty" : "Redo last local draft change"}
      >
        ⎌ Redo
      </button>
    </div>
  );
}
