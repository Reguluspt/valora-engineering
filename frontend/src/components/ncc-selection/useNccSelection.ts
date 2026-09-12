import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchNccSelections,
  type NccSelectionAggregateResponse,
} from "../../api/nccSelection";

export type NccSelectionLoadState =
  | "INITIAL_LOADING"
  | "READY"
  | "PAGE_ERROR";

export interface NccSelectionLoadError {
  title: string;
  message: string;
  nextAction: string;
}

export type ConfirmFailure =
  | { kind: "version_conflict"; message: string }
  | { kind: "error"; message: string };

function statusOf(error: unknown): number {
  return typeof error === "object" && error !== null && "status" in error
    ? Number((error as { status?: unknown }).status)
    : 0;
}

function codeOf(error: unknown): string | undefined {
  if (typeof error !== "object" || error === null) return undefined;
  const asRecord = error as {
    code?: unknown;
    detail?: {
      code?: unknown;
      error_code?: unknown;
      detail?: { code?: unknown; error_code?: unknown } | unknown;
    };
  };
  if (typeof asRecord.code === "string") return asRecord.code;
  const detail = asRecord.detail;
  if (detail && typeof detail === "object") {
    if (typeof detail.code === "string") return detail.code;
    if (typeof detail.error_code === "string") return detail.error_code;
    const nested = detail.detail;
    if (nested && typeof nested === "object") {
      const nestedRecord = nested as { code?: unknown; error_code?: unknown };
      if (typeof nestedRecord.error_code === "string") return nestedRecord.error_code;
      if (typeof nestedRecord.code === "string") return nestedRecord.code;
    }
  }
  return undefined;
}

export function friendlyNccError(error: unknown): NccSelectionLoadError {
  const status = statusOf(error);
  if (status === 401) {
    return {
      title: "Phiên làm việc đã hết hạn",
      message: "Không thể tải dữ liệu lựa chọn NCC khi phiên đăng nhập không còn hiệu lực.",
      nextAction: "Vui lòng đăng nhập lại rồi mở hồ sơ.",
    };
  }
  if (status === 403) {
    return {
      title: "Không có quyền xem dữ liệu",
      message: "Tài khoản hiện tại chưa có quyền xem lựa chọn NCC của hồ sơ này.",
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
    title: "Chưa thể tải dữ liệu NCC",
    message: "Hệ thống chưa thể tải dữ liệu lựa chọn NCC tại thời điểm này.",
    nextAction: "Vui lòng thử tải lại.",
  };
}

export function mapConfirmError(error: unknown): ConfirmFailure {
  const status = statusOf(error);
  if (status === 409 && codeOf(error) === "selection_revision_conflict") {
    return {
      kind: "version_conflict",
      message:
        "Dữ liệu lựa chọn NCC đã được thay đổi. Vui lòng tải lại và xác nhận lại.",
    };
  }
  return { kind: "error", message: "Không thể xác nhận lựa chọn NCC." };
}

export function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `ncc-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function useNccSelection(projectId: string) {
  const [aggregate, setAggregate] = useState<NccSelectionAggregateResponse | null>(null);
  const [state, setState] = useState<NccSelectionLoadState>("INITIAL_LOADING");
  const [error, setError] = useState<NccSelectionLoadError | null>(null);
  const generationRef = useRef(0);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    generationRef.current += 1;
    const generation = generationRef.current;
    const controller = new AbortController();

    setAggregate(null);
    setState("INITIAL_LOADING");
    setError(null);

    fetchNccSelections(projectId, controller.signal)
      .then((result) => {
        if (controller.signal.aborted || generation !== generationRef.current) return;
        setAggregate(result);
        setState("READY");
      })
      .catch((caught) => {
        if (controller.signal.aborted || generation !== generationRef.current) return;
        setError(friendlyNccError(caught));
        setState("PAGE_ERROR");
      });

    return () => {
      controller.abort();
      generationRef.current += 1;
    };
  }, [projectId, retryToken]);

  const reload = useCallback(() => setRetryToken((token) => token + 1), []);

  return { aggregate, state, error, retry: reload, reload };
}
