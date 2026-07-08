import React from "react";

interface WorkbenchRightPanelShellProps {
  children?: React.ReactNode;
}

export function WorkbenchRightPanelShell({ children }: WorkbenchRightPanelShellProps) {
  return (
    <aside className="workbench-right-drawer">
      <h3 style={{ borderBottom: "1px solid var(--border-color)", paddingBottom: "var(--space-sm)", marginTop: 0 }}>
        Right Panels Shell
      </h3>
      {children || (
        <>
          <div className="panel-tab">
            <h4 className="panel-tab-title">[Knowledge]</h4>
            <p style={{ fontSize: "var(--font-size-sm)", color: "var(--text-muted)" }}>
              Suggested tech spec information will render here.
            </p>
          </div>
          <div className="panel-tab">
            <h4 className="panel-tab-title">[Price Evidence]</h4>
            <p style={{ fontSize: "var(--font-size-sm)", color: "var(--text-muted)" }}>
              Market Quote vs Appraised Price split comparison layout.
            </p>
          </div>
          <div className="panel-tab">
            <h4 className="panel-tab-title">[Lineage]</h4>
            <p style={{ fontSize: "var(--font-size-sm)", color: "var(--text-muted)" }}>
              Lineage trail chain viewer workspace.
            </p>
          </div>
          <div className="panel-tab">
            <h4 className="panel-tab-title">[Validation]</h4>
            <p style={{ fontSize: "var(--font-size-sm)", color: "var(--text-muted)" }}>
              Blocking and Warning level details list.
            </p>
          </div>
        </>
      )}
    </aside>
  );
}
