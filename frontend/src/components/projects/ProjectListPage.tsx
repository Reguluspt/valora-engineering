import React, { useCallback, useEffect, useState } from "react";

import { ApiError } from "../../api/client";
import { getProject, listProjects, ProjectSummary, resolveProjectReference } from "../../api/projects";
import { APP_ROUTES, projectDocumentsPath, projectOverviewPath } from "../../contracts/valoraV23";
import { EmptyState } from "../common/EmptyState";
import { ErrorState } from "../common/ErrorState";
import { LoadingState } from "../common/LoadingState";
import "./projectList.css";

export function ProjectListPage({
  onNavigate,
  onSessionExpired,
  verificationCode,
}: {
  onNavigate: (path: string) => void;
  onSessionExpired?: () => void;
  verificationCode?: string | null;
}) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error" | "sessionExpired">("loading");

  const load = useCallback(async () => {
    setState("loading");
    try {
      if (verificationCode) {
        const match = await resolveProjectReference(verificationCode);
        const project = match.matched_by === "code" ? await getProject(match.project_id) : null;
        setProjects(project?.code.toLowerCase() === verificationCode.toLowerCase() ? [project] : []);
      } else {
        setProjects(await listProjects());
      }
      setState("ready");
    } catch (error) {
      if (verificationCode && error instanceof ApiError && error.status === 401) {
        setState("sessionExpired");
        return;
      }
      if (verificationCode && error instanceof ApiError && error.status === 404) {
        setProjects([]);
        setState("ready");
        return;
      }
      setState("error");
    }
  }, [verificationCode]);

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
        {state === "ready" && (
          <div className="project-list-header-actions">
            {verificationCode ? (
              <>
                <span>Kiểm tra mã hồ sơ {verificationCode}</span>
                <button
                  className="valora-button valora-button--secondary"
                  onClick={() => onNavigate(APP_ROUTES.projectList)}
                  type="button"
                >
                  Xem tất cả hồ sơ
                </button>
              </>
            ) : (
              <>
                <span>{projects.length} hồ sơ</span>
                <button
                  className="valora-button valora-button--primary"
                  onClick={() => onNavigate(APP_ROUTES.preliminaryRequestCreate)}
                  type="button"
                >
                  Tạo yêu cầu sơ bộ
                </button>
              </>
            )}
          </div>
        )}
      </header>
      {state === "loading" && <LoadingState message="Đang tải danh sách hồ sơ…" />}
      {state === "error" && (
        <ErrorState
          title={verificationCode ? "Chưa thể kiểm tra mã hồ sơ" : "Chưa thể tải danh sách hồ sơ"}
          message={verificationCode
            ? "Hệ thống chưa thể xác minh yêu cầu vừa gửi."
            : "Hệ thống chưa thể đọc hồ sơ trong đơn vị hiện tại."}
          onRetry={() => void load()}
        />
      )}
      {state === "sessionExpired" && (
        <ErrorState
          title="Phiên làm việc đã hết hạn"
          message="Vui lòng đăng nhập lại để kiểm tra mã hồ sơ."
          onRetry={onSessionExpired}
          retryLabel="Đăng nhập lại"
        />
      )}
      {state === "ready" && projects.length === 0 && verificationCode && (
        <EmptyState
          kind="no-results"
          title="Chưa tìm thấy mã hồ sơ này lúc này"
          message="Nếu bạn vừa gửi yêu cầu, hãy kiểm tra lại trước khi tạo yêu cầu mới."
          onAction={() => void load()}
          actionLabel="Kiểm tra lại"
        />
      )}
      {state === "ready" && projects.length === 0 && !verificationCode && (
        <EmptyState
          kind="first-use"
          title="Đơn vị chưa có hồ sơ"
          message="Tạo yêu cầu sơ bộ để bắt đầu hồ sơ đầu tiên."
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
