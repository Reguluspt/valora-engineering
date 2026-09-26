import React from "react";
import { StateSurface } from "../ui/StateSurface";

interface ErrorStateProps {
  scope?: "section" | "page";
  title?: string;
  message?: string;
  onRetry?: () => void;
  retryLabel?: string;
}

export function ErrorState({
  scope = "page",
  title = "Chưa thể tải dữ liệu",
  message = "Hệ thống chưa thể tải nội dung này.",
  onRetry,
  retryLabel = "Thử lại",
}: ErrorStateProps) {
  return (
    <StateSurface
      actionLabel={retryLabel}
      message={message}
      onAction={onRetry}
      role="alert"
      state={scope === "section" ? "SECTION_ERROR" : "PAGE_ERROR"}
      title={title}
      tone="error"
    />
  );
}
