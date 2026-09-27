import React from "react";
import {
  APP_ROUTES,
  projectOverviewPath,
  projectWorkbenchPath,
  projectNccSelectionPath,
  projectDocumentsPath,
  splitProjectRoute,
} from "../../contracts/valoraV23";
import type { AccountContext } from "../../api/auth";
import { t } from "../../i18n";

interface AppShellProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  children: React.ReactNode;
  account: AccountContext;
  onLogout: () => void;
}

export function AppShell({ currentPath, onNavigate, account, onLogout, children }: AppShellProps) {
  const projectRoute = splitProjectRoute(currentPath);

  const workbenchPath = projectRoute
    ? projectWorkbenchPath(projectRoute.projectRef)
    : APP_ROUTES.projectList;

  const navigate = (event: React.MouseEvent<HTMLAnchorElement>, path: string) => {
    event.preventDefault();
    onNavigate(path);
  };

  const navItem = (path: string, label: string, isCurrent: boolean) => (
    <li className="nav-item">
      <a
        aria-current={isCurrent ? "page" : undefined}
        className={`nav-link${isCurrent ? " active" : ""}`}
        href={`#${path}`}
        onClick={(event) => navigate(event, path)}
      >
        {label}
      </a>
    </li>
  );

  return (
    <div className="app-container">
      <aside className="sidebar">
        <header>
          <p className="project-title">Valora</p>
        </header>
        <nav aria-label="Điều hướng chính">
          <ul className="nav-links">
            {navItem(
              workbenchPath,
              t("nav.workbench"),
              projectRoute?.view === "workbench" || currentPath === APP_ROUTES.projectList,
            )}
            {projectRoute && navItem(
              projectOverviewPath(projectRoute.projectRef),
              t("nav.caseOverview"),
              projectRoute.view === "overview",
            )}
            {projectRoute && navItem(
              projectDocumentsPath(projectRoute.projectRef),
              "Không gian tài liệu",
              projectRoute.view === "documents",
            )}
            {projectRoute && navItem(
              projectNccSelectionPath(projectRoute.projectRef),
              t("nav.nccSelection"),
              projectRoute.view === "ncc-selection",
            )}
          </ul>
        </nav>
        <div className="account-context">
          <span>{account.organization_slug}</span>
          <strong>{account.full_name || account.email}</strong>
          <small>{account.email}</small>
          <button aria-label={`Đăng xuất tài khoản ${account.email}`} onClick={onLogout} type="button">
            Đăng xuất
          </button>
        </div>
      </aside>
      <main aria-label="Nội dung chính" className="main-content">
        {children}
      </main>
    </div>
  );
}
