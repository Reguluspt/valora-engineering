import React, { useCallback, useEffect, useMemo, useState } from "react";

import {
  AdoptionOptions,
  beginOneDriveAuthorization,
  createIdempotencyKey,
  getAdoptionOptions,
  getOneDriveConnection,
  listOperationalDocuments,
  OneDriveConnection,
  OneDriveEntry,
  OperationalDocument,
  provisionOperationalDocument,
  RevalidationClassification,
  revalidateOperationalDocument,
} from "../../api/m365";
import { APP_ROUTES } from "../../contracts/valoraV23";
import { useSession } from "../../auth/SessionProvider";
import { useResolvedProject } from "../workbench/project-context";
import { EmptyState } from "../common/EmptyState";
import { ErrorState } from "../common/ErrorState";
import { LoadingState } from "../common/LoadingState";
import "./m365Workspace.css";

const HANDOFF_KEY = "valora:m365-word-handoff";

const CLASSIFICATION_COPY: Record<
  RevalidationClassification,
  { label: string; detail: string; tone: string }
> = {
  no_change: {
    label: "Không có thay đổi",
    detail: "Tệp OneDrive vẫn khớp baseline đã xác minh.",
    tone: "safe",
  },
  external_change_outside_managed: {
    label: "Thay đổi ngoài vùng quản lý",
    detail: "Nội dung diễn giải bên ngoài vùng Valora đã thay đổi; đây không phải conflict mặc định.",
    tone: "notice",
  },
  external_change_in_managed: {
    label: "Thay đổi trong vùng quản lý",
    detail: "Có thay đổi cần được xem xét. Sync/conflict vẫn chưa được phép trong PR-07.",
    tone: "warning",
  },
  file_replaced_or_moved: {
    label: "Không xác minh được tệp gốc",
    detail: "Định danh tệp không còn đáng tin cậy; cần kết nối hoặc liên kết lại.",
    tone: "danger",
  },
  access_unavailable: {
    label: "Chưa thể truy cập OneDrive",
    detail: "Kết quả trước chỉ là ngữ cảnh cũ. Hãy thử kiểm tra lại hoặc kết nối lại.",
    tone: "danger",
  },
};

export function M365WorkspacePage({ projectRef }: { projectRef: string }) {
  const resolved = useResolvedProject(projectRef);
  if (resolved.state === "loading" || resolved.state === "idle") {
    return <LoadingState message="Đang xác định hồ sơ tài liệu…" />;
  }
  if (resolved.state === "error" || !resolved.projectId) {
    return (
      <ErrorState
        title="Chưa thể mở không gian tài liệu"
        message={resolved.error?.message || "Không thể xác định hồ sơ cần mở."}
        onRetry={resolved.retry}
      />
    );
  }
  return (
    <ResolvedM365Workspace
      key={resolved.projectId}
      projectId={resolved.projectId}
      projectName={resolved.displayName || "Hồ sơ"}
    />
  );
}

