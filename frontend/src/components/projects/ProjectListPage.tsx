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

  return (
    <main className="project-list-page">
      <header className="project-list-header">
        <div>
          <p>Hồ sơ của đơn vị</p>
          <h1>Danh sách hồ sơ</h1>
        </div>
        {state === "ready" && <span>{projects.length} hồ sơ</span>}
      </header>
      {state === "loading" && <LoadingState message="Đang tải danh sách hồ sơ…" />}
      {state === "error" && (
        <ErrorState
          title="Chưa thể tải danh sách hồ sơ"
          message="Hệ thống chưa thể đọc hồ sơ trong đơn vị hiện tại."
          onRetry={() => void load()}
        />
      )}
      {state === "ready" && projects.length === 0 && (
        <EmptyState
          kind="first-use"
          title="Đơn vị chưa có hồ sơ"
          message="Hiện chưa có hồ sơ nào để mở."
        />
      )}
      {state === "ready" && projects.length > 0 && (
        <section className="valora-table-shell project-list" aria-label="Danh sách hồ sơ">
          <table className="valora-table project-table">
            <thead>
              <tr>
                <th scope="col">Hồ sơ</th>
                <th scope="col">Mô tả</th>
                <th scope="col">Tác vụ</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((project) => (
                <tr key={project.id}>
                  <td className="project-identity">
                    <span>{project.code}</span>
                    <strong>{project.name}</strong>
                  </td>
                  <td className="project-description">{project.description || "Chưa có mô tả hồ sơ."}</td>
                  <td>
                    <div className="project-actions">
                      <button
                        className="valora-button valora-button--secondary"
                        onClick={() => onNavigate(projectDocumentsPath(project.id))}
                        type="button"
                      >
                        Không gian tài liệu
                      </button>
                      <button
                        className="valora-button valora-button--primary"
                        onClick={() => onNavigate(projectOverviewPath(project.id))}
                        type="button"
                      >
                        Mở tổng quan
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </main>
  );
}
