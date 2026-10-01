import React, { useCallback, useEffect, useRef, useState } from "react";

import { fetchCaseState, type CaseStateResponse } from "../../api/caseState";
import { ApiError } from "../../api/client";
import {
  bindPreliminaryCustomer, commitOfficialIntake, downloadPreliminaryResult,
  generatePreliminaryResult, getCustomer, getPreliminaryResult, searchActiveCustomers,
  type CustomerSummary, type PreliminaryResultRead,
} from "../../api/preliminaryCompletion";
import { getProject, type ProjectSummary } from "../../api/projects";
import { projectOverviewPath, projectPreliminaryAnalysisPath } from "../../contracts/valoraV23";
import { ErrorState } from "../common/ErrorState";
import { LoadingState } from "../common/LoadingState";
import { useResolvedProject } from "../workbench/project-context";
import {
  attemptCommitted, attemptRetryable, canBindCustomer, canCommitIntake, canGenerateResult,
  type CompletionAttempt,
} from "./preliminaryCompletionModel";
import "./preliminaryCompletion.css";

interface CompletionData {
  projection: CaseStateResponse;
  project: ProjectSummary;
  result: PreliminaryResultRead | null;
  customer: CustomerSummary | null;
  customerReadFailure: "forbidden" | "unavailable" | null;
}

type LoadState = "loading" | "refreshing" | "ready" | "error" | "sessionExpired" | "forbidden";
type ConfirmAction = CompletionAttempt["kind"] | null;

const pendingKey = (projectId: string) => `valora:g11j:pending:${projectId}`;
const permissionForAttempt = { result: "project:preliminary_result:generate", customer: "project:update", intake: "project:official_intake:commit" } as const;
const customerReadPermission = "master_data:customer:read";

