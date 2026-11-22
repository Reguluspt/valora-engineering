import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

import { fetchAssetImportRows, type ProjectAssetImportStagingRowResponse } from "../../api/assetImports";
import { fetchCaseState, type CaseStateResponse } from "../../api/caseState";
import { ApiError } from "../../api/client";
import { getCurrentAccount, type AccountContext } from "../../api/auth";
import {
  claimPreliminaryAnalysisAttempt, finalizePreliminaryAnalysis, getPreliminaryAnalysis,
  getPreliminaryAnalysisAttempt, getPreliminaryAnalysisAttemptState, reconcilePreliminaryAnalysisAttempt,
  type PreliminaryAnalysisAttemptClaim, type PreliminaryAnalysisAttemptState, type PreliminaryAnalysisReadResponse,
} from "../../api/preliminaryAnalysis";
import { getMappingRecovery, getSourceArtifact, type ImportSourceArtifact, type MappingRecoveryState } from "../../api/preliminaryIntake";
import { projectOverviewPath, projectPreliminaryIntakePath, projectPreliminaryCompletionPath } from "../../contracts/valoraV23";
import { ErrorState } from "../common/ErrorState";
import { LoadingState } from "../common/LoadingState";
import { useResolvedProject } from "../workbench/project-context";
import { analysisContextReady, buildAnalysisManifest, draftFromStaging, sourceQuantityValid, type AnalysisDraft } from "./analysisReviewModel";
import { PreliminaryAnalysisWorkspace } from "./PreliminaryAnalysisWorkspace";
import "./precase.css";

interface AnalysisData {
  caseState: CaseStateResponse;
  recovery: MappingRecoveryState | null;
  rows: ProjectAssetImportStagingRowResponse[];
  snapshot: PreliminaryAnalysisReadResponse | null;
  blockedReason: string | null;
  attemptState: PreliminaryAnalysisAttemptState;
  source: ImportSourceArtifact | null;
}

const legacyPendingPrefix = "valora:g11i:analysis-pending:";
const finalizePermission = "project:preliminary_analysis:finalize";
const reconcilePermission = "project:preliminary_analysis:reconcile";

export function clearLegacyAnalysisStorage() {
  try {
    for (let index = sessionStorage.length - 1; index >= 0; index--) {
      const key = sessionStorage.key(index);
      if (key?.startsWith(legacyPendingPrefix)) sessionStorage.removeItem(key);
    }
  } catch { /* Storage access may be disabled. */ }
}

export function analysisOwner(account: AccountContext | null): string | null {
  return account?.id && account.organization_id && account.permissions.includes("project:read") && account.permissions.includes(finalizePermission) &&
    account.session_incarnation && /^[0-9a-f]{64}$/.test(account.session_incarnation)
    ? JSON.stringify([account.organization_id, account.id, account.session_incarnation]) : null;
}

function sourceFingerprint(data: AnalysisData): string | null {
  const mapping = data.recovery;
  const source = data.source;
  const state = data.caseState;
  if (data.blockedReason || !mapping || !source) return null;
  return JSON.stringify([
    state.preliminary.project_id, state.case_version, state.preliminary.project_row_version,
    state.preliminary.current_preliminary_analysis_snapshot_id,
    data.attemptState.base_analysis_version, source.import_batch_id, source.id, source.generation, source.checksum_sha256,
    mapping.selection_revision, mapping.selected_structure_snapshot_id, mapping.selected_confirmation_decision_id,
    mapping.selected_usage_id, mapping.current_staging_usage_id, mapping.mapping_digest_sha256,
    mapping.materialized_mapping_digest_sha256,
    data.rows.map(({ id, source_row_number }) => [id, source_row_number]),
  ]);
}

function stageResult(state: CaseStateResponse, stage: "PRELIMINARY_REQUEST" | "PRELIMINARY_ANALYSIS") {
  return state.stages.find((item) => item.stage === stage)?.result;
}

