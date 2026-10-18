import { useCallback, useEffect, useRef, useState } from "react";
import { fetchImportContext, fetchImportStatus, importQuotationTxt, type ImportCommand, type ImportContext, type ImportStatus } from "../../../api/quotationDocuments";

type Selection = { file: File; filename: string; sha256: string; preview: string; truncated: boolean };
type Attempt = { command: ImportCommand };
const HASH = /^[0-9a-f]{64}$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
export const importError = (status: number) => status === 401 ? "Phiên đăng nhập đã hết hạn. Đăng nhập lại để kiểm tra thao tác gốc."
  : status === 403 ? "Máy chủ từ chối thao tác theo quyền hoặc trạng thái hiện tại. Kiểm tra kết quả trước khi tiếp tục."
  : status === 409 ? "Xung đột phiên bản hoặc tệp gốc. Kiểm tra kết quả của lần nhập này."
  : [400, 413, 415, 422].includes(status) ? "Tệp hoặc thông tin nhập chưa hợp lệ. Chọn một tệp UTF-8 .txt từ 1 đến 1.048.576 byte."
  : "Chưa xác định được kết quả. Kiểm tra biên nhận của thao tác gốc.";

function restore(key: string): Attempt | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(key) || "null");
    const c = value?.command;
    return c?.contract_version === "quotation-txt-import-v1" && c.confirm === true && UUID.test(c.command_id)
      && HASH.test(c.expected_sha256) && HASH.test(c.expected_case_version) && Number.isSafeInteger(c.expected_project_row_version)
      && c.expected_project_row_version > 0 && Number.isSafeInteger(c.expected_byte_length)
      && c.expected_byte_length > 0 && c.expected_byte_length <= 1048576 ? { command: c } : null;
  } catch { return null; }
}

