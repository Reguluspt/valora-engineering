import React, { useCallback, useEffect, useState } from "react";

import { listProjects, ProjectSummary } from "../../api/projects";
import { projectDocumentsPath, projectOverviewPath } from "../../contracts/valoraV23";
import { EmptyState } from "../common/EmptyState";
import { ErrorState } from "../common/ErrorState";
import { LoadingState } from "../common/LoadingState";
import "./projectList.css";

export function ProjectListPage({ onNavigate }: { onNavigate: (path: string) => void }) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  const load = useCallback(async () => {
    setState("loading");
    try {
      setProjects(await listProjects());
      setState("ready");
    } catch {
      setState("error");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (state === "loading") return <LoadingState message="Đang tải danh sách hồ sơ…" />;
  if (state === "error") {
    return (
      <ErrorState
        title="Chưa thể tải danh sách hồ sơ"
        message="Hệ thống chưa thể đọc hồ sơ trong đơn vị hiện tại."
        onRetry={() => void load()}
      />
    );
  }
  if (projects.length === 0) {
    return (
      <EmptyState
        title="Đơn vị chưa có hồ sơ"
        message="Danh sách này được đọc trực tiếp từ hệ thống; hiện chưa có hồ sơ nào để mở."
      />
    );
  }

  return (
    <main className="project-list-page">
      <header className="project-list-header">
        <div>
          <p>OPERATIONAL ENTRY · {String(projects.length).padStart(2, "0")} HỒ SƠ</p>
          <h1>Chọn hồ sơ đang làm việc</h1>
        </div>
        <span>Dữ liệu theo đúng đơn vị của phiên hiện tại</span>
      </header>
      <section className="project-list" aria-label="Danh sách hồ sơ">
        {projects.map((project, index) => (
          <article className="project-row" key={project.id}>
            <span className="project-index">{String(index + 1).padStart(2, "0")}</span>
            <div className="project-identity">
              <p>{project.code}</p>
              <h2>{project.name}</h2>
              <span>{project.description || "Chưa có mô tả hồ sơ."}</span>
            </div>
            <div className="project-meta">
              <span>Trạng thái</span>
              <strong>{project.status}</strong>
              <small>Phiên bản {project.row_version}</small>
            </div>
            <div className="project-actions">
              <button
                className="project-secondary-action"
                onClick={() => onNavigate(projectDocumentsPath(project.id))}
                type="button"
              >
                Không gian tài liệu
              </button>
              <button
                className="project-primary-action"
                onClick={() => onNavigate(projectOverviewPath(project.id))}
                type="button"
              >
                Mở tổng quan
              </button>
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}
