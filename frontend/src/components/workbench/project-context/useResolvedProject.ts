import { useState, useEffect, useCallback, useRef } from "react";
import { resolveProjectReference } from "../../../api/projects";
import { isValidProjectUuid } from "../validators";

export type ResolutionState = "idle" | "loading" | "ready" | "error";

export interface ResolvedProject {
  projectId: string | null;
  displayName: string | null;
  state: ResolutionState;
  error: { title: string; message: string; nextAction: string } | null;
  retry: () => void;
}

export function useResolvedProject(routeRef: string | null): ResolvedProject {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState<string | null>(null);
  const [state, setState] = useState<ResolutionState>("idle");
  const [error, setError] = useState<ResolvedProject["error"]>(null);
  const generationRef = useRef(0);

  const resolve = useCallback(async () => {
    generationRef.current += 1;
    const gen = generationRef.current;

    setProjectId(null);
    setDisplayName(null);

    if (!routeRef) {
      if (gen !== generationRef.current) return;
      setState("idle");
      setError(null);
      return;
    }

    const trimmed = routeRef.trim();
    if (!trimmed) {
      if (gen !== generationRef.current) return;
      setState("error");
      setError({
        title: "Mã hồ sơ không hợp lệ",
        message: "Không thể sử dụng mã dự án rỗng.",
        nextAction: "Vui lòng chọn một hồ sơ từ danh sách.",
      });
      return;
    }

    if (isValidProjectUuid(trimmed)) {
      if (gen !== generationRef.current) return;
      setProjectId(trimmed);
      setDisplayName("Hồ sơ");
      setState("ready");
      setError(null);
      return;
    }

    if (UUID_RE.test(trimmed) && !isValidProjectUuid(trimmed)) {
      if (gen !== generationRef.current) return;
      setState("error");
      setError({
        title: "Mã hồ sơ không hợp lệ",
        message: "Không thể sử dụng mã dự án rỗng.",
        nextAction: "Vui lòng chọn một hồ sơ từ danh sách.",
      });
      return;
    }

    if (gen !== generationRef.current) return;
    setState("loading");
    setError(null);

    try {
      const res = await resolveProjectReference(trimmed);
      if (gen !== generationRef.current) return;
      setProjectId(res.project_id);
      setDisplayName(res.display_name);
      setState("ready");
      setError(null);
    } catch (err: any) {
      if (gen !== generationRef.current) return;
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
  }, [routeRef]);

  useEffect(() => {
    resolve();
    return () => {
      generationRef.current += 1;
    };
  }, [resolve]);

  const retry = useCallback(() => {
    generationRef.current += 1;
    setState("loading");
    setError(null);
    resolve();
  }, [resolve]);

  return { projectId, displayName, state, error, retry };
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
