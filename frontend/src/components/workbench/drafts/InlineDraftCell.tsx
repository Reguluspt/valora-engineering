import React, { useState, useEffect } from "react";

interface InlineDraftCellProps {
  value: string;
  isDirty: boolean;
  onSave: (newValue: string) => void;
}

export function InlineDraftCell({ value, isDirty, onSave }: InlineDraftCellProps) {
  const [editing, setEditing] = useState(false);
  const [currentValue, setCurrentValue] = useState(value);

  // Sync value changes from outside (e.g. undo/redo)
  useEffect(() => {
    setCurrentValue(value);
  }, [value]);

  const handleBlur = () => {
    setEditing(false);
    onSave(currentValue);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      setEditing(false);
      onSave(currentValue);
    } else if (e.key === "Escape") {
      setEditing(false);
      setCurrentValue(value); // Revert
    }
  };

  if (editing) {
    return (
      <input
        className="valora-field asset-grid-draft-input"
        type="text"
        aria-label="Giá thẩm định nháp"
        onClick={(event) => event.stopPropagation()}
        value={currentValue}
        onChange={(e) => setCurrentValue(e.target.value)}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        autoFocus
      />
    );
  }

  return (
    <button
      type="button"
      className="asset-grid-draft-trigger"
      onClick={(event) => {
        event.stopPropagation();
        setEditing(true);
      }}
      data-dirty={isDirty}
      aria-label="Chỉnh sửa giá thẩm định nháp"
      title="Chọn để sửa nháp. Enter để lưu nháp, Escape để hủy chỉnh sửa."
    >
      {currentValue || <span className="asset-context-muted">—</span>}
      {isDirty && (
        <span
          className="asset-grid-draft-label"
          title="Giá trị nháp, chưa áp dụng vào dữ liệu chính thức"
        >
          Nháp chưa áp dụng
        </span>
      )}
    </button>
  );
}
