import { useEffect, useState } from "react";
import { fetchCaseState } from "../../api/caseState";
import { useResolvedProject } from "../workbench/project-context";

export function useStageNavigation(projectRef: string | null, actorScope: string) {
  const resolved = useResolvedProject(projectRef);
  const [authorization, setAuthorization] = useState<{ scope: string; allowed: boolean } | null>(null);
  const scope = `${actorScope}:${resolved.projectId || ""}`;
  useEffect(() => {
    const controller = new AbortController();
    setAuthorization(null);
    if (resolved.projectId) {
      void fetchCaseState(resolved.projectId, controller.signal).then(state => {
        if (!controller.signal.aborted) setAuthorization({ scope, allowed: state.capabilities.some(c => c.stage === "SUPPLIER_SELECTION" && c.available) });
      }).catch(() => { if (!controller.signal.aborted) setAuthorization({ scope, allowed: false }); });
    }
    return () => controller.abort();
  }, [resolved.projectId, scope]);
  return authorization?.scope === scope && authorization.allowed;
}
