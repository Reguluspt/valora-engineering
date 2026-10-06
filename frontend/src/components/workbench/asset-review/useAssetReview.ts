import { useCallback, useEffect, useRef, useState } from "react";
import { fetchCaseState, type CaseStateResponse } from "../../../api/caseState";
import { fetchAssetReviewReceipt, submitAssetReview, type LineCommandRequest,
  type LineCommandResponse, type ReviewDecision } from "../../../api/assetReview";
import type { AssetLineGridRow } from "../AssetGridTypes";

type Attempt = { lineId: string; commandId: string; contract: LineCommandRequest["contract_version"] };
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const KEYS = ["asset_review_line_validate_required", "asset_review_line_review_required", "asset_review_line_blocked"];

export function useAssetReview({ projectId, sessionId, sessionBlocked, rows, gridLoading,
  gridError, hasMore, loadingMore, loadMore, refreshGrid, selectLine, actorScope }: {
  projectId: string; sessionId?: string; sessionBlocked: boolean;
  rows: AssetLineGridRow[]; gridLoading: boolean; gridError: boolean;
  hasMore: boolean; loadingMore: boolean; loadMore: () => Promise<void>;
  refreshGrid: () => void; selectLine: (id: string) => void; actorScope?: string;
}) {
  // Retain only recovery identifiers across reload; never persist reason notes or authority tokens.
  const storageKey = actorScope ? `valora:asset-review:${actorScope}:${projectId}` : null;
  const [pending, setPending] = useState<Attempt | null>(() => {
    if (!storageKey) return null;
    try {
      const item = JSON.parse(sessionStorage.getItem(storageKey) || "null");
      return item && UUID.test(item.lineId) && UUID.test(item.commandId) &&
        ["asset-line-validation-v1", "asset-line-human-review-v1"].includes(item.contract) ? item : null;
    } catch { return null; }
  });
  const [projection, setProjection] = useState<CaseStateResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [result, setResult] = useState<LineCommandResponse | null>(null);
  const generation = useRef(0);
  const busyRef = useRef(false);
  const alive = useRef(true);
  const callbacks = useRef({ refreshGrid, selectLine });
  callbacks.current = { refreshGrid, selectLine };

  const retain = useCallback((attempt: Attempt | null) => {
    if (storageKey) {
      if (attempt) sessionStorage.setItem(storageKey, JSON.stringify(attempt));
      else sessionStorage.removeItem(storageKey);
    }
    if (alive.current) setPending(attempt);
  }, [storageKey]);

  const refresh = useCallback(async () => {
    const current = ++generation.current;
    setLoading(true);
    setProjection(null);
    try {
      const fresh = await fetchCaseState(projectId);
      if (alive.current && current === generation.current) setProjection(fresh);
    } catch {
      if (alive.current && current === generation.current)
        setNotice("Chưa thể tải trạng thái rà soát. Vui lòng tải lại; chưa thể gửi thao tác.");
    } finally {
      if (alive.current && current === generation.current) setLoading(false);
    }
  }, [projectId]);
  useEffect(() => {
    alive.current = true;
    void refresh();
    return () => { alive.current = false; ++generation.current; };
  }, [refresh, sessionId, sessionBlocked]);

  const action = projection?.next_action;
  const context = action?.context;
  const lineId = context?.line_id;
  const row = rows.find(item => item.project_asset_line_id === lineId);
  useEffect(() => {
    if (!lineId || gridLoading || gridError || loadingMore) return;
    if (row) callbacks.current.selectLine(lineId);
    else if (hasMore) void loadMore();
  }, [lineId, row, gridLoading, gridError, loadingMore, hasMore, loadMore]);

  const capability = projection?.capabilities?.find(item => item.stage === "ASSET_REVIEW");
  const scoped = Boolean(capability?.available && capability.provider_key === "asset_review_line_decision_v1" &&
    projection && action?.stage === "ASSET_REVIEW" &&
    KEYS.includes(action.semantic_route_key || "") && context?.kind === "line" &&
    context.project_id === projectId && context.case_version === projection.case_version &&
    context.confirmation_required === true && UUID.test(lineId || "") && row &&
    Number.isSafeInteger(context.line_row_version) && context.line_row_version! > 0 &&
    row.row_version === context.line_row_version &&
    /^[0-9a-f]{64}$/.test(projection.case_version));
  const ready = scoped && !loading && !busy && !pending && !gridLoading && !gridError &&
    Boolean(sessionId) && !sessionBlocked;
  const negative = action?.kind === "BLOCKER" && action.semantic_route_key === "asset_review_line_blocked" &&
    context?.contract_version === "asset-line-human-review-v1" &&
    ["review_flagged", "review_rejected"].includes(context?.reason_code || "");
  // For negative holds, the receipt proves only the just-confirmed validation's current generation.
  // After reload or a newer mutation, explicitly validate again before offering positive reversal.
  const validReversal = Boolean(negative && result?.result.validation_outcome === "valid" &&
    !result.historical && result.result.line_id === lineId &&
    result.result.proof_id === context?.validation_generation_id &&
    result.current_case_version === projection?.case_version);
  const canValidate = Boolean(ready && ((action?.kind === "PENDING" &&
    action.semantic_route_key === "asset_review_line_validate_required" &&
    context?.contract_version === "asset-line-validation-v1" &&
    context.reason_code !== "line_validation_warning") || negative ||
    (action?.kind === "BLOCKER" && context?.reason_code === "validation_invalid" &&
      context.contract_version === "asset-line-validation-v1")));
  const canReview = Boolean(ready && ((action?.kind === "PENDING" &&
    action.semantic_route_key === "asset_review_line_review_required" &&
    context?.contract_version === "asset-line-human-review-v1") || negative));
  const canAccept = canReview && (!negative || validReversal);

  const reconcile = useCallback(async (attempt: Attempt) => {
    try {
      const receipt = await fetchAssetReviewReceipt(projectId, attempt.lineId, attempt.commandId);
      if (receipt.result.command_id !== attempt.commandId || receipt.result.project_id !== projectId ||
          receipt.result.line_id !== attempt.lineId || receipt.result.contract_version !== attempt.contract)
        throw new Error("Receipt scope mismatch");
      if (alive.current) {
        setResult(receipt);
        setNotice("Đã tìm thấy kết quả đã ghi nhận. Kết quả này thuộc thao tác trước; trạng thái hiện tại được tải lại.");
      }
      retain(null);
    } catch (error) {
      const status = (error as { status?: number }).status;
      if (status === 404) {
        retain(null);
        if (alive.current) setNotice("Chưa tìm thấy kết quả đã ghi nhận. Tải lại trạng thái và xác nhận lại trước một thao tác mới.");
      } else if (alive.current) setNotice("Chưa xác định được kết quả. Kiểm tra kết quả trước khi gửi thao tác mới.");
    }
    if (alive.current) { callbacks.current.refreshGrid(); await refresh(); }
  }, [projectId, refresh, retain]);

  const recover = useCallback(async () => {
    if (!pending || busyRef.current) return;
    busyRef.current = true; setBusy(true);
    try { await reconcile(pending); }
    finally { busyRef.current = false; if (alive.current) setBusy(false); }
  }, [pending, reconcile]);

  const submit = async (decision: "validate" | ReviewDecision, reason: string,
    confirmedCaseVersion: string, confirmedLineId: string) => {
    if (busyRef.current || !context || !projection || !lineId ||
        confirmedCaseVersion !== projection.case_version || confirmedLineId !== lineId ||
        (decision === "validate" ? !canValidate : decision === "accepted" ? !canAccept : !canReview)) return;
    const trimmed = reason.trim();
    if (decision !== "validate" && ((decision !== "accepted" || context.prior_decision_id) && !trimmed ||
      [...trimmed].length > 2000)) return;
    const payload: LineCommandRequest = { command_id: crypto.randomUUID(), confirm: true,
      expected_row_version: context.line_row_version!, expected_case_version: projection.case_version,
      contract_version: decision === "validate" ? "asset-line-validation-v1" : "asset-line-human-review-v1" };
    if (decision !== "validate") Object.assign(payload, { target_review_status: decision,
      reason_note: trimmed || null, supersedes_decision_id: context.prior_decision_id || null });
    const attempt = { commandId: payload.command_id, lineId, contract: payload.contract_version };
    busyRef.current = true; setBusy(true); setNotice(""); setResult(null);
    try {
      retain(attempt);
    } catch {
      setNotice("Không thể lưu thông tin khôi phục kết quả. Chưa gửi thao tác; vui lòng thử lại.");
      busyRef.current = false; setBusy(false); return;
    }
    try {
      const response = await submitAssetReview(projectId, lineId, payload);
      if (alive.current) { setResult(response); setNotice("Đã ghi nhận thao tác. Đang cập nhật trạng thái từ hệ thống."); }
      retain(null);
      if (alive.current) { callbacks.current.refreshGrid(); await refresh(); }
    } catch (error) {
      const status = (error as { status?: number }).status || 0;
      if (status === 0 || status >= 500) await reconcile(attempt);
      else {
        retain(null);
        if (alive.current) {
          setNotice(status === 409 ? "Dữ liệu đã thay đổi hoặc chưa đủ điều kiện. Đã tải lại; vui lòng xem lại và xác nhận mới."
            : status === 401 ? "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại."
            : status === 403 ? "Bạn không có quyền thực hiện thao tác này."
            : status === 404 ? "Không tìm thấy dòng hoặc phiên làm việc còn hiệu lực. Vui lòng mở lại bàn làm việc."
            : "Không thể ghi nhận thao tác. Vui lòng kiểm tra dữ liệu và xác nhận lại.");
          callbacks.current.refreshGrid(); await refresh();
        }
      }
    } finally { busyRef.current = false; if (alive.current) setBusy(false); }
  };

  return { projection, action, context, row, loading, busy, notice, result, pending,
    canValidate, canReview, canAccept, negative, submit, recover,
    refreshProjection: refresh,
    refresh: () => { callbacks.current.refreshGrid(); return refresh(); } };
}
