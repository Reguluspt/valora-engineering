import React, { useCallback, useEffect, useState } from "react";

import { ApiError } from "../../api/client";
import { getProject, type ProjectSummary } from "../../api/projects";
import {
  analyzeStructure,
  confirmMapping,
  createPreliminaryBatch,
  getMappingRecovery,
  getSourceArtifact,
  listPreliminaryBatches,
  listSourceArtifacts,
  listStructureSnapshots,
  materializeMapping,
  proposeMapping,
  uploadSourceArtifact,
  type ImportSourceArtifact,
  type MappingField,
  type MappingProposal,
  type MappingRecoveryState,
  type MappingSnapshot,
  type PreliminaryBatch,
  type SemanticRole,
  type WorkbookStructureSnapshot,
} from "../../api/preliminaryIntake";
import { APP_ROUTES, projectOverviewPath } from "../../contracts/valoraV23";
import { ErrorState } from "../common/ErrorState";
import { LoadingState } from "../common/LoadingState";
import { useResolvedProject } from "../workbench/project-context";
import "./precase.css";

interface IntakeData {
  project: ProjectSummary;
  batches: PreliminaryBatch[];
  batch: PreliminaryBatch | null;
  recovery: MappingRecoveryState | null;
  source: ImportSourceArtifact | null;
  artifacts: ImportSourceArtifact[];
  snapshots: WorkbookStructureSnapshot[];
}

interface PendingUnknown {
  kind: "batch" | "source" | "structure" | "proposal" | "confirmation" | "materialization";
  batchId?: string;
  previousSourceId?: string | null;
  knownSnapshotIds?: string[];
  commandId?: string;
  confirmationId?: string;
  confirmationPayload?: Parameters<typeof confirmMapping>[2];
  materializationPayload?: Parameters<typeof materializeMapping>[2];
  proposalPayload?: {
    source_artifact_id: string;
    structure_snapshot_id: string;
    candidate_index: number;
    command_id: string;
  };
}

const pendingKey = (projectId: string) => `valora:g11h:pending:${projectId}`;

function readPending(projectId: string): PendingUnknown | null {
  try {
    const raw = sessionStorage.getItem(pendingKey(projectId));
    if (!raw) return null;
    const value = JSON.parse(raw) as PendingUnknown;
    return ["batch", "source", "structure", "proposal", "confirmation", "materialization"].includes(value.kind)
      ? value : null;
  } catch {
    return null;
  }
}

function pendingSuperseded(pending: PendingUnknown, data: IntakeData): boolean {
  const recovery = data.recovery;
  if (!recovery) return false;
  if (pending.kind === "confirmation" && pending.confirmationPayload) {
    if (recovery.selected_command_id === pending.commandId) return false;
    return recovery.official_intake_closed ||
      recovery.selection_revision > pending.confirmationPayload.expected_selection_revision;
  }
  if (pending.kind === "materialization" && pending.materializationPayload) {
    if (recovery.status === "materialized" &&
      recovery.selected_confirmation_decision_id === pending.confirmationId) return false;
    return recovery.official_intake_closed ||
      recovery.selection_revision > pending.materializationPayload.expected_selection_revision;
  }
  return false;
}

function pendingResolved(pending: PendingUnknown, data: IntakeData): boolean {
  if (pendingSuperseded(pending, data)) return true;
  switch (pending.kind) {
    case "batch": return Boolean(data.batch && data.project.current_preliminary_import_batch_id === data.batch.id);
    case "source": return Boolean(data.source && data.source.state === "available" &&
      data.recovery?.current_source_artifact_id !== pending.previousSourceId);
    case "structure": return data.snapshots.some((item) => !pending.knownSnapshotIds?.includes(item.id));
    case "confirmation": return Boolean(pending.commandId && data.recovery?.selected_command_id === pending.commandId);
    case "materialization": return data.recovery?.status === "materialized" &&
      data.recovery.selected_confirmation_decision_id === pending.confirmationId;
    case "proposal": return Boolean(
      pending.proposalPayload && data.recovery &&
      (data.recovery.current_source_artifact_id !== pending.proposalPayload.source_artifact_id ||
        data.recovery.recent_proposals.some((item) =>
          item.command_id === pending.commandId && item.terminal_outcomes.length > 0))
    );
  }
}

const ROLE_LABELS: Record<SemanticRole, string> = {
  row_number: "Số thứ tự",
  raw_asset_name: "Tên tài sản",
  raw_description: "Đặc điểm / mô tả",
  unit: "Đơn vị tính",
  quantity: "Số lượng",
  customer_unit_price: "Đơn giá khách hàng",
  customer_amount: "Thành tiền khách hàng",
  reference_value: "Giá trị tham khảo",
  appraiser_proposed_price: "Giá đề xuất thẩm định",
  evidence_note: "Ghi chú chứng cứ",
  ignore: "Không ánh xạ",
};
const ROLES = Object.keys(ROLE_LABELS) as SemanticRole[];
const SOURCE_STATE_LABELS: Record<string, string> = {
  available: "Sẵn sàng",
  pending: "Đang xử lý",
  failed: "Xử lý thất bại",
  orphaned: "Không còn hiện hành",
};

function unknownResult(error: unknown): boolean {
  return !(error instanceof ApiError) || error.status === 0 || error.status === 408 ||
    error.status === 429 || error.status >= 500;
}

