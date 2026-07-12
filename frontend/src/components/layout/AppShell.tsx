import React from "react";
import { AppShell as AstryxAppShell } from "@astryxdesign/core/AppShell";
import { SideNav, SideNavItem, SideNavSection } from "@astryxdesign/core/SideNav";
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
    if (currentPath.startsWith("/workbench/projects/")) {
      onNavigate(currentPath);
    } else {
      onNavigate("/workbench/projects");
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
            isSelected={getLinkActive("/workbench/projects")}
            label={t("nav.workbench")}
            onClick={handleWorkbenchClick}
          />
          <SideNavItem
            isSelected={getLinkActive("/workbench/queue") || getLinkActive("/queue")}
            label={t("review.queue")}
            onClick={() => onNavigate("/workbench/queue")}
          />
          <SideNavItem
            isSelected={getLinkActive("/workbench/validation") || getLinkActive("/validation")}
            label={t("nav.errorDashboard")}
            onClick={() => onNavigate("/workbench/validation")}
          />
        </SideNavSection>
      </SideNav>
      <section className="main-content" style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {children}
      </section>
    </AstryxAppShell>
  );
}
