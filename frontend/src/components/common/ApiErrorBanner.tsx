import React from "react";
import { getFriendlyErrorFromUnknown } from "../../errors/errorRegistry";

interface ApiErrorBannerProps {
  message: string;
  onDismiss?: () => void;
}

export function ApiErrorBanner({ message, onDismiss }: ApiErrorBannerProps) {
  // Translate the raw exception details to user friendly Vietnamese directions
  const friendly = getFriendlyErrorFromUnknown(message);

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
      flexDirection: "column",
      gap: "var(--space-xs)",
      justifyContent: "space-between",
      alignItems: "flex-start"
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", width: "100%" }}>
        <span>⚠️ <strong>{friendly.title}</strong></span>
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
      <span style={{ color: "var(--text-primary)" }}>{friendly.message}</span>
      <span style={{ color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>{friendly.nextAction}</span>
    </div>
  );
}
