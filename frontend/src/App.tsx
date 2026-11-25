import React, { useCallback, useState, useEffect, useLayoutEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { activateCreateScope, clearCreatePayloads } from "./components/precase/preliminaryCreateIntent";
import { AppShell } from "./components/layout/AppShell";
import { WorkbenchLayout } from "./components/layout/WorkbenchLayout";
import { EmptyState } from "./components/common/EmptyState";
import { ErrorState } from "./components/common/ErrorState";
import { LoadingState } from "./components/common/LoadingState";
import { CaseOverviewPage } from "./components/case-overview/CaseOverviewPage";
import { NccSelectionPage } from "./components/ncc-selection/NccSelectionPage";
import { useStageNavigation } from "./components/case-overview/useStageNavigation";
import { ProjectListPage } from "./components/projects/ProjectListPage";
import { PreliminaryRequestCreatePage } from "./components/precase/PreliminaryRequestCreatePage";
import { PreliminaryRequestsPage } from "./components/precase/PreliminaryRequestsPage";
import { PreliminaryIntakePage } from "./components/precase/PreliminaryIntakePage";
import { analysisOwner, clearLegacyAnalysisStorage, PreliminaryAnalysisPage } from "./components/precase/PreliminaryAnalysisPage";
import { PreliminaryCompletionPage } from "./components/precase/PreliminaryCompletionPage";
import { M365ReturnPage, M365WorkspacePage } from "./components/m365/M365WorkspacePage";
import { LoginPage } from "./auth/LoginPage";
import { SessionProvider, useSession } from "./auth/SessionProvider";
import {
  APP_ROUTES,
  projectListVerificationCode,
  projectOverviewPath,
  projectPreliminaryAnalysisPath,
  splitProjectRoute,
} from "./contracts/valoraV23";

const WORKBENCH_BASE = APP_ROUTES.projectList;
const NEUTRAL_PATH = WORKBENCH_BASE;

export function App() {
  return (
    <SessionProvider>
      <SessionGate />
    </SessionProvider>
  );
}

function SessionGate() {
  const session = useSession();
  useLayoutEffect(clearLegacyAnalysisStorage, []);
  const authenticated = session.status === "authenticated";
  const account = session.account;
  if (session.status === "unauthenticated") return <LoginPage />;
  return <>
    {account && <div hidden={!authenticated}>
      <AuthenticatedApp key={JSON.stringify([account.organization_id, account.id, account.session_incarnation, analysisOwner(account)])}
        sessionActive={authenticated} />
    </div>}
    {session.status === "loading" && <LoadingState message="Đang khôi phục phiên làm việc…" />}
    {session.status === "error" && <ErrorState
      title="Chưa thể xác minh phiên làm việc"
      message={session.error || "Không thể kết nối với máy chủ."}
      onRetry={() => void session.restore()}
    />}
  </>;
}

const historyPath = () => window.location.hash.slice(1) || NEUTRAL_PATH;

function AnalysisRoute(props: React.ComponentProps<typeof PreliminaryAnalysisPage>) {
  const host = useRef<HTMLDivElement>(null);
  const [container] = useState(() => document.createElement("div"));
  useLayoutEffect(() => {
    if (props.active) host.current?.appendChild(container);
    return () => container.remove();
  }, [container, props.active]);
  // Detached editors keep their UI state without putting their data or fixed workspace IDs in the destination DOM.
  return <div ref={host} hidden={!props.active}>{createPortal(<PreliminaryAnalysisPage {...props} />, container)}</div>;
}

export function AuthenticatedApp({ sessionActive = true }: { sessionActive?: boolean } = {}) {
  const { account, logout, restore } = useSession();
  useLayoutEffect(() => {
    activateCreateScope(account ? { organization_id: account.organization_id, actor_user_id: account.id } : null);
    return () => activateCreateScope(null);
  }, [account?.organization_id, account?.id]);
  const [currentPath, setCurrentPath] = useState(historyPath);
  const [dirtyProjects, setDirtyProjects] = useState<ReadonlySet<string>>(() => new Set());
  const [leavePath, setLeavePath] = useState<string | null>(null);
  const leaveDialog = useRef<HTMLDialogElement>(null);
  const leaveFocus = useRef<HTMLElement | null>(null);
  const currentProjectRoute = splitProjectRoute(currentPath);
  const activeAnalysis = currentProjectRoute?.view === "preliminary-analysis" ? currentProjectRoute.projectRef : null;
  const parkedDrafts = [...dirtyProjects].filter((projectRef) => projectRef !== activeAnalysis);
  const analysisProjects = [...dirtyProjects];
  if (activeAnalysis && !dirtyProjects.has(activeAnalysis)) analysisProjects.push(activeAnalysis);
  const setAnalysisDirty = useCallback((projectRef: string, dirty: boolean) => {
    setDirtyProjects((current) => {
      if (current.has(projectRef) === dirty) return current;
      const next = new Set(current);
      if (dirty) next.add(projectRef);
      else next.delete(projectRef);
      return next;
    });
  }, []);
  const invalidateAnalysisOwner = useCallback(() => {
    setDirtyProjects(new Set());
  }, []);

  useLayoutEffect(() => {
    const followBrowserHistory = () => {
      const path = historyPath();
      if (path === currentPath) return;
      setLeavePath(null);
      leaveFocus.current = null;
      setCurrentPath(path);
    };
    window.addEventListener("hashchange", followBrowserHistory);
    window.addEventListener("popstate", followBrowserHistory);
    return () => {
      window.removeEventListener("hashchange", followBrowserHistory);
      window.removeEventListener("popstate", followBrowserHistory);
    };
  }, [currentPath]);

  useEffect(() => {
    if (leavePath && leaveDialog.current && !leaveDialog.current.open) leaveDialog.current.showModal();
  }, [leavePath]);

  const navigate = (path: string) => {
    if (historyPath() !== path) window.history.pushState(null, "", `#${path}`);
    setCurrentPath(path);
  };
  const handleNavigate = (path: string) => {
    if (path === currentPath) return;
    const next = splitProjectRoute(path);
    if (activeAnalysis && dirtyProjects.has(activeAnalysis) &&
      (next?.view !== "preliminary-analysis" || next.projectRef !== activeAnalysis)) {
      leaveFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      setLeavePath(path);
      return;
    }
    navigate(path);
  };
  const stay = () => {
    setLeavePath(null);
    leaveDialog.current?.close();
    leaveFocus.current?.focus();
    leaveFocus.current = null;
  };
  const discardAndNavigate = () => {
    if (!leavePath || historyPath() !== currentPath) return;
    if (activeAnalysis) setAnalysisDirty(activeAnalysis, false);
    setLeavePath(null);
    leaveFocus.current = null;
    navigate(leavePath);
  };
  const supplierSelectionAvailable = useStageNavigation(splitProjectRoute(currentPath)?.projectRef || null,
    account ? `${account.organization_id}:${account.id}` : "");

  const renderRoute = () => {
    const projectRoute = splitProjectRoute(currentPath);
    if (projectRoute?.view === "overview") {
      return <CaseOverviewPage projectRef={projectRoute.projectRef} onNavigate={handleNavigate} />;
    }

    if (projectRoute?.view === "preliminary-intake") {
      return <PreliminaryIntakePage projectRef={projectRoute.projectRef} onNavigate={handleNavigate} onSessionExpired={() => void restore()} />;
    }

    if (projectRoute?.view === "preliminary-completion") {
      return <PreliminaryCompletionPage projectRef={projectRoute.projectRef} permissions={account?.permissions ?? []} onNavigate={handleNavigate} onSessionExpired={() => void restore()} />;
    }

    if (projectRoute?.view === "workbench") {
      return (
        <WorkbenchLayout
          projectRef={projectRoute.projectRef}
          actorScope={account ? `${account.organization_id}:${account.id}` : undefined}
          onNavigateOverview={() => handleNavigate(projectOverviewPath(projectRoute.projectRef))}
        />
      );
    }

    if (projectRoute?.view === "ncc-selection") {
      return supplierSelectionAvailable ? <NccSelectionPage projectRef={projectRoute.projectRef} onNavigate={handleNavigate} />
        : <EmptyState title="Chưa có hành động tiếp theo được phép" message="Trạng thái hồ sơ hiện tại chưa cho phép chọn nhà cung cấp."
          actionLabel="Về tổng quan hồ sơ" onAction={() => handleNavigate(projectOverviewPath(projectRoute.projectRef))} />;
    }

    if (projectRoute?.view === "documents") {
      return <M365WorkspacePage projectRef={projectRoute.projectRef} />;
    }

    if (currentPath.split("?", 1)[0] === APP_ROUTES.projectList) {
      return <ProjectListPage onNavigate={handleNavigate} onSessionExpired={() => void restore()} verificationCode={projectListVerificationCode(currentPath)} />;
    }

    if (currentPath === APP_ROUTES.preliminaryRequestCreate) {
      return <PreliminaryRequestCreatePage scope={{ organization_id: account!.organization_id, actor_user_id: account!.id }} canCreate={account!.permissions.includes("project:create")} onNavigate={handleNavigate} onSessionExpired={() => void restore()} />;
    }

    if (currentPath === APP_ROUTES.preliminaryRequestManagement) {
      return <PreliminaryRequestsPage onNavigate={handleNavigate} onSessionExpired={() => void restore()} />;
    }

    if (currentPath.split("?", 1)[0] === APP_ROUTES.m365Return) {
      return <M365ReturnPage currentPath={currentPath} onNavigate={handleNavigate} />;
    }

    return (
      <EmptyState
        title="Không tìm thấy trang"
        message="Trang được yêu cầu không tồn tại."
        onAction={() => handleNavigate(NEUTRAL_PATH)}
        actionLabel="Về bàn làm việc"
      />
    );
  };

  return (
    <AppShell
      account={account!}
      currentPath={currentPath}
      supplierSelectionAvailable={supplierSelectionAvailable}
      onLogout={() => { clearCreatePayloads(); void logout(); }}
      onNavigate={handleNavigate}
      utilityActions={<button className="valora-button valora-button--subtle" onClick={() => handleNavigate(APP_ROUTES.preliminaryRequestCreate)} type="button">Khôi phục yêu cầu sơ bộ</button>}
    >
      {sessionActive && <div role="status">{parkedDrafts.length > 0 && "Còn bản nháp phân tích chưa chốt trong phiên này."}</div>}
      {sessionActive && parkedDrafts.map((projectRef) =>
        <div key={projectRef} className="valora-message" role="group" aria-label={`Bản nháp phân tích hồ sơ ${projectRef}`}>
          <span>Hồ sơ {projectRef}</span>{" "}
          <button className="valora-button valora-button--secondary" onClick={() => handleNavigate(projectPreliminaryAnalysisPath(projectRef))} type="button">Quay lại tiếp tục chỉnh sửa</button>{" "}
          <button className="valora-button valora-button--secondary" onClick={() => setAnalysisDirty(projectRef, false)} type="button">Bỏ bản nháp</button>
        </div>)}
      {analysisProjects.map((projectRef) => <AnalysisRoute key={projectRef} projectRef={projectRef}
        active={projectRef === activeAnalysis && sessionActive} owner={analysisOwner(account)}
        onNavigate={handleNavigate} onSessionExpired={() => void restore()} onOwnerLost={invalidateAnalysisOwner}
        onDirtyChange={setAnalysisDirty} />)}
      {!activeAnalysis && renderRoute()}
      {leavePath && sessionActive && <dialog ref={leaveDialog} aria-label="Rời phân tích sơ bộ"
        className="valora-panel precase-confirm-dialog" onCancel={(event) => { event.preventDefault(); stay(); }}>
        <div className="valora-panel__header">Bản nháp phân tích chưa chốt</div>
        <div className="valora-panel__body"><p>Rời trang sẽ bỏ các thay đổi trong bản nháp này.</p>
          <button className="valora-button valora-button--secondary" onClick={stay} type="button">Ở lại chỉnh sửa</button>
          <button className="valora-button valora-button--primary" onClick={discardAndNavigate} type="button">Rời đi và bỏ thay đổi</button>
        </div>
      </dialog>}
    </AppShell>
  );
}
