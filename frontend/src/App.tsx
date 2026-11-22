import React, { useState, useEffect, useLayoutEffect, useRef } from "react";
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

export function AuthenticatedApp({ sessionActive = true }: { sessionActive?: boolean } = {}) {
  const { account, logout, restore } = useSession();
  useLayoutEffect(() => {
    activateCreateScope(account ? { organization_id: account.organization_id, actor_user_id: account.id } : null);
    return () => activateCreateScope(null);
  }, [account?.organization_id, account?.id]);
  const [currentPath, setCurrentPath] = useState(historyPath);
  const [rememberedAnalysis, setRememberedAnalysis] = useState<string | null>(null);
  const [analysisDirty, setAnalysisDirty] = useState(false);
  const [discardVersion, setDiscardVersion] = useState(0);
  const [leavePath, setLeavePath] = useState<string | null>(null);
  const leaveDialog = useRef<HTMLDialogElement>(null);
  const leaveFocus = useRef<HTMLElement | null>(null);
  const currentProjectRoute = splitProjectRoute(currentPath);
  const isAnalysis = currentProjectRoute?.view === "preliminary-analysis";
  const analysisPath = isAnalysis ? currentPath : rememberedAnalysis;
  const analysisProjectRef = analysisPath ? splitProjectRoute(analysisPath)?.projectRef : null;

  useLayoutEffect(() => {
    if (isAnalysis) setRememberedAnalysis(currentPath);
  }, [currentPath, isAnalysis]);

  useEffect(() => {
    const followBrowserHistory = () => {
      setLeavePath(null);
      setCurrentPath(historyPath());
    };
    window.addEventListener("hashchange", followBrowserHistory);
    window.addEventListener("popstate", followBrowserHistory);
    return () => {
      window.removeEventListener("hashchange", followBrowserHistory);
      window.removeEventListener("popstate", followBrowserHistory);
    };
  }, []);

  useEffect(() => {
    if (leavePath && leaveDialog.current && !leaveDialog.current.open) leaveDialog.current.showModal();
  }, [leavePath]);

  const navigate = (path: string) => {
    if (historyPath() === path) return;
    window.history.pushState(null, "", `#${path}`);
    setCurrentPath(path);
  };
  const discardAnalysis = () => {
    setAnalysisDirty(false);
    setDiscardVersion((version) => version + 1);
  };
  const handleNavigate = (path: string) => {
    if (path === currentPath) return;
    const next = splitProjectRoute(path);
    if (analysisDirty && (isAnalysis || (next?.view === "preliminary-analysis" && next.projectRef !== analysisProjectRef))) {
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
    if (!leavePath) return;
    discardAnalysis();
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
      {analysisPath && analysisProjectRef && <div hidden={!isAnalysis}>
        <PreliminaryAnalysisPage key={analysisProjectRef} projectRef={analysisProjectRef} active={isAnalysis && sessionActive}
          owner={analysisOwner(account)} onNavigate={handleNavigate} onSessionExpired={() => void restore()}
          onDirtyChange={setAnalysisDirty} discardVersion={discardVersion} />
      </div>}
      {!isAnalysis && renderRoute()}
      {sessionActive && !isAnalysis && analysisDirty && rememberedAnalysis &&
        <div className="valora-message" role="status">
          <span>Còn bản nháp phân tích chưa chốt trong phiên này.</span>{" "}
          <button className="valora-button valora-button--secondary" onClick={() => navigate(rememberedAnalysis)} type="button">Quay lại tiếp tục chỉnh sửa</button>{" "}
          <button className="valora-button valora-button--secondary" onClick={discardAnalysis} type="button">Bỏ bản nháp</button>
        </div>}
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
