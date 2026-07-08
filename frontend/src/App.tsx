import React, { useState, useEffect } from "react";
import { AppShell } from "./components/layout/AppShell";
import { WorkbenchLayout } from "./components/layout/WorkbenchLayout";
import { EmptyState } from "./components/common/EmptyState";

export function App() {
  const [currentPath, setCurrentPath] = useState("/workbench/projects/hd-98-gia-lai");

  // Keep hash sync for manual page refreshes if relevant
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
    if (currentPath.startsWith("/workbench/projects/")) {
      const parts = currentPath.split("/");
      const projectId = parts[parts.length - 1];
      return (
        <WorkbenchLayout
          projectTitle={`Project: ${projectId.toUpperCase().replace(/-/g, " ")}`}
          status="review"
          statusLabel="Ready for Review"
          issuesCount={2}
        />
      );
    }

    if (currentPath === "/workbench/queue") {
      return (
        <div style={{ padding: "var(--space-xl)" }}>
          <h2 style={{ color: "#fff" }}>Review Queue</h2>
          <p style={{ color: "var(--text-muted)", marginBottom: "var(--space-lg)" }}>
            Below is the list of pending review items requiring human action.
          </p>
          <EmptyState
            title="Queue is Empty"
            message="No pending items matching the identity_review or appraised_price_review queues."
          />
        </div>
      );
    }

    if (currentPath === "/workbench/validation") {
      return (
        <div style={{ padding: "var(--space-xl)" }}>
          <h2 style={{ color: "#fff" }}>Validation Dashboard</h2>
          <p style={{ color: "var(--text-muted)", marginBottom: "var(--space-lg)" }}>
            Overview of validation warnings and blocking issues.
          </p>
          <div style={{ border: "1px solid var(--border-color)", padding: "var(--space-lg)", borderRadius: "var(--radius-lg)" }}>
            <h3>No Unresolved Critical Issues</h3>
            <p style={{ color: "var(--text-muted)" }}>
              All project constraints are verified and complete.
            </p>
          </div>
        </div>
      );
    }

    return (
      <EmptyState
        title="Page Not Found"
        message="The requested route does not exist."
        onAction={() => handleNavigate("/workbench/projects/hd-98-gia-lai")}
        actionLabel="Go to Workbench"
      />
    );
  };

  return (
    <AppShell currentPath={currentPath} onNavigate={handleNavigate}>
      {renderRoute()}
    </AppShell>
  );
}
