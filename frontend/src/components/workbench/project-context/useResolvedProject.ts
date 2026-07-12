import { useState, useEffect, useCallback } from "react";
import { resolveProjectReference } from "../../../api/projects";

export type ResolutionState = "idle" | "loading" | "ready" | "error";

export interface ResolvedProject {
  projectId: string | null;
  displayName: string | null;
  state: ResolutionState;
  error: { title: string; message: string; nextAction: string } | null;
  retry: () => void;
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ZERO_UUID = "00000000-0000-0000-0000-000000000000";

export function useResolvedProject(routeRef: string | null): ResolvedProject {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState<string | null>(null);
  const [state, setState] = useState<ResolutionState>("idle");
  const [error, setError] = useState<ResolvedProject["error"]>(null);
  const [retryCounter, setRetryCounter] = useState(0);

  const resolve = useCallback(async () => {
    if (!routeRef) {
      setProjectId(null);
      setDisplayName(null);
      setState("idle");
      setError(null);
      return;
    }

    if (UUID_RE.test(routeRef) && routeRef !== ZERO_UUID) {
      setProjectId(routeRef);
      setDisplayName("Hồ sơ");
      setState("ready");
      setError(null);
      return;
    }

    if (routeRef === ZERO_UUID) {
      setState("error");
      setError({
        title: "Mã hồ sơ không hợp lệ",
        message: "Không thể sử dụng mã hồ sơ rỗng.",
        nextAction: "Vui lòng chọn một hồ sơ từ danh sách.",
      });
      return;
    }

    setState("loading");
    setError(null);

    try {
      const res = await resolveProjectReference(routeRef);
      setProjectId(res.project_id);
      setDisplayName(res.display_name);
      setState("ready");
      setError(null);
    } catch (err: any) {
      setState("error");
      if (err.status === 404) {
        setError({
          title: "Không tìm thấy hồ sơ",
          message: "Không tìm thấy hồ sơ tương ứng với mã cung cấp.",
          nextAction: "Vui lòng mở hồ sơ từ danh sách hồ sơ hoặc thử tải lại.",
        });
      } else if (err.status === 409) {
        setError({
          title: "Trùng lặp hồ sơ",
          message: "Có nhiều hồ sơ trùng thông tin, vui lòng chọn từ danh sách hồ sơ.",
          nextAction: "Vui lòng liên hệ quản trị viên hoặc chọn chính xác mã ID.",
        });
      } else if (err.status === 403) {
        setError({
          title: "Không có quyền truy cập",
          message: "Hồ sơ không thuộc phạm vi truy cập của tài khoản này.",
          nextAction: "Vui lòng liên hệ quản trị viên để đăng ký vai trò phù hợp.",
        });
      } else {
        setError({
          title: "Lỗi phân giải hồ sơ",
          message: err.message || "Không thể phân giải mã hồ sơ.",
          nextAction: "Vui lòng thử lại hoặc chọn hồ sơ khác.",
        });
      }
    }
  }, [routeRef, retryCounter]);

  useEffect(() => {
    resolve();
  }, [resolve]);

  const retry = useCallback(() => {
    setRetryCounter((c) => c + 1);
  }, []);

  return { projectId, displayName, state, error, retry };
}