function mappingConflictMessage(error: ApiError): string {
  if (["mapping_profile_conflict", "mapping_profile_stale"].includes(error.code || "")) {
    return "Ký ức ánh xạ đã thay đổi hoặc có nhiều mẫu hiện hành. Hãy đối soát ký ức trước khi tiếp tục.";
  }
  if (error.code === "mapping_usage_conflict") {
    return "Nguồn hoặc cấu trúc này đã có dữ liệu tạm. Hãy kiểm tra staging hiện hành trước khi tiếp tục.";
  }
  if (["mapping_proposal_resolved", "mapping_proposal_not_current"].includes(error.code || "")) {
    return "Đề xuất ánh xạ không còn hiệu lực. Hãy rà soát nguồn hiện hành và tạo đề xuất mới.";
  }
  if (["mapping_source_not_current", "mapping_source_not_available", "mapping_materialization_stale",
    "mapping_batch_not_current", "mapping_candidate_invalid"].includes(error.code || "")) {
    return "Nguồn hoặc cấu trúc hiện hành đã thay đổi. Hãy rà soát lại tệp và vùng bảng.";
  }
  if (["mapping_official_intake_closed", "mapping_batch_already_applied"].includes(error.code || "")) {
    return "Hồ sơ đã chuyển sang thẩm định chính thức. Không thể tiếp tục ánh xạ sơ bộ.";
  }
  if (error.code === "mapping_customer_required") {
    return "Chưa có khách hàng để ghi nhớ ánh xạ. Hãy chọn không lưu ký ức hoặc hoàn tất bước gắn khách hàng có thẩm quyền.";
  }
  if (error.code === "idempotency_key_reused") {
    return "Mã thao tác đã gắn với nội dung khác. Hãy đối soát trạng thái máy chủ trước khi tiếp tục.";
  }
  if (["mapping_selection_revision_conflict", "mapping_selection_not_current"].includes(error.code || "")) {
    return "Phiên bản chọn ánh xạ đã thay đổi. Hãy rà soát quyền chọn hiện hành trước khi tiếp tục.";
  }
  return "Trạng thái ánh xạ có xung đột. Hãy rà soát nguồn, đề xuất và quyền chọn hiện hành trước khi tiếp tục.";
}

function mappingFieldsValid(fields: MappingField[]): boolean {
  const roles = fields.map((field) => field.semantic_role).filter((role) => role !== "ignore");
  return roles.filter((role) => role === "raw_asset_name").length === 1 &&
    new Set(roles).size === roles.length;
}

function sourceIsCurrent(data: IntakeData): boolean {
  return Boolean(
    data.batch && data.recovery && data.source &&
    data.recovery.current_batch_id === data.batch.id &&
    data.recovery.current_source_artifact_id === data.source.id &&
    data.source.import_batch_id === data.batch.id &&
    data.source.state === "available"
  );
}

export function PreliminaryIntakePage({
  projectRef,
  onNavigate,
  onSessionExpired,
}: {
  projectRef: string;
  onNavigate: (path: string) => void;
  onSessionExpired: () => void;
}) {
  const resolved = useResolvedProject(projectRef);
  if (resolved.state === "loading" || resolved.state === "idle") return <LoadingState message="Đang xác định yêu cầu sơ bộ…" />;
  if (resolved.state === "error" || !resolved.projectId) {
    return <ErrorState title={resolved.error?.title || "Chưa thể mở yêu cầu"} message={resolved.error?.message || "Không thể xác định hồ sơ."} onRetry={resolved.retry} />;
  }
  return (
    <ResolvedPreliminaryIntake
      key={resolved.projectId}
      projectId={resolved.projectId}
      onNavigate={onNavigate}
      onSessionExpired={onSessionExpired}
    />
  );
}

