import React from "react";

interface StatusBadgeProps {
  status: "draft" | "review" | "approved" | "warning" | "error" | "blocking";
  label: string;
}

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const tone = {
    draft: "warning",
    review: "info",
    approved: "success",
    warning: "warning",
    error: "error",
    blocking: "error",
  }[status];

  return (
    <span className={`valora-status valora-status--${tone}`} data-status={status}>
      {label}
    </span>
  );
}
