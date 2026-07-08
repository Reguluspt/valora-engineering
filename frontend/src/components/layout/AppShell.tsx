import React from "react";

interface AppShellProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  children: React.ReactNode;
}

export function AppShell({ currentPath, onNavigate, children }: AppShellProps) {
  const getLinkClass = (path: string) => {
    return currentPath.startsWith(path) ? "nav-link active" : "nav-link";
  };

  return (
    <div className="app-container">
      <nav className="sidebar">
        <h2 style={{ color: "var(--accent-cyan)", margin: "0 0 var(--space-md) 0" }}>Valora</h2>
        <ul className="nav-links">
          <li className="nav-item">
            <a
              href="#/workbench"
              className={getLinkClass("/workbench")}
              onClick={(e) => {
                e.preventDefault();
                onNavigate("/workbench/projects/hd-98-gia-lai");
              }}
            >
              Project Workbench
            </a>
          </li>
          <li className="nav-item">
            <a
              href="#/queue"
              className={getLinkClass("/queue")}
              onClick={(e) => {
                e.preventDefault();
                onNavigate("/workbench/queue");
              }}
            >
              Review Queue
            </a>
          </li>
          <li className="nav-item">
            <a
              href="#/validation"
              className={getLinkClass("/validation")}
              onClick={(e) => {
                e.preventDefault();
                onNavigate("/workbench/validation");
              }}
            >
              Validation Dashboard
            </a>
          </li>
        </ul>
        <div style={{ marginTop: "auto", fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
          <p>User: Appraiser</p>
          <p>Org: Gia Lai Division</p>
        </div>
      </nav>
      <section className="main-content">
        {children}
      </section>
    </div>
  );
}
