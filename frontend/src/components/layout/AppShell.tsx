import React from "react";
import { Button, FluentProvider, Menu, MenuItem, MenuList, MenuPopover, MenuTrigger, useModalAttributes, webLightTheme } from "@fluentui/react-components";
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
import { SidebarCollapseContext } from "./SidebarCollapseContext";

interface AppShellProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  children: React.ReactNode;
  account: AccountContext;
  onLogout: () => void;
  supplierSelectionAvailable?: boolean;
  utilityActions?: React.ReactNode;
  analysisContext?: { catalogName: string; assetCount: number; viewedCount: number; avatarLabel?: string };
  onCompareAnalysisSources?: () => void;
}

export function AppShell({ currentPath, onNavigate, account, onLogout, children, supplierSelectionAvailable = false, utilityActions, analysisContext, onCompareAnalysisSources }: AppShellProps) {
  const {
    compact, extreme, extremeOpen, phoneOverlay, toggleSidebar, collapseOnPhone, collapseSidebar,
    openExtremeSidebar, discardSidebarReturn, sidebarRef, openButtonRef, toggleButtonRef, workspaceRef, swipeHandlers,
  } = useInlineSidebar(currentPath);
  const { modalAttributes } = useModalAttributes({ trapFocus: true, legacyTrapFocus: true });
  const projectRoute = splitProjectRoute(currentPath);
  const accountName = account.full_name || account.email;
  const accountInitials = accountName.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
  const sidebarToggleLabel = extreme ? "Đóng điều hướng" : compact ? "Mở rộng điều hướng" : "Thu gọn điều hướng";

  const workbenchPath = projectRoute
    ? projectWorkbenchPath(projectRoute.projectRef)
    : APP_ROUTES.projectList;
  const currentView = projectRoute?.view;
  const analysisView = currentView === "preliminary-analysis";
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
    discardSidebarReturn(path);
    collapseOnPhone();
    onNavigate(path);
  };

  const navigateFromAccount = (path: string) => {
    discardSidebarReturn(path);
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
        {analysisView && isCurrent && analysisContext && <span className="analysis-nav-count">{analysisContext.assetCount}</span>}
      </a>
    </li>
  );

  return (
    <FluentProvider theme={analysisView ? { ...webLightTheme, fontFamilyBase: "var(--valora-analysis-font-family)" } : webLightTheme} className={`app-container${compact && !extreme ? " app-container--compact" : ""}${analysisView ? " app-container--analysis" : ""}${extreme ? " app-container--extreme" : ""}${phoneOverlay ? " app-container--phone-overlay" : ""}`}>
      {phoneOverlay && <button type="button" className="sidebar-overlay-scrim" tabIndex={-1} aria-hidden="true" onClick={collapseSidebar} />}
      <aside ref={sidebarRef} className="sidebar" id="valora-sidebar" aria-label="Điều hướng VALORA"
        role={phoneOverlay ? "dialog" : undefined} aria-modal={phoneOverlay || undefined}
        {...(phoneOverlay ? modalAttributes : {})}
        inert={extreme && !extremeOpen || undefined}
        {...(extremeOpen ? swipeHandlers : undefined)}
        onKeyDown={extremeOpen || phoneOverlay ? (event) => {
          if (event.key === "Escape" && !event.defaultPrevented && event.currentTarget.contains(event.target as Node)) {
            if (phoneOverlay) event.preventDefault();
            event.stopPropagation();
            collapseSidebar();
          }
        } : undefined}>
        <header className="sidebar-brand">
          <div className="sidebar-brand-identity" aria-label="VALORA — Thẩm định giá Máy móc Thiết bị">
            <span className="sidebar-brand-mark" aria-hidden="true">V</span>
            <p className="sidebar-brand-title">VALORA<small>{analysisView ? "KHÔNG GIAN THẨM ĐỊNH" : "Thẩm định giá"}</small></p>
          </div>
          <Button ref={toggleButtonRef} appearance="subtle" className="sidebar-toggle" icon={<ShellIcon name="sidebar" />}
            aria-controls="valora-sidebar" aria-expanded={extreme ? extremeOpen : !compact} aria-label={sidebarToggleLabel}
            title={sidebarToggleLabel} onClick={toggleSidebar} type="button" />
        </header>
        {analysisView && projectRoute && <>
          <div className="analysis-workspace-switch"><ShellIcon name="folder" /><div><b>Hồ sơ {projectRoute.projectRef}</b><small>{analysisContext?.catalogName || "Danh mục hiện hành"}</small></div></div>
          <nav aria-label="Chức năng chính"><p className="nav-group-label">Hồ sơ thẩm định</p><ul className="nav-links">
            {navItem(projectOverviewPath(projectRoute.projectRef), "Tổng quan hồ sơ", false, "overview")}
            {navItem(projectPreliminaryAnalysisPath(projectRoute.projectRef), "Phân tích danh mục", true, "analysis")}
            <li className="nav-item"><Button appearance="transparent" className="nav-link" disabledFocusable={!onCompareAnalysisSources} onClick={onCompareAnalysisSources} aria-label="Đối chiếu nguồn" title={onCompareAnalysisSources ? undefined : "API phân tích chưa hỗ trợ đối chiếu nhiều nguồn"}><ShellIcon name="compare" /><span className="nav-link-label">Đối chiếu nguồn</span></Button></li>
            {navItem(projectPreliminaryCompletionPath(projectRoute.projectRef), "Tổng kết & xuất", false, "results")}
          </ul><p className="nav-group-label">Dữ liệu hồ sơ</p><ul className="nav-links">{navItem(projectDocumentsPath(projectRoute.projectRef), "Tài liệu nguồn", false, "documents")}</ul></nav>
          {analysisContext && <div className="analysis-sidebar-progress"><div><b>Tiến độ xem danh mục</b><span>{analysisContext.viewedCount}/{analysisContext.assetCount}</span></div><progress value={analysisContext.viewedCount} max={analysisContext.assetCount} /><small>{analysisContext.assetCount - analysisContext.viewedCount} tài sản chưa xem</small></div>}
        </>}
        <nav aria-label="Điều hướng chính" hidden={analysisView}>
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
          {analysisView ? <Menu positioning="above-start" inline={phoneOverlay}>
            <MenuTrigger disableButtonEnhancement><Button appearance="transparent" className="account-summary analysis-account-trigger" aria-label="Tài khoản và điều hướng">
              <span className="account-avatar" aria-hidden="true">{analysisContext?.avatarLabel || accountInitials}</span>
              <span className="account-details"><strong>{accountName}</strong><small>{account.email}</small></span>
            </Button></MenuTrigger>
            <MenuPopover><MenuList>
              <MenuItem onClick={() => navigateFromAccount(APP_ROUTES.preliminaryRequestManagement)}>Quản lý yêu cầu sơ bộ</MenuItem>
              <MenuItem onClick={() => navigateFromAccount(workbenchPath)}>{t("nav.workbench")}</MenuItem>
              {utilityActions}
              <MenuItem onClick={onLogout}>Đăng xuất</MenuItem>
            </MenuList></MenuPopover>
          </Menu> : <><div className="account-summary" title={`${accountName} · ${account.organization_slug}`}>
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
          </>}
        </div>
      </aside>
      {extreme && !extremeOpen && <>
        <Button ref={openButtonRef} appearance="subtle" className="sidebar-toggle sidebar-open-trigger" icon={<ShellIcon name="sidebar" />}
          aria-controls="valora-sidebar" aria-expanded={false} aria-label="Mở điều hướng"
          onClick={openExtremeSidebar} type="button">Điều hướng</Button>
        <div className="sidebar-edge-swipe" aria-hidden="true" {...swipeHandlers} />
      </>}
      <div className="app-workspace" inert={phoneOverlay || undefined} onFocusCapture={analysisView || extreme ? undefined : collapseOnPhone}>
        <div className="app-topbar" hidden={analysisView}>
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
        <main ref={workspaceRef} tabIndex={extreme ? -1 : undefined} aria-label="Nội dung chính" className="main-content">
          <SidebarCollapseContext.Provider value={collapseSidebar}>{children}</SidebarCollapseContext.Provider>
        </main>
      </div>
    </FluentProvider>
  );
}
