import { useState, useEffect, useRef, useCallback } from "react";
import { WorkbenchSession } from "./WorkbenchSessionTypes";
import { createSession, sendHeartbeat } from "../../../api/workbenchSession";
import { ApiError } from "../../../api/client";

const ZERO_UUID = "00000000-0000-0000-0000-000000000000";

export function useWorkbenchSession(projectId: string) {
  const [session, setSession] = useState<WorkbenchSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rbacError, setRbacError] = useState<string | null>(null);
  const [conflictError, setConflictError] = useState<boolean>(false);
  const [lastHeartbeat, setLastHeartbeat] = useState<string>("N/A");

  const sessionRef = useRef<WorkbenchSession | null>(null);
  sessionRef.current = session;

  const initSession = useCallback(async () => {
    if (!projectId || projectId === ZERO_UUID) {
      setLoading(false);
      setError("Mã hồ sơ không hợp lệ");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setRbacError(null);
      setConflictError(false);
      const newSession = await createSession({ project_id: projectId });
      setSession(newSession);
      setLastHeartbeat(new Date().toLocaleTimeString());
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 403) {
          setRbacError("Tài khoản chưa được cấp quyền mở phiên làm việc.");
        } else {
          setError(err.message);
        }
      } else {
        setError(err.message || "Không thể khởi tạo phiên làm việc");
      }
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    initSession();
  }, [initSession]);

  useEffect(() => {
    if (!session) return;

    const interval = setInterval(async () => {
      const current = sessionRef.current;
      if (!current) return;

      try {
        const updated = await sendHeartbeat(current.id, {
          expected_row_version: current.row_version
        });
        setSession(updated);
        setLastHeartbeat(new Date().toLocaleTimeString());
        setConflictError(false);
      } catch (err: any) {
        if (err instanceof ApiError) {
          if (err.status === 409) {
            setConflictError(true);
            clearInterval(interval);
          } else if (err.status === 403) {
            setRbacError("Phiên làm việc hết hạn hoặc quyền đã bị thu hồi.");
            clearInterval(interval);
          }
        }
      }
    }, 15000);

    return () => clearInterval(interval);
  }, [session]);

  return {
    session,
    loading,
    error,
    rbacError,
    conflictError,
    lastHeartbeat,
    retry: initSession
  };
}
