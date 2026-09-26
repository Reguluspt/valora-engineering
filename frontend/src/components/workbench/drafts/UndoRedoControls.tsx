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
    <div className="workbench-undo-controls" role="group" aria-label="Thao tác nháp">
      <button
        type="button"
        className="valora-button valora-button--subtle"
        onClick={onUndo}
        disabled={undoDisabled}
        title={undoDisabled ? "Không có thay đổi nháp để hoàn tác" : "Hoàn tác thay đổi nháp gần nhất"}
      >
        Hoàn tác
      </button>
      <button
        type="button"
        className="valora-button valora-button--subtle"
        onClick={onRedo}
        disabled={redoDisabled}
        title={redoDisabled ? "Không có thay đổi nháp để làm lại" : "Làm lại thay đổi nháp gần nhất"}
      >
        Làm lại
      </button>
    </div>
  );
}
