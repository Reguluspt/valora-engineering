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
        type="text"
        value={currentValue}
        onChange={(e) => setCurrentValue(e.target.value)}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        autoFocus
        style={{
          width: "100%",
          backgroundColor: "var(--bg-primary)",
          color: "#fff",
          border: "1px solid var(--accent-cyan)",
          borderRadius: "var(--radius-sm)",
          padding: "2px 4px",
          outline: "none"
        }}
      />
    );
  }

  return (
    <div
      onClick={() => setEditing(true)}
      style={{
        padding: "4px",
        borderRadius: "var(--radius-sm)",
        border: isDirty ? "1px solid var(--status-draft)" : "1px solid transparent",
        backgroundColor: isDirty ? "rgba(229, 193, 88, 0.05)" : "transparent",
        minHeight: "24px",
        display: "flex",
        alignItems: "center"
      }}
      title="Click to edit locally. Hit Enter to save, Esc to revert."
    >
      {currentValue || <span style={{ color: "var(--text-muted)", fontStyle: "italic" }}>—</span>}
      {isDirty && (
        <span
          style={{
            marginLeft: "var(--space-xs)",
            fontSize: "10px",
            color: "var(--status-draft)",
            fontWeight: "bold"
          }}
          title="Draft only — not committed to database"
        >
          ● Draft
        </span>
      )}
    </div>
  );
}
