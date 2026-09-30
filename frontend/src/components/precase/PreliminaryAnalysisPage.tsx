import React, { useCallback, useEffect, useRef, useState } from "react";

import { fetchAssetImportRows, type ProjectAssetImportStagingRowResponse } from "../../api/assetImports";
import { fetchCaseState, type CaseStateResponse } from "../../api/caseState";
import { ApiError } from "../../api/client";
import {
  finalizePreliminaryAnalysis, getPreliminaryAnalysis,
  type PreliminaryAnalysisFinalizeRequest, type PreliminaryAnalysisReadResponse,
} from "../../api/preliminaryAnalysis";
import { getMappingRecovery, getSourceArtifact, type MappingRecoveryState } from "../../api/preliminaryIntake";
import { projectOverviewPath, projectPreliminaryIntakePath } from "../../contracts/valoraV23";
import { ErrorState } from "../common/ErrorState";
import { LoadingState } from "../common/LoadingState";
import { useResolvedProject } from "../workbench/project-context";
import { analysisContextReady, buildAnalysisManifest, draftFromStaging, sourceQuantityValid, type AnalysisDraft } from "./analysisReviewModel";
import "./precase.css";

interface AnalysisData {
  caseState: CaseStateResponse;
  recovery: MappingRecoveryState | null;
  rows: ProjectAssetImportStagingRowResponse[];
  snapshot: PreliminaryAnalysisReadResponse | null;
  blockedReason: string | null;
}

interface PendingAttempt { payload: PreliminaryAnalysisFinalizeRequest }

const pendingKey = (projectId: string) => "valora:g11i:analysis-pending:" + projectId;

function readPending(projectId: string): PendingAttempt | null {
  try {
    const raw = sessionStorage.getItem(pendingKey(projectId));
    if (!raw) return null;
    const attempt = JSON.parse(raw) as PendingAttempt;
    return attempt.payload?.idempotency_key && Array.isArray(attempt.payload.line_manifest) ? attempt : null;
  } catch { return null; }
}

function storePending(projectId: string, attempt: PendingAttempt | null): void {
  try {
    if (attempt) sessionStorage.setItem(pendingKey(projectId), JSON.stringify(attempt));
    else sessionStorage.removeItem(pendingKey(projectId));
  } catch { /* Server reads still recover committed state. */ }
}

function unknownResult(error: unknown): boolean {
  return !(error instanceof ApiError) || error.status === 0 || error.status === 408 ||
    error.status === 429 || error.status >= 500;
}

function stageResult(state: CaseStateResponse, stage: "PRELIMINARY_REQUEST" | "PRELIMINARY_ANALYSIS") {
  return state.stages.find((item) => item.stage === stage)?.result;
}

async function readCurrentRows(projectId: string, batchId: string): Promise<ProjectAssetImportStagingRowResponse[]> {
  const rows: ProjectAssetImportStagingRowResponse[] = [];
  const seen = new Set<number>();
  let total: number | null = null;
  while (total === null || rows.length < total) {
    const page = await fetchAssetImportRows(projectId, batchId, { limit: 100, offset: rows.length });
    if (page.project_id !== projectId || page.import_batch_id !== batchId ||
        !Number.isInteger(page.total) || page.total < 0 ||
        (total !== null && page.total !== total) || page.items.length > 100 ||
        (page.items.length === 0 && page.total > rows.length)) {
      throw new Error("Staging pagination changed during analysis read");
    }
    total = page.total;
    for (const row of page.items) {
      if (row.import_batch_id !== batchId || !Number.isInteger(row.source_row_number) ||
          row.source_row_number < 1 || row.source_row_number > 1_048_576 || seen.has(row.source_row_number)) {
        throw new Error("Staging provenance is incomplete");
      }
      seen.add(row.source_row_number);
      rows.push(row);
    }
  }
  if (rows.length !== total) throw new Error("Staging pagination is incomplete");
  return rows;
}

