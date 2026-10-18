import { useCallback, useEffect, useRef, useState } from "react";
import { fetchCaseState, type CaseStateResponse, type PostIntakeImportContext } from "../../api/caseState";
import { getCurrentAccount } from "../../api/auth";
import { applyAssetImport, validateAssetImport, fetchAssetImportBatches, fetchAssetImportRows,
  type ProjectAssetImportBatchResponse as Batch, type ProjectAssetImportStagingRowPaginationResponse as Rows } from "../../api/assetImports";
import { allValid, APPLY_CONTRACT, coherentPage, importContext, PAGE_SIZE, promotionProven,
  sameSelectedSource, targetKey, UUID, validApplyResponse } from "./postIntakeImportModel";

type Snapshot = { projection: CaseStateResponse; target: PostIntakeImportContext; batch: Batch; rows: Rows };
type Attempt = { operation: "validate" | "apply"; target: PostIntakeImportContext };
type Pending = Attempt | "unreadable" | null;
export interface PostIntakeImportOptions {
  projectId: string;
  actorScope: string;
  canEdit: boolean;
  projection: CaseStateResponse;
  onProjection: (projection: CaseStateResponse) => void;
}

function readPending(key: string): Pending {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const value = JSON.parse(raw) as Attempt;
    const c = value?.target;
    return c && ["validate", "apply"].includes(value.operation) && c.kind === value.operation &&
      [c.project_id, c.batch_id, c.staging_usage_id, c.official_intake_commit_id, c.result_id].every(id => UUID.test(id || "")) &&
      /^[0-9a-f]{64}$/.test(c.case_version) ? value : "unreadable";
  } catch { return "unreadable"; }
}

const CONFLICT_MESSAGES: Record<string, string> = {
  validation_project_not_draft: "Hồ sơ không còn ở trạng thái nháp. Tải lại dữ liệu để kiểm tra bước tiếp theo.",
  validation_lineage_conflict: "Nguồn dữ liệu của lô nhập đã thay đổi. Tải lại dữ liệu mới nhất rồi rà soát trước khi tiếp tục.",
  validation_version_conflict: "Trạng thái hồ sơ đã thay đổi. Tải lại dữ liệu mới nhất rồi rà soát và xác nhận lại.",
  apply_state_not_allowed: "Lô nhập không còn ở trạng thái có thể áp dụng. Tải lại dữ liệu để kiểm tra bước tiếp theo.",
  apply_rows_not_ready: "Lô nhập chưa sẵn sàng để áp dụng. Rà soát các dòng chưa hợp lệ rồi tải lại dữ liệu.",
  apply_intake_required: "Hồ sơ chưa hoàn tất tiếp nhận chính thức. Tải lại dữ liệu để kiểm tra bước tiếp theo.",
  apply_entry_conflict: "Danh mục tài sản hiện tại đã thay đổi hoặc không còn trống. Tải lại dữ liệu và rà soát trước khi tiếp tục.",
  apply_lineage_conflict: "Nguồn dữ liệu của lô nhập đã thay đổi. Tải lại dữ liệu mới nhất rồi rà soát trước khi tiếp tục.",
  apply_version_conflict: "Trạng thái hồ sơ đã thay đổi. Tải lại dữ liệu mới nhất rồi rà soát và xác nhận lại.",
};

function safeErrorCode(cause: unknown): string | undefined {
  if (!cause || typeof cause !== "object") return undefined;
  const source = cause as Record<string, unknown>;
  const detail = source.detail;
  const nested = detail && typeof detail === "object" ? detail as Record<string, unknown> : undefined;
  const nestedDetail = nested?.detail;
  const deeper = nestedDetail && typeof nestedDetail === "object"
    ? nestedDetail as Record<string, unknown> : undefined;
  const candidates = [source.code, source.error_code, nested?.error_code, nested?.code,
    deeper?.error_code, deeper?.code];
  return candidates.find((value): value is string => typeof value === "string" &&
    Object.prototype.hasOwnProperty.call(CONFLICT_MESSAGES, value) && typeof CONFLICT_MESSAGES[value] === "string");
}

