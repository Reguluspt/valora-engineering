import { useState, useEffect, useRef, useCallback } from "react";
import { WorkbenchSession } from "./WorkbenchSessionTypes";
import { createSession, sendHeartbeat } from "../../../api/workbenchSession";
import { ApiError } from "../../../api/client";

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
    try {
      setLoading(true);
      setError(null);
      setRbacError(null);
      setConflictError(false);
      // Hardcode UUID project ID for API compatibility with mock string
      const apiProjectId = "00000000-0000-0000-0000-000000000000";
      const newSession = await createSession({ project_id: apiProjectId });
      setSession(newSession);
      setLastHeartbeat(new Date().toLocaleTimeString());
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 403) {
          setRbacError("Permission denied: You do not have the required scopes to open a workbench session.");
        } else {
          setError(err.message);
        }
      } else {
        setError(err.message || "Failed to initialize workbench session");
      }
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    initSession();
  }, [initSession]);

  // Heartbeat loop
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
            setRbacError("Session expired or permission revoked.");
            clearInterval(interval);
          } else {
            // Treat other issues as temporary network loss
            console.warn("Heartbeat network warning:", err.message);
          }
        }
      }
    }, 15000); // 15 seconds interval

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
