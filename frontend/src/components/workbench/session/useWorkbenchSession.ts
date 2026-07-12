import { useState, useEffect, useRef, useCallback } from "react";
import { WorkbenchSession } from "./WorkbenchSessionTypes";
import { createSession, sendHeartbeat } from "../../../api/workbenchSession";
import { ApiError } from "../../../api/client";
import { isValidProjectUuid } from "../validators";

export function useWorkbenchSession(projectId: string) {
  const [session, setSession] = useState<WorkbenchSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rbacError, setRbacError] = useState<string | null>(null);
  const [conflictError, setConflictError] = useState<boolean>(false);
  const [lastHeartbeat, setLastHeartbeat] = useState<string>("—");

  const sessionRef = useRef<WorkbenchSession | null>(null);
  const projectGen = useRef(0);

  const initSession = useCallback(async () => {
    projectGen.current += 1;
    const gen = projectGen.current;

    if (!projectId || !isValidProjectUuid(projectId)) {
      setSession(null);
      sessionRef.current = null;
      setLoading(false);
      setError(projectId ? "Mã hồ sơ không hợp lệ" : null);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setRbacError(null);
      setConflictError(false);
      const newSession = await createSession({ project_id: projectId });
      if (gen !== projectGen.current) return;
      sessionRef.current = newSession;
      setSession(newSession);
      setLastHeartbeat(new Date().toLocaleTimeString());
    } catch (err: any) {
      if (gen !== projectGen.current) return;
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
      if (gen === projectGen.current) setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    setSession(null);
    sessionRef.current = null;
    setLoading(true);
    setError(null);
    setRbacError(null);
    setConflictError(false);
    initSession();
    return () => {
      projectGen.current += 1;
    };
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
        if (sessionRef.current !== current) return;
        sessionRef.current = updated;
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
