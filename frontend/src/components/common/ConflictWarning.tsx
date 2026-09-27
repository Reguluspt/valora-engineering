import React from "react";
import { MessageBar } from "../ui/MessageBar";

interface ConflictWarningProps {
  onResolve: () => void;
}

export function ConflictWarning({ onResolve }: ConflictWarningProps) {
  return (
    <MessageBar
      actionLabel="Cập nhật dữ liệu"
      detail="Bản nháp cục bộ vẫn được giữ. Hãy rà soát dữ liệu mới trước khi xác nhận lại thay đổi."
      message="Dữ liệu trên hệ thống không còn khớp với phiên bản đang hiển thị."
      onAction={onResolve}
      title="Dữ liệu đã thay đổi"
      tone="conflict"
    />
  );
}
