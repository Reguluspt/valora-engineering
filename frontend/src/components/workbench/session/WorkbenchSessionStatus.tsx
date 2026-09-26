import React from "react";
import { getFriendlyErrorFromUnknown } from "../../../errors/errorRegistry";
import { t } from "../../../i18n";
import { MessageBar } from "../../ui/MessageBar";

interface WorkbenchSessionStatusProps {
  loading: boolean;
  error: string | null;
  rbacError: string | null;
  conflictError: boolean;
  sessionId: string | undefined;
  rowVersion: number | undefined;
  lastHeartbeat: string;
  onRetry: () => void;
}

export function WorkbenchSessionStatus({
  loading,
  error,
  rbacError,
  conflictError,
  lastHeartbeat,
  onRetry
}: WorkbenchSessionStatusProps) {
  if (loading) {
    return (
      <MessageBar
        message="Hệ thống đang xác minh kết nối của phiên làm việc."
        title="Đang chuẩn bị phiên làm việc"
        tone="info"
      />
    );
  }

  if (rbacError || conflictError) {
    return null;
  }

  if (error) {
    const friendly = getFriendlyErrorFromUnknown(error);
    return (
      <MessageBar
        actionLabel={t("workbench.status.retry")}
        detail={friendly.nextAction}
        message={friendly.message}
        onAction={onRetry}
        title={friendly.title}
        tone="error"
      />
    );
  }

  return (
    <MessageBar
      detail={`Lần kiểm tra gần nhất: ${lastHeartbeat}`}
      message="Anh/chị có thể tiếp tục làm việc với dữ liệu đang hiển thị."
      title="Phiên làm việc đang hoạt động"
      tone="success"
    />
  );
}