function ResolvedPreliminaryIntake({
  projectId,
  onNavigate,
  onSessionExpired,
}: {
  projectId: string;
  onNavigate: (path: string) => void;
  onSessionExpired: () => void;
}) {
  const [data, setData] = useState<IntakeData | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error" | "sessionExpired" | "forbidden">("loading");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ text: string; tone: "info" | "warning" | "error" } | null>(null);
  const [uncertain, setUncertain] = useState(() => Boolean(readPending(projectId)));
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string | null>(null);
  const [candidateIndex, setCandidateIndex] = useState<number | null>(null);
  const [proposal, setProposal] = useState<MappingProposal | null>(null);
  const [fields, setFields] = useState<MappingField[]>([]);
  const [memoryScope, setMemoryScope] = useState<"none" | "customer">("none");
  const [supersedesProfileId, setSupersedesProfileId] = useState<string | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [replaceSource, setReplaceSource] = useState(false);

  const markUnknown = (pending: PendingUnknown) => {
    try { sessionStorage.setItem(pendingKey(projectId), JSON.stringify(pending)); } catch { /* Keep the in-memory lock. */ }
    setUncertain(true);
  };

  const setAccessState = (error: unknown): boolean => {
    if (!(error instanceof ApiError)) return false;
    if (error.status === 401) {
      setLoadState("sessionExpired");
      return true;
    }
    if (error.status === 403) {
      setLoadState("forbidden");
      return true;
    }
    return false;
  };

  const load = useCallback(async (): Promise<IntakeData | null> => {
    setLoadState("loading");
    try {
      const [project, batches] = await Promise.all([getProject(projectId), listPreliminaryBatches(projectId)]);
      const batch = project.current_preliminary_import_batch_id
        ? batches.find((item) => item.id === project.current_preliminary_import_batch_id) || null
        : null;
      const recovery = batch ? await getMappingRecovery(projectId, batch.id) : null;
      const artifacts = batch ? await listSourceArtifacts(projectId, batch.id) : [];
      const source = batch && recovery?.current_source_artifact_id
        ? await getSourceArtifact(projectId, batch.id, recovery.current_source_artifact_id)
        : null;
      const snapshots = batch && source?.state === "available"
        ? await listStructureSnapshots(projectId, batch.id, source.id)
        : [];
      const next = { project, batches, batch, recovery, source, artifacts, snapshots };
      setData(next);
      const pending = readPending(projectId);
      if (pending) {
        if (pendingResolved(pending, next)) {
          try { sessionStorage.removeItem(pendingKey(projectId)); } catch { /* In-memory state still updates. */ }
          setUncertain(false);
          if (pendingSuperseded(pending, next)) {
            setNotice({ tone: "warning", text: "Quyền chọn đã thay đổi. Lệnh trước không còn áp dụng; hãy rà soát trạng thái hiện hành trước khi tiếp tục." });
          }
        } else {
          setUncertain(true);
        }
      }
      setSelectedSnapshotId((previous) => {
        if (recovery?.status === "selected_unmaterialized" || recovery?.status === "materialized") {
          return recovery.selected_structure_snapshot_id;
        }
        return snapshots.some((item) => item.id === previous) ? previous : null;
      });
      setCandidateIndex(null);
      setProposal(null);
      setReviewed(false);
      setSupersedesProfileId(null);
      setReplaceSource(false);
      if (!project.customer_id) setMemoryScope("none");
      setLoadState("ready");
      return next;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) setLoadState("sessionExpired");
      else if (error instanceof ApiError && error.status === 403) setLoadState("forbidden");
      else setLoadState("error");
      return null;
    }
  }, [projectId]);

  useEffect(() => { void load(); }, [load]);

  const refresh = async () => {
    setNotice(null);
    const pending = readPending(projectId);
    const fresh = await load();
    if (pending?.kind === "confirmation" && pending.confirmationPayload && fresh?.batch &&
      fresh.batch.id === pending.batchId && sourceIsCurrent(fresh) &&
      !fresh.recovery?.official_intake_closed &&
      fresh.recovery?.selection_revision === pending.confirmationPayload.expected_selection_revision &&
      fresh.source?.id === pending.confirmationPayload.mapping_snapshot?.source?.source_artifact_id &&
      (pending.confirmationPayload.memory_scope === "none" || Boolean(fresh.project.customer_id)) &&
      fresh.recovery?.recent_proposals.some((item) =>
        item.proposal_decision_id === pending.confirmationPayload?.proposal_decision_id &&
        item.source_artifact_id === fresh.source?.id &&
        item.structure_snapshot_id === pending.confirmationPayload?.mapping_snapshot?.structure?.structure_snapshot_id &&
        item.terminal_outcomes.length === 0)) {
      setBusy("recovery");
      try {
        await confirmMapping(projectId, fresh.batch.id, pending.confirmationPayload);
        const verified = await load();
        if (verified?.recovery?.selected_command_id === pending.confirmationPayload.command_id) {
          try { sessionStorage.removeItem(pendingKey(projectId)); } catch { /* In-memory state still updates. */ }
          setUncertain(false);
          setNotice({ tone: "info", text: "Đã khôi phục đúng yêu cầu xác nhận trước. Ánh xạ hiện hành lấy từ máy chủ." });
        }
      } catch (error) {
        if (setAccessState(error)) return;
        setNotice({ tone: "warning", text: "Chưa thể khôi phục xác nhận cũ. Hãy kiểm tra trạng thái máy chủ trước khi tiếp tục." });
      } finally {
        setBusy(null);
      }
      return;
    }
    if (pending?.kind === "materialization" && pending.materializationPayload && fresh?.batch &&
      fresh.batch.id === pending.batchId && sourceIsCurrent(fresh) &&
      fresh.recovery?.status === "selected_unmaterialized" &&
      !fresh.recovery.official_intake_closed &&
      fresh.recovery.selected_confirmation_decision_id === pending.materializationPayload.confirmation_decision_id &&
      fresh.recovery.selection_revision === pending.materializationPayload.expected_selection_revision) {
      setBusy("recovery");
      try {
        await materializeMapping(projectId, fresh.batch.id, pending.materializationPayload);
        const verified = await load();
        if (verified?.recovery?.status === "materialized" &&
          verified.recovery.selected_confirmation_decision_id === pending.materializationPayload.confirmation_decision_id) {
          try { sessionStorage.removeItem(pendingKey(projectId)); } catch { /* In-memory state still updates. */ }
          setUncertain(false);
          setNotice({ tone: "info", text: "Đã khôi phục đúng yêu cầu tạo dữ liệu tạm trước. Danh mục chính thức chưa thay đổi." });
        }
      } catch (error) {
        if (setAccessState(error)) return;
        setNotice({ tone: "warning", text: "Chưa thể khôi phục lần tạo dữ liệu tạm cũ. Hãy kiểm tra trạng thái máy chủ trước khi tiếp tục." });
      } finally {
        setBusy(null);
      }
      return;
    }
    if (pending?.kind === "proposal" && pending.proposalPayload && fresh?.batch &&
      fresh.recovery?.recent_proposals.some((item) => item.command_id === pending.commandId &&
        item.terminal_outcomes.length === 0)) {
      try {
        const result = await proposeMapping(projectId, fresh.batch.id, pending.proposalPayload);
        setProposal(result);
        setSupersedesProfileId(null);
        setSelectedSnapshotId(result.structure_snapshot_id);
        setCandidateIndex(result.mapping_snapshot.candidate.candidate_index);
        setFields(result.mapping_snapshot.fields.map((field) => ({ ...field })));
        setReviewed(false);
        try { sessionStorage.removeItem(pendingKey(projectId)); } catch { /* In-memory state still updates. */ }
        setUncertain(false);
        setNotice({ tone: "info", text: "Đã khôi phục đề xuất từ đúng yêu cầu trước. Hãy rà soát từng cột." });
      } catch (error) {
        if (setAccessState(error)) return;
        setNotice({ tone: "warning", text: "Chưa thể khôi phục đề xuất cũ. Không gửi yêu cầu ánh xạ mới khi kết quả chưa rõ." });
      }
    }
  };

  const handleUpload = async () => {
    if (!data || !selectedFile || loadState !== "ready" || busy || uncertain || data.artifacts.some((item) => item.state === "pending")) return;
    setBusy("upload");
    setNotice(null);
    let phase: "batch" | "source" = "batch";
    const previousSourceId = data.recovery?.current_source_artifact_id;
    try {
      let batchId = data.batch?.id;
      if (!batchId) {
        const created = await createPreliminaryBatch(projectId, selectedFile.name);
        const project = await getProject(projectId);
        if (project.current_preliminary_import_batch_id !== created.id) {
          await load();
          setNotice({ tone: "warning", text: "Batch hiện hành đã thay đổi. Hãy kiểm tra trước khi tải tệp." });
          return;
        }
        batchId = created.id;
      }
      phase = "source";
      const uploaded = await uploadSourceArtifact(projectId, batchId, selectedFile);
      const fresh = await load();
      setSelectedFile(null);
      setReplaceSource(false);
      if (fresh?.recovery?.current_source_artifact_id === uploaded.id) {
        setNotice({ tone: "info", text: "Tệp nguồn đã được ghi nhận. Tiếp tục phân tích cấu trúc." });
      } else {
        setNotice({ tone: "warning", text: "Tệp nguồn hiện hành đã thay đổi. Hãy xem trạng thái mới trước khi tiếp tục." });
      }
    } catch (error) {
      const fresh = await load();
      if (setAccessState(error)) return;
      if (error instanceof ApiError && error.status === 409) {
        setNotice({ tone: "warning", text: "Dữ liệu hiện hành đã thay đổi. Hãy xem lại batch và tệp nguồn." });
      } else if (unknownResult(error)) {
        if (phase === "batch" && fresh?.batch) {
          setNotice({ tone: "info", text: "Batch hiện hành đã được ghi nhận. Hãy chọn tệp để tiếp tục." });
        } else if (phase === "source" && fresh?.recovery && fresh.source?.state === "available" &&
          fresh.recovery.current_source_artifact_id !== previousSourceId) {
          setNotice({ tone: "warning", text: "Tệp nguồn hiện hành đã thay đổi. Hãy kiểm tra tệp đang hiển thị trước khi tiếp tục." });
        } else {
          markUnknown(phase === "batch"
            ? { kind: "batch" }
            : { kind: "source", previousSourceId });
          setNotice({ tone: "warning", text: "Chưa xác định thao tác đã hoàn tất hay chưa. Hãy kiểm tra trạng thái máy chủ; không tải lại tệp ngay." });
        }
      } else {
        setNotice({ tone: "error", text: "Tệp Excel chưa được chấp nhận. Hãy kiểm tra định dạng và quyền truy cập." });
      }
    } finally {
      setBusy(null);
    }
  };

  const handleAnalyze = async () => {
    if (!data?.batch || !data.source || loadState !== "ready" || busy || uncertain || !sourceIsCurrent(data)) return;
    setBusy("structure");
    setNotice(null);
    try {
      const created = await analyzeStructure(projectId, data.batch.id, data.source.id);
      const fresh = await load();
      if (fresh && !fresh.snapshots.some((item) => item.id === created.id)) {
        setData({ ...fresh, snapshots: [...fresh.snapshots, created] });
      }
      setSelectedSnapshotId(created.id);
      setNotice({ tone: "info", text: "Đã phân tích cấu trúc. Hãy xem vùng bảng và chọn cột trước khi tạo đề xuất." });
    } catch (error) {
      const fresh = await load();
      if (setAccessState(error)) return;
      if (unknownResult(error)) {
        if (fresh?.snapshots.some((item) => !data.snapshots.some((known) => known.id === item.id))) {
          setNotice({ tone: "info", text: "Máy chủ đã ghi nhận bản phân tích mới. Hãy chọn vùng bảng để tiếp tục." });
        } else {
          markUnknown({ kind: "structure", knownSnapshotIds: data.snapshots.map((item) => item.id) });
          setNotice({ tone: "warning", text: "Chưa xác định bản phân tích đã được tạo hay chưa. Hãy kiểm tra lại trước khi phân tích tiếp." });
        }
      } else {
        setNotice({ tone: "error", text: "Chưa thể phân tích cấu trúc tệp nguồn hiện hành." });
      }
    } finally {
      setBusy(null);
    }
  };

  const handlePropose = async () => {
    if (!data?.batch || !data.source || !selectedSnapshotId || candidateIndex === null || loadState !== "ready" || busy || uncertain ||
      (data.recovery?.status === "selected_recovery_required" &&
        selectedSnapshotId === data.recovery.selected_structure_snapshot_id)) return;
    const commandId = crypto.randomUUID();
    const payload = {
      source_artifact_id: data.source.id,
      structure_snapshot_id: selectedSnapshotId,
      candidate_index: candidateIndex,
      command_id: commandId,
    };
    setBusy("proposal");
    setNotice(null);
    try {
      const result = await proposeMapping(projectId, data.batch.id, payload);
      const fresh = await load();
      if (!fresh) {
        markUnknown({ kind: "proposal", commandId, proposalPayload: payload });
        setNotice({ tone: "warning", text: "Đề xuất đã được ghi nhận nhưng chưa thể kiểm tra nguồn hiện hành. Hãy kiểm tra trạng thái trước khi xác nhận." });
        return;
      }
      if (fresh.recovery?.current_source_artifact_id !== result.source_artifact_id) {
        setNotice({ tone: "warning", text: "Tệp nguồn đã thay đổi. Hãy xem lại trước khi xác nhận ánh xạ." });
        return;
      }
      setProposal(result);
      setSupersedesProfileId(null);
      setSelectedSnapshotId(result.structure_snapshot_id);
      setCandidateIndex(result.mapping_snapshot.candidate.candidate_index);
      setFields(result.mapping_snapshot.fields.map((field) => ({ ...field })));
      setReviewed(false);
    } catch (error) {
      const fresh = await load();
      if (setAccessState(error)) return;
      if (unknownResult(error) && fresh?.recovery?.recent_proposals.some((item) => item.command_id === commandId)) {
        try {
          const result = await proposeMapping(projectId, data.batch.id, payload);
          setProposal(result);
          setSupersedesProfileId(null);
          setSelectedSnapshotId(result.structure_snapshot_id);
          setCandidateIndex(result.mapping_snapshot.candidate.candidate_index);
          setFields(result.mapping_snapshot.fields.map((field) => ({ ...field })));
          setReviewed(false);
          setNotice({ tone: "info", text: "Đã khôi phục đề xuất từ yêu cầu trước. Hãy rà soát từng cột." });
          return;
        } catch (replayError) {
          if (setAccessState(replayError)) return;
          // The same command identity may no longer be replayable after authority changes.
        }
      }
      if (unknownResult(error)) {
        markUnknown({ kind: "proposal", commandId, proposalPayload: payload });
        setNotice({ tone: "warning", text: "Chưa xác định đề xuất đã được tạo hay chưa. Hãy kiểm tra trạng thái trước khi tạo yêu cầu mới." });
      } else if (error instanceof ApiError && error.status === 409) {
        setNotice({ tone: "warning", text: mappingConflictMessage(error) });
      } else {
        setNotice({ tone: "error", text: "Chưa thể tạo đề xuất ánh xạ cho vùng bảng đã chọn." });
      }
    } finally {
      setBusy(null);
    }
  };

  const handleConfirm = async () => {
    if (!data?.batch || !data.recovery || !proposal || !reviewed || !mappingFieldsValid(fields) || loadState !== "ready" || busy || uncertain) return;
    const commandId = crypto.randomUUID();
    const mappingSnapshot: MappingSnapshot = { ...proposal.mapping_snapshot, fields: fields.map((field) => ({ ...field })) };
    const payload: Parameters<typeof confirmMapping>[2] = {
      proposal_decision_id: proposal.decision_id,
      mapping_snapshot: mappingSnapshot,
      memory_scope: data.project.customer_id ? memoryScope : "none",
      supersedes_profile_id: data.project.customer_id && memoryScope === "customer"
        ? supersedesProfileId : null,
      command_id: commandId,
      expected_selection_revision: data.recovery.selection_revision,
    };
    setBusy("confirmation");
    setNotice(null);
    try {
      await confirmMapping(projectId, data.batch.id, payload);
      const fresh = await load();
      setNotice({
        tone: fresh?.recovery?.selected_command_id === commandId ? "info" : "warning",
        text: fresh?.recovery?.selected_command_id === commandId
          ? "Ánh xạ đã được xác nhận bởi người dùng. Chưa tạo dữ liệu tạm."
          : "Quyền chọn ánh xạ đã thay đổi. Hãy xem trạng thái hiện hành.",
      });
    } catch (error) {
      const fresh = await load();
      if (setAccessState(error)) return;
      if (fresh?.recovery?.selected_command_id === commandId) {
        setNotice({ tone: "info", text: "Máy chủ đã ghi nhận xác nhận ánh xạ. Chưa tạo dữ liệu tạm." });
      } else if (error instanceof ApiError && error.status === 409) {
        setNotice({ tone: "warning", text: mappingConflictMessage(error) });
      } else if (unknownResult(error)) {
        markUnknown({ kind: "confirmation", commandId, batchId: data.batch.id, confirmationPayload: payload });
        setNotice({ tone: "warning", text: "Chưa xác định xác nhận đã được ghi nhận hay chưa. Hãy kiểm tra trạng thái máy chủ; không gửi quyết định mới ngay." });
      } else {
        setNotice({ tone: "error", text: "Chưa thể xác nhận ánh xạ. Hãy kiểm tra các vai trò cột và quyền truy cập." });
      }
    } finally {
      setBusy(null);
    }
  };

  const handleMaterialize = async () => {
    const recovery = data?.recovery;
    if (!data?.batch || !recovery?.selected_confirmation_decision_id ||
      recovery.status !== "selected_unmaterialized" || loadState !== "ready" || busy || uncertain) return;
    const commandId = crypto.randomUUID();
    const payload: Parameters<typeof materializeMapping>[2] = {
      confirmation_decision_id: recovery.selected_confirmation_decision_id,
      expected_selection_revision: recovery.selection_revision,
      command_id: commandId,
    };
    setBusy("materialization");
    setNotice(null);
    try {
      await materializeMapping(projectId, data.batch.id, payload);
      const fresh = await load();
      setNotice({
        tone: fresh?.recovery?.status === "materialized" ? "info" : "warning",
        text: fresh?.recovery?.status === "materialized"
          ? "Ánh xạ đã tạo dữ liệu tạm trong staging. Danh mục thẩm định chính thức chưa được cập nhật."
          : "Trạng thái ánh xạ đã thay đổi. Hãy kiểm tra dữ liệu hiện hành.",
      });
    } catch (error) {
      const fresh = await load();
      if (setAccessState(error)) return;
      if (fresh?.recovery?.status === "materialized" &&
        fresh.recovery.selected_confirmation_decision_id === recovery.selected_confirmation_decision_id) {
        setNotice({ tone: "info", text: "Máy chủ đã tạo dữ liệu tạm trong staging. Danh mục thẩm định chính thức chưa được cập nhật." });
      } else if (error instanceof ApiError && error.status === 409) {
        setNotice({ tone: "warning", text: mappingConflictMessage(error) });
      } else if (unknownResult(error)) {
        markUnknown({
          kind: "materialization", batchId: data.batch.id,
          confirmationId: recovery.selected_confirmation_decision_id, materializationPayload: payload,
        });
        setNotice({ tone: "warning", text: "Chưa xác định dữ liệu tạm đã được tạo hay chưa. Hãy kiểm tra trạng thái máy chủ; không gửi yêu cầu mới ngay." });
      } else {
        setNotice({ tone: "error", text: "Chưa thể tạo dữ liệu tạm từ ánh xạ đã xác nhận." });
      }
    } finally {
      setBusy(null);
    }
  };

  const loadMoreSnapshots = async () => {
    if (!data?.batch || !data.source || !data.snapshots.length || loadState !== "ready" || busy || uncertain) return;
    setBusy("snapshots");
    try {
      const cursor = data.snapshots[data.snapshots.length - 1].snapshot_version;
      const more = await listStructureSnapshots(projectId, data.batch.id, data.source.id, cursor);
      setData({ ...data, snapshots: [...data.snapshots, ...more.filter((item) => !data.snapshots.some((existing) => existing.id === item.id))] });
    } catch (error) {
      if (setAccessState(error)) return;
      setNotice({ tone: "error", text: "Chưa thể tải thêm bản phân tích cấu trúc." });
    } finally {
      setBusy(null);
    }
  };

  if (!data && loadState === "loading") return <LoadingState message="Đang tải nguồn và ánh xạ hiện hành…" />;
  if (!data && loadState === "error") return <ErrorState title="Chưa thể tải yêu cầu sơ bộ" message="Không thể đọc trạng thái nhập liệu hiện hành." onRetry={() => void load()} />;
  if (loadState === "sessionExpired") return <ErrorState title="Phiên làm việc đã hết hạn" message="Vui lòng đăng nhập lại để tiếp tục." onRetry={onSessionExpired} retryLabel="Đăng nhập lại" />;
  if (loadState === "forbidden") return <ErrorState title="Chưa có quyền truy cập" message="Tài khoản hiện tại không có quyền xem hoặc xử lý yêu cầu này." />;
  if (!data) return null;

  const noBatch = !data.project.current_preliminary_import_batch_id && data.batches.length === 0;
  const unresolvedBatch = !data.project.current_preliminary_import_batch_id && data.batches.length > 0;
  const staleBatch = Boolean(data.project.current_preliminary_import_batch_id && !data.batch);
  const recovery = data.recovery;
  const currentSource = sourceIsCurrent(data);
  const pendingUpload = data.artifacts.some((item) => item.state === "pending");
  const structureReview = currentSource && (
    recovery?.status === "no_selection" || recovery?.status === "unresolved_legacy_history" ||
    recovery?.status === "selected_recovery_required" || recovery?.status === "stale_lineage"
  );
  const selectedSnapshot = data.snapshots.find((item) => item.id === selectedSnapshotId) || null;
  const canPropose = structureReview && selectedSnapshot && candidateIndex !== null &&
    selectedSnapshot.structure_payload.candidates[candidateIndex] &&
    (recovery?.status !== "selected_recovery_required" ||
      selectedSnapshot.id !== recovery.selected_structure_snapshot_id) && loadState === "ready" && !busy && !uncertain;
  const mustAnalyze = data.snapshots.length === 0 ||
    (recovery?.status === "selected_recovery_required" &&
      selectedSnapshotId === recovery.selected_structure_snapshot_id);
  const controlsBlocked = loadState !== "ready" || Boolean(busy) || uncertain || pendingUpload;

  return (
    <main className="precase-intake-page">
      <header className="precase-intake-header">
        <div>
          <p>Quản lý yêu cầu sơ bộ / Upload & Mapping Excel</p>
          <h1>{data.project.name}</h1>
          <span>{data.project.code} · Dữ liệu Excel chỉ vào vùng dữ liệu tạm sau khi bạn xác nhận ánh xạ.</span>
        </div>
        <button className="valora-button valora-button--secondary" onClick={() => onNavigate(APP_ROUTES.preliminaryRequestManagement)} type="button">Về danh sách</button>
      </header>

      {loadState === "loading" && <p className="precase-intake-refresh" role="status">Đang cập nhật trạng thái máy chủ…</p>}
      {loadState === "error" && <ErrorState scope="section" title="Chưa thể cập nhật trạng thái" message="Thông tin đang hiển thị có thể đã cũ." onRetry={() => void load()} />}
      {notice && <div className={`valora-message valora-message--${notice.tone}`} role="status">{notice.text}</div>}
      {uncertain && (
        <section className="precase-intake-blocked" role="alert">
          <h2>Kết quả thao tác chưa rõ</h2>
          <p>Kiểm tra lại trạng thái máy chủ trước khi gửi thêm yêu cầu. Nếu trạng thái vẫn chưa rõ, liên hệ quản trị để đối soát thao tác.</p>
          <button className="valora-button valora-button--primary" onClick={() => void refresh()} type="button">Kiểm tra trạng thái</button>
        </section>
      )}

      <section className="precase-intake-summary valora-panel" aria-label="Nguồn hiện hành">
        <div className="valora-panel__header">Nguồn hiện hành</div>
        <div className="valora-panel__body">
          <div><span>Batch</span><strong>{data.batch?.id || (unresolvedBatch ? "Chưa xác định" : "Chưa có")}</strong></div>
          <div><span>Tệp Excel</span><strong>{data.source?.original_filename || "Chưa có"}</strong></div>
          <div><span>Trạng thái nguồn</span><strong>{data.source ? SOURCE_STATE_LABELS[data.source.state] || data.source.state : "Chưa có nguồn hiện hành"}</strong></div>
          <div><span>Phiên bản chọn ánh xạ</span><strong>{recovery?.selection_revision ?? "—"}</strong></div>
          {data.source && !recovery?.official_intake_closed &&
            <button className="valora-button valora-button--secondary" disabled={controlsBlocked || pendingUpload} onClick={() => setReplaceSource(true)} type="button">Tải tệp Excel khác</button>}
        </div>
      </section>

      {unresolvedBatch && <BlockedState title="Chưa xác định batch hiện hành" message="Yêu cầu còn batch đã lưu nhưng Project chưa có con trỏ batch hiện hành. Cần xử lý theo quy trình có thẩm quyền trước khi nhập thêm tệp." />}
      {staleBatch && <BlockedState title="Batch hiện hành không khả dụng" message="Con trỏ batch của Project không khớp dữ liệu có thể đọc. Hãy kiểm tra lại hoặc yêu cầu hỗ trợ." onRefresh={() => void refresh()} />}
      {recovery?.official_intake_closed && <BlockedState title="Yêu cầu đã chuyển sang thẩm định chính thức" message="Lịch sử nhập liệu chỉ còn để tham khảo. Không thể tạo ánh xạ hoặc dữ liệu tạm mới." onOverview={() => onNavigate(projectOverviewPath(projectId))} />}

      {pendingUpload && <BlockedState title="Tệp đang được xử lý" message="Một lần tải tệp vẫn đang chờ máy chủ hoàn tất. Hãy kiểm tra trạng thái trước khi gửi tệp mới." onRefresh={() => void refresh()} />}
      {!unresolvedBatch && !staleBatch && !pendingUpload && !recovery?.official_intake_closed && (noBatch || !data.source || replaceSource) && (
        <section className="precase-intake-step valora-panel">
          <div className="valora-panel__header">1 · Tải tệp Excel</div>
          <div className="valora-panel__body">
            <p>{noBatch ? "Chưa có batch nhập liệu. Khi tải tệp, hệ thống sẽ tạo batch đầu tiên." : data.source ? "Tệp mới sẽ trở thành nguồn hiện hành sau khi máy chủ chấp nhận; ánh xạ cũ có thể hết hiệu lực." : "Batch hiện hành chưa có tệp nguồn."}</p>
            <label className="precase-file-field">Tệp Excel (.xlsx hoặc .xls)
              <input accept=".xlsx,.xls" disabled={controlsBlocked} onChange={(event) => setSelectedFile(event.target.files?.[0] || null)} type="file" />
            </label>
            <button className="valora-button valora-button--primary" disabled={!selectedFile || controlsBlocked} onClick={() => void handleUpload()} type="button">
              {busy === "upload" ? "Đang tải tệp…" : "Tải tệp Excel"}
            </button>
            {replaceSource && <button className="valora-button valora-button--secondary" disabled={controlsBlocked} onClick={() => {
              setReplaceSource(false);
              setSelectedFile(null);
            }} type="button">Hủy thay tệp</button>}
          </div>
        </section>
      )}

      {data.source && !currentSource && !recovery?.official_intake_closed && (
        <BlockedState title="Tệp nguồn chưa sẵn sàng" message="Tệp hiện hành chưa ở trạng thái khả dụng hoặc không khớp batch hiện hành. Hãy kiểm tra lại; không dùng nguồn cũ để ánh xạ." onRefresh={() => void refresh()} />
      )}
      {recovery?.status === "stale_lineage" && <BlockedState title="Ánh xạ không còn khớp nguồn hiện hành" message="Nguồn, cấu trúc hoặc quyền chọn đã thay đổi. Hãy rà soát lại cấu trúc nguồn hiện hành và tạo đề xuất mới." />}

      {structureReview && !replaceSource && !recovery?.official_intake_closed && (
        <section className="precase-intake-step valora-panel">
          <div className="valora-panel__header">2 · Rà soát cấu trúc workbook</div>
          <div className="valora-panel__body">
            {recovery?.status === "unresolved_legacy_history" && <p className="precase-intake-warning">Lịch sử ánh xạ cũ chưa có lựa chọn hiện hành được xác minh. Rà soát cấu trúc hiện tại hoặc phân tích lại trước khi đề xuất mới.</p>}
            {recovery?.status === "selected_recovery_required" && <p className="precase-intake-warning">Dữ liệu tạm cũ không còn chứng minh được quyền sở hữu. Cần bản cấu trúc mới, đề xuất mới và xác nhận mới.</p>}
            {data.snapshots.length === 0 ? (
              <p>Chưa có bản phân tích cấu trúc cho tệp nguồn hiện hành.</p>
            ) : (
              <>
                <label>Bản phân tích cấu trúc
                  <select className="valora-field" onChange={(event) => { setSelectedSnapshotId(event.target.value || null); setCandidateIndex(null); setProposal(null); }} value={selectedSnapshotId || ""}>
                    <option value="">Chọn bản phân tích để xem</option>
                    {data.snapshots.map((item) => <option key={item.id} value={item.id}>Phiên bản {item.snapshot_version} · {item.candidate_count} vùng bảng</option>)}
                  </select>
                </label>
                {data.snapshots.length >= 50 && <button className="valora-button valora-button--secondary" disabled={controlsBlocked} onClick={() => void loadMoreSnapshots()} type="button">Tải thêm bản phân tích</button>}
              </>
            )}
            {selectedSnapshot && (
              <div className="precase-candidate-list" role="group" aria-label="Vùng bảng được phát hiện">
                <h3>Vùng bảng được phát hiện</h3>
                {selectedSnapshot.structure_payload.candidates.length === 0 && <p>Không tìm thấy vùng bảng có thể ánh xạ. Hãy kiểm tra tệp hoặc phân tích lại.</p>}
                {selectedSnapshot.structure_payload.candidates.map((candidate, index) => (
                  <label className="precase-candidate" key={`${selectedSnapshot.id}-${index}`}>
                    <input checked={candidateIndex === index} name="workbook-candidate" onChange={() => { setCandidateIndex(index); setProposal(null); }} type="radio" />
                    <span><strong>{candidate.sheet_name} · dòng {candidate.header_start_row}–{candidate.candidate_table_bounds.max_row}</strong><small>Tiêu đề: {candidate.header_labels.map((item, position) => item || `Cột ${position + candidate.candidate_table_bounds.min_column} trống`).join(" · ")}</small></span>
                  </label>
                ))}
              </div>
            )}
            {recovery?.status === "selected_recovery_required" &&
              selectedSnapshotId === recovery.selected_structure_snapshot_id &&
              <p className="precase-intake-warning">Bản cấu trúc đã dùng cho lựa chọn cũ không đủ để phục hồi. Hãy phân tích lại cấu trúc.</p>}
            {!proposal && (
              <div className="precase-intake-actions">
                <button className="valora-button valora-button--primary" disabled={controlsBlocked || (!mustAnalyze && !canPropose)} onClick={() => void (mustAnalyze ? handleAnalyze() : handlePropose())} type="button">
                  {busy === "structure" || busy === "proposal" ? "Đang xử lý…" : mustAnalyze ? "Phân tích cấu trúc" : "Tạo đề xuất ánh xạ"}
                </button>
                {!mustAnalyze && <button className="valora-button valora-button--secondary" disabled={controlsBlocked} onClick={() => void handleAnalyze()} type="button">Phân tích lại cấu trúc</button>}
              </div>
            )}
          </div>
        </section>
      )}

      {proposal && structureReview && !replaceSource && (
        <section className="precase-intake-step valora-panel" data-mapping-stage="proposal">
          <div className="valora-panel__header">3 · Đề xuất ánh xạ · cần người xác nhận</div>
          <div className="valora-panel__body">
            <p>Đề xuất chưa có hiệu lực và chưa tạo dữ liệu tạm. Rà soát từng vai trò cột trước khi xác nhận.</p>
            {proposal.review_required && <p className="precase-intake-warning">Hệ thống yêu cầu rà soát kỹ các cột chưa rõ.</p>}
            <MappingTable fields={fields} onChange={(index, role) => {
              setFields((current) => current.map((field, position) => position === index ? { ...field, semantic_role: role } : field));
              setReviewed(false);
            }} />
            {!mappingFieldsValid(fields) && <p className="precase-intake-warning" role="alert">Cần đúng một cột tên tài sản; các vai trò khác chỉ được dùng một lần.</p>}
            {data.project.customer_id && (
              <label>Ghi nhớ ánh xạ cho khách hàng
                <select className="valora-field" onChange={(event) => {
                  setMemoryScope(event.target.value as "none" | "customer");
                  setSupersedesProfileId(null);
                  setReviewed(false);
                }} value={memoryScope}>
                  <option value="none">Không lưu ký ức ánh xạ</option>
                  <option value="customer">Lưu ký ức cho khách hàng đã gắn</option>
                </select>
              </label>
            )}
            {data.project.customer_id && memoryScope === "customer" &&
              (proposal.exact_profile_id || proposal.similar_profile_ids.length > 0) && (
                <label>Ký ức sẽ thay thế
                  <select className="valora-field" onChange={(event) => {
                    setSupersedesProfileId(event.target.value || null);
                    setReviewed(false);
                  }} value={supersedesProfileId || ""}>
                    <option value="">Không thay thế ký ức hiện có</option>
                    {proposal.exact_profile_id && <option value={proposal.exact_profile_id}>Ký ức hiện hành của mẫu này</option>}
                    {!proposal.exact_profile_id && proposal.similar_profile_ids.map((id, index) =>
                      <option key={id} value={id}>Ký ức tương tự {index + 1} · {id.slice(0, 8)}</option>)}
                  </select>
                  <small>Nếu vai trò cột khác ký ức hiện hành, chọn đúng ký ức cần thay thế. Máy chủ sẽ kiểm tra lại khi xác nhận.</small>
                </label>
              )}
            <label className="precase-review-check"><input checked={reviewed} onChange={(event) => setReviewed(event.target.checked)} type="checkbox" />Tôi đã rà soát vùng bảng và từng vai trò cột.</label>
            <button className="valora-button valora-button--primary" disabled={!reviewed || !mappingFieldsValid(fields) || controlsBlocked} onClick={() => void handleConfirm()} type="button">
              {busy === "confirmation" ? "Đang xác nhận…" : "Xác nhận ánh xạ"}
            </button>
          </div>
        </section>
      )}

      {recovery && !replaceSource && ["selected_unmaterialized", "materialized"].includes(recovery.status) && recovery.mapping_snapshot && (
        <section className="precase-intake-step valora-panel" data-mapping-stage="confirmed">
          <div className="valora-panel__header">Ánh xạ đã được người dùng xác nhận</div>
          <div className="valora-panel__body">
            <p>Quyền chọn hiện hành lấy từ máy chủ · phiên bản {recovery.selection_revision}. Đề xuất trước đó không tự trở thành dữ liệu tạm.</p>
            <MappingTable fields={recovery.mapping_snapshot.fields} />
            {recovery.status === "selected_unmaterialized" && (
              <button className="valora-button valora-button--primary" disabled={controlsBlocked} onClick={() => void handleMaterialize()} type="button">
                {busy === "materialization" ? "Đang tạo dữ liệu tạm…" : "Tạo dữ liệu tạm"}
              </button>
            )}
            {recovery.status === "materialized" && (
              <p className="precase-materialized" role="status">{recovery.materialized_asset_row_count === null
                ? "Đã tạo dữ liệu tạm; chưa xác định số dòng tài sản."
                : `Đã đưa ${recovery.materialized_asset_row_count} dòng tài sản vào vùng dữ liệu tạm.`} Chưa chuyển thành danh mục thẩm định chính thức.</p>
            )}
          </div>
        </section>
      )}
    </main>
  );
}

