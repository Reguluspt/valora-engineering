import React from "react";
import { AppShell as AstryxAppShell } from "@astryxdesign/core/AppShell";
import { SideNav, SideNavItem, SideNavSection } from "@astryxdesign/core/SideNav";
import { APP_ROUTES, LEGACY_ROUTE_ALIASES } from "../../contracts/valoraV23";
import { t } from "../../i18n";

interface AppShellProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  children: React.ReactNode;
}

export function AppShell({ currentPath, onNavigate, children }: AppShellProps) {
  const getLinkActive = (path: string) => {
    return currentPath.startsWith(path);
  };

  const handleWorkbenchClick = () => {
    if (currentPath.startsWith(APP_ROUTES.projectDetailPrefix)) {
      onNavigate(currentPath);
    } else {
      onNavigate(APP_ROUTES.projectList);
    }
  };

  return (
    <AstryxAppShell>
      <SideNav>
        <div style={{ padding: "var(--space-md) var(--space-lg)" }}>
          <h2 style={{ color: "var(--accent-cyan)", margin: 0 }}>Valora</h2>
        </div>
        <SideNavSection title="Menu" isHeaderHidden={true}>
          <SideNavItem
            isSelected={getLinkActive(APP_ROUTES.projectList)}
            label={t("nav.workbench")}
            onClick={handleWorkbenchClick}
          />
          <SideNavItem
            isSelected={getLinkActive(APP_ROUTES.legacyReviewQueue) || getLinkActive(LEGACY_ROUTE_ALIASES.reviewQueue)}
            label={t("review.queue")}
            onClick={() => onNavigate(APP_ROUTES.legacyReviewQueue)}
          />
          <SideNavItem
            isSelected={getLinkActive(APP_ROUTES.legacyValidationDashboard) || getLinkActive(LEGACY_ROUTE_ALIASES.validationDashboard)}
            label={t("nav.errorDashboard")}
            onClick={() => onNavigate(APP_ROUTES.legacyValidationDashboard)}
          />
        </SideNavSection>
      </SideNav>
      <section className="main-content" style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {children}
      </section>
    </AstryxAppShell>
  );
}