function ResolvedM365Workspace({ projectId, projectName }: { projectId: string; projectName: string }) {
  const { account } = useSession();
  const canAdopt = account?.permissions.includes("project:update") ?? false;
  const [connection, setConnection] = useState<OneDriveConnection | null>(null);
  const [documents, setDocuments] = useState<OperationalDocument[]>([]);
  const [options, setOptions] = useState<AdoptionOptions | null>(null);
  const [folderTrail, setFolderTrail] = useState<Array<{ id?: string; name: string }>>([
    { name: "OneDrive" },
  ]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [sectionError, setSectionError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<OneDriveEntry | null>(null);
  const [templateId, setTemplateId] = useState("");
  const [title, setTitle] = useState("");
  const [adopting, setAdopting] = useState(false);
  const [checkingDocumentId, setCheckingDocumentId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setState("loading");
    setSectionError(null);
    try {
      const [currentConnection, currentDocuments] = await Promise.all([
        getOneDriveConnection(),
        listOperationalDocuments(projectId),
      ]);
      setConnection(currentConnection);
      setDocuments(currentDocuments);
      if (currentConnection.status === "active" && canAdopt) {
        const currentOptions = await getAdoptionOptions(projectId);
        setOptions(currentOptions);
        setTemplateId((existing) => existing || currentOptions.templates[0]?.template_version_id || "");
      } else {
        setOptions(null);
      }
      setState("ready");
    } catch {
      setState("error");
    }
  }, [canAdopt, projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  const refreshDocuments = useCallback(async () => {
    setDocuments(await listOperationalDocuments(projectId));
  }, [projectId]);

  const checkDocument = useCallback(
    async (document: OperationalDocument) => {
      setCheckingDocumentId(document.document_id);
      setSectionError(null);
      try {
        await revalidateOperationalDocument(projectId, document.readiness);
        await refreshDocuments();
      } catch {
        setSectionError("Chưa thể kiểm tra thay đổi. Thông tin hiện tại được giữ ở trạng thái cũ.");
      } finally {
        setCheckingDocumentId(null);
      }
    },
    [projectId, refreshDocuments],
  );

  useEffect(() => {
    const onFocus = () => {
      const documentId = sessionStorage.getItem(HANDOFF_KEY);
      if (!documentId) return;
      sessionStorage.removeItem(HANDOFF_KEY);
      const document = documents.find((item) => item.document_id === documentId);
      if (document) void checkDocument(document);
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [checkDocument, documents]);

  const navigateFolder = async (folder: OneDriveEntry) => {
    setSectionError(null);
    try {
      const next = await getAdoptionOptions(projectId, folder.drive_item_id);
      setOptions(next);
      setFolderTrail((trail) => [...trail, { id: folder.drive_item_id, name: folder.name }]);
      setSelectedFile(null);
    } catch {
      setSectionError("Chưa thể mở thư mục OneDrive này. Vui lòng thử lại.");
    }
  };

  const navigateTrail = async (index: number) => {
    const target = folderTrail[index];
    setSectionError(null);
    try {
      const next = await getAdoptionOptions(projectId, target.id);
      setOptions(next);
      setFolderTrail((trail) => trail.slice(0, index + 1));
      setSelectedFile(null);
    } catch {
      setSectionError("Chưa thể quay lại thư mục đã chọn.");
    }
  };

  const connect = async () => {
    setSectionError(null);
    try {
      const authorizationUrl = await beginOneDriveAuthorization();
      window.location.assign(authorizationUrl);
    } catch {
      setSectionError("Chưa thể bắt đầu kết nối Microsoft. Vui lòng thử lại.");
    }
  };

  const adopt = async () => {
    if (!options || !selectedFile || !templateId || !title.trim()) return;
    setAdopting(true);
    setSectionError(null);
    try {
      await provisionOperationalDocument(projectId, {
        template_version_id: templateId,
        connection_id: options.connection_id,
        drive_item_id: selectedFile.drive_item_id,
        title: title.trim(),
        data_snapshot: options.data_snapshot,
        idempotency_key: createIdempotencyKey("adoption"),
      });
      setSelectedFile(null);
      setTitle("");
      await refreshDocuments();
    } catch {
      setSectionError("Không thể nhận tài liệu này. Hãy tải lại lựa chọn và kiểm tra tệp DOCX.");
    } finally {
      setAdopting(false);
    }
  };

  const openInWord = (document: OperationalDocument) => {
    sessionStorage.setItem(HANDOFF_KEY, document.document_id);
    window.open(document.readiness.web_url, "_blank", "noopener,noreferrer");
  };

  if (state === "loading") return <LoadingState message="Đang tải trạng thái OneDrive…" />;
  if (state === "error" || !connection) {
    return (
      <ErrorState
        title="Chưa thể tải không gian OneDrive"
        message="Không thể đọc trạng thái kết nối hoặc tài liệu của hồ sơ."
        onRetry={() => void load()}
      />
    );
  }

  return (
    <main className="m365-page">
      <header className="m365-header">
        <div>
          <p>ONEDRIVE PERSONAL · READ-ONLY INTEGRATION</p>
          <h1>{projectName}</h1>
          <span>Mở trong Word, quay lại Valora và kiểm tra thay đổi có kiểm soát.</span>
        </div>
        <ConnectionBadge connection={connection} />
      </header>

      {sectionError && <div className="m365-inline-error" role="alert">{sectionError}</div>}

      {connection.status !== "active" ? (
        <section className="m365-connect-panel">
          <div>
            <p>BƯỚC 01</p>
            <h2>Kết nối OneDrive Personal</h2>
            <span>
              Valora chỉ yêu cầu quyền đọc tệp. Tài khoản Business và SharePoint không nằm trong
              phạm vi này.
            </span>
          </div>
          {canAdopt ? (
            <button onClick={() => void connect()} type="button">Kết nối Microsoft</button>
          ) : (
            <p className="m365-permission-note">Tài khoản cần quyền cập nhật hồ sơ để kết nối.</p>
          )}
        </section>
      ) : (
        <div className="m365-layout">
          <section className="m365-documents" aria-labelledby="m365-documents-title">
            <div className="m365-section-heading">
              <div>
                <p>TÀI LIỆU CANONICAL</p>
                <h2 id="m365-documents-title">Tài liệu của hồ sơ</h2>
              </div>
              <span>{documents.length}</span>
            </div>
            {documents.length === 0 ? (
              <div className="m365-empty-copy">
                <strong>Chưa có tài liệu OneDrive được nhận</strong>
                <span>Chọn một DOCX ở khu vực bên phải để tạo lineage đầu tiên.</span>
              </div>
            ) : (
              <div className="m365-document-list">
                {documents.map((document) => (
                  <DocumentCard
                    canManageConnection={canAdopt}
                    checking={checkingDocumentId === document.document_id}
                    document={document}
                    key={document.document_id}
                    onCheck={() => void checkDocument(document)}
                    onOpen={() => openInWord(document)}
                    onReconnect={() => void connect()}
                  />
                ))}
              </div>
            )}
          </section>

          <aside className="m365-adoption" aria-labelledby="m365-adoption-title">
            <div className="m365-section-heading">
              <div>
                <p>BƯỚC 02 · NHẬN TỆP HIỆN CÓ</p>
                <h2 id="m365-adoption-title">Chọn DOCX từ OneDrive</h2>
              </div>
            </div>
            {!canAdopt ? (
              <p className="m365-permission-note">Bạn có quyền xem nhưng chưa có quyền nhận tài liệu.</p>
            ) : options ? (
              <>
                <nav className="m365-breadcrumb" aria-label="Đường dẫn thư mục">
                  {folderTrail.map((folder, index) => (
                    <button key={`${folder.id || "root"}-${index}`} onClick={() => void navigateTrail(index)} type="button">
                      {folder.name}
                    </button>
                  ))}
                </nav>
                <div className="m365-file-list">
                  {options.items.length === 0 && <span>Thư mục này không có DOCX hoặc thư mục con.</span>}
                  {options.items.map((item) => (
                    <button
                      className={selectedFile?.drive_item_id === item.drive_item_id ? "is-selected" : ""}
                      key={item.drive_item_id}
                      onClick={() => item.kind === "folder" ? void navigateFolder(item) : setSelectedFile(item)}
                      type="button"
                    >
                      <span>{item.kind === "folder" ? "THƯ MỤC" : "DOCX"}</span>
                      <strong>{item.name}</strong>
                      {item.size_bytes != null && <small>{formatBytes(item.size_bytes)}</small>}
                    </button>
                  ))}
                </div>
                {options.truncated && <p className="m365-truncated">Danh sách đã đạt giới hạn 100 mục.</p>}
                <div className="m365-adoption-form">
                  <label>
                    Mẫu và vùng quản lý
                    <select onChange={(event) => setTemplateId(event.target.value)} value={templateId}>
                      {options.templates.map((template) => (
                        <option key={template.template_version_id} value={template.template_version_id}>
                          {template.template_name} · v{template.version_number}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Tên tài liệu trong Valora
                    <input
                      onChange={(event) => setTitle(event.target.value)}
                      placeholder={selectedFile?.name.replace(/\.docx$/i, "") || "Chọn một tệp DOCX trước"}
                      value={title}
                    />
                  </label>
                  <div className="m365-selected-file">
                    <span>Tệp đã chọn</span>
                    <strong>{selectedFile?.name || "Chưa chọn"}</strong>
                  </div>
                  <button
                    className="m365-primary-action"
                    disabled={!selectedFile || !templateId || !title.trim() || adopting}
                    onClick={() => void adopt()}
                    type="button"
                  >
                    {adopting ? "Đang xác minh và nhận…" : "Nhận làm tài liệu canonical"}
                  </button>
                  <small>
                    Thao tác chỉ đọc tệp để xác minh baseline; không ghi nội dung trở lại OneDrive.
                  </small>
                </div>
              </>
            ) : (
              <div className="m365-empty-copy">Chưa có lựa chọn OneDrive khả dụng.</div>
            )}
          </aside>
        </div>
      )}
    </main>
  );
}

function ConnectionBadge({ connection }: { connection: OneDriveConnection }) {
  const connected = connection.status === "active";
  return (
    <div className={`m365-connection-badge ${connected ? "is-active" : ""}`}>
      <span>{connected ? "ĐÃ KẾT NỐI" : "CHƯA SẴN SÀNG"}</span>
      <strong>{connected ? "OneDrive Personal" : connection.status}</strong>
      <small>{connection.last_verified_at ? `Xác minh ${formatDate(connection.last_verified_at)}` : "Chưa xác minh"}</small>
    </div>
  );
}

function DocumentCard({
  canManageConnection,
  document,
  checking,
  onOpen,
  onCheck,
  onReconnect,
}: {
  canManageConnection: boolean;
  document: OperationalDocument;
  checking: boolean;
  onOpen: () => void;
  onCheck: () => void;
  onReconnect: () => void;
}) {
  const presentation = document.readiness.classification
    ? CLASSIFICATION_COPY[document.readiness.classification]
    : {
        label: "Chưa kiểm tra sau khi nhận",
        detail: "Hãy kiểm tra thay đổi để có trạng thái freshness hiện tại.",
        tone: "stale",
      };
  const nextAction = document.readiness.next_action;
  const primaryAction = nextAction === "check_changes" || nextAction === "retry_revalidation"
    ? { label: checking ? "Đang kiểm tra…" : "Kiểm tra thay đổi", run: onCheck, disabled: checking }
    : nextAction === "reconnect_or_rebind"
      ? canManageConnection
        ? { label: "Kết nối lại OneDrive", run: onReconnect, disabled: false }
        : { label: "Cần quyền kết nối lại", run: onReconnect, disabled: true }
      : { label: nextAction === "review_managed_changes" ? "Mở trong Word để xem" : "Mở trong Word", run: onOpen, disabled: false };
  const primaryIsOpen = primaryAction.run === onOpen;
  const primaryIsCheck = primaryAction.run === onCheck;
  return (
    <article
      className="m365-document-card"
      data-recovery-code={document.readiness.recovery_code || undefined}
    >
      <div className="m365-document-title">
        <span>{document.document_type}</span>
        <h3>{document.title}</h3>
        <p>{document.readiness.file_name} · Revision {document.readiness.document_revision}</p>
      </div>
      <div className={`m365-classification m365-classification--${presentation.tone}`}>
        <strong>{presentation.label}</strong>
        <span>{presentation.detail}</span>
        {document.readiness.recovery_code && (
          <small>Mã hỗ trợ: {document.readiness.recovery_code}</small>
        )}
        {document.readiness.completed_at && <small>Kiểm tra {formatDate(document.readiness.completed_at)}</small>}
      </div>
      <div className="m365-document-actions">
        <button
          className="m365-primary-action"
          disabled={primaryAction.disabled}
          onClick={primaryAction.run}
          type="button"
        >
          {primaryAction.label}
        </button>
        {!primaryIsOpen && <button onClick={onOpen} type="button">Mở trong Word</button>}
        {!primaryIsCheck && document.readiness.baseline_eligible && (
          <button disabled={checking} onClick={onCheck} type="button">
            {checking ? "Đang kiểm tra…" : "Kiểm tra lại"}
          </button>
        )}
      </div>
    </article>
  );
}

export function M365ReturnPage({ currentPath, onNavigate }: { currentPath: string; onNavigate: (path: string) => void }) {
  const [connection, setConnection] = useState<OneDriveConnection | null>(null);
  const [failed, setFailed] = useState(false);
  const query = useMemo(() => new URLSearchParams(currentPath.split("?", 2)[1] || ""), [currentPath]);

  useEffect(() => {
    setFailed(query.get("m365") === "failed");
    getOneDriveConnection().then(setConnection).catch(() => setFailed(true));
  }, [query]);

  if (!connection && !failed) return <LoadingState message="Đang xác nhận kết nối OneDrive…" />;
  const connected = connection?.status === "active" && !failed;
  return (
    <main className="m365-return-page">
      <p>MICROSOFT CALLBACK · SERVER VERIFIED</p>
      <h1>{connected ? "OneDrive Personal đã sẵn sàng." : "Kết nối chưa hoàn tất."}</h1>
      <span>
        {connected
          ? "Valora đã đọc lại trạng thái kết nối từ server. Anh/chị có thể chọn hồ sơ để làm việc."
          : "Không có token hay chi tiết nhà cung cấp nào được đưa về trình duyệt. Vui lòng thử kết nối lại từ hồ sơ."}
      </span>
      <button onClick={() => onNavigate(APP_ROUTES.projectList)} type="button">Về danh sách hồ sơ</button>
    </main>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}