export function useQuotationDocumentImport({ projectId, actorScope, onImported }: {
  projectId: string; actorScope?: string; onImported: () => void | Promise<unknown>;
}) {
  const key = `valora:quotation-txt:${actorScope || "unknown"}:${projectId}`;
  const scope = useRef(key); scope.current = key;
  const active = useRef(true), locked = useRef(false), generation = useRef(0), selectionGeneration = useRef(0), lifetime = useRef(0);
  const terminalStatus = useRef<number | null>(null);
  const callback = useRef(onImported); callback.current = onImported;
  const [stateKey, setStateKey] = useState(key), [context, setContext] = useState<ImportContext | null>(null);
  const [pending, setPending] = useState<Attempt | null>(() => restore(key));
  const [selection, setSelection] = useState<Selection | null>(null), [status, setStatus] = useState<ImportStatus | null>(null);
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(false), [error, setError] = useState("");
  const current = () => active.current && scope.current === key;
  const refresh = useCallback(async () => {
    const gen = ++generation.current; setLoading(true); setError("");
    try {
      const value = await fetchImportContext(projectId);
      if (!current() || gen !== generation.current) return;
      if (value.project_id !== projectId || !HASH.test(value.case_version) || !Number.isSafeInteger(value.project_row_version)
        || value.contract_version !== "quotation-txt-import-v1") throw new Error("Context mismatch");
      setContext(value);
    } catch (caught) {
      if (current() && gen === generation.current) { setContext(null); setError(importError((caught as { status?: number }).status || 0)); }
    } finally { if (current() && gen === generation.current) setLoading(false); }
  }, [key, projectId]);
  useEffect(() => {
    ++lifetime.current;
    terminalStatus.current = null;
    active.current = true; locked.current = false; ++selectionGeneration.current;
    setStateKey(key); setPending(restore(key)); setSelection(null); setStatus(null); setContext(null); setBusy(false);
    if (actorScope) void refresh(); else setLoading(false);
    return () => { active.current = false; ++lifetime.current; ++generation.current; ++selectionGeneration.current; };
  }, [key, refresh, actorScope]);
  const select = async (file: File | null) => {
    if (locked.current) return;
    const gen = ++selectionGeneration.current; setSelection(null); setError("");
    if (!file) return;
    try {
      const filename = file.name.normalize("NFC");
      if (file.size < 1 || file.size > 1048576 || !filename.toLowerCase().endsWith(".txt")
        || filename !== filename.trim() || new TextEncoder().encode(filename).length > 255
        || /[/\\:\p{C}]/u.test(filename) || /^(con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])(?:\..*)?$/i.test(filename)) throw new Error("Invalid TXT");
      const bytes = await file.arrayBuffer();
      const text = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes);
      const sha256 = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), n => n.toString(16).padStart(2, "0")).join("");
      let preview = "", count = 0, truncated = false;
      for (const scalar of text) { if (count === 4096) { truncated = true; break; } preview += scalar; ++count; }
      if (current() && gen === selectionGeneration.current) setSelection({ file, filename, sha256, preview, truncated });
    } catch { if (current() && gen === selectionGeneration.current) setError(importError(422)); }
  };
  const persist = (attempt: Attempt | null) => {
    if (attempt) sessionStorage.setItem(key, JSON.stringify(attempt)); else sessionStorage.removeItem(key);
    if (current()) setPending(attempt);
  };
  const matches = (result: ImportStatus, attempt: Attempt) => result.project_id === projectId
    && result.command_id === attempt.command.command_id && result.contract_version === "quotation-txt-import-v1"
    && result.sha256 === attempt.command.expected_sha256 && result.byte_length === attempt.command.expected_byte_length;
  const receive = async (result: ImportStatus, attempt: Attempt) => {
    const owner = lifetime.current;
    if (!matches(result, attempt)) throw new Error("Receipt mismatch");
    if (!current()) return;
    if (result.outcome === "finalized") {
      if (!UUID.test(result.receipt_id || "") || !UUID.test(result.revision_id || "") || !UUID.test(result.binding_id || "")
        || result.generation !== 1 || !result.finalized_at || !result.source) throw new Error("Incomplete receipt");
      setStatus(result);
      persist(null); setSelection(null); await refresh(); if (current() && owner === lifetime.current) await callback.current();
    } else if (result.outcome === "pending") setStatus(result);
    else throw new Error("Unknown outcome");
  };
  const reconcile = async () => {
    if (!pending || locked.current) return;
    const owner = lifetime.current;
    locked.current = true; setBusy(true); setError("");
    try {
      const result = await fetchImportStatus(projectId, pending.command.command_id);
      if (current() && owner === lifetime.current) await receive(result, pending);
    } catch (caught) {
      if (current() && owner === lifetime.current) {
        const code = (caught as { status?: number }).status || 0;
        if (code === 404 && terminalStatus.current !== null) {
          persist(null); setStatus(null); setSelection(null); terminalStatus.current = null;
          await refresh();
          if (current() && owner === lifetime.current) setError("Máy chủ chưa ghi nhận lần nhập này. Chọn lại tệp, xem lại hồ sơ và xác nhận một lần nhập mới.");
        } else setError(code === 404 ? "Chưa tìm thấy biên nhận. Giữ thao tác gốc và tiếp tục kiểm tra; hệ thống chưa tự gửi lại." : importError(code));
      }
    } finally { if (current() && owner === lifetime.current) { locked.current = false; setBusy(false); } }
  };
  const sameFile = !!selection && !!pending && selection.sha256 === pending.command.expected_sha256 && selection.file.size === pending.command.expected_byte_length;
  const canRecover = !!pending && status?.outcome === "pending" && status.recovery_permitted === true && sameFile;
  const enabled = stateKey === key && !!actorScope && !loading && !busy && !!selection
    && (pending ? canRecover : context?.can_import === true);
  const submit = async () => {
    if (locked.current || !enabled || !selection || !context) return false;
    const owner = lifetime.current;
    locked.current = true; setBusy(true); setError("");
    const recovery = pending ? status?.storage_state_version : undefined;
    const attempt = pending || { command: { contract_version: "quotation-txt-import-v1" as const,
      command_id: crypto.randomUUID(), confirm: true as const, expected_case_version: context.case_version,
      expected_project_row_version: context.project_row_version, expected_sha256: selection.sha256, expected_byte_length: selection.file.size } };
    try {
      persist(attempt);
    } catch {
      locked.current = false; setBusy(false); setError("Không lưu được mã thao tác trong phiên này. Chưa gửi yêu cầu nhập."); return false;
    }
    const file = selection.file; setSelection(null); ++selectionGeneration.current;
    terminalStatus.current = null;
    try {
      const result = await importQuotationTxt(projectId, attempt.command, file, recovery);
      if (!current() || owner !== lifetime.current) return false;
      await receive(result, attempt); return true;
    } catch (caught) {
      if (current() && owner === lifetime.current) {
        const code = (caught as { status?: number }).status || 0;
        if ([401, 403, 404, 409].includes(code)) terminalStatus.current = code;
        if ([400, 413, 415, 422].includes(code)) persist(null);
        setError(importError(code));
      }
      return false;
    } finally { if (current() && owner === lifetime.current) { locked.current = false; setBusy(false); } }
  };
  const scoped = stateKey === key;
  return { context: scoped ? context : null, selection: scoped ? selection : null, pending: scoped ? pending : null,
    status: scoped ? status : null, loading, busy, error, enabled, canRecover, select, submit, reconcile, refresh };
}
export type QuotationDocumentImportController = ReturnType<typeof useQuotationDocumentImport>;