async function readCurrentRows(projectId: string, batchId: string): Promise<ProjectAssetImportStagingRowResponse[]> {
  const rows: ProjectAssetImportStagingRowResponse[] = [];
  const seen = new Set<number>();
  const seenIds = new Set<string>();
  let total: number | null = null;
  while (total === null || rows.length < total) {
    const page = await fetchAssetImportRows(projectId, batchId, { limit: 100, offset: rows.length });
    if (page.project_id !== projectId || page.import_batch_id !== batchId ||
        !Number.isInteger(page.total) || page.total < 0 ||
        (total !== null && page.total !== total) || page.items.length > 100 || page.offset !== rows.length ||
        (page.items.length === 0 && page.total > rows.length)) {
      throw new Error("Staging pagination changed during analysis read");
    }
    total = page.total;
    for (const row of page.items) {
      if (!row.id || seenIds.has(row.id) || row.import_batch_id !== batchId || !Number.isInteger(row.source_row_number) ||
          row.source_row_number < 1 || row.source_row_number > 1_048_576 || seen.has(row.source_row_number)) {
        throw new Error("Staging provenance is incomplete");
      }
      seen.add(row.source_row_number);
      seenIds.add(row.id);
      rows.push(row);
    }
  }
  if (rows.length !== total) throw new Error("Staging pagination is incomplete");
  return rows;
}

interface AnalysisPageProps {
  projectRef: string;
  onNavigate: (path: string) => void;
  onSessionExpired: () => void;
  active?: boolean;
  owner?: string | null;
  onDirtyChange?: (dirty: boolean) => void;
  discardVersion?: number;
}

export function PreliminaryAnalysisPage(props: AnalysisPageProps) {
  const resolved = useResolvedProject(props.projectRef);
  if (resolved.state === "loading" || resolved.state === "idle") return <LoadingState message="Đang xác định yêu cầu sơ bộ…" />;
  if (resolved.state === "error" || !resolved.projectId) {
    return <ErrorState title={resolved.error?.title || "Chưa thể mở phân tích"} message={resolved.error?.message || "Không thể xác định hồ sơ."} onRetry={resolved.retry} />;
  }
  return <ResolvedPreliminaryAnalysis key={resolved.projectId} projectId={resolved.projectId} {...props} />;
}

