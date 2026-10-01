import React from "react";
import {
  APP_ROUTES,
  projectOverviewPath,
  projectWorkbenchPath,
  projectNccSelectionPath,
  projectDocumentsPath,
  projectPreliminaryIntakePath,
  projectPreliminaryAnalysisPath,
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
  const currentView = projectRoute?.view;
  const isPrecase = currentPath === APP_ROUTES.preliminaryRequestManagement
    || currentPath === APP_ROUTES.preliminaryRequestCreate
    || currentView === "preliminary-intake"
    || currentView === "preliminary-analysis";
  const pageLabel = currentPath.split("?", 1)[0] === APP_ROUTES.m365Return ? "Kết nối Microsoft 365"
    : currentPath === APP_ROUTES.preliminaryRequestCreate ? "Tạo yêu cầu sơ bộ"
    : currentPath === APP_ROUTES.preliminaryRequestManagement ? "Quản lý yêu cầu sơ bộ"
    : currentView === "preliminary-intake" ? "Upload & Mapping Excel"
    : currentView === "preliminary-analysis" ? "Phân tích danh mục"
    : currentView === "overview" ? "Tổng quan hồ sơ"
    : currentView === "documents" ? "Không gian tài liệu"
    : currentView === "ncc-selection" ? "Chọn NCC đã xác nhận giá"
    : currentView === "workbench" ? "Workbench tài sản"
    : "Danh sách hồ sơ";

  const navigate = (event: React.MouseEvent<HTMLAnchorElement>, path: string) => {
    event.preventDefault();
    onNavigate(path);
  };

  const navItem = (path: string, label: string, isCurrent: boolean, icon: string) => (
    <li className="nav-item">
      <a
        aria-current={isCurrent ? "page" : undefined}
        className={`nav-link${isCurrent ? " active" : ""}`}
        data-icon={icon}
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
        <header className="sidebar-brand">
          <span className="sidebar-brand-mark" aria-hidden="true">✦</span>
          <p className="project-title">VALORA<small>Thẩm định giá Máy móc Thiết bị</small></p>
        </header>
        <nav aria-label="Điều hướng chính">
          <p className="nav-group-label">Yêu cầu sơ bộ</p>
          <ul className="nav-links">
            {navItem(
              APP_ROUTES.preliminaryRequestManagement,
              "Quản lý yêu cầu sơ bộ",
              currentPath === APP_ROUTES.preliminaryRequestManagement,
              "▤",
            )}
          </ul>
          <p className="nav-group-label">Hồ sơ thẩm định</p>
          <ul className="nav-links">
            {navItem(
              workbenchPath,
              t("nav.workbench"),
              projectRoute?.view === "workbench"
                || currentPath.split("?", 1)[0] === APP_ROUTES.projectList,
              "▦",
            )}
            {projectRoute && navItem(
              projectOverviewPath(projectRoute.projectRef),
              t("nav.caseOverview"),
              projectRoute.view === "overview",
              "◉",
            )}
            {projectRoute && navItem(
              projectDocumentsPath(projectRoute.projectRef),
              "Không gian tài liệu",
              projectRoute.view === "documents",
              "▣",
            )}
            {projectRoute && navItem(
              projectNccSelectionPath(projectRoute.projectRef),
              t("nav.nccSelection"),
              projectRoute.view === "ncc-selection",
              "◈",
            )}
          </ul>
          {projectRoute && isPrecase && (
            <>
              <p className="nav-group-label">Đang thực hiện</p>
              <ul className="nav-links">
                {currentView === "preliminary-intake" && navItem(
                  projectPreliminaryIntakePath(projectRoute.projectRef),
                  "Upload & Mapping Excel",
                  true,
                  "⇧",
                )}
                {currentView === "preliminary-analysis" && navItem(
                  projectPreliminaryAnalysisPath(projectRoute.projectRef),
                  "Phân tích danh mục",
                  true,
                  "▥",
                )}
              </ul>
            </>
          )}
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
      <div className="app-workspace">
        <div className="app-topbar">
          <nav className="app-breadcrumb" aria-label="Vị trí hiện tại">
            <span>Thẩm định giá</span><span aria-hidden="true">›</span>
            {projectRoute && <><span className="app-breadcrumb-project">Hồ sơ</span><span aria-hidden="true">›</span></>}
            <strong>{pageLabel}</strong>
          </nav>
          <span className="app-topbar-account" title={account.email}>{account.full_name || account.email}</span>
        </div>
        <main aria-label="Nội dung chính" className="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}
