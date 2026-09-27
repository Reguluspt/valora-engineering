import React from "react";

interface StateSurfaceProps {
  state: string;
  title: string;
  message: string;
  tone?: "neutral" | "error" | "success";
  role?: "alert" | "status";
  titleClassName?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function StateSurface({
  state,
  title,
  message,
  tone = "neutral",
  role = "status",
  titleClassName = "valora-state__title",
  actionLabel,
  onAction,
}: StateSurfaceProps) {
  const content = (
    <>
      <h2 className={titleClassName}>{title}</h2>
      <p>{message}</p>
    </>
  );

  return (
    <section
      aria-live={role === "alert" ? "assertive" : "polite"}
      className="valora-state"
      data-state={state}
      role={role}
    >
      {tone === "neutral" ? content : (
        <div className={`valora-message valora-message--${tone}`}>
          <div>{content}</div>
        </div>
      )}
      {onAction && actionLabel && (
        <button className="valora-button valora-button--primary" onClick={onAction} type="button">
          {actionLabel}
        </button>
      )}
    </section>
  );
}
