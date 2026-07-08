import React from "react";

interface StatusBadgeProps {
  status: "draft" | "review" | "approved" | "warning" | "error" | "blocking";
  label: string;
}

export function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <span className={`badge badge-${status}`}>
      {label}
    </span>
  );
}