function retryMatchesCurrent(data: AnalysisData, attempt: PendingAttempt): boolean {
  const current = data.caseState.preliminary;
  const mapping = data.recovery;
  const payload = attempt.payload;
  return Boolean(mapping && analysisContextReady(current, mapping) &&
    current.project_row_version === payload.expected_project_version &&
    current.current_preliminary_import_batch_id === payload.import_batch_id &&
    current.current_source_artifact_id === payload.source_artifact_id &&
    mapping.selected_structure_snapshot_id === payload.structure_snapshot_id &&
    mapping.selected_confirmation_decision_id === payload.mapping_decision_id &&
    mapping.selected_usage_id === payload.mapping_profile_usage_id &&
    mapping.mapping_digest_sha256 === payload.mapping_decision_digest_sha256 &&
    mapping.materialized_mapping_digest_sha256 === payload.profile_usage_mapping_digest_sha256);
}

export function PreliminaryAnalysisPage({ projectRef, onNavigate, onSessionExpired }: {
  projectRef: string;
  onNavigate: (path: string) => void;
  onSessionExpired: () => void;
}) {
  const resolved = useResolvedProject(projectRef);
  if (resolved.state === "loading" || resolved.state === "idle") return <LoadingState message="Đang xác định yêu cầu sơ bộ…" />;
  if (resolved.state === "error" || !resolved.projectId) {
    return <ErrorState title={resolved.error?.title || "Chưa thể mở phân tích"} message={resolved.error?.message || "Không thể xác định hồ sơ."} onRetry={resolved.retry} />;
  }
  return <ResolvedPreliminaryAnalysis key={resolved.projectId} projectId={resolved.projectId}
    projectRef={projectRef} onNavigate={onNavigate} onSessionExpired={onSessionExpired} />;
}