function readPending(projectId: string): CompletionAttempt | null {
  try {
    const raw = sessionStorage.getItem(pendingKey(projectId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as CompletionAttempt;
    return ["result", "customer", "intake"].includes(parsed.kind) &&
      typeof parsed.payload?.idempotency_key === "string" ? parsed : null;
  } catch { return null; }
}

function storePending(projectId: string, attempt: CompletionAttempt | null): boolean {
  try {
    if (attempt) sessionStorage.setItem(pendingKey(projectId), JSON.stringify(attempt));
    else sessionStorage.removeItem(pendingKey(projectId));
    return true;
  } catch { return false; }
}

function unknownResult(error: unknown): boolean {
  return !(error instanceof ApiError) || error.status === 0 || error.status === 408 ||
    error.status === 429 || error.status >= 500;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function PreliminaryCompletionPage({ projectRef, permissions, onNavigate, onSessionExpired }: {
  projectRef: string;
  permissions: string[];
  onNavigate: (path: string) => void;
  onSessionExpired: () => void;
}) {
  const resolved = useResolvedProject(projectRef);
  if (resolved.state === "loading" || resolved.state === "idle") return <LoadingState message="Đang xác định hồ sơ sơ bộ…" />;
  if (resolved.state === "error" || !resolved.projectId) {
    return <ErrorState title={resolved.error?.title || "Chưa thể mở hồ sơ"} message={resolved.error?.message || "Không thể xác định hồ sơ."} onRetry={resolved.retry} />;
  }
  return <ResolvedCompletion key={resolved.projectId} projectId={resolved.projectId} projectRef={projectRef}
    permissions={permissions} onNavigate={onNavigate} onSessionExpired={onSessionExpired} />;
}

function ResolvedCompletion({ projectId, projectRef, permissions, onNavigate, onSessionExpired }: {
  projectId: string;
  projectRef: string;
  permissions: string[];
  onNavigate: (path: string) => void;
  onSessionExpired: () => void;
}) {
  const [data, setData] = useState<CompletionData | null>(null);
  const dataRef = useRef<CompletionData | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [confirmAction, setConfirmAction] = useState<ConfirmAction>(null);
  const confirmRef = useRef<HTMLDialogElement>(null);
  const pendingRef = useRef<CompletionAttempt | null>(readPending(projectId));
  const [pending, setPendingView] = useState<CompletionAttempt | null>(pendingRef.current);
  const [searchText, setSearchText] = useState("");
  const [searchState, setSearchState] = useState<"idle" | "loading" | "ready" | "error" | "forbidden">("idle");
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerSummary | null>(null);

  const savePending = useCallback((attempt: CompletionAttempt | null) => {
    if (!storePending(projectId, attempt)) return false;
    pendingRef.current = attempt;
    setPendingView(attempt);
    return true;
  }, [projectId]);

  const load = useCallback(async (): Promise<CompletionData | null> => {
    setLoadState(dataRef.current ? "refreshing" : "loading");
    try {
      const projection = await fetchCaseState(projectId);
      const selected = projection.preliminary;
      if (selected.project_id !== projectId) throw new Error("Project authority mismatch");
      let customerReadFailure: CompletionData["customerReadFailure"] = null;
      const [project, result, customer] = await Promise.all([
        getProject(projectId),
        selected.current_preliminary_result_artifact_id
          ? getPreliminaryResult(projectId, selected.current_preliminary_result_artifact_id) : Promise.resolve(null),
        selected.customer_id ? getCustomer(selected.customer_id).catch((error) => {
          if (error instanceof ApiError && error.status === 401) throw error;
          customerReadFailure = error instanceof ApiError && error.status === 403 ? "forbidden" : "unavailable";
          return null;
        }) : Promise.resolve(null),
      ]);
      if (project.id !== projectId || project.row_version !== selected.project_row_version ||
          project.customer_id !== selected.customer_id ||
          (result && (result.project_id !== projectId || result.id !== selected.current_preliminary_result_artifact_id ||
            result.version !== selected.current_preliminary_result_version)) ||
          (customer && customer.id !== selected.customer_id)) {
        throw new Error("Current Pre-case readback changed");
      }
      const next = { projection, project, result, customer, customerReadFailure };
      dataRef.current = next;
      setData(next);
      const attempt = pendingRef.current;
      if (attempt && attemptCommitted(projection, attempt)) savePending(null);
      else if (attempt?.kind === "customer" && !selected.customer_id) {
        try {
          setSelectedCustomer(await getCustomer(attempt.payload.customer_id));
        } catch (error) {
          if (error instanceof ApiError && error.status === 401) throw error;
          setSelectedCustomer(null);
        }
      }
      setLoadState("ready");
      return next;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) setLoadState("sessionExpired");
      else if (error instanceof ApiError && error.status === 403) setLoadState("forbidden");
      else setLoadState("error");
      return null;
    }
  }, [projectId, savePending]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const dialog = confirmRef.current;
    if (confirmAction && dialog && !dialog.open) dialog.showModal();
  }, [confirmAction]);

  const search = async () => {
    setSearchState("loading");
    setSelectedCustomer(null);
    setCustomers([]);
    try {
      const found = await searchActiveCustomers(searchText);
      setCustomers(found.filter((item) => item.status === "active"));
      setSearchState("ready");
    } catch (error) {
      setSearchState(error instanceof ApiError && error.status === 403 ? "forbidden" : "error");
    }
  };

  const perform = async (attempt: CompletionAttempt) => {
    if (busyRef.current) return;
    if (!permissions.includes(permissionForAttempt[attempt.kind])) {
      setNotice("Tài khoản chưa có quyền thực hiện lệnh này. Hãy kiểm tra quyền truy cập trước khi tiếp tục.");
      setConfirmAction(null);
      return;
    }
    if (!savePending(attempt)) {
      setNotice("Trình duyệt chưa lưu được lần thử. Hãy cho phép lưu dữ liệu phiên rồi thực hiện lại.");
      setConfirmAction(null);
      return;
    }
    busyRef.current = true;
    setBusy(true);
    setConfirmAction(null);
    setNotice(null);
    try {
      if (attempt.kind === "result") await generatePreliminaryResult(projectId, attempt.payload);
      else if (attempt.kind === "customer") await bindPreliminaryCustomer(projectId, attempt.payload);
      else await commitOfficialIntake(projectId, attempt.payload);
      const refreshed = await load();
      if (!refreshed || !attemptCommitted(refreshed.projection, attempt)) {
        setNotice("Lệnh đã trả về nhưng trạng thái hiện hành chưa được xác minh. Hãy kiểm tra lại trước khi tiếp tục.");
      }
    } catch (error) {
      const refreshed = await load();
      if (!refreshed || !attemptCommitted(refreshed.projection, attempt)) {
        setNotice(unknownResult(error)
          ? "Chưa rõ lệnh đã được ghi nhận hay chưa. Hãy kiểm tra trạng thái; nếu chưa ghi nhận, thử lại cùng mã lệnh."
          : error instanceof ApiError && error.status === 409
            ? "Hồ sơ đã thay đổi hoặc lệnh không còn hợp lệ. Hãy rà soát trạng thái hiện hành; hệ thống không ghi đè thay đổi."
            : error instanceof ApiError && error.status === 403
              ? "Tài khoản chưa có quyền thực hiện lệnh này. Hãy kiểm tra quyền truy cập trước khi tiếp tục."
            : "Lệnh chưa được xác nhận. Hãy kiểm tra trạng thái trước khi quyết định tiếp tục.");
      }
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  };

  const confirm = () => {
    if (!data || pendingRef.current || busyRef.current || loadState !== "ready") return;
    const selected = data.projection.preliminary;
    const idempotency_key = `g11j-${crypto.randomUUID()}`;
    if (confirmAction === "result" && permissions.includes(permissionForAttempt.result) && canGenerateResult(data.projection)) {
      void perform({ kind: "result", payload: {
        preliminary_analysis_snapshot_id: selected.current_preliminary_analysis_snapshot_id!,
        expected_project_version: selected.project_row_version, idempotency_key, confirmed: true,
      } });
    } else if (confirmAction === "customer" && permissions.includes(permissionForAttempt.customer) && canBindCustomer(data.projection) && selectedCustomer?.status === "active") {
      void perform({ kind: "customer", payload: {
        customer_id: selectedCustomer.id, expected_project_version: selected.project_row_version, idempotency_key,
      } });
    } else if (confirmAction === "intake" && permissions.includes(permissionForAttempt.intake) && canCommitIntake(data.projection, data.customer?.status === "active")) {
      void perform({ kind: "intake", payload: {
        preliminary_result_artifact_id: selected.current_preliminary_result_artifact_id!,
        expected_preliminary_result_version: selected.current_preliminary_result_version!,
        expected_project_version: selected.project_row_version, idempotency_key, confirmed: true,
      } });
    }
  };

  const retryPending = () => {
    const attempt = pendingRef.current;
    if (!attempt || !data || loadState !== "ready" || busyRef.current) return;
    if (!permissions.includes(permissionForAttempt[attempt.kind]) || !attemptRetryable(data.projection, attempt,
      attempt.kind === "customer" ? selectedCustomer?.status === "active" : data.customer?.status === "active")) return;
    void perform(attempt);
  };

  const download = async () => {
    if (!data?.result) return;
    try {
      const blob = await downloadPreliminaryResult(projectId, data.result.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `ket-qua-so-bo-v${data.result.version}.xlsx`;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setNotice("Chưa thể tải tệp kết quả sơ bộ. Hãy kiểm tra kết nối rồi thử lại.");
    }
  };

  if (!data && loadState === "loading") return <LoadingState message="Đang đọc trạng thái kết quả sơ bộ…" />;
  if (loadState === "sessionExpired") return <ErrorState title="Phiên làm việc đã hết hạn" message="Đăng nhập lại rồi kiểm tra trạng thái hồ sơ trước khi tiếp tục." onRetry={onSessionExpired} retryLabel="Đăng nhập lại" />;
  if (loadState === "forbidden") return <ErrorState title="Chưa có quyền truy cập" message="Tài khoản không có quyền đọc hồ sơ hoặc kết quả hiện hành." />;
  if (!data && loadState === "error") return <ErrorState title="Chưa thể tải kết quả sơ bộ" message="Không thể xác minh trạng thái hồ sơ hiện hành." onRetry={() => void load()} />;
  if (!data) return null;

  const { projection, project, result, customer } = data;
  const selected = projection.preliminary;
  const committed = Boolean(selected.official_intake_commit_id);
  const unavailable = !committed && (projection.next_action?.kind === "UNAVAILABLE" || projection.stages.some(
    (stage) => (stage.stage === "PRELIMINARY_ANALYSIS" || stage.stage === "PRELIMINARY_READY") &&
      stage.result === "NOT_AVAILABLE"));
  const retryable = Boolean(pending && attemptRetryable(projection, pending,
    pending.kind === "customer" ? selectedCustomer?.status === "active" : customer?.status === "active") &&
    permissions.includes(permissionForAttempt[pending.kind]));
  const canGenerate = canGenerateResult(projection) && permissions.includes(permissionForAttempt.result);
  const canBind = canBindCustomer(projection) && permissions.includes(permissionForAttempt.customer);
  const canIntake = canCommitIntake(projection, customer?.status === "active") && permissions.includes(permissionForAttempt.intake);
  const canSearchCustomer = permissions.includes(permissionForAttempt.customer) && permissions.includes(customerReadPermission);

  return <div className="precase-completion-page">
    <header className="precase-completion-header">
      <div><p>Yêu cầu sơ bộ / Tiếp nhận</p><h1>Kết quả sơ bộ & tiếp nhận</h1>
        <span>{project.code} · {project.name}</span></div>
      <button className="valora-button valora-button--secondary" onClick={() => onNavigate(projectOverviewPath(projectRef))} type="button">Về Tổng quan hồ sơ</button>
    </header>

    <section className="precase-completion-strip" aria-label="Tình trạng Pre-case">
      <div><span>Phân tích</span><strong>{selected.current_preliminary_analysis_version ? `Đã chốt · bản ${selected.current_preliminary_analysis_version}` : "Chưa chốt"}</strong></div>
      <div><span>Kết quả sơ bộ</span><strong>{result ? `Đã tạo · bản ${result.version}` : unavailable ? "Chưa khả dụng" : "Chưa tạo"}</strong></div>
      <div><span>Khách hàng</span><strong>{customer ? customer.display_name || customer.legal_name :
        selected.customer_id ? "Đã gắn · chưa xem được" : "Chưa gắn"}</strong></div>
      <div><span>Tiếp nhận</span><strong>{committed ? "Đã hoàn tất" : "Chưa chuyển"}</strong></div>
    </section>

    {loadState === "refreshing" && <p className="precase-completion-note" role="status">Đang kiểm tra trạng thái hiện hành…</p>}
    {busy && <p className="precase-completion-note" role="status">Đang xử lý lệnh đã xác nhận…</p>}
    {loadState === "error" && <ErrorState title="Chưa thể cập nhật trạng thái" message="Dữ liệu đang hiển thị chưa được xác minh lại. Không thể thực hiện lệnh lúc này." onRetry={() => void load()} />}
    {notice && <p className="precase-completion-note" role="status">{notice}</p>}

    <div className="precase-completion-layout">
      <div className="precase-completion-main">
        {committed && <section className="precase-completion-success" role="status">
          <span aria-hidden="true" className="precase-completion-success-icon">✓</span>
          <div><strong>Đã tiếp nhận chính thức</strong>
            <p>Hồ sơ Pre-case đã được khóa sau quyết định chuyển. Kết quả sơ bộ và Customer dưới đây chỉ để xem lại.</p></div>
        </section>}

        <section className="valora-panel" aria-labelledby="completion-result-title">
          <div className="valora-panel__header"><h2 id="completion-result-title">Kết quả sơ bộ</h2></div>
          <div className="valora-panel__body">
            {result ? <div className="precase-completion-result">
              <dl><div><dt>Phiên bản</dt><dd>{result.version}</dd></div>
                <div><dt>Tạo lúc</dt><dd>{formatDate(result.created_at)}</dd></div>
                <div><dt>Dung lượng</dt><dd>{new Intl.NumberFormat("vi-VN").format(result.file_size_bytes)} byte</dd></div></dl>
              <button className="valora-button valora-button--secondary" onClick={() => void download()} type="button">Tải tệp Excel</button>
            </div> : unavailable ? <div className="valora-message valora-message--info precase-completion-unavailable" role="status">
              <span aria-hidden="true" className="precase-completion-info-icon">i</span>
              <div><strong>Chưa khả dụng</strong>
                <p>Trạng thái Pre-case chưa khả dụng từ bằng chứng hiện hành. Xem Tổng quan hồ sơ trước khi tiếp tục.</p></div>
            </div> : <p>{selected.current_preliminary_analysis_snapshot_id
              ? "Phân tích hiện hành đã chốt. Tạo tệp kết quả sơ bộ từ đúng bản phân tích này."
              : "Chưa có bản phân tích hiện hành đã chốt để tạo kết quả."}</p>}
            {!result && !unavailable && canGenerate && !pending && loadState === "ready" &&
              <button className="valora-button valora-button--primary" disabled={busy} onClick={() => setConfirmAction("result")} type="button">Tạo kết quả sơ bộ</button>}
            {!result && !unavailable && canGenerateResult(projection) && !permissions.includes(permissionForAttempt.result) &&
              <p role="status">Tài khoản chưa có quyền tạo kết quả sơ bộ.</p>}
            {!result && !unavailable && !canGenerate && selected.current_preliminary_analysis_snapshot_id === null &&
              <button className="valora-button valora-button--secondary" onClick={() => onNavigate(projectPreliminaryAnalysisPath(projectRef))} type="button">Mở phân tích danh mục</button>}
          </div>
        </section>

        {result && <section className="valora-panel" aria-labelledby="completion-customer-title">
          <div className="valora-panel__header"><h2 id="completion-customer-title">Chủ đầu tư / Khách hàng</h2></div>
          <div className="valora-panel__body">
            {customer ? <div className="precase-completion-customer"><strong>{customer.display_name || customer.legal_name}</strong>
              <span>{customer.tax_code ? `MST ${customer.tax_code}` : "Chưa bổ sung mã số thuế"}</span>
              <span>{customer.contact_phone || "Chưa bổ sung số điện thoại"}</span>
              {customer.status !== "active" && <p role="alert">Khách hàng hiện không còn hoạt động. Chưa thể tiếp nhận chính thức.</p>}
            </div> : selected.customer_id ? <p className="valora-message valora-message--warning" role="status">
              {data.customerReadFailure === "forbidden"
                ? "Customer đã gắn với hồ sơ. Tài khoản chưa có quyền xem chi tiết Customer nên chưa thể xác minh điều kiện tiếp nhận."
                : "Customer đã gắn với hồ sơ nhưng chưa đọc được chi tiết hiện hành. Kết quả sơ bộ vẫn có thể xem lại; hãy thử tải lại trước khi tiếp nhận."}
            </p> : <>
              <p>Chọn một Customer đang hoạt động trong dữ liệu chủ. Việc gắn Customer cần xác nhận riêng.</p>
              {!permissions.includes(permissionForAttempt.customer) && <p role="status">Tài khoản chưa có quyền gắn Customer với hồ sơ.</p>}
              {permissions.includes(permissionForAttempt.customer) && !permissions.includes(customerReadPermission) &&
                <p role="status">Tài khoản chưa có quyền tìm Customer trong dữ liệu chủ.</p>}
              {canSearchCustomer && <>
              <div className="precase-completion-search">
                <label htmlFor="completion-customer-query">Tên, mã số thuế hoặc số điện thoại</label>
                <div><input className="valora-field" id="completion-customer-query" onChange={(event) => setSearchText(event.target.value)} value={searchText} />
                  <button className="valora-button valora-button--secondary" disabled={searchState === "loading"} onClick={() => void search()} type="button">Tìm khách hàng</button></div>
              </div>
              {searchState === "loading" && <p role="status">Đang tìm trong dữ liệu chủ…</p>}
              {searchState === "error" && <p role="alert">Chưa thể tìm Customer. Hãy kiểm tra kết nối rồi thử lại.</p>}
              {searchState === "forbidden" && <p role="alert">Tài khoản không còn quyền tìm Customer trong dữ liệu chủ. Hãy kiểm tra quyền truy cập.</p>}
              {searchState === "ready" && customers.length === 0 && <p>Không có Customer đang hoạt động phù hợp.</p>}
              {customers.length > 0 && <div className="precase-completion-customer-list" role="radiogroup" aria-label="Chọn Customer đang hoạt động">
                {customers.map((item) => <label key={item.id}>
                  <input checked={selectedCustomer?.id === item.id} name="selected-customer" onChange={() => setSelectedCustomer(item)} type="radio" />
                  <span><strong>{item.display_name || item.legal_name}</strong><small>{item.tax_code ? `MST ${item.tax_code}` : item.contact_phone || "Chưa bổ sung mã số thuế"}</small></span>
                </label>)}
              </div>}
              {canBind && !unavailable && selectedCustomer?.status === "active" && !pending && loadState === "ready" &&
                <button className="valora-button valora-button--primary" disabled={busy} onClick={() => setConfirmAction("customer")} type="button">Gắn khách hàng đã chọn</button>}
              </>}
            </>}
          </div>
        </section>}

        {result && customer && <section className="valora-panel" aria-labelledby="completion-intake-title">
          <div className="valora-panel__header"><h2 id="completion-intake-title">Chuyển sang thẩm định chính thức</h2></div>
          <div className="valora-panel__body">
            {committed ? <p>Quyết định chuyển đã hoàn tất. Kết quả sơ bộ bản {result.version} và Customer đã được giữ làm ngữ cảnh bất biến.</p>
              : <><p>Tiếp nhận sẽ khóa luồng Pre-case hiện hành: tệp nguồn, ánh xạ, bản phân tích, kết quả sơ bộ và Customer gắn với hồ sơ. Các bước thẩm định tiếp theo được xử lý từ Tổng quan hồ sơ.</p>
                {projection.blockers.length > 0 && <p className="valora-message valora-message--error" role="alert">Đang có vấn đề ngăn tiếp nhận chính thức. Xem chi tiết tại Tổng quan hồ sơ trước khi tiếp tục.</p>}
                {canCommitIntake(projection, customer.status === "active") && !permissions.includes(permissionForAttempt.intake) &&
                  <p role="status">Tài khoản chưa có quyền chuyển sang thẩm định chính thức.</p>}
                {canIntake && !unavailable && !pending && loadState === "ready" && <button className="valora-button valora-button--primary" disabled={busy} onClick={() => setConfirmAction("intake")} type="button">Chuyển sang thẩm định chính thức</button>}
              </>}
          </div>
        </section>}

        {pending && !committed && !busy && <section className="valora-panel precase-completion-recovery" role="alert">
          <div className="valora-panel__header">Cần xác minh kết quả lệnh</div>
          <div className="valora-panel__body"><p>Một lần thử đang được giữ lại. Kiểm tra trạng thái máy chủ trước khi gửi lại; lần thử lại dùng cùng mã lệnh.</p>
            <div className="precase-completion-actions"><button className="valora-button valora-button--secondary" disabled={busy} onClick={() => void load()} type="button">Kiểm tra lại trạng thái</button>
              {retryable && loadState === "ready" && <button className="valora-button valora-button--primary" disabled={busy} onClick={retryPending} type="button">Thử lại cùng lệnh</button>}
            </div>
            {!retryable && <p>Dữ liệu hiện hành không còn khớp lần thử này. Hãy rà soát hồ sơ trước khi đưa ra quyết định mới.</p>}
            {!retryable && loadState === "ready" && <button className="valora-button valora-button--secondary" onClick={() => {
              setNotice(savePending(null)
                ? "Lần thử cũ đã được kết thúc sau khi xác minh trạng thái hiện hành. Hãy rà soát lại trước thao tác mới."
                : "Chưa thể kết thúc lần thử cũ trong phiên này. Hãy kiểm tra quyền lưu dữ liệu phiên rồi thử lại.");
            }} type="button">Kết thúc lần thử cũ</button>}
          </div>
        </section>}
      </div>

      <aside className="precase-completion-rail" aria-label="Ngữ cảnh và điều kiện tiếp nhận">
        <section className="valora-panel"><div className="valora-panel__header">Tình trạng hồ sơ</div><div className="valora-panel__body">
          <p className={projection.blockers.length > 0 && !committed ? "precase-completion-blocking" : undefined}>{committed ? "Pre-case đã khóa" : projection.next_action?.kind === "BLOCKER" ? "Có vấn đề đang ngăn bước tiếp theo" :
            unavailable ? "Bước Pre-case hiện chưa khả dụng" : result ? customer ? "Sẵn sàng xem điều kiện tiếp nhận" :
              selected.customer_id ? "Chưa thể xác minh Customer đã gắn" : "Cần gắn Customer" : "Cần tệp kết quả sơ bộ"}</p>
          <dl><div><dt>{projection.blockers.length > 0 && <span aria-hidden="true" className="precase-completion-severity-icon precase-completion-severity-icon--blocking">!</span>}Vấn đề ngăn bước</dt><dd className={projection.blockers.length > 0 ? "precase-completion-blocking" : undefined}>{projection.blockers.length}</dd></div>
            <div><dt>{projection.warnings.length > 0 && <span aria-hidden="true" className="precase-completion-severity-icon precase-completion-severity-icon--warning">⚠</span>}Cảnh báo</dt><dd className={projection.warnings.length > 0 ? "precase-completion-warning-count" : undefined}>{projection.warnings.length}</dd></div></dl>
          {projection.blockers.length > 0 && !committed && <button className="valora-button valora-button--secondary" onClick={() => onNavigate(projectOverviewPath(projectRef))} type="button">Xem vấn đề tại Tổng quan</button>}
          {projection.warnings.length > 0 && <p className="precase-completion-warning">Cảnh báo được giữ riêng; hệ thống không tự xem là vấn đề ngăn bước.</p>}
        </div></section>
        <section className="valora-panel"><div className="valora-panel__header">Thông tin hồ sơ</div><div className="valora-panel__body">
          <h3>Nhận diện</h3><dl><div><dt>Mã hồ sơ</dt><dd>{project.code}</dd></div>
            <div><dt>Tên hồ sơ</dt><dd>{project.name}</dd></div></dl>
          <h3>Mốc hồ sơ</h3><p>Chưa bổ sung tại bước này.</p>
          <h3>Giá trị & phí</h3><p>Chưa bổ sung tại bước này.</p>
        </div></section>
      </aside>
    </div>

    {confirmAction && <dialog aria-label="Xác nhận thao tác Pre-case" className="precase-completion-dialog" onCancel={() => setConfirmAction(null)} ref={confirmRef}>
      <div className="valora-panel"><div className="valora-panel__header">{confirmAction === "result" ? "Xác nhận tạo kết quả sơ bộ" : confirmAction === "customer" ? "Xác nhận gắn Customer" : "Xác nhận chuyển chính thức"}</div>
        <div className="valora-panel__body"><p>{confirmAction === "result"
          ? `Tạo tệp Excel bất biến từ bản phân tích sơ bộ ${selected.current_preliminary_analysis_version}.`
          : confirmAction === "customer"
            ? `Gắn ${selectedCustomer?.display_name || selectedCustomer?.legal_name || "Customer đã chọn"} với hồ sơ ${project.code}.`
            : `Chuyển ${project.code} sang thẩm định chính thức với kết quả sơ bộ bản ${result?.version} và Customer ${customer?.display_name || customer?.legal_name}. Pre-case sẽ được khóa.`}</p>
          <div className="precase-completion-actions"><button className="valora-button valora-button--secondary" onClick={() => setConfirmAction(null)} type="button">Quay lại</button>
            <button className="valora-button valora-button--primary" onClick={confirm} type="button">{confirmAction === "intake" ? "Xác nhận chuyển chính thức" : "Xác nhận"}</button></div>
        </div></div>
    </dialog>}
  </div>;
}
