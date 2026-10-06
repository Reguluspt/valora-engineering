import { useCallback, useEffect, useRef, useState } from "react";
import { fetchCaseState, type CaseStateResponse } from "../../../api/caseState";
import { fetchWorkbenchPreparation, fetchWorkbenchReceipt, submitWorkbench,
  type WorkbenchPreparation, type WorkbenchCommand, type WorkbenchReceipt } from "../../../api/assetWorkbench";

type Attempt = { commandId: string; contract: WorkbenchCommand["contract_version"] };
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const HASH = /^[0-9a-f]{64}$/;
export function preparationIsScoped(snapshot: WorkbenchPreparation, projectId: string, token: string) {
  return snapshot.project_id === projectId && snapshot.case_version === token && HASH.test(token) &&
    Number.isSafeInteger(snapshot.project_row_version) && snapshot.project_row_version > 0 &&
    UUID.test(snapshot.seal_id || "") && HASH.test(snapshot.authoritative_set_sha256 || "") &&
    Number.isSafeInteger(snapshot.membership_version) && snapshot.membership_version! > 0 &&
    (snapshot.prior_confirmation_id === null || UUID.test(snapshot.prior_confirmation_id)) &&
    snapshot.line_versions.length > 0 && new Set(snapshot.line_versions.map(v => v.line_id)).size === snapshot.line_versions.length &&
    snapshot.line_versions.every(v => UUID.test(v.line_id) && Number.isSafeInteger(v.row_version) && v.row_version > 0);
}
export function useAssetWorkbench({ projectId, sessionId, sessionBlocked, actorScope, onRefresh, revision }: {
  projectId: string; sessionId?: string; sessionBlocked: boolean; actorScope?: string; onRefresh: () => void;
  revision?: string;
}) {
  const storageKey = actorScope ? `valora:asset-workbench:${actorScope}:${projectId}` : null;
  const [pending, setPending] = useState<Attempt | null>(() => {
    if (!storageKey) return null;
    try {
      const item = JSON.parse(sessionStorage.getItem(storageKey) || "null");
      return item && UUID.test(item.commandId) && ["asset-workbench-confirmation-v1", "asset-workbench-withdrawal-v1"].includes(item.contract) ? item : null;
    } catch { return null; }
  });
  const [projection, setProjection] = useState<CaseStateResponse | null>(null);
  const [snapshot, setSnapshot] = useState<WorkbenchPreparation | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [receipt, setReceipt] = useState<WorkbenchReceipt | null>(null);
  const generation = useRef(0);
  const active = useRef(true);
  const locked = useRef(false);
  const refreshCallback = useRef(onRefresh);
  refreshCallback.current = onRefresh;
  const retain = useCallback((attempt: Attempt | null) => {
    if (storageKey) {
      if (attempt) sessionStorage.setItem(storageKey, JSON.stringify(attempt));
      else sessionStorage.removeItem(storageKey);
    }
    if (active.current) setPending(attempt);
  }, [storageKey]);
  const refresh = useCallback(async () => {
    const gen = ++generation.current;
    setLoading(true); setSnapshot(null); setProjection(null);
    const results = await Promise.allSettled([fetchCaseState(projectId), fetchWorkbenchPreparation(projectId)]);
    if (!active.current || gen !== generation.current) return;
    const [state, preparation] = results;
    if (state.status === "fulfilled") {
      setProjection(state.value);
      if (preparation.status === "fulfilled" && preparation.value.project_id === projectId &&
          preparation.value.case_version === state.value.case_version) setSnapshot(preparation.value);
      else if (preparation.status === "fulfilled") setNotice("Dữ liệu đã thay đổi trong lúc tải. Tải lại trước khi xác nhận.");
    } else setNotice("Chưa tải được trạng thái hồ sơ. Tải lại trước khi thực hiện thao tác.");
    setLoading(false);
  }, [projectId]);
  useEffect(() => {
    active.current = true; void refresh();
    return () => { active.current = false; ++generation.current; };
  }, [refresh, sessionId, sessionBlocked]);
  useEffect(() => { if (revision) void refresh(); }, [refresh, revision]);
  const scoped = Boolean(snapshot && projection && preparationIsScoped(snapshot, projectId, projection.case_version) &&
    (!revision || snapshot.case_version === revision) &&
    projection.capabilities.some(c => c.stage === "ASSET_WORKBENCH" && c.available && c.provider_key === "asset_workbench_confirmation_v1"));
  const enabled = scoped && !loading && !busy && !pending && Boolean(sessionId) && !sessionBlocked;
  const canConfirm = Boolean(enabled && snapshot?.can_confirm === true);
  const canWithdraw = Boolean(enabled && snapshot?.can_withdraw === true);
  const canEdit = Boolean(snapshot?.can_edit_description === true && !loading && !busy && !pending && sessionId && !sessionBlocked);
  const reconcile = useCallback(async (attempt: Attempt) => {
    try {
      const found = await fetchWorkbenchReceipt(projectId, attempt.commandId);
      if (found.result.project_id !== projectId || found.result.command_id !== attempt.commandId ||
          found.result.contract_version !== attempt.contract) throw new Error("Receipt scope mismatch");
      if (active.current) { setReceipt(found); setNotice("Đã tìm thấy kết quả thao tác trước. Trạng thái hiện tại được tải lại từ hệ thống."); }
      retain(null);
    } catch (error) {
      if ((error as { status?: number }).status === 404) {
        retain(null);
        if (active.current) setNotice("Chưa tìm thấy kết quả. Tải lại và xác nhận rõ ràng trước một thao tác mới.");
      } else if (active.current) setNotice("Chưa xác định được kết quả. Kiểm tra kết quả trước khi gửi thao tác mới.");
    }
    if (active.current) { refreshCallback.current(); await refresh(); }
  }, [projectId, refresh, retain]);
  const recover = async () => {
    if (!pending || locked.current) return;
    locked.current = true; setBusy(true);
    try { await reconcile(pending); }
    finally { locked.current = false; if (active.current) setBusy(false); }
  };
  const submit = async (operation: "confirm" | "withdraw", reason: string, confirmed: WorkbenchPreparation) => {
    if (locked.current || !snapshot || confirmed !== snapshot || (operation === "confirm" ? !canConfirm : !canWithdraw)) return;
    const required = operation === "withdraw" || snapshot.prior_confirmation_id !== null;
    const note = reason.trim();
    if (required && !note || [...note].length > 2000) return;
    const base = {
      command_id: crypto.randomUUID(), confirm: true as const, expected_project_row_version: snapshot.project_row_version,
      expected_case_version: snapshot.case_version, expected_seal_id: snapshot.seal_id!,
      expected_authoritative_set_sha256: snapshot.authoritative_set_sha256!, expected_membership_version: snapshot.membership_version!,
      expected_line_versions: snapshot.line_versions,
    };
    const command: WorkbenchCommand = operation === "confirm"
      ? { ...base, contract_version: "asset-workbench-confirmation-v1", reason_note: required ? note : null,
        supersedes_confirmation_id: snapshot.prior_confirmation_id }
      : { ...base, contract_version: "asset-workbench-withdrawal-v1", reason_note: note,
        expected_confirmation_id: snapshot.prior_confirmation_id! };
    const attempt = { commandId: command.command_id, contract: command.contract_version };
    locked.current = true; setBusy(true); setNotice(""); setReceipt(null);
    try { retain(attempt); }
    catch { setNotice("Chưa lưu được thông tin khôi phục. Chưa gửi thao tác."); locked.current = false; setBusy(false); return; }
    try {
      const result = await submitWorkbench(projectId, command);
      if (result.result.project_id !== projectId || result.result.command_id !== command.command_id ||
          result.result.contract_version !== command.contract_version) throw new Error("Receipt scope mismatch");
      if (active.current) { setReceipt(result); setNotice("Đã ghi nhận thao tác. Trạng thái hồ sơ đang được tải lại từ hệ thống."); }
      retain(null);
      if (active.current) { refreshCallback.current(); await refresh(); }
    } catch (error) {
      const status = (error as { status?: number }).status || 0;
      if (status === 0 || status >= 500) await reconcile(attempt);
      else {
        retain(null);
        if (active.current) {
          setNotice(status === 409 ? "Dữ liệu hoặc điều kiện đã thay đổi. Đã tải lại; xem lại và xác nhận mới."
            : status === 401 ? "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại."
            : status === 403 ? "Bạn chưa có quyền thực hiện thao tác này."
            : status === 404 ? "Hồ sơ hoặc phiên làm việc không còn khả dụng. Mở lại bàn làm việc."
            : "Chưa thể ghi nhận thao tác. Kiểm tra dữ liệu và điều kiện trước khi xác nhận lại.");
          refreshCallback.current(); await refresh();
        }
      }
    } finally { locked.current = false; if (active.current) setBusy(false); }
  };
  return { projection, snapshot, loading, busy, notice, receipt, pending, canConfirm, canWithdraw, canEdit,
    refresh, recover, submit };
}
