import React from "react";

interface EmptyStateProps {
  title?: string;
  message?: string;
  onAction?: () => void;
  actionLabel?: string;
}

export function EmptyState({
  title = "No Data Found",
  message = "No items match your active filters or query parameters.",
  onAction,
  actionLabel = "Retry Search"
}: EmptyStateProps) {
  return (
    <div className="state-container">
      <h2 className="state-title">{title}</h2>
      <p className="state-message">{message}</p>
      {onAction && (
        <button className="action-btn" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  );
}
