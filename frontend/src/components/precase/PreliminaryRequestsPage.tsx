import React, { useCallback, useEffect, useState } from "react";

import { ApiError } from "../../api/client";
import {
  listPreliminaryRequests,
  type PreliminaryRequestManagementItem,
  type PreliminaryRequestManagementPage,
} from "../../api/preliminaryIntake";
import { APP_ROUTES, projectPreliminaryIntakePath } from "../../contracts/valoraV23";
import { EmptyState } from "../common/EmptyState";
import { ErrorState } from "../common/ErrorState";
import { LoadingState } from "../common/LoadingState";
import "./precase.css";

function sourceLabel(item: PreliminaryRequestManagementItem): string {
  if (!item.current_batch_id) {
    return item.has_retained_batches ? "Chưa xác định batch hiện hành" : "Chưa có batch";
  }
  if (!item.current_source_artifact_id) return "Chưa có tệp nguồn";
  if (item.current_source_state === "available") return "Tệp nguồn sẵn sàng";
  if (!item.current_source_state) return "Cần xác minh tệp nguồn";
  return `Tệp nguồn: ${item.current_source_state}`;
}

export function PreliminaryRequestsPage({
  onNavigate,
  onSessionExpired,
}: {
  onNavigate: (path: string) => void;
  onSessionExpired: () => void;
}) {
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<PreliminaryRequestManagementPage | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error" | "sessionExpired" | "forbidden">("loading");

  const load = useCallback(async () => {
    setState("loading");
    try {
      const next = await listPreliminaryRequests(page);
      setResult(next);
      setState("ready");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) setState("sessionExpired");
      else if (error instanceof ApiError && error.status === 403) setState("forbidden");
      else setState("error");
    }
  }, [page]);

  useEffect(() => { void load(); }, [load]);

  return (
    <main className="precase-management-page">
      <header className="precase-management-header">
        <div>
          <p>Yêu cầu sơ bộ</p>
          <h1>Quản lý yêu cầu sơ bộ</h1>
          <span>Tiếp tục nhập tệp Excel và xác nhận ánh xạ cho từng yêu cầu.</span>
        </div>
        <button
          className="valora-button valora-button--primary"
          onClick={() => onNavigate(APP_ROUTES.preliminaryRequestCreate)}
          type="button"
        >
          Tạo yêu cầu sơ bộ
        </button>
      </header>

      {state === "loading" && <LoadingState message="Đang tải yêu cầu sơ bộ…" />}
      {state === "error" && (
        <ErrorState title="Chưa thể tải yêu cầu sơ bộ" message="Không thể đọc danh sách của đơn vị hiện tại." onRetry={() => void load()} />
      )}
      {state === "sessionExpired" && (
        <ErrorState title="Phiên làm việc đã hết hạn" message="Vui lòng đăng nhập lại để xem yêu cầu sơ bộ." onRetry={onSessionExpired} retryLabel="Đăng nhập lại" />
      )}
      {state === "forbidden" && (
        <ErrorState title="Chưa có quyền xem yêu cầu sơ bộ" message="Tài khoản hiện tại không có quyền đọc hồ sơ của đơn vị." />
      )}
      {state === "ready" && result?.total === 0 && (
        <EmptyState kind="first-use" title="Chưa có yêu cầu sơ bộ" message="Tạo yêu cầu sơ bộ để bắt đầu nhập tệp Excel." onAction={() => onNavigate(APP_ROUTES.preliminaryRequestCreate)} actionLabel="Tạo yêu cầu sơ bộ" />
      )}
      {state === "ready" && result && result.total > 0 && (
        <>
          <section className="valora-table-shell precase-management-table" aria-label="Danh sách yêu cầu sơ bộ">
            <table className="valora-table">
              <thead>
                <tr>
                  <th scope="col">Yêu cầu</th>
                  <th scope="col">Tệp nguồn hiện hành</th>
                  <th scope="col">Khách hàng</th>
                  <th scope="col">Tác vụ</th>
                </tr>
              </thead>
              <tbody>
                {result.items.map((item) => (
                  <tr key={item.project_id}>
                    <td><span className="precase-management-code">{item.code}</span><strong>{item.name}</strong></td>
                    <td>{sourceLabel(item)}</td>
                    <td>{item.customer_id ? "Đã gắn" : "Chưa gắn"}</td>
                    <td>
                      <button className="valora-button valora-button--secondary" onClick={() => onNavigate(projectPreliminaryIntakePath(item.project_id))} type="button">
                        Mở nhập liệu
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <nav className="precase-management-pagination" aria-label="Phân trang yêu cầu sơ bộ">
            <span>{result.total} yêu cầu · Trang {result.page}</span>
            <button className="valora-button valora-button--secondary" disabled={page === 1} onClick={() => setPage(page - 1)} type="button">Trang trước</button>
            <button className="valora-button valora-button--secondary" disabled={page * result.page_size >= result.total} onClick={() => setPage(page + 1)} type="button">Trang sau</button>
          </nav>
        </>
      )}
    </main>
  );
}
