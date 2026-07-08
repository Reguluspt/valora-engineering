import React from "react";

interface ApiErrorBannerProps {
  message: string;
  onDismiss?: () => void;
}

export function ApiErrorBanner({ message, onDismiss }: ApiErrorBannerProps) {
  return (
    <div style={{
      backgroundColor: "rgba(220,53,69,0.15)",
      color: "var(--status-error)",
      border: "1px solid var(--status-error)",
      borderRadius: "var(--radius-md)",
      padding: "var(--space-md)",
      marginBottom: "var(--space-md)",
      fontSize: "var(--font-size-sm)",
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center"
    }}>
      <span>⚠️ <strong>System Warning:</strong> {message}</span>
      {onDismiss && (
        <button
          onClick={onDismiss}
          style={{
            background: "none",
            border: "none",
            color: "var(--status-error)",
            cursor: "pointer",
            fontWeight: "bold"
          }}
        >
          ✕
        </button>
      )}
    </div>
  );
}
