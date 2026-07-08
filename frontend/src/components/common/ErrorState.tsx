import React from "react";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({
  title = "Error Loading Session",
  message = "A communication or security validation error occurred.",
  onRetry
}: ErrorStateProps) {
  return (
    <div className="state-container">
      <h2 className="state-title" style={{ color: "var(--status-error)" }}>{title}</h2>
      <p className="state-message">{message}</p>
      {onRetry && (
        <button className="action-btn" onClick={onRetry}>
          Retry Action
        </button>
      )}
    </div>
  );
}
