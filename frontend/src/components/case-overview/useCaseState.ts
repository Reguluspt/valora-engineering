import { useCallback, useEffect, useRef, useState } from "react";

import { fetchCaseState, type CaseStateResponse } from "../../api/caseState";

export type CaseStateLoadState =
  | "INITIAL_LOADING"
  | "READY"
  | "PAGE_ERROR";

export interface CaseStateLoadError {
  title: string;
  message: string;
  nextAction: string;
}

function friendlyProjectionError(error: unknown): CaseStateLoadError {
  const status = typeof error === "object" && error !== null && "status" in error
    ? Number((error as { status?: unknown }).status)
    : 0;

  if (status === 401) {
    return {
      title: "Phiên làm việc đã hết hạn",
      message: "Không thể tải trạng thái hồ sơ khi phiên đăng nhập không còn hiệu lực.",
      nextAction: "Vui lòng đăng nhập lại rồi mở hồ sơ.",
    };
  }
  if (status === 403) {
    return {
      title: "Không có quyền xem hồ sơ",
      message: "Tài khoản hiện tại chưa có quyền xem trạng thái hồ sơ này.",
      nextAction: "Vui lòng liên hệ quản trị viên để kiểm tra quyền truy cập.",
    };
  }
  if (status === 404) {
    return {
      title: "Không tìm thấy hồ sơ",
      message: "Hồ sơ không tồn tại hoặc không thuộc phạm vi truy cập của tài khoản.",
      nextAction: "Vui lòng quay lại danh sách và chọn hồ sơ khác.",
    };
  }
  return {
    title: "Chưa thể tải trạng thái hồ sơ",
    message: "Hệ thống chưa thể tổng hợp trạng thái hồ sơ tại thời điểm này.",
    nextAction: "Vui lòng thử tải lại. Dữ liệu workflow sẽ không được suy đoán từ nguồn khác.",
  };
}

export function useCaseState(projectId: string) {
  const [projection, setProjection] = useState<CaseStateResponse | null>(null);
  const [state, setState] = useState<CaseStateLoadState>("INITIAL_LOADING");
  const [error, setError] = useState<CaseStateLoadError | null>(null);
  const generationRef = useRef(0);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    generationRef.current += 1;
    const generation = generationRef.current;
    const controller = new AbortController();

    setProjection(null);
    setState("INITIAL_LOADING");
    setError(null);

    fetchCaseState(projectId, controller.signal)
      .then((result) => {
        if (controller.signal.aborted || generation !== generationRef.current) return;
        setProjection(result);
        setState("READY");
      })
      .catch((caught) => {
        if (controller.signal.aborted || generation !== generationRef.current) return;
        setError(friendlyProjectionError(caught));
        setState("PAGE_ERROR");
      });

    return () => {
      controller.abort();
      generationRef.current += 1;
    };
  }, [projectId, retryToken]);

  const retry = useCallback(() => setRetryToken((token) => token + 1), []);

  return { projection, state, error, retry };
}
