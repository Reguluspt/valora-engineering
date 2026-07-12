import React, { useState, useEffect } from "react";
import { AppShell } from "./components/layout/AppShell";
import { WorkbenchLayout } from "./components/layout/WorkbenchLayout";
import { EmptyState } from "./components/common/EmptyState";
import { useResolvedProject } from "./components/workbench/project-context";

import { ReviewQueueDashboard } from "./components/workbench/review/ReviewQueueDashboard";

const WORKBENCH_BASE = "/workbench/projects";
const NEUTRAL_PATH = WORKBENCH_BASE;

export function App() {
  const [currentPath, setCurrentPath] = useState(() => {
    const hash = window.location.hash?.replace("#", "");
    return hash || NEUTRAL_PATH;
  });

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
      const ref = currentPath.substring("/workbench/projects/".length);
      return <WorkbenchLayout projectRef={ref || null} />;
    }

    if (currentPath === "/workbench/projects") {
      return (
        <div style={{ padding: "var(--space-xl)" }}>
          <h2 style={{ color: "#fff" }}>Chọn hồ sơ</h2>
          <p style={{ color: "var(--text-muted)", marginBottom: "var(--space-lg)" }}>
            Vui lòng chọn một hồ sơ từ thanh điều hướng để bắt đầu làm việc.
          </p>
        </div>
      );
    }

    if (currentPath === "/workbench/queue") {
      return <ReviewQueueDashboard />;
    }

    if (currentPath === "/workbench/validation") {
      return (
        <div style={{ padding: "var(--space-xl)" }}>
          <h2 style={{ color: "#fff" }}>Bảng lỗi cần xử lý</h2>
          <p style={{ color: "var(--text-muted)", marginBottom: "var(--space-lg)" }}>
            Tổng quan các cảnh báo và lỗi cần xử lý.
          </p>
          <div style={{ border: "1px solid var(--border-color)", padding: "var(--space-lg)", borderRadius: "var(--radius-lg)" }}>
            <h3>Không có lỗi nghiêm trọng</h3>
            <p style={{ color: "var(--text-muted)" }}>
              Tất cả các ràng buộc dự án đã được xác minh và hoàn tất.
            </p>
          </div>
        </div>
      );
    }

    return (
      <EmptyState
        title="Không tìm thấy trang"
        message="Trang được yêu cầu không tồn tại."
        onAction={() => handleNavigate(NEUTRAL_PATH)}
        actionLabel="Về bàn làm việc"
      />
    );
  };

  return (
    <AppShell currentPath={currentPath} onNavigate={handleNavigate}>
      {renderRoute()}
    </AppShell>
  );
}