function ResolvedPreliminaryAnalysis({ projectId, projectRef, onNavigate, onSessionExpired }: {
  projectId: string;
  projectRef: string;
  onNavigate: (path: string) => void;
  onSessionExpired: () => void;
}) {
  const [data, setData] = useState<AnalysisData | null>(null);
  const [drafts, setDrafts] = useState<AnalysisDraft[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error" | "sessionExpired" | "forbidden">("loading");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const confirmDialogRef = useRef<HTMLDialogElement>(null);
  const [pageIndex, setPageIndex] = useState(0);
  const pendingRef = useRef<PendingAttempt | null>(readPending(projectId));
  const [uncertain, setUncertain] = useState(Boolean(pendingRef.current));

  const clearPending = useCallback(() => {
    pendingRef.current = null;
    storePending(projectId, null);
    setUncertain(false);
  }, [projectId]);

  const load = useCallback(async (): Promise<AnalysisData | null> => {
    setLoadState("loading");
    try {
      const state = await fetchCaseState(projectId);
      const current = state.preliminary;
      if (current.project_id !== projectId) throw new Error("Project authority mismatch");
      if (current.current_preliminary_analysis_snapshot_id) {
        const snapshot = await getPreliminaryAnalysis(projectId, current.current_preliminary_analysis_snapshot_id);
        if (snapshot.id !== current.current_preliminary_analysis_snapshot_id ||
            snapshot.project_id !== projectId || snapshot.version !== current.current_preliminary_analysis_version) {
          throw new Error("Analysis readback mismatch");
        }
        const completed = { caseState: state, recovery: null, rows: [], snapshot, blockedReason: null };
        setData(completed);
        setDrafts([]);
        setPageIndex(0);
        clearPending();
        setLoadState("ready");
        return completed;
      }
      let blockedReason: string | null = null;
      if (current.official_intake_commit_id) blockedReason = "Hồ sơ đã chuyển sang thẩm định chính thức.";
      else if (!current.current_preliminary_import_batch_id) blockedReason = "Chưa xác định đợt nhập liệu hiện hành. Hãy kiểm tra yêu cầu sơ bộ.";
      else if (!current.current_source_artifact_id || stageResult(state, "PRELIMINARY_REQUEST") !== "COMPLETE") {
        blockedReason = "Tệp nguồn hiện hành chưa sẵn sàng để phân tích.";
      } else if (stageResult(state, "PRELIMINARY_ANALYSIS") !== "INCOMPLETE") {
        blockedReason = "Trạng thái phân tích hiện chưa cho phép chốt dữ liệu.";
      }
      const batchId = current.current_preliminary_import_batch_id;
      let mapping: MappingRecoveryState | null = null;
      let rows: ProjectAssetImportStagingRowResponse[] = [];
      if (!blockedReason && batchId && current.current_source_artifact_id) {
        mapping = await getMappingRecovery(projectId, batchId);
        if (!analysisContextReady(current, mapping)) {
          blockedReason = "Ánh xạ chưa tạo dữ liệu tạm hiện hành. Hãy rà soát và tạo dữ liệu tạm từ ánh xạ đã chọn.";
        } else {
          const source = await getSourceArtifact(projectId, batchId, current.current_source_artifact_id);
          if (source.id !== current.current_source_artifact_id || source.import_batch_id !== batchId || source.state !== "available") {
            blockedReason = "Tệp nguồn hiện hành không còn khả dụng. Hãy tải lại trạng thái yêu cầu.";
          } else {
            rows = await readCurrentRows(projectId, batchId);
            if (mapping.materialized_asset_row_count !== rows.length) {
              blockedReason = "Số dòng dữ liệu tạm không khớp ánh xạ hiện hành. Hãy tải lại trạng thái.";
            } else if (rows.length === 0) {
              blockedReason = "Chưa có dòng thiết bị trong dữ liệu tạm hiện hành. Hãy kiểm tra tệp nguồn.";
            } else {
              const [verified, verifiedMapping] = await Promise.all([
                fetchCaseState(projectId), getMappingRecovery(projectId, batchId),
              ]);
              if (verified.case_version !== state.case_version ||
                  verified.preliminary.project_row_version !== current.project_row_version ||
                  verifiedMapping.selection_revision !== mapping.selection_revision ||
                  verifiedMapping.selected_usage_id !== mapping.selected_usage_id ||
                  !analysisContextReady(verified.preliminary, verifiedMapping)) {
                blockedReason = "Nguồn hoặc ánh xạ đã thay đổi khi tải dòng. Hãy tải lại trước khi phân tích.";
              }
            }
          }
        }
      }
      const next = { caseState: state, recovery: mapping, rows, snapshot: null, blockedReason };
      setData(next);
      setDrafts(blockedReason ? [] : rows.map(draftFromStaging));
      setPageIndex(0);
      setLoadState("ready");
      return next;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) setLoadState("sessionExpired");
      else if (error instanceof ApiError && error.status === 403) setLoadState("forbidden");
      else setLoadState("error");
      return null;
    }
  }, [projectId, clearPending]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    const dialog = confirmDialogRef.current;
    if (confirmOpen && dialog && !dialog.open) dialog.showModal();
  }, [confirmOpen]);

  const updateDraft = (index: number, patch: Partial<AnalysisDraft>) => {
    setDrafts((current) => current.map((row, position) => position === index
      ? { ...row, ...patch, human_line_confirmed: patch.human_line_confirmed ?? false }
      : row));
  };

  const submit = async (attempt: PendingAttempt) => {
    setBusy(true);
    setConfirmOpen(false);
    pendingRef.current = attempt;
    storePending(projectId, attempt);
    try {
      await finalizePreliminaryAnalysis(projectId, attempt.payload);
      const refreshed = await load();
      if (!refreshed?.snapshot) {
        setUncertain(true);
        setNotice("Lệnh đã trả về nhưng chưa đọc được bản phân tích hiện hành. Hãy kiểm tra lại trạng thái máy chủ.");
      } else setNotice(null);
    } catch (error) {
      if (unknownResult(error)) {
        setUncertain(true);
        const refreshed = await load();
        if (!refreshed?.snapshot) setNotice("Chưa rõ lệnh chốt đã được ghi nhận hay chưa. Hãy kiểm tra hoặc thử lại cùng mã lệnh.");
      } else if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        setUncertain(true);
        setLoadState(error.status === 401 ? "sessionExpired" : "forbidden");
      } else {
        clearPending();
        await load();
        setNotice("Dữ liệu đã thay đổi hoặc lệnh không còn hợp lệ. Hãy rà soát lại nguồn và từng dòng trước khi chốt.");
      }
    } finally { setBusy(false); }
  };

  const manifest = buildAnalysisManifest(drafts);
  const reviewedCount = drafts.filter((row) => row.human_line_confirmed && !row.has_unresolved_blocking_line).length;
  const canFinalize = Boolean(data && !data.snapshot && !data.blockedReason && data.recovery &&
    analysisContextReady(data.caseState.preliminary, data.recovery) && manifest && !busy && !uncertain && loadState === "ready");

  const confirmFinalize = () => {
    if (!canFinalize || !data?.recovery || !manifest) return;
    const current = data.caseState.preliminary;
    const mapping = data.recovery;
    const payload: PreliminaryAnalysisFinalizeRequest = {
      expected_project_version: current.project_row_version,
      import_batch_id: current.current_preliminary_import_batch_id!,
      source_artifact_id: current.current_source_artifact_id!,
      structure_snapshot_id: mapping.selected_structure_snapshot_id!,
      mapping_decision_id: mapping.selected_confirmation_decision_id!,
      mapping_profile_usage_id: mapping.selected_usage_id!,
      mapping_decision_digest_sha256: mapping.mapping_digest_sha256!,
      profile_usage_mapping_digest_sha256: mapping.materialized_mapping_digest_sha256!,
      line_manifest: manifest,
      idempotency_key: "g11i-" + crypto.randomUUID(),
      confirmed: true,
    };
    void submit({ payload });
  };

  const retryPending = () => {
    const pending = pendingRef.current;
    if (!pending || !data || !retryMatchesCurrent(data, pending) || busy) return;
    void submit(pending);
  };

  if (!data && loadState === "loading") return <LoadingState message="Đang tải phân tích sơ bộ hiện hành…" />;
  if (loadState === "sessionExpired") return <ErrorState title="Phiên làm việc đã hết hạn" message="Đăng nhập lại rồi kiểm tra trạng thái phân tích trước khi tiếp tục." onRetry={onSessionExpired} retryLabel="Đăng nhập lại" />;
  if (loadState === "forbidden") return <ErrorState title="Chưa có quyền truy cập" message="Tài khoản hiện tại không có quyền xem hoặc chốt phân tích này." />;
  if (!data && loadState === "error") return <ErrorState title="Chưa thể tải phân tích sơ bộ" message="Không thể xác minh nguồn và trạng thái hiện hành." onRetry={() => void load()} />;
  if (!data) return null;

  const completed = data.snapshot;
  const visibleDrafts = drafts.slice(pageIndex * 50, (pageIndex + 1) * 50);
  const pageCount = Math.max(1, Math.ceil((completed?.line_manifest.length ?? drafts.length) / 50));
  return (
    <main className="precase-analysis-page">
      <header className="precase-intake-header">
        <div><p className="precase-intake-eyebrow">Yêu cầu sơ bộ</p><h1>Phân tích danh mục</h1>
          <p>Rà soát từng dòng trên đúng dữ liệu tạm của tệp và ánh xạ hiện hành.</p></div>
        <button className="valora-button valora-button--secondary" onClick={() => onNavigate(projectOverviewPath(projectRef))} type="button">Về Tổng quan hồ sơ</button>
      </header>
      {notice && <p className="precase-intake-warning" role="status">{notice}</p>}
      {loadState === "loading" && <p role="status">Đang kiểm tra dữ liệu hiện hành…</p>}
      {loadState === "error" && <ErrorState title="Chưa thể cập nhật phân tích" message="Không thể đọc trạng thái hiện hành. Dữ liệu đang hiển thị chưa được xác minh lại." onRetry={() => void load()} />}
      {completed ? (
        <section className="valora-panel" data-analysis-state="completed">
          <div className="valora-panel__header">Đã chốt phân tích sơ bộ · phiên bản {completed.version}</div>
          <div className="valora-panel__body">
            <p>Bản phân tích bất biến đã được chọn từ trạng thái hồ sơ hiện hành. {completed.line_manifest.length} dòng đã được xác nhận.</p>
            <div className="valora-table-shell precase-analysis-table"><table className="valora-table">
              <thead><tr><th scope="col">Dòng nguồn</th><th scope="col">Nhận diện</th><th scope="col">Số lượng</th><th scope="col">Cơ sở giá</th><th scope="col">Giá tham chiếu</th><th scope="col">Vận chuyển</th><th scope="col">Đơn giá đề xuất</th></tr></thead>
              <tbody>{completed.line_manifest.slice(pageIndex * 50, (pageIndex + 1) * 50).map((line) => <tr key={line.source_row_number}>
                <td>{line.source_row_number}</td><td>{line.identity}</td><td>{line.quantity}</td><td>{line.accepted_price_basis}</td>
                <td>{line.confirmed_reference_price}</td><td>{line.transport_percentage}%</td><td>{line.proposed_unit_price}</td>
              </tr>)}</tbody>
            </table></div>
            {pageCount > 1 && <div className="precase-intake-actions">
              <button className="valora-button valora-button--secondary" disabled={pageIndex === 0} onClick={() => setPageIndex(pageIndex - 1)} type="button">Trang trước</button>
              <span>Trang {pageIndex + 1}/{pageCount}</span>
              <button className="valora-button valora-button--secondary" disabled={pageIndex + 1 === pageCount} onClick={() => setPageIndex(pageIndex + 1)} type="button">Trang sau</button>
            </div>}
          </div>
        </section>
      ) : data.blockedReason ? (
        <section className="valora-panel" role="alert">
          <div className="valora-panel__header">Chưa thể chốt phân tích</div>
          <div className="valora-panel__body"><p>{data.blockedReason}</p>
            <button className="valora-button valora-button--secondary" onClick={() => void load()} type="button">Kiểm tra lại</button>
            <button className="valora-button valora-button--secondary" onClick={() => onNavigate(projectPreliminaryIntakePath(projectRef))} type="button">Về nguồn và ánh xạ</button>
          </div>
        </section>
      ) : (
        <>
          <section className="valora-panel">
            <div className="valora-panel__header">Dữ liệu phân tích · {reviewedCount}/{drafts.length} dòng đã xác nhận</div>
            <div className="valora-panel__body">
              <p>Đơn giá và cơ sở giá cần người dùng nhập, kiểm tra và xác nhận. Số lượng và vị trí dòng lấy từ dữ liệu tạm hiện hành.</p>
              {drafts.some((line) => !sourceQuantityValid(line.quantity)) && <p className="precase-intake-warning" role="alert">Có dòng thiếu số lượng nguồn hoặc số lượng không hợp lệ. Hãy sửa ánh xạ hoặc tệp nguồn trước khi chốt.</p>}
              <div className="valora-table-shell precase-analysis-table"><table className="valora-table">
                <thead><tr><th scope="col">Dòng nguồn</th><th scope="col">Nhận diện</th><th scope="col">Số lượng nguồn</th><th scope="col">Cơ sở giá được chấp nhận</th><th scope="col">Giá tham chiếu đã xác nhận</th><th scope="col">Vận chuyển %</th><th scope="col">Đơn giá đề xuất</th><th scope="col">Còn vướng mắc</th><th scope="col">Đã rà soát</th></tr></thead>
                <tbody>{visibleDrafts.map((line, position) => {
                  const index = pageIndex * 50 + position;
                  return <tr key={line.source_row_number} data-row-source={line.source_row_number}>
                    <td>{line.source_row_number}</td>
                    <td><input aria-label={"Nhận diện dòng " + line.source_row_number} className="valora-field" maxLength={255} name="identity" onChange={(event) => updateDraft(index, { identity: event.target.value })} value={line.identity} /></td>
                    <td>{line.quantity || "Thiếu"}</td>
                    <td><input aria-label={"Cơ sở giá dòng " + line.source_row_number} className="valora-field" maxLength={64} name="accepted_price_basis" onChange={(event) => updateDraft(index, { accepted_price_basis: event.target.value })} value={line.accepted_price_basis} /></td>
                    <td><input aria-label={"Giá tham chiếu dòng " + line.source_row_number} className="valora-field" inputMode="decimal" name="confirmed_reference_price" onChange={(event) => updateDraft(index, { confirmed_reference_price: event.target.value })} value={line.confirmed_reference_price} /></td>
                    <td><input aria-label={"Vận chuyển dòng " + line.source_row_number} className="valora-field" inputMode="decimal" name="transport_percentage" onChange={(event) => updateDraft(index, { transport_percentage: event.target.value })} value={line.transport_percentage} /></td>
                    <td><input aria-label={"Đơn giá đề xuất dòng " + line.source_row_number} className="valora-field" inputMode="decimal" name="proposed_unit_price" onChange={(event) => updateDraft(index, { proposed_unit_price: event.target.value })} value={line.proposed_unit_price} /></td>
                    <td><input aria-label={"Vướng mắc dòng " + line.source_row_number} checked={line.has_unresolved_blocking_line} name="has_unresolved_blocking_line" onChange={(event) => updateDraft(index, { has_unresolved_blocking_line: event.target.checked })} type="checkbox" /></td>
                    <td><input aria-label={"Xác nhận rà soát dòng " + line.source_row_number} checked={line.human_line_confirmed} disabled={line.has_unresolved_blocking_line} name="human_line_confirmed" onChange={(event) => updateDraft(index, { human_line_confirmed: event.target.checked })} type="checkbox" /></td>
                  </tr>;
                })}</tbody>
              </table></div>
              {pageCount > 1 && <div className="precase-intake-actions">
                <button className="valora-button valora-button--secondary" disabled={pageIndex === 0} onClick={() => setPageIndex(pageIndex - 1)} type="button">Trang trước</button>
                <span>Trang {pageIndex + 1}/{pageCount}</span>
                <button className="valora-button valora-button--secondary" disabled={pageIndex + 1 === pageCount} onClick={() => setPageIndex(pageIndex + 1)} type="button">Trang sau</button>
              </div>}
            </div>
          </section>
          {uncertain && <section className="valora-panel" role="alert">
            <div className="valora-panel__header">Chưa rõ kết quả chốt phân tích</div>
            <div className="valora-panel__body"><p>Kiểm tra trạng thái máy chủ trước khi gửi lại. Lần thử lại dùng đúng mã lệnh cũ.</p>
              <button className="valora-button valora-button--secondary" onClick={() => void load()} type="button">Kiểm tra trạng thái</button>
              {pendingRef.current && retryMatchesCurrent(data, pendingRef.current) &&
                <button className="valora-button valora-button--primary" disabled={busy || loadState !== "ready"} onClick={retryPending} type="button">Thử lại cùng mã lệnh</button>}
            </div>
          </section>}
          <section className="valora-panel"><div className="valora-panel__body">
            {!manifest && <p className="precase-intake-warning" role="status">Cần đủ thông tin giá, số lượng hợp lệ, không còn vướng mắc và xác nhận riêng từng dòng trước khi chốt.</p>}
            <button className="valora-button valora-button--primary" disabled={!canFinalize} onClick={() => setConfirmOpen(true)} type="button">Chốt phân tích sơ bộ</button>
          </div></section>
        </>
      )}
      {confirmOpen && <dialog className="precase-analysis-confirm" ref={confirmDialogRef} onCancel={() => setConfirmOpen(false)} aria-label="Xác nhận chốt phân tích sơ bộ">
        <div className="valora-panel"><div className="valora-panel__header">Xác nhận chốt phân tích sơ bộ</div>
          <div className="valora-panel__body"><p>Thao tác này tạo bản phân tích bất biến, có phiên bản mới cho {drafts.length} dòng đã rà soát.</p>
            <button className="valora-button valora-button--secondary" onClick={() => setConfirmOpen(false)} type="button">Tiếp tục rà soát</button>
            <button className="valora-button valora-button--primary" onClick={confirmFinalize} type="button">Xác nhận chốt</button>
          </div></div>
      </dialog>}
    </main>
  );
}
