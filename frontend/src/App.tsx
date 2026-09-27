import React, { useState, useEffect } from "react";
import { AppShell } from "./components/layout/AppShell";
import { WorkbenchLayout } from "./components/layout/WorkbenchLayout";
import { EmptyState } from "./components/common/EmptyState";
import { ErrorState } from "./components/common/ErrorState";
import { LoadingState } from "./components/common/LoadingState";
import { CaseOverviewPage } from "./components/case-overview/CaseOverviewPage";
import { NccSelectionPage } from "./components/ncc-selection/NccSelectionPage";
import { ProjectListPage } from "./components/projects/ProjectListPage";
import { M365ReturnPage, M365WorkspacePage } from "./components/m365/M365WorkspacePage";
import { LoginPage } from "./auth/LoginPage";
import { SessionProvider, useSession } from "./auth/SessionProvider";
import {
  APP_ROUTES,
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
  if (session.status === "loading") {
    return <LoadingState message="Đang khôi phục phiên làm việc…" />;
  }
  if (session.status === "error") {
    return (
      <ErrorState
        title="Chưa thể xác minh phiên làm việc"
        message={session.error || "Không thể kết nối với máy chủ."}
        onRetry={() => void session.restore()}
      />
    );
  }
  if (session.status === "unauthenticated" || !session.account) return <LoginPage />;
  return <AuthenticatedApp />;
}

export function AuthenticatedApp() {
  const { account, logout } = useSession();
  const [currentPath, setCurrentPath] = useState(() => {
    const hash = window.location.hash?.replace("#", "");
    return hash || NEUTRAL_PATH;
  });

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace("#", "");
      if (hash) {
        setCurrentPath(hash);
      }
    };
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const handleNavigate = (path: string) => {
    window.location.hash = path;
    setCurrentPath(path);
  };

  const renderRoute = () => {
    const projectRoute = splitProjectRoute(currentPath);
    if (projectRoute?.view === "overview") {
      return <CaseOverviewPage projectRef={projectRoute.projectRef} onNavigate={handleNavigate} />;
    }

    if (projectRoute?.view === "workbench") {
      return (
        <WorkbenchLayout
          projectRef={projectRoute.projectRef}
          onNavigateOverview={() => handleNavigate(projectOverviewPath(projectRoute.projectRef))}
        />
      );
    }

    if (projectRoute?.view === "ncc-selection") {
      return <NccSelectionPage projectRef={projectRoute.projectRef} onNavigate={handleNavigate} />;
    }

    if (projectRoute?.view === "documents") {
      return <M365WorkspacePage projectRef={projectRoute.projectRef} />;
    }

    if (currentPath === APP_ROUTES.projectList) {
      return <ProjectListPage onNavigate={handleNavigate} />;
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
      onLogout={() => void logout()}
      onNavigate={handleNavigate}
    >
      {renderRoute()}
    </AppShell>
  );
}
