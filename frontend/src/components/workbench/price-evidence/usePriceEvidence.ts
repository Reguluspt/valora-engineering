import { useCallback, useEffect, useRef, useState } from "react";
import { fetchCaseState, type CaseStateResponse } from "../../../api/caseState";
import { EVIDENCE_CONTRACTS, fetchEvidencePreparation, fetchEvidenceWorkspace, fetchEvidenceReceipt, submitEvidence,
  type EvidenceIntent, type EvidencePreparation, type EvidenceWorkspace, type EvidenceReceipt } from "../../../api/priceEvidence";

type Attempt = { commandId: string; contract: string };
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const HASH = /^[0-9a-f]{64}$/;
export function evidenceScope(prep: EvidencePreparation, projectId: string, token: string) {
  return prep.project_id === projectId && prep.case_version === token && HASH.test(token) &&
    UUID.test(prep.seal_id || "") && UUID.test(prep.workbench_confirmation_id || "") &&
    HASH.test(prep.authoritative_set_sha256 || "") && Number.isSafeInteger(prep.project_row_version) && prep.project_row_version > 0 &&
    Number.isSafeInteger(prep.membership_version) && prep.membership_version! > 0 &&
    prep.lines.length > 0 && new Set(prep.lines.map(l => l.line_id)).size === prep.lines.length &&
    prep.lines.every(l => UUID.test(l.line_id) && HASH.test(l.proof_sha256) && Number.isSafeInteger(l.row_version) && l.row_version > 0);
}
export function evidenceError(status: number) {
  return status === 401 ? "Phiên đăng nhập đã hết hạn. Đăng nhập lại để tiếp tục."
    : status === 403 ? "Bạn chưa có quyền truy cập hoặc thao tác với dữ liệu này."
    : status === 404 ? "Ngữ cảnh không còn khả dụng. Mở lại hồ sơ để kiểm tra."
    : status === 409 ? "Dữ liệu hoặc điều kiện đã thay đổi. Tải lại và xem xét trước khi xác nhận mới."
    : status === 400 ? "Dữ liệu chưa phù hợp hợp đồng nguồn giá. Kiểm tra các trường và điều kiện thao tác."
    : "Chưa tải được dữ liệu nguồn giá. Tải lại để kiểm tra trạng thái.";
}
export function usePriceEvidence({ projectId, lineId, sessionId, sessionBlocked, actorScope, revision, onRefresh }: {
  projectId: string; lineId: string | null; sessionId?: string; sessionBlocked: boolean; actorScope?: string;
  revision?: string; onRefresh: () => void;
}) {
  const storageKey = `valora:price-evidence:${actorScope || "unknown"}:${projectId}`;
  const readAttempt = () => {
    try { const value = JSON.parse(sessionStorage.getItem(storageKey) || "null");
      return value && UUID.test(value.commandId) && Object.values(EVIDENCE_CONTRACTS).includes(value.contract) ? value : null;
    } catch { return null; }
  };
  const [pending, setPending] = useState<Attempt | null>(readAttempt);
  const [loadedScope, setLoadedScope] = useState(storageKey);
  const currentScope = useRef(storageKey); currentScope.current = storageKey;
  const inScope = () => active.current && currentScope.current === storageKey;
  const [projection, setProjection] = useState<CaseStateResponse | null>(null);
  const [snapshot, setSnapshot] = useState<EvidencePreparation | null>(null);
  const [workspace, setWorkspace] = useState<EvidenceWorkspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [receipt, setReceipt] = useState<EvidenceReceipt | null>(null);
  const active = useRef(true), locked = useRef(false), generation = useRef(0);
  const latest = useRef({ lineId, onRefresh }); latest.current = { lineId, onRefresh };
  const retain = (attempt: Attempt | null) => {
    if (attempt) sessionStorage.setItem(storageKey, JSON.stringify(attempt)); else sessionStorage.removeItem(storageKey);
    if (inScope()) setPending(attempt);
  };
  const refresh = useCallback(async () => {
    const gen = ++generation.current;
    setLoading(true); setError("");
    const selected = latest.current.lineId;
    const results = await Promise.allSettled([fetchCaseState(projectId), fetchEvidencePreparation(projectId), fetchEvidenceWorkspace(projectId, selected)]);
    if (!active.current || gen !== generation.current) return false;
    const denied = results.find(r => r.status === "rejected" && [401, 403, 404].includes(r.reason?.status));
    if (denied?.status === "rejected") {
      setProjection(null); setSnapshot(null); setWorkspace(null); setError(evidenceError(denied.reason.status));
      setLoading(false); return false;
    }
    const [state, prep, view] = results;
    if (state.status === "fulfilled" && prep.status === "fulfilled" && view.status === "fulfilled" &&
      prep.value.project_id === projectId && view.value.project_id === projectId && view.value.line_id === selected &&
      state.value.case_version === prep.value.case_version && prep.value.case_version === view.value.case_version) {
      setProjection(state.value); setSnapshot(prep.value); setWorkspace(view.value); setLoading(false); return true;
    }
    setError(results.some(r => r.status === "rejected") ? evidenceError(0) : evidenceError(409));
    setLoading(false); return false;
  }, [projectId, storageKey]);
  useEffect(() => { active.current = true; void refresh(); return () => { active.current = false; ++generation.current; }; }, [refresh]);
  useEffect(() => {
    setLoadedScope(storageKey); setPending(readAttempt()); setProjection(null); setSnapshot(null); setWorkspace(null);
    setReceipt(null); setNotice(""); setError("");
  }, [storageKey]);
  useEffect(() => { void refresh(); }, [refresh, lineId, sessionId, sessionBlocked, revision]);
  const enabled = Boolean(loadedScope === storageKey && !loading && !busy && !pending && !error && sessionId && !sessionBlocked && snapshot && projection && workspace &&
    workspace.line_id === lineId && workspace.case_version === snapshot.case_version && evidenceScope(snapshot, projectId, projection.case_version) &&
    (!revision || revision === snapshot.case_version) &&
    projection.capabilities.some(c => c.stage === "PRICE_EVIDENCE" && c.available && c.provider_key === "price_evidence_confirmation_v1"));
  const matches = (value: EvidenceReceipt, attempt: Attempt) => value.historical === true && value.result.project_id === projectId &&
    value.result.command_id === attempt.commandId && value.result.contract_version === attempt.contract;
  const recover = async () => {
    if (!pending || locked.current) return;
    locked.current = true; setBusy(true);
    try {
      let resolved = false;
      try {
        const result = await fetchEvidenceReceipt(projectId, pending.commandId);
        if (!inScope()) return;
        if (!matches(result, pending)) throw new Error("Receipt scope mismatch");
        setReceipt(result); setNotice("Đã tìm thấy kết quả thao tác trước. Đang tải trạng thái hiện tại."); resolved = true;
      } catch (caught) {
        if (!inScope()) return;
        const status = (caught as { status?: number }).status || 0;
        if (status === 404) { setNotice("Chưa có biên nhận cho thao tác. Sau khi tải lại, cần xem xét và xác nhận rõ ràng nếu thực hiện thao tác mới."); resolved = true; }
        else setNotice(status === 401 || status === 403 ? evidenceError(status) : "Chưa xác định được kết quả. Tiếp tục kiểm tra biên nhận thao tác gốc.");
      }
      const fresh = await refresh();
      if (resolved && fresh) retain(null);
      latest.current.onRefresh();
    } finally { locked.current = false; if (active.current) setBusy(false); }
  };
  const submit = async (intent: EvidenceIntent, confirmed: EvidencePreparation) => {
    if (locked.current || !enabled || !snapshot || confirmed.project_id !== snapshot.project_id || confirmed.case_version !== snapshot.case_version || !workspace) return false;
    const source = "evidence_revision_id" in intent ? workspace.sources.find(s => s.evidence_revision_id === intent.evidence_revision_id) : null;
    const permitted = intent.operation === "register" ? snapshot.can_register
      : intent.operation === "confirm" ? snapshot.can_confirm && intent.supersedes_confirmation_id === snapshot.prior_confirmation_id
      : intent.operation === "withdraw-confirmation" ? workspace.can_withdraw_confirmation && intent.expected_confirmation_id === workspace.confirmation_id
      : intent.operation === "decide" ? intent.line_id === workspace.line_id && (intent.facts.outcome === "accepted" ? source?.can_accept : source?.can_reject)
      : snapshot.can_withdraw && workspace.sources.some(s => intent.target_kind === "source" ? s.can_withdraw && s.evidence_revision_id === intent.target_id
        : s.decision?.can_withdraw && (intent.target_kind === "decision" ? s.decision.decision_id : s.decision.relationship_id) === intent.target_id);
    if (!permitted) return false;
    const reasonRequired = intent.operation === "withdraw" || intent.operation === "withdraw-confirmation" ||
      intent.operation === "confirm" && intent.supersedes_confirmation_id !== null ||
      intent.operation === "register" && intent.predecessor_revision_id !== null ||
      intent.operation === "decide" && (intent.facts.outcome === "rejected" || intent.prior_decision_id !== null);
    if (reasonRequired && !intent.reason_note?.trim() || [...(intent.reason_note || "")].length > 2000) return false;
    const attempt = { commandId: crypto.randomUUID(), contract: EVIDENCE_CONTRACTS[intent.operation] };
    locked.current = true; setBusy(true); setNotice(""); setReceipt(null);
    try { retain(attempt); } catch { locked.current = false; setBusy(false); setError("Chưa lưu được thông tin khôi phục. Chưa gửi thao tác."); return false; }
    try {
      const result = await submitEvidence(projectId, intent, confirmed, attempt.commandId);
      if (!inScope()) return false;
      if (!matches(result, attempt)) throw new Error("Receipt scope mismatch");
      setReceipt(result); retain(null); setNotice("Đã ghi nhận thao tác. Kết quả hoàn tất chỉ lấy từ trạng thái hồ sơ đã tải lại.");
      await refresh(); latest.current.onRefresh(); return true;
    } catch (caught) {
      if (!inScope()) return false;
      const status = (caught as { status?: number }).status || 0;
      if (status === 0 || status >= 500) setNotice("Chưa xác định được kết quả thao tác. Kiểm tra biên nhận trước khi thực hiện thao tác khác.");
      else { retain(null); setNotice(evidenceError(status)); await refresh(); latest.current.onRefresh(); }
      return false;
    } finally { locked.current = false; if (active.current) setBusy(false); }
  };
  const loadMore = async () => {
    if (loading || busy || !workspace || workspace.next_offset === null) return;
    const previous = workspace, gen = ++generation.current;
    setLoading(true);
    try {
      const next = await fetchEvidenceWorkspace(projectId, lineId, previous.next_offset!);
      if (!active.current || gen !== generation.current) return;
      if (next.project_id !== projectId || next.line_id !== lineId || next.case_version !== previous.case_version) throw { status: 409 };
      setWorkspace({ ...next, sources: [...previous.sources, ...next.sources] });
    } catch (caught) { if (active.current && gen === generation.current) setError(evidenceError((caught as { status?: number }).status || 0)); }
    finally { if (active.current && gen === generation.current) setLoading(false); }
  };
  const scoped = loadedScope === storageKey;
  return { projection: scoped ? projection : null, snapshot: scoped ? snapshot : null, workspace: scoped ? workspace : null,
    loading, busy, error: scoped ? error : "", notice: scoped ? notice : "", receipt: scoped ? receipt : null,
    pending: scoped ? pending : null, enabled, refresh, recover, submit, loadMore };
}
export type PriceEvidenceController = ReturnType<typeof usePriceEvidence>;
