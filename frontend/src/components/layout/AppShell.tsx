import React from "react";
import { Button, FluentProvider, webLightTheme } from "@fluentui/react-components";
import {
  APP_ROUTES,
  projectOverviewPath,
  projectWorkbenchPath,
  projectNccSelectionPath,
  projectDocumentsPath,
  projectPreliminaryIntakePath,
  projectPreliminaryAnalysisPath,
  projectPreliminaryCompletionPath,
  splitProjectRoute,
} from "../../contracts/valoraV23";
import type { AccountContext } from "../../api/auth";
import { t } from "../../i18n";
import { ShellIcon, type ShellIconName } from "./ShellIcon";
import { useInlineSidebar } from "./useInlineSidebar";

interface AppShellProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  children: React.ReactNode;
  account: AccountContext;
  onLogout: () => void;
  supplierSelectionAvailable?: boolean;
  utilityActions?: React.ReactNode;
}

export function AppShell({ currentPath, onNavigate, account, onLogout, children, supplierSelectionAvailable = false, utilityActions }: AppShellProps) {
  const { compact, toggleSidebar, collapseOnPhone } = useInlineSidebar(currentPath);
  const projectRoute = splitProjectRoute(currentPath);
  const accountName = account.full_name || account.email;
  const accountInitials = accountName.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
  const sidebarToggleLabel = compact ? "Mở rộng điều hướng" : "Thu gọn điều hướng";

  const workbenchPath = projectRoute
    ? projectWorkbenchPath(projectRoute.projectRef)
    : APP_ROUTES.projectList;
  const currentView = projectRoute?.view;
  const isPrecase = currentPath === APP_ROUTES.preliminaryRequestManagement
    || currentPath === APP_ROUTES.preliminaryRequestCreate
    || currentView === "preliminary-intake"
    || currentView === "preliminary-analysis"
    || currentView === "preliminary-completion";
  const pageLabel = currentPath.split("?", 1)[0] === APP_ROUTES.m365Return ? "Kết nối Microsoft 365"
    : currentPath === APP_ROUTES.preliminaryRequestCreate ? "Tạo yêu cầu sơ bộ"
    : currentPath === APP_ROUTES.preliminaryRequestManagement ? "Quản lý yêu cầu sơ bộ"
    : currentView === "preliminary-intake" ? "Upload & Mapping Excel"
    : currentView === "preliminary-analysis" ? "Phân tích danh mục"
    : currentView === "preliminary-completion" ? "Kết quả sơ bộ & tiếp nhận"
    : currentView === "overview" ? "Tổng quan hồ sơ"
    : currentView === "documents" ? "Không gian tài liệu"
    : currentView === "ncc-selection" ? "Chọn NCC đã xác nhận giá"
    : currentView === "workbench" ? "Workbench tài sản"
    : "Danh sách hồ sơ";

  const navigate = (event: React.MouseEvent<HTMLAnchorElement>, path: string) => {
    event.preventDefault();
    collapseOnPhone();
    onNavigate(path);
  };

  const navItem = (path: string, label: string, isCurrent: boolean, icon: ShellIconName) => (
    <li className="nav-item">
      <a
        aria-current={isCurrent ? "page" : undefined}
        aria-label={label}
        className={`nav-link${isCurrent ? " active" : ""}`}
        href={`#${path}`}
        title={label}
        onClick={(event) => navigate(event, path)}
      >
        <ShellIcon name={icon} />
        <span className="nav-link-label">{label}</span>
      </a>
    </li>
  );

  return (
    <FluentProvider theme={webLightTheme} className={`app-container${compact ? " app-container--compact" : ""}`}>
      <aside className="sidebar" id="valora-sidebar" aria-label="Điều hướng VALORA">
        <header className="sidebar-brand">
          <div className="sidebar-brand-identity" aria-label="VALORA — Thẩm định giá Máy móc Thiết bị">
            <span className="sidebar-brand-mark" aria-hidden="true">V</span>
            <p className="sidebar-brand-title">VALORA<small>Thẩm định giá</small></p>
          </div>
          <Button appearance="subtle" className="sidebar-toggle" icon={<ShellIcon name="sidebar" />}
            aria-controls="valora-sidebar" aria-expanded={!compact} aria-label={sidebarToggleLabel}
            title={sidebarToggleLabel} onClick={toggleSidebar} type="button" />
        </header>
        <nav aria-label="Điều hướng chính">
          <p className="nav-group-label">Yêu cầu sơ bộ</p>
          <ul className="nav-links">
            {navItem(
              APP_ROUTES.preliminaryRequestManagement,
              "Quản lý yêu cầu sơ bộ",
              currentPath === APP_ROUTES.preliminaryRequestManagement,
              "requests",
            )}
          </ul>
          <p className="nav-group-label">Hồ sơ thẩm định</p>
          <ul className="nav-links">
            {navItem(
              workbenchPath,
              t("nav.workbench"),
              projectRoute?.view === "workbench"
                || currentPath.split("?", 1)[0] === APP_ROUTES.projectList,
              "workbench",
            )}
            {projectRoute && navItem(
              projectOverviewPath(projectRoute.projectRef),
              t("nav.caseOverview"),
              projectRoute.view === "overview",
              "overview",
            )}
            {projectRoute && navItem(
              projectDocumentsPath(projectRoute.projectRef),
              "Không gian tài liệu",
              projectRoute.view === "documents",
              "documents",
            )}
            {projectRoute && supplierSelectionAvailable && navItem(
              projectNccSelectionPath(projectRoute.projectRef),
              t("nav.nccSelection"),
              projectRoute.view === "ncc-selection",
              "suppliers",
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
                  "upload",
                )}
                {currentView === "preliminary-analysis" && navItem(
                  projectPreliminaryAnalysisPath(projectRoute.projectRef),
                  "Phân tích danh mục",
                  true,
                  "analysis",
                )}
                {currentView === "preliminary-completion" && navItem(
                  projectPreliminaryCompletionPath(projectRoute.projectRef),
                  "Kết quả & tiếp nhận",
                  true,
                  "results",
                )}
              </ul>
            </>
          )}
        </nav>
        <div className="account-context">
          <div className="account-summary" title={`${accountName} · ${account.organization_slug}`}>
            <span className="account-avatar" aria-hidden="true">{accountInitials}</span>
            <div className="account-details">
              <span>{account.organization_slug}</span>
              <strong>{accountName}</strong>
              <small>{account.email}</small>
            </div>
          </div>
          <Button appearance="subtle" className="account-logout" icon={<ShellIcon name="logout" />}
            aria-label={`Đăng xuất tài khoản ${account.email}`} title="Đăng xuất" onClick={onLogout} type="button">
            <span className="account-logout-label">Đăng xuất</span>
          </Button>
        </div>
      </aside>
      <div className="app-workspace" onFocusCapture={collapseOnPhone}>
        <div className="app-topbar">
          <nav className="app-breadcrumb" aria-label="Vị trí hiện tại">
            <span>Thẩm định giá</span><span aria-hidden="true">›</span>
            {projectRoute && <><span className="app-breadcrumb-project">Hồ sơ</span><span aria-hidden="true">›</span></>}
            <strong>{pageLabel}</strong>
          </nav>
          <div className="app-topbar-utilities">
            {utilityActions}
            <span className="app-topbar-account" title={account.email}>{accountName}</span>
          </div>
        </div>
        <main aria-label="Nội dung chính" className="main-content">
          {children}
        </main>
      </div>
    </FluentProvider>
  );
}
