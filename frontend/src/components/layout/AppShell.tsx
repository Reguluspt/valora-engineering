import React from "react";
import { AppShell as AstryxAppShell } from "@astryxdesign/core/AppShell";
import { SideNav, SideNavItem, SideNavSection } from "@astryxdesign/core/SideNav";
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

  const handleWorkbenchClick = () => {
    if (projectRoute) {
      onNavigate(projectWorkbenchPath(projectRoute.projectRef));
    } else {
      onNavigate(APP_ROUTES.projectList);
    }
  };

  const sideNav = (
    <SideNav>
      <div style={{ padding: "var(--space-md) var(--space-lg)" }}>
        <h2 style={{ color: "var(--accent-cyan)", margin: 0 }}>Valora</h2>
      </div>
      <SideNavSection title="Menu" isHeaderHidden={true}>
        <SideNavItem
          isSelected={projectRoute?.view === "workbench" || currentPath === APP_ROUTES.projectList}
          label={t("nav.workbench")}
          onClick={handleWorkbenchClick}
        />
        {projectRoute && (
          <SideNavItem
            isSelected={projectRoute.view === "overview"}
            label={t("nav.caseOverview")}
            onClick={() => onNavigate(projectOverviewPath(projectRoute.projectRef))}
          />
        )}
        {projectRoute && (
          <SideNavItem
            isSelected={projectRoute.view === "documents"}
            label="Không gian tài liệu"
            onClick={() => onNavigate(projectDocumentsPath(projectRoute.projectRef))}
          />
        )}
        {projectRoute && (
          <SideNavItem
            isSelected={projectRoute.view === "ncc-selection"}
            label={t("nav.nccSelection")}
            onClick={() => onNavigate(projectNccSelectionPath(projectRoute.projectRef))}
          />
        )}
      </SideNavSection>
      <div className="account-context">
        <span>{account.organization_slug}</span>
        <strong>{account.full_name || account.email}</strong>
        <small>{account.email}</small>
        <button onClick={onLogout} type="button">Đăng xuất</button>
      </div>
    </SideNav>
  );

  return (
    <AstryxAppShell contentPadding={0} sideNav={sideNav}>
      <section className="main-content" style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {children}
      </section>
    </AstryxAppShell>
  );
}