function ResolvedPreliminaryAnalysis({
  projectId, projectRef, onNavigate, onSessionExpired, active = true, owner, onDirtyChange, discardVersion = 0,
}: AnalysisPageProps & { projectId: string }) {
  const [data, setData] = useState<AnalysisData | null>(null);
  const [drafts, setDrafts] = useState<AnalysisDraft[]>([]);
  const [dirty, setDirty] = useState(false);
  const [quarantined, setQuarantined] = useState(false);
  const [revising, setRevising] = useState(false);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error" | "sessionExpired" | "forbidden">("loading");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [reconcileOpen, setReconcileOpen] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [workspaceVersion, setWorkspaceVersion] = useState(0);
  const [canReconcile, setCanReconcile] = useState(false);
  const confirmDialogRef = useRef<HTMLDialogElement>(null);
  const reconcileDialogRef = useRef<HTMLDialogElement>(null);
  const epoch = useRef(0);
  const fingerprint = useRef<string | null>(null);
  const currentOwner = useRef<string | null>(null);
  const attemptId = useRef<string | null>(null);
  const submitting = useRef(false);
  const draftDirty = useRef(false);
  const quarantine = useRef(false);
  const priorDiscardVersion = useRef(discardVersion);
  const previousFocus = useRef<HTMLElement | null>(null);
  const restoreFocus = useRef(false);

  const clearDraft = useCallback(() => {
    fingerprint.current = null;
    draftDirty.current = false;
    quarantine.current = false;
    setDrafts([]);
    setDirty(false);
    setQuarantined(false);
    previousFocus.current = null;
    setWorkspaceVersion((version) => version + 1);
  }, []);

  const invalidate = useCallback((error: unknown) => {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      clearDraft();
      currentOwner.current = null;
      attemptId.current = null;
      setData(null);
      setCanReconcile(false);
      setUncertain(false);
      setLoadState(error.status === 401 ? "sessionExpired" : "forbidden");
    } else setLoadState("error");
  }, [clearDraft]);

  const verifiedAccount = useCallback(async () => {
    const account = await getCurrentAccount();
    const observed = analysisOwner(account);
    if (!account.permissions.includes("project:read") || !account.session_incarnation ||
        !/^[0-9a-f]{64}$/.test(account.session_incarnation)) throw new ApiError("Phiên không còn quyền truy cập.", 403);
    if ((owner && observed !== owner) || (currentOwner.current && observed !== currentOwner.current)) {
      throw new ApiError("Phiên làm việc đã thay đổi.", 401);
    }
    return account;
  }, [owner]);

  const load = useCallback(async (editRevision = false): Promise<AnalysisData | null> => {
    const generation = ++epoch.current;
    setLoadState("loading");
    try {
      const account = await verifiedAccount();
      if (generation !== epoch.current) return null;
      currentOwner.current = analysisOwner(account);
      const incarnation = account.session_incarnation!;
      const [state, attemptState] = await Promise.all([
        fetchCaseState(projectId), getPreliminaryAnalysisAttemptState(projectId, incarnation),
      ]);
      const current = state.preliminary;
      if (current.project_id !== projectId) throw new Error("Project authority mismatch");
      let snapshot: PreliminaryAnalysisReadResponse | null = null;
      let blockedReason: string | null = null;
      let mapping: MappingRecoveryState | null = null;
      let source: ImportSourceArtifact | null = null;
      let rows: ProjectAssetImportStagingRowResponse[] = [];
      if (current.current_preliminary_analysis_snapshot_id && !editRevision) {
        snapshot = await getPreliminaryAnalysis(projectId, current.current_preliminary_analysis_snapshot_id);
        if (snapshot.id !== current.current_preliminary_analysis_snapshot_id || snapshot.project_id !== projectId ||
            snapshot.version !== current.current_preliminary_analysis_version) throw new Error("Analysis readback mismatch");
      } else {
        const batchId = current.current_preliminary_import_batch_id;
        const sourceId = current.current_source_artifact_id;
        if (current.official_intake_commit_id) blockedReason = "Hồ sơ đã chuyển sang thẩm định chính thức.";
        else if (!batchId) blockedReason = "Chưa xác định đợt nhập liệu hiện hành. Hãy kiểm tra yêu cầu sơ bộ.";
        else if (!sourceId || stageResult(state, "PRELIMINARY_REQUEST") !== "COMPLETE") {
          blockedReason = "Tệp nguồn hiện hành chưa sẵn sàng để phân tích.";
        } else if (!editRevision && stageResult(state, "PRELIMINARY_ANALYSIS") !== "INCOMPLETE") {
          blockedReason = "Trạng thái phân tích hiện chưa cho phép chốt dữ liệu.";
        } else {
          mapping = await getMappingRecovery(projectId, batchId);
          if (!analysisContextReady(current, mapping, editRevision)) {
            blockedReason = "Ánh xạ chưa tạo dữ liệu tạm hiện hành. Hãy rà soát và tạo dữ liệu tạm từ ánh xạ đã chọn.";
          } else {
            source = await getSourceArtifact(projectId, batchId, sourceId);
            if (source.id !== sourceId || source.import_batch_id !== batchId || source.state !== "available" ||
                !Number.isInteger(source.generation) || source.generation < 1 || !/^[0-9a-f]{64}$/.test(source.checksum_sha256)) {
              blockedReason = "Tệp nguồn hiện hành không còn khả dụng. Hãy tải lại trạng thái yêu cầu.";
            } else {
              try {
                rows = await readCurrentRows(projectId, batchId);
              } catch (error) {
                if (error instanceof ApiError) throw error;
                blockedReason = "Các dòng dữ liệu tạm không còn khớp ánh xạ. Hãy kiểm tra lại nguồn.";
              }
              if (!blockedReason && (mapping.materialized_asset_row_count !== rows.length || rows.length === 0)) {
                blockedReason = "Số dòng dữ liệu tạm không khớp ánh xạ hiện hành. Hãy tải lại trạng thái.";
              }
              if (!blockedReason) {
                const [verified, verifiedMapping] = await Promise.all([
                  fetchCaseState(projectId), getMappingRecovery(projectId, batchId),
                ]);
                if (verified.case_version !== state.case_version ||
                    verified.preliminary.project_row_version !== current.project_row_version ||
                    verifiedMapping.selection_revision !== mapping.selection_revision ||
                    verifiedMapping.selected_usage_id !== mapping.selected_usage_id ||
                    verifiedMapping.mapping_digest_sha256 !== mapping.mapping_digest_sha256 ||
                    verifiedMapping.materialized_mapping_digest_sha256 !== mapping.materialized_mapping_digest_sha256 ||
                    !analysisContextReady(verified.preliminary, verifiedMapping, editRevision)) {
                  blockedReason = "Nguồn hoặc ánh xạ đã thay đổi khi tải dòng. Hãy tải lại trước khi phân tích.";
                }
              }
            }
          }
        }
      }
      let terminal = false;
      let committed = false;
      const knownAttempt = attemptId.current;
      if (knownAttempt && !attemptState.blocked) {
        try {
          const status = await getPreliminaryAnalysisAttempt(projectId, knownAttempt, incarnation);
          if (status.status === "COMMITTED" && status.committed_snapshot_id &&
              status.committed_snapshot_id === current.current_preliminary_analysis_snapshot_id) {
            const fact = snapshot ?? await getPreliminaryAnalysis(projectId, status.committed_snapshot_id);
            if (fact.id !== status.committed_snapshot_id || fact.project_id !== projectId ||
                fact.version !== current.current_preliminary_analysis_version) throw new Error("Analysis readback mismatch");
            snapshot = fact;
            committed = true;
          }
          terminal = status.status === "REJECTED_TERMINAL" || committed;
        } catch (error) {
          if (!(error instanceof ApiError) || error.status !== 404) throw error;
        }
      }
      const verified = await verifiedAccount();
      if (generation !== epoch.current) return null;
      if (verified.session_incarnation !== incarnation || verified.id !== account.id ||
          verified.organization_id !== account.organization_id || analysisOwner(verified) !== analysisOwner(account)) {
        throw new ApiError("Phiên làm việc đã thay đổi.", 401);
      }
      setCanReconcile(verified.roles.includes("owner") && verified.permissions.includes(reconcilePermission));
      if (terminal) {
        attemptId.current = null;
        setUncertain(false);
        clearDraft();
        if (committed) {
          setNotice(null);
          if (editRevision) setRevising(false);
        }
      }
      const next = { caseState: state, recovery: mapping, rows, snapshot, blockedReason, attemptState, source };
      const nextFingerprint = sourceFingerprint(next);
      if (draftDirty.current && fingerprint.current !== nextFingerprint) {
        quarantine.current = true;
        setQuarantined(true);
      } else if (!draftDirty.current && !quarantine.current) {
        fingerprint.current = nextFingerprint;
        setDrafts(blockedReason || !analysisOwner(verified) ? [] : rows.map(draftFromStaging));
      }
      setData(next);
      setLoadState("ready");
      return next;
    } catch (error) {
      if (generation === epoch.current) invalidate(error);
      return null;
    }
  }, [clearDraft, invalidate, projectId, verifiedAccount]);

  useLayoutEffect(() => {
    if (active) void load(revising);
    return () => { epoch.current++; };
  }, [active, load, revising]);

  useLayoutEffect(() => {
    if (discardVersion === priorDiscardVersion.current) return;
    priorDiscardVersion.current = discardVersion;
    clearDraft();
    if (active) void load(revising);
  }, [active, clearDraft, discardVersion, load, revising]);

  useEffect(() => { onDirtyChange?.(dirty); }, [dirty, onDirtyChange]);
  useEffect(() => {
    if (confirmOpen && confirmDialogRef.current && !confirmDialogRef.current.open) confirmDialogRef.current.showModal();
    if (reconcileOpen && reconcileDialogRef.current && !reconcileDialogRef.current.open) reconcileDialogRef.current.showModal();
  }, [confirmOpen, reconcileOpen]);
  useLayoutEffect(() => {
    if (!active) {
      setLoadState("loading");
      restoreFocus.current = true;
      setConfirmOpen(false);
      setReconcileOpen(false);
    }
  }, [active]);
  useLayoutEffect(() => {
    if (active && loadState === "ready" && !quarantined && restoreFocus.current) {
      restoreFocus.current = false;
      if (previousFocus.current?.isConnected) previousFocus.current.focus();
    }
  }, [active, loadState, quarantined]);

  const updateDraft = (index: number, patch: Partial<AnalysisDraft>) => {
    if (!active || busy || uncertain || loadState !== "ready" || confirmOpen || quarantined || !currentOwner.current) return;
    draftDirty.current = true;
    setDirty(true);
    setDrafts((current) => current.map((row, position) => position === index
      ? { ...row, ...patch, human_line_confirmed: patch.human_line_confirmed ?? false }
      : row));
  };

  const manifest = buildAnalysisManifest(drafts);
  const reviewedCount = drafts.filter((row) => row.human_line_confirmed && !row.has_unresolved_blocking_line).length;
  const base = data?.attemptState.base_analysis_version;
  const canFinalize = Boolean(data && !data.snapshot && !data.blockedReason && data.recovery && data.source &&
    typeof base === "number" && !data.attemptState.blocked && currentOwner.current &&
    manifest && !busy && !uncertain && !quarantined && loadState === "ready" && active);

  const confirmFinalize = async () => {
    if (!canFinalize || !data?.recovery || !data.source || !manifest || base === undefined || submitting.current) return;
    const mapping = data.recovery;
    const source = data.source;
    const commandId = crypto.randomUUID();
    const claim: PreliminaryAnalysisAttemptClaim = {
      command_id: commandId,
      expected_analysis_version: base,
      expected_project_version: data.caseState.preliminary.project_row_version,
      import_batch_id: source.import_batch_id,
      source_artifact_id: source.id,
      source_generation: source.generation,
      source_checksum_sha256: source.checksum_sha256,
      structure_snapshot_id: mapping.selected_structure_snapshot_id!,
      mapping_decision_id: mapping.selected_confirmation_decision_id!,
      mapping_profile_usage_id: mapping.selected_usage_id!,
      selection_revision: mapping.selection_revision,
      mapping_decision_digest_sha256: mapping.mapping_digest_sha256!,
      profile_usage_mapping_digest_sha256: mapping.materialized_mapping_digest_sha256!,
    };
    const v3Lines = manifest.flatMap((line, index) => {
      const id = drafts[index].staging_row_id;
      return id ? [{ ...line, staging_row_id: id }] : [];
    });
    if (v3Lines.length !== manifest.length) return;
    const generation = epoch.current;
    submitting.current = true;
    setBusy(true);
    setConfirmOpen(false);
    let claimStarted = false;
    try {
      const account = await verifiedAccount();
      if (epoch.current !== generation) return;
      const incarnation = account.session_incarnation!;
      claimStarted = true;
      setUncertain(true);
      const attempt = await claimPreliminaryAnalysisAttempt(projectId, claim, incarnation);
      attemptId.current = attempt.attempt_id;
      if (epoch.current !== generation || attempt.status !== "RECEIVED") return;
      await finalizePreliminaryAnalysis(projectId, {
        attempt_id: attempt.attempt_id,
        expected_analysis_version: claim.expected_analysis_version,
        expected_project_version: claim.expected_project_version,
        import_batch_id: claim.import_batch_id,
        source_artifact_id: claim.source_artifact_id,
        structure_snapshot_id: claim.structure_snapshot_id,
        mapping_decision_id: claim.mapping_decision_id,
        mapping_profile_usage_id: claim.mapping_profile_usage_id,
        mapping_decision_digest_sha256: claim.mapping_decision_digest_sha256,
        profile_usage_mapping_digest_sha256: claim.profile_usage_mapping_digest_sha256,
        line_manifest: v3Lines, idempotency_key: commandId, confirmed: true,
      }, incarnation);
      if (epoch.current !== generation) return;
      setNotice(null);
      if (revising) setRevising(false);
      else await load();
    } catch (error) {
      if (epoch.current !== generation) return;
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        invalidate(error);
      } else if (!claimStarted) {
        invalidate(error);
      } else {
        if (!attemptId.current && error instanceof ApiError && (error.status === 409 || error.status === 422)) {
          setUncertain(false);
          setNotice("Dữ liệu đã thay đổi hoặc đang có lệnh chốt. Hãy kiểm tra lại trạng thái.");
        } else {
          setNotice("Chưa xác minh được kết quả chốt. Hãy kiểm tra trạng thái trên máy chủ.");
        }
        await load(revising);
      }
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  };

  const reconcile = async () => {
    const attempt = data?.attemptState.active_attempt;
    if (!attempt || !canReconcile || busy) return;
    setReconcileOpen(false);
    setBusy(true);
    const generation = epoch.current;
    try {
      const account = await verifiedAccount();
      if (epoch.current !== generation) return;
      await reconcilePreliminaryAnalysisAttempt(projectId, attempt, account.session_incarnation!,
        attempt.status === "RECEIVED" ? "request_abandoned" : "executor_unresponsive");
      if (epoch.current !== generation) return;
      setUncertain(false);
      attemptId.current = null;
      clearDraft();
      setNotice("Đã đối soát lệnh chốt theo trạng thái máy chủ. Hãy rà soát lại dữ liệu trước khi chốt.");
      await load(revising);
    } catch (error) {
      if (epoch.current !== generation) return;
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) invalidate(error);
      else await load(revising);
    } finally { setBusy(false); }
  };

  if (!data && loadState === "loading") return <LoadingState message="Đang tải phân tích sơ bộ hiện hành…" />;
  if (loadState === "sessionExpired") return <ErrorState title="Phiên làm việc đã hết hạn" message="Đăng nhập lại rồi kiểm tra trạng thái phân tích trước khi tiếp tục." onRetry={onSessionExpired} retryLabel="Đăng nhập lại" />;
  if (loadState === "forbidden") return <ErrorState title="Chưa có quyền truy cập" message="Tài khoản hiện tại không có quyền xem hoặc chốt phân tích này." />;
  if (!data && loadState === "error") return <ErrorState title="Chưa thể tải phân tích sơ bộ" message="Không thể xác minh nguồn và trạng thái hiện hành." onRetry={() => void load()} />;
  if (!data) return null;

  const completed = data.snapshot;
  const attemptBlocked = uncertain || data.attemptState.blocked;
  return (
    <div className="precase-analysis-page" onFocusCapture={(event) => {
      if (event.target instanceof HTMLElement) previousFocus.current = event.target;
    }}>
      {data.blockedReason && <header className="precase-intake-header">
        <div><p className="precase-intake-eyebrow">Yêu cầu sơ bộ</p><h1>Phân tích danh mục</h1>
          <p>Rà soát từng dòng trên đúng dữ liệu tạm của tệp và ánh xạ hiện hành.</p></div>
        <button className="valora-button valora-button--secondary" onClick={() => onNavigate(projectOverviewPath(projectRef))} type="button">Về Tổng quan hồ sơ</button>
      </header>}
      {notice && <p className="precase-intake-warning" role="status">{notice}</p>}
      {loadState === "loading" && <p role="status">Đang kiểm tra dữ liệu hiện hành…</p>}
      {loadState === "error" && <ErrorState title="Chưa thể cập nhật phân tích" message="Không thể đọc trạng thái hiện hành. Dữ liệu đang hiển thị chưa được xác minh lại." onRetry={() => void load()} />}
      {attemptBlocked && loadState === "ready" && <section className="valora-panel" role="alert">
        <div className="valora-panel__header">Chưa rõ kết quả chốt phân tích</div>
        <div className="valora-panel__body"><p>Kiểm tra trạng thái máy chủ. Có thể chốt lại sau khi lệnh trước đã có kết quả cuối cùng.</p>
          <button className="valora-button valora-button--secondary" onClick={() => void load(revising)} type="button">Kiểm tra trạng thái</button>
          {canReconcile && data.attemptState.active_attempt && <button className="valora-button valora-button--secondary" disabled={busy} onClick={() => setReconcileOpen(true)} type="button">Đối soát lệnh chốt</button>}
        </div>
      </section>}
      {quarantined && <section className="valora-panel" role="alert">
        <div className="valora-panel__header">Nguồn đã thay đổi. Bản nháp đang được giữ riêng.</div>
        <div className="valora-panel__body">
          <button className="valora-button valora-button--secondary" onClick={() => onNavigate(projectPreliminaryIntakePath(projectRef))} type="button">Xem nguồn hiện tại</button>
          <button className="valora-button valora-button--secondary" onClick={() => { clearDraft(); void load(revising); }} type="button">Bỏ bản nháp</button>
        </div>
      </section>}
      {completed ? (
        <>
          <div className="valora-message valora-message--success precase-analysis-completed" data-analysis-state="completed">
            <strong>Đã chốt phân tích sơ bộ · phiên bản {completed.version}</strong>
            <span>Bản phân tích bất biến hiện hành · {completed.line_manifest.length} dòng đã được xác nhận.</span>
          </div>
          {!data.caseState.preliminary.official_intake_commit_id && currentOwner.current && !attemptBlocked && !quarantined &&
            typeof base === "number" && base === completed.version && loadState === "ready" &&
            <button className="valora-button valora-button--secondary" onClick={() => { clearDraft(); setRevising(true); }} type="button">Rà soát phiên bản phân tích mới</button>}
          <PreliminaryAnalysisWorkspace key={completed.id} drafts={[]} sourceRows={[]} snapshot={completed}
            disabled onUpdateDraft={updateDraft} initialDetailOpen presentation={{ projectCode: projectRef, catalogName: "Bản phân tích đã chốt" }} onSummary={() => onNavigate(projectPreliminaryCompletionPath(projectRef))} />
        </>
      ) : data.blockedReason ? (
        <section className="valora-panel" role="alert">
          <div className="valora-panel__header">Chưa thể chốt phân tích</div>
          <div className="valora-panel__body"><p>{data.blockedReason}</p>
            <button className="valora-button valora-button--secondary" onClick={() => void load(revising)} type="button">Kiểm tra lại</button>
            <button className="valora-button valora-button--secondary" onClick={() => onNavigate(projectPreliminaryIntakePath(projectRef))} type="button">Về nguồn và ánh xạ</button>
          </div>
        </section>
      ) : (
        <>
          <div hidden={!active || loadState !== "ready" || quarantined}>
            {drafts.some((line) => !sourceQuantityValid(line.quantity)) && <p className="precase-intake-warning" role="alert">Có dòng thiếu số lượng nguồn hoặc số lượng không hợp lệ. Hãy sửa ánh xạ hoặc tệp nguồn trước khi chốt.</p>}
            <PreliminaryAnalysisWorkspace key={workspaceVersion} drafts={drafts} sourceRows={data.rows}
              disabled={busy || attemptBlocked || loadState !== "ready" || confirmOpen || !currentOwner.current}
              onUpdateDraft={updateDraft} initialDetailOpen presentation={{ projectCode: projectRef, catalogName: "Danh mục từ nguồn hiện hành" }} onSummary={() => onNavigate(projectPreliminaryCompletionPath(projectRef))} />
          </div>
          <section className="valora-panel"><div className="valora-panel__body">
            <p>{reviewedCount}/{drafts.length} dòng đã xác nhận. Đã xem chi tiết không thay thế xác nhận.</p>
            {!manifest && <p className="precase-intake-warning" role="status">Cần đủ thông tin giá, số lượng hợp lệ, không còn vướng mắc và xác nhận riêng từng dòng trước khi chốt.</p>}
            <button className="valora-button valora-button--primary" disabled={!canFinalize} onClick={() => setConfirmOpen(true)} type="button">Chốt phân tích sơ bộ</button>
          </div></section>
        </>
      )}
      {reconcileOpen && <dialog ref={reconcileDialogRef} className="valora-panel precase-confirm-dialog"
        aria-label="Đối soát lệnh chốt" onCancel={() => setReconcileOpen(false)}>
        <div className="valora-panel__header">Đối soát lệnh chốt</div>
        <div className="valora-panel__body"><p>Máy chủ sẽ kiểm tra bản đã chốt và vô hiệu hóa lệnh cũ nếu trạng thái vẫn khớp.</p>
          <button className="valora-button valora-button--secondary" onClick={() => setReconcileOpen(false)} type="button">Quay lại</button>
          <button className="valora-button valora-button--primary" onClick={() => void reconcile()} type="button">Xác nhận đối soát</button>
        </div>
      </dialog>}
      {confirmOpen && <dialog className="precase-analysis-confirm" ref={confirmDialogRef} onCancel={() => setConfirmOpen(false)} aria-label="Xác nhận chốt phân tích sơ bộ">
        <div className="valora-panel"><div className="valora-panel__header">Xác nhận chốt phân tích sơ bộ</div>
          <div className="valora-panel__body"><p>Thao tác này tạo bản phân tích bất biến, có phiên bản mới cho {drafts.length} dòng đã rà soát.</p>
            <button className="valora-button valora-button--secondary" onClick={() => setConfirmOpen(false)} type="button">Tiếp tục rà soát</button>
            <button className="valora-button valora-button--primary" onClick={() => void confirmFinalize()} type="button">Xác nhận chốt</button>
          </div></div>
      </dialog>}
    </div>
  );
}
