import { useCallback, useEffect, useRef, useState } from "react";
import { fetchCaseState, type CaseStateResponse } from "../../../api/caseState";
import { fetchQuotePreparation, fetchQuoteHistory, fetchQuoteSources, fetchQuoteSuppliers, fetchQuoteReceipt,
  quoteCommand, submitQuoteCommand, QUOTE_CONTRACTS, type QuotePreparation, type QuoteHistory,
  type QuoteSource, type QuoteSupplier, type QuotePage, type QuoteIntent, type QuoteReceipt } from "../../../api/supplierQuotes";

type Attempt = { commandId: string; contract: string };
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const HASH = /^[0-9a-f]{64}$/;
export const quoteError = (status: number) => status === 401 ? "Phiên đăng nhập đã hết hạn. Đăng nhập lại để tiếp tục."
  : status === 403 ? "Bạn chưa có quyền truy cập hoặc thao tác với báo giá này."
  : status === 404 ? "Ngữ cảnh không còn khả dụng. Mở lại hồ sơ để kiểm tra."
  : status === 409 ? "Xung đột phiên bản. Dữ liệu đã thay đổi; cần tải lại và xem xét trước thao tác mới."
  : status === 400 ? "Dữ liệu báo giá chưa hợp lệ. Kiểm tra các trường và điều kiện thao tác."
  : "Chưa tải được báo giá. Tải lại để kiểm tra trạng thái.";