function MappingTable({ fields, onChange }: {
  fields: MappingField[];
  onChange?: (index: number, role: SemanticRole) => void;
}) {
  return (
    <div className="valora-table-shell precase-mapping-table">
      <table className="valora-table">
        <thead><tr><th scope="col">Cột</th><th scope="col">Tiêu đề nguồn</th><th scope="col">Vai trò dữ liệu</th></tr></thead>
        <tbody>
          {fields.map((field, index) => (
            <tr key={field.source_column_index}>
              <td>{field.source_column_letter}</td>
              <td>{field.original_header || "(Tiêu đề trống)"}</td>
              <td>{onChange ? (
                <select aria-label={`Vai trò cho cột ${field.source_column_letter}`} className="valora-field" onChange={(event) => onChange(index, event.target.value as SemanticRole)} value={field.semantic_role}>
                  {ROLES.map((role) => <option key={role} value={role}>{ROLE_LABELS[role]}</option>)}
                </select>
              ) : ROLE_LABELS[field.semantic_role]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BlockedState({ title, message, onRefresh, onOverview }: {
  title: string;
  message: string;
  onRefresh?: () => void;
  onOverview?: () => void;
}) {
  return (
    <section className="precase-intake-blocked" role="alert">
      <h2>{title}</h2>
      <p>{message}</p>
      {onRefresh && <button className="valora-button valora-button--primary" onClick={onRefresh} type="button">Kiểm tra trạng thái</button>}
      {onOverview && <button className="valora-button valora-button--primary" onClick={onOverview} type="button">Mở tổng quan hồ sơ</button>}
    </section>
  );
}
