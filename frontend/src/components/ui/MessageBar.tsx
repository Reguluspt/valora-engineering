import React from "react";

export type MessageTone = "info" | "success" | "warning" | "error" | "conflict";

interface MessageBarProps {
  title: string;
  message: string;
  detail?: string;
  tone?: MessageTone;
  role?: "alert" | "status";
  actionLabel?: string;
  onAction?: () => void;
  dismissLabel?: string;
  onDismiss?: () => void;
}

const TONE_ICONS: Record<MessageTone, string> = {
  info: "ℹ",
  success: "✓",
  warning: "!",
  error: "!",
  conflict: "↻",
};

export function MessageBar({
  title,
  message,
  detail,
  tone = "info",
  role = tone === "error" || tone === "conflict" ? "alert" : "status",
  actionLabel,
  onAction,
  dismissLabel = "Đóng thông báo",
  onDismiss,
}: MessageBarProps) {
  return (
    <div
      aria-live={role === "alert" ? "assertive" : "polite"}
      className={`valora-message valora-message--${tone}`}
      role={role}
    >
      <span aria-hidden="true">{TONE_ICONS[tone]}</span>
      <div>
        <strong>{title}</strong>
        <div>{message}</div>
        {detail && <small>{detail}</small>}
      </div>
      {onAction && actionLabel && (
        <button className="valora-button valora-button--secondary" onClick={onAction} type="button">
          {actionLabel}
        </button>
      )}
      {onDismiss && (
        <button
          aria-label={dismissLabel}
          className="valora-button valora-button--subtle"
          onClick={onDismiss}
          title={dismissLabel}
          type="button"
        >
          <span aria-hidden="true">×</span>
        </button>
      )}
    </div>
  );
}