export function quoteScope(p: QuotePreparation, projectId: string, sessionId: string, token: string) {
  return p.project_id === projectId && p.session_id === sessionId && p.case_version === token && HASH.test(token) &&
    UUID.test(p.seal_id || "") && UUID.test(p.price_evidence_confirmation_id || "") && HASH.test(p.authoritative_set_sha256 || "") &&
    Number.isSafeInteger(p.project_row_version) && p.project_row_version > 0 && Number.isSafeInteger(p.membership_version) && p.membership_version! > 0 &&
    p.line_versions.length > 0 && new Set(p.line_versions.map(l => l.line_id)).size === p.line_versions.length &&
    p.line_versions.every(l => UUID.test(l.line_id) && Number.isSafeInteger(l.row_version) && l.row_version > 0);
}
export function useSupplierQuotes({ projectId, sessionId, sessionBlocked, actorScope, revision, onRefresh }: {
  projectId: string; sessionId?: string; sessionBlocked: boolean; actorScope?: string; revision?: string; onRefresh: () => void;
}) {
  const storageKey = `valora:supplier-quotes:${actorScope || "unknown"}:${projectId}`;
  const restore = (): Attempt | null => {
    try { const a = JSON.parse(sessionStorage.getItem(storageKey) || "null");
      return a && UUID.test(a.commandId) && Object.values(QUOTE_CONTRACTS).includes(a.contract) ? a : null;
    } catch { return null; }
  };
  const [scope, setScope] = useState(storageKey), [pending, setPending] = useState<Attempt | null>(restore);
  const [projection, setProjection] = useState<CaseStateResponse | null>(null);
  const [snapshot, setSnapshot] = useState<QuotePreparation | null>(null), [history, setHistory] = useState<QuoteHistory | null>(null);
  const [suppliers, setSuppliers] = useState<QuotePage<QuoteSupplier> | null>(null), [sources, setSources] = useState<QuotePage<QuoteSource> | null>(null);
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(false), [error, setError] = useState("");
  const [notice, setNotice] = useState(""), [conflict, setConflict] = useState(false);
  const [denied, setDenied] = useState(false);
  const active = useRef(true), locked = useRef(false), generation = useRef(0), scopeRef = useRef(storageKey);
  scopeRef.current = storageKey;
  const current = () => active.current && scopeRef.current === storageKey;
  const latest = useRef(onRefresh); latest.current = onRefresh;
  const retain = (a: Attempt | null) => {
    if (a) sessionStorage.setItem(storageKey, JSON.stringify(a)); else sessionStorage.removeItem(storageKey);
    if (current()) setPending(a);
  };
  const refresh = useCallback(async () => {
    const gen = ++generation.current; setLoading(true); setError("");
    const results = await Promise.allSettled([fetchCaseState(projectId), fetchQuotePreparation(projectId),
      fetchQuoteHistory(projectId), fetchQuoteSuppliers(projectId), fetchQuoteSources(projectId)]);
    if (!current() || gen !== generation.current) return false;
    const failure = results.find(r => r.status === "rejected" && [401, 403, 404].includes(r.reason?.status)) || results.find(r => r.status === "rejected");
    if (failure?.status === "rejected") {
      const status = failure.reason?.status || 0;
      if ([401, 403, 404].includes(status)) { setProjection(null); setSnapshot(null); setHistory(null); setSuppliers(null); setSources(null); }
      else if (status === 409) {
        const [state, prep, view, supplierPage, sourcePage] = results;
        if (prep.status === "fulfilled" && prep.value.project_id === projectId && (state.status === "rejected" ||
          state.value.case_version === prep.value.case_version && prep.value.result === state.value.stages.find(s => s.stage === "SUPPLIER_QUOTES")?.result)) {
          setProjection(state.status === "fulfilled" ? state.value : null); setSnapshot(prep.value);
          setHistory(view.status === "fulfilled" && view.value.case_version === prep.value.case_version ? view.value : null);
          setSuppliers(supplierPage.status === "fulfilled" ? supplierPage.value : null); setSources(sourcePage.status === "fulfilled" ? sourcePage.value : null);
        }
      }
      setError(quoteError(status)); setLoading(false); return false;
    }
    const [state, prep, view, supplierPage, sourcePage] = results;
    if (state.status === "fulfilled" && prep.status === "fulfilled" && view.status === "fulfilled" && supplierPage.status === "fulfilled" && sourcePage.status === "fulfilled" &&
      prep.value.project_id === projectId && state.value.case_version === prep.value.case_version && prep.value.case_version === view.value.case_version &&
      prep.value.result === state.value.stages.find(s => s.stage === "SUPPLIER_QUOTES")?.result) {
      setProjection(state.value); setSnapshot(prep.value); setHistory(view.value); setSuppliers(supplierPage.value); setSources(sourcePage.value);
      setConflict(false); setLoading(false); return true;
    }
    setError(quoteError(409)); setConflict(true); setLoading(false); return false;
  }, [storageKey, projectId]);
  useEffect(() => { active.current = true; setScope(storageKey); setPending(restore()); setProjection(null); setSnapshot(null);
    setHistory(null); setSuppliers(null); setSources(null); setNotice(""); setConflict(false); setDenied(false);
    void refresh(); return () => { active.current = false; ++generation.current; }; }, [refresh]);
  useEffect(() => { void refresh(); }, [refresh, sessionId, sessionBlocked, revision]);
  const scoped = scope === storageKey;
  const enabled = Boolean(scoped && !denied && !loading && !busy && !pending && !error && !sessionBlocked && actorScope && sessionId && snapshot && projection && history &&
    snapshot.writable && quoteScope(snapshot, projectId, sessionId, projection.case_version) &&
    (!revision || revision === snapshot.case_version) && projection.capabilities.some(c => c.stage === "SUPPLIER_QUOTES" && c.available && c.provider_key === "supplier_quotes_v1"));
  const matches = (r: QuoteReceipt, a: Attempt) => r.historical === true && r.result.project_id === projectId &&
    r.result.command_id === a.commandId && r.result.contract_version === a.contract;
  const recover = async () => {
    if (!pending || locked.current) return;
    locked.current = true; setBusy(true);
    try {
      let found = false;
      try { const r = await fetchQuoteReceipt(projectId, pending.commandId);
        if (!current()) return;
        if (!matches(r, pending)) throw new Error("Receipt scope mismatch");
        found = true; setNotice("Đã tìm thấy kết quả thao tác trước. Trạng thái hiện tại được tải riêng từ hồ sơ.");
      } catch (caught) {
        if (!current()) return;
        const status = (caught as { status?: number }).status || 0;
        setNotice(status === 404 ? "Chưa tìm thấy biên nhận. Giữ thao tác gốc và tiếp tục kiểm tra; chưa thể gửi lại."
          : [401, 403].includes(status) ? quoteError(status) : "Chưa xác định được kết quả. Tiếp tục kiểm tra thao tác gốc.");
      }
      const fresh = await refresh();
      if (found && fresh) retain(null);
      latest.current();
    } finally { locked.current = false; if (current()) setBusy(false); }
  };
  const submit = async (intent: QuoteIntent, expectedToken: string) => {
    if (locked.current || !enabled || !snapshot || !history || snapshot.case_version !== expectedToken || !suppliers || !sources) return false;
    const head = snapshot.quotes.find(q => q.quote_id === intent.quote_id);
    const permitted = intent.operation === "register" ? snapshot.can_register && !head
      : head?.revision_id === intent.revision_id && (intent.operation === "confirm" ? head.can_confirm
        : intent.operation === "register-line" ? head.can_register_line
        : intent.operation === "revise" ? head.can_revise
        : intent.operation === "withdraw" ? head.can_withdraw && head.confirmed_revision_id === intent.target_revision_id : head.can_reject);
    if (!permitted || "reason_note" in intent && (!intent.reason_note.trim() || [...intent.reason_note.trim()].length > 2000)) return false;
    let payload: ReturnType<typeof quoteCommand>;
    const attempt = { commandId: crypto.randomUUID(), contract: QUOTE_CONTRACTS[intent.operation] };
    try { payload = quoteCommand(snapshot, intent, attempt.commandId, suppliers.items, sources.items, history.items); }
    catch { setError("Ngữ cảnh thao tác chưa đủ. Tải thêm lịch sử hoặc tải lại báo giá."); return false; }
    locked.current = true; setBusy(true); setNotice("");
    try { retain(attempt); } catch { locked.current = false; setBusy(false); setError("Chưa lưu được thông tin khôi phục. Chưa gửi thao tác."); return false; }
    try {
      const r = await submitQuoteCommand(projectId, intent.operation, payload);
      if (!current()) return false;
      if (!matches(r, attempt)) throw new Error("Receipt scope mismatch");
      retain(null); setNotice("Đã ghi nhận thao tác. Đang kiểm tra trạng thái báo giá hiện tại.");
      const fresh = await refresh(); setNotice(fresh ? "Đã ghi nhận thao tác. Trạng thái đã được máy chủ kiểm tra lại."
        : "Thao tác đã được ghi nhận nhưng chưa tải lại được trạng thái. Tải lại trước khi tiếp tục.");
      latest.current(); return true;
    } catch (caught) {
      if (!current()) return false;
      const status = (caught as { status?: number }).status || 0;
      if (!status || status >= 500) setNotice("Chưa xác định được kết quả thao tác. Kiểm tra kết quả trước khi tiếp tục.");
      else { retain(null); setNotice(quoteError(status)); if ([401, 403].includes(status)) setDenied(true); if (status === 409) setConflict(true);
        await refresh(); latest.current(); }
      return false;
    } finally { locked.current = false; if (current()) setBusy(false); }
  };
  const loadMore = async (kind: "history" | "suppliers" | "sources") => {
    if (locked.current || loading || busy) return;
    locked.current = true; setLoading(true); const gen = ++generation.current;
    try {
      if (kind === "history" && history) {
        const next = await fetchQuoteHistory(projectId, history.offset + history.limit);
        if (!current() || gen !== generation.current) return;
        if (next.case_version !== history.case_version) throw { status: 409 };
        setHistory({ ...next, items: [...history.items, ...next.items] });
      } else if (kind === "suppliers" && suppliers) {
        const next = await fetchQuoteSuppliers(projectId, suppliers.offset + suppliers.limit);
        if (current() && gen === generation.current) setSuppliers({ ...next, items: [...suppliers.items, ...next.items] });
      } else if (kind === "sources" && sources) {
        const next = await fetchQuoteSources(projectId, sources.offset + sources.limit);
        if (current() && gen === generation.current) setSources({ ...next, items: [...sources.items, ...next.items] });
      }
    } catch (caught) {
      if (current()) { const status = (caught as { status?: number }).status || 0; setError(quoteError(status));
        if ([401, 403, 404].includes(status)) { setProjection(null); setSnapshot(null); setHistory(null); setSuppliers(null); setSources(null); } }
    } finally { locked.current = false; if (current() && gen === generation.current) setLoading(false); }
  };
  return { projection: scoped ? projection : null, snapshot: scoped ? snapshot : null, history: scoped ? history : null,
    suppliers: scoped ? suppliers : null, sources: scoped ? sources : null, loading, busy, error, notice, conflict,
    pending: scoped ? pending : null, enabled, refresh, recover, submit, loadMore };
}
export type SupplierQuotesController = ReturnType<typeof useSupplierQuotes>;
