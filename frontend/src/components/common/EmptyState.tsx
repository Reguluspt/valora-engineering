import React from "react";
import { StateSurface } from "../ui/StateSurface";

export type EmptyStateKind = "first-use" | "no-results" | "not-applicable" | "completed";

interface EmptyStateProps {
  kind?: EmptyStateKind;
  title?: string;
  message?: string;
  onAction?: () => void;
  actionLabel?: string;
}

export function EmptyState({
  kind = "no-results",
  title,
  message,
  onAction,
  actionLabel,
}: EmptyStateProps) {
  const defaults: Record<EmptyStateKind, { title: string; message: string; actionLabel?: string }> = {
    "first-use": {
      title: "Chưa có dữ liệu",
      message: "Chưa có thông tin để hiển thị trong mục này.",
      actionLabel: "Bắt đầu",
    },
    "no-results": {
      title: "Không tìm thấy dữ liệu phù hợp",
      message: "Không có mục nào khớp với bộ lọc hoặc từ khóa hiện tại.",
      actionLabel: "Đặt lại tìm kiếm",
    },
    "not-applicable": {
      title: "Nội dung không áp dụng",
      message: "Mục này không áp dụng trong ngữ cảnh hiện tại.",
    },
    completed: {
      title: "Đã hoàn tất",
      message: "Không còn mục nào cần xử lý.",
    },
  };
  const fallback = defaults[kind];

  return (
    <StateSurface
      actionLabel={actionLabel ?? fallback.actionLabel}
      message={message ?? fallback.message}
      onAction={onAction}
      state={`EMPTY_${kind.replace("-", "_").toUpperCase()}`}
      title={title ?? fallback.title}
      tone={kind === "completed" ? "success" : "neutral"}
    />
  );
}