function rejection(status: number, errorCode?: string): string {
  if (status === 401) return "Phiên đăng nhập hết hiệu lực. Đăng nhập lại và tải lại dữ liệu trước khi tiếp tục.";
  if (status === 403) return "Bạn chưa có quyền thực hiện thao tác này. Kiểm tra quyền truy cập trước khi tải lại.";
  if (status === 404) return "Không tìm thấy dữ liệu trong phạm vi truy cập hiện tại. Không thể tiếp tục thao tác.";
  if (status === 409) {
    const message = errorCode && Object.prototype.hasOwnProperty.call(CONFLICT_MESSAGES, errorCode)
      ? CONFLICT_MESSAGES[errorCode] : undefined;
    return typeof message === "string" ? message
      : "Trạng thái, nguồn hoặc phiên bản hồ sơ đã thay đổi. Rà soát dữ liệu mới và xác nhận lại.";
  }
  return "Máy chủ từ chối yêu cầu. Kiểm tra điều kiện hồ sơ và tải lại dữ liệu trước khi xác nhận lại.";
}

export function usePostIntakeImport({ projectId, actorScope, canEdit, projection, onProjection }: PostIntakeImportOptions) {
  const storageKey = `valora:post-intake:${actorScope}:${projectId}`;
  const [pending, setPending] = useState<Pending>(() => readPending(storageKey));
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [confirmation, setConfirmation] = useState<Snapshot | null>(null);
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(""), [conflict, setConflict] = useState(false);
  const [error, setError] = useState("");
  const [proven, setProven] = useState(false);
  const alive = useRef(true), dispatchLock = useRef(false), generation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const lastTarget = useRef<PostIntakeImportContext | null>(null);
  const scope = `${storageKey}:${canEdit}`;
  const liveScope = useRef(scope); liveScope.current = scope;
  const publish = useRef(onProjection); publish.current = onProjection;
  const current = useRef({ snapshot, projection, canEdit, pending });
  current.current = { snapshot, projection, canEdit, pending };
  const active = useCallback(() => alive.current && liveScope.current === scope, [scope]);

  const retain = useCallback((value: Attempt | null) => {
    if (value) {
      const raw = JSON.stringify(value);
      localStorage.setItem(storageKey, raw);
      if (localStorage.getItem(storageKey) !== raw) throw new Error("Pending marker not retained");
    } else localStorage.removeItem(storageKey);
    if (active()) setPending(value);
  }, [storageKey, active]);

  const read = useCallback(async (offset = 0, recovery?: Attempt): Promise<Snapshot | null> => {
    const ticket = ++generation.current;
    controller.current?.abort();
    const abort = new AbortController(); controller.current = abort;
    if (active()) { setLoading(true); setSnapshot(null); setConfirmation(null); setError(""); setProven(false); }
    const valid = () => active() && ticket === generation.current && !abort.signal.aborted;
    const checkActor = async () => {
      const account = await getCurrentAccount();
      if (`${account.organization_id}:${account.id}` !== actorScope || account.status !== "active" ||
          (current.current.canEdit && !account.permissions.includes("workbench:edit"))) throw { status: 403 };
    };
    try {
      await checkActor();
      if (!valid()) return null;
      const before = await fetchCaseState(projectId, abort.signal);
      if (!valid()) return null;
      const entry = importContext(before, projectId);
      const target = recovery?.target || entry ||
        (lastTarget.current && sameSelectedSource(before, lastTarget.current) ? lastTarget.current : null);
      if (!target || target.project_id !== projectId) {
        if (valid()) { publish.current(before); setError("Trạng thái hiện tại chưa cho phép kiểm tra hoặc áp dụng danh mục nhập. Hãy xem hành động tiếp theo của hồ sơ."); }
        return null;
      }
      const [batches, rows] = await Promise.all([
        fetchAssetImportBatches(projectId, abort.signal),
        fetchAssetImportRows(projectId, target.batch_id, { limit: PAGE_SIZE, offset }, abort.signal),
      ]);
      const after = await fetchCaseState(projectId, abort.signal);
      await checkActor();
      if (!valid()) return null;
      const matches = batches.filter(b => b.id === target.batch_id);
      const batch = matches[0];
      if (before.case_version !== after.case_version || !sameSelectedSource(after, target) || matches.length !== 1 ||
          !coherentPage(batch, rows, projectId, target.batch_id, offset)) throw new Error("Incoherent reads");
      const fresh = importContext(after, projectId);
      if (recovery) {
        const applied = promotionProven(after, batch, target);
        const validated = recovery.operation === "validate" && fresh?.kind === "apply" &&
          fresh.batch_id === target.batch_id && fresh.staging_usage_id === target.staging_usage_id &&
          fresh.result_id === target.result_id && fresh.official_intake_commit_id === target.official_intake_commit_id &&
          fresh.case_version !== target.case_version && allValid(batch, rows);
        if (applied || validated) {
          retain(null); setProven(applied);
          setNotice(applied ? "Máy chủ xác nhận danh mục đã được áp dụng. Tiếp tục rà soát tài sản trong Bàn làm việc."
            : "Máy chủ đã cung cấp kết quả kiểm tra hiện hành. Rà soát lại danh mục trước khi xác nhận áp dụng.");
        } else setNotice("Chưa chứng minh được kết quả thao tác trước. Chỉ được tải lại để đối soát; liên hệ người phụ trách hồ sơ nếu chưa xác định được kết quả.");
      }
      publish.current(after);
      if (fresh && (fresh.batch_id !== target.batch_id || fresh.staging_usage_id !== target.staging_usage_id ||
          fresh.result_id !== target.result_id || fresh.official_intake_commit_id !== target.official_intake_commit_id ||
          (!recovery && entry && targetKey(fresh) !== targetKey(target)))) {
        setError("Lựa chọn hoặc phiên bản hồ sơ đã thay đổi. Tải lại dữ liệu trước khi tiếp tục.");
        return null;
      }
      if (fresh) lastTarget.current = fresh;
      const next = { projection: after, target: fresh || target, batch, rows };
      setSnapshot(next);
      return next;
    } catch (cause) {
      if (valid()) {
        const status = Number((cause as { status?: number }).status || 0);
        setError([401, 403, 404].includes(status) ? rejection(status)
          : "Chưa xác minh được dữ liệu đồng nhất của hồ sơ và danh mục. Thao tác đang khóa; hãy tải lại dữ liệu.");
      }
      return null;
    } finally { if (valid()) setLoading(false); }
  }, [active, actorScope, projectId, retain]);

  useEffect(() => {
    alive.current = true;
    const marker = readPending(storageKey); setPending(marker);
    void read(0, marker && marker !== "unreadable" ? marker : undefined);
    return () => { alive.current = false; ++generation.current; controller.current?.abort(); };
  }, [read, storageKey]);

  useEffect(() => {
    if (snapshot && snapshot.projection.case_version !== projection.case_version) {
      ++generation.current; controller.current?.abort(); setSnapshot(null); setConfirmation(null);
      setError("Trạng thái hồ sơ đã thay đổi. Tải lại và xác nhận lại trước khi tiếp tục.");
    }
  }, [projection.case_version, snapshot]);

  useEffect(() => {
    const invalidate = () => {
      if (!active() || dispatchLock.current) return;
      setSnapshot(null); setConfirmation(null);
      setError("Cần kiểm tra lại trạng thái sau khi chuyển cửa sổ. Tải lại dữ liệu trước khi tiếp tục.");
    };
    const storageChanged = (event: StorageEvent) => {
      if (event.key === storageKey) { setPending(readPending(storageKey)); invalidate(); }
    };
    window.addEventListener("focus", invalidate); window.addEventListener("storage", storageChanged);
    return () => { window.removeEventListener("focus", invalidate); window.removeEventListener("storage", storageChanged); };
  }, [active, storageKey]);

  const authoritative = importContext(projection, projectId);
  const ready = canEdit && !loading && !busy && !pending && !error && snapshot !== null && authoritative !== null &&
    snapshot.projection.case_version === projection.case_version && targetKey(authoritative) === targetKey(snapshot.target);
  const canValidate = ready && snapshot.target.kind === "validate" &&
    ["parsed", "validation_failed", "ready_for_review"].includes(snapshot.batch.status);
  const canApply = ready && snapshot.target.kind === "apply" && allValid(snapshot.batch, snapshot.rows);

  const refresh = async (offset = 0) => {
    if (dispatchLock.current) return;
    const marker = readPending(storageKey); setPending(marker);
    await read(offset, marker && marker !== "unreadable" ? marker : undefined);
  };
  const openConfirmation = async () => {
    if (!canApply || dispatchLock.current || !snapshot) return;
    dispatchLock.current = true; setBusy(true);
    const expected = targetKey(snapshot.target);
    try {
      const fresh = await read(snapshot.rows.offset);
      if (active() && fresh && targetKey(fresh.target) === expected && fresh.target.kind === "apply" && allValid(fresh.batch, fresh.rows))
        setConfirmation(fresh);
      else if (active()) setNotice("Dữ liệu đã thay đổi. Rà soát danh mục mới rồi mở lại xác nhận.");
    } finally { dispatchLock.current = false; if (active()) setBusy(false); }
  };

  const submit = async (operation: "validate" | "apply") => {
    const approved = operation === "apply" ? confirmation : snapshot;
    if (dispatchLock.current || !active() || !approved || !(operation === "apply" ? canApply : canValidate) ||
        targetKey(approved.target) !== targetKey(snapshot!.target) || readPending(storageKey)) return;
    dispatchLock.current = true; setBusy(true); setNotice(""); setConflict(false); setConfirmation(null);
    let dispatched = false;
    const attempt: Attempt = { operation, target: approved.target };
    try {
      const fresh = await read(approved.rows.offset);
      if (!active() || !current.current.canEdit || !fresh || targetKey(fresh.target) !== targetKey(approved.target) ||
          (operation === "apply" && !allValid(fresh.batch, fresh.rows))) {
        if (active()) setNotice("Lựa chọn hoặc phiên bản đã thay đổi. Rà soát và xác nhận lại; chưa gửi thao tác.");
        return;
      }
      if (readPending(storageKey)) { setPending(readPending(storageKey)); return; }
      retain(attempt);
      dispatched = true;
      if (operation === "validate") {
        const result = await validateAssetImport(projectId, approved.target.batch_id,
          { expected_case_version: approved.target.case_version });
        if (!active()) return;
        if (result.id !== approved.target.batch_id || result.project_id !== projectId ||
            !["ready_for_review", "validation_failed"].includes(result.status)) throw new Error("Malformed validation response");
        retain(null);
        setNotice("Đã nhận kết quả kiểm tra. Điều kiện áp dụng được tải lại từ máy chủ.");
        await read();
      } else {
        const result = await applyAssetImport(projectId, approved.target.batch_id, { confirm: true,
          contract_version: APPLY_CONTRACT, expected_case_version: approved.target.case_version });
        if (!active()) return;
        if (!validApplyResponse(result, approved.batch, approved.rows)) throw new Error("Malformed Apply response");
        await read(0, attempt);
      }
    } catch (cause) {
      if (!active()) return;
      const status = Number((cause as { status?: number }).status || 0);
      if (dispatched && [400, 401, 403, 404, 409, 422].includes(status)) {
        try { retain(null); } catch { setPending("unreadable"); }
        setSnapshot(null); setNotice(rejection(status, status === 409 ? safeErrorCode(cause) : undefined)); setConflict(status === 409);
        if (status === 409) await read();
        else setError(rejection(status));
      } else {
        if (!dispatched) setPending("unreadable");
        setSnapshot(null);
        setNotice(dispatched ? "Kết quả thao tác chưa xác định. Chỉ kiểm tra lại bằng cách đọc dữ liệu; không gửi lại thao tác."
          : "Không thể lưu dấu đối soát an toàn. Chưa gửi thao tác; quyền ghi đang khóa.");
      }
    } finally { dispatchLock.current = false; if (active()) setBusy(false); }
  };

  return { snapshot, confirmation: ready && confirmation && targetKey(confirmation.target) === targetKey(snapshot!.target) ? confirmation : null,
    loading, busy, pending, notice, error, conflict, proven, canValidate, canApply,
    refresh, openConfirmation, closeConfirmation: () => setConfirmation(null), submit };
}

export type PostIntakeImportController = ReturnType<typeof usePostIntakeImport>;
