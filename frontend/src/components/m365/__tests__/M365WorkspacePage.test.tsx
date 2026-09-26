import React from "react";
import { act, create } from "react-test-renderer";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";

const api = vi.hoisted(() => ({
  beginOneDriveAuthorization: vi.fn(),
  createExchangeCopy: vi.fn(),
  createIdempotencyKey: vi.fn(() => "adoption-test-key"),
  getAdoptionOptions: vi.fn(),
  getOneDriveConnection: vi.fn(),
  importExchangeDocx: vi.fn(),
  importExchangeXlsx: vi.fn(),
  listExchangeArtifacts: vi.fn(),
  listOperationalDocuments: vi.fn(),
  provisionOperationalDocument: vi.fn(),
  revalidateOperationalDocument: vi.fn(),
  reimportExchangeArtifact: vi.fn(),
}));
const session = vi.hoisted(() => ({
  permissions: ["project:read", "project:update"],
}));

vi.mock("../../../api/m365", () => api);
vi.mock("../../workbench/project-context", () => ({
  useResolvedProject: () => ({
    state: "ready",
    projectId: "project-1",
    displayName: "Nhà máy An Phú",
  }),
}));
vi.mock("../../../auth/SessionProvider", () => ({
  useSession: () => ({
    account: { permissions: session.permissions },
  }),
}));

import { M365ReturnPage, M365WorkspacePage } from "../M365WorkspacePage";

const snapshot = {
  contract_version: "valora-operational-adoption-v1",
  project_id: "project-1",
  project_row_version: 2,
};

const readinessBase = {
  document_revision_id: "revision-1",
  document_revision: 1,
  binding_id: "binding-1",
  drive_id: "drive-1",
  drive_item_id: "item-current",
  file_name: "Bao-cao.docx",
  file_path: null,
  web_url: "https://onedrive.live.com/document",
  baseline_eligible: true,
  recovery_code: null,
  completed_at: "2026-09-13T01:00:00Z",
  affected_region_keys: [],
  is_fresh: true,
  is_safe_for_freshness_required_action: true,
  stale_reason: null,
  blocking_reason: null,
  next_action: null,
  retryable: false,
};

function document(classification: string, index: number) {
  return {
    document_id: `document-${index}`,
    title: `Báo cáo ${index}`,
    document_type: "valuation_report",
    readiness: {
      ...readinessBase,
      document_id: `document-${index}`,
      classification,
    },
  };
}

describe("M365WorkspacePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    session.permissions = ["project:read", "project:update"];
    vi.stubGlobal("sessionStorage", {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
    vi.stubGlobal("window", {
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      open: vi.fn(),
      location: { assign: vi.fn() },
    });
    api.getOneDriveConnection.mockResolvedValue({
      connection_id: "connection-1",
      drive_id: "drive-1",
      status: "active",
      last_verified_at: "2026-09-13T00:00:00Z",
      capability_state: "read-only",
      read_available: true,
      appfolder_write_available: false,
    });
    api.getAdoptionOptions.mockResolvedValue({
      project_id: "project-1",
      project_code: "HS-01",
      project_name: "Nhà máy An Phú",
      connection_id: "connection-1",
      drive_id: "drive-1",
      parent_item_id: null,
      data_snapshot: snapshot,
      templates: [
        {
          template_version_id: "template-1",
          template_name: "Mẫu báo cáo",
          document_type: "valuation_report",
          version_number: 1,
        },
      ],
      items: [
        {
          drive_item_id: "item-1",
          kind: "docx",
          name: "Bao-cao.docx",
          size_bytes: 2048,
          last_modified_at: null,
          web_url: "https://onedrive.live.com/item-1",
        },
      ],
      truncated: false,
    });
    api.provisionOperationalDocument.mockResolvedValue({ document_id: "new-document" });
    api.beginOneDriveAuthorization.mockResolvedValue("https://login.microsoftonline.com/consumers");
    api.revalidateOperationalDocument.mockResolvedValue(undefined);
    api.listExchangeArtifacts.mockResolvedValue([]);
    api.createExchangeCopy.mockResolvedValue({ artifact_id: "exchange-copy" });
    api.importExchangeDocx.mockResolvedValue({ artifact_id: "exchange-import" });
    api.importExchangeXlsx.mockResolvedValue({ artifact_id: "exchange-xlsx" });
    api.reimportExchangeArtifact.mockResolvedValue({ artifact_id: "exchange-reimport" });
  });

  it("selects a document context without changing its revision", async () => {
    api.listOperationalDocuments.mockResolvedValue([
      document("no_change", 1),
      { ...document("external_change_in_managed", 2), readiness: { ...document("external_change_in_managed", 2).readiness, document_revision: 4 } },
    ]);
    let root: any;
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });

    const cards = root.root.findAllByType("article");
    const selectSecond = cards[1].findAllByType("button").find((button: any) =>
      button.children.includes("Xem chi tiết"),
    );
    act(() => selectSecond.props.onClick());

    const context = root.root.findByProps({ "aria-label": "Tài liệu đang xem" });
    expect(context.findByType("h3").children).toContain("Báo cáo 2");
    expect(context.findAllByType("dd")[0].children).toContain("4");
    expect(api.revalidateOperationalDocument).not.toHaveBeenCalled();
    expect(api.reimportExchangeArtifact).not.toHaveBeenCalled();
  });

  it("renders provider-neutral h1, case identity, and no retired QC/PDF/lock workflows", async () => {
    api.listOperationalDocuments.mockResolvedValue([]);
    let root: any;
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });

    const h1 = root.root.findByType("h1");
    expect(h1.children).toEqual(["Không gian tài liệu"]);

    const text = JSON.stringify(root.toJSON());
    expect(text).toContain("Hồ sơ · ");
    expect(text).toContain("Nhà máy An Phú");
    expect(text).toContain("Mở trong Word, quay lại Valora và kiểm tra thay đổi có kiểm soát.");

    expect(text).not.toContain("Khóa phiên bản");
    expect(text).not.toContain("Xuất PDF");
    expect(text).not.toContain("phê duyệt");
    expect(text).not.toContain("QC");
    expect(text).not.toContain("reviewer");
  });

  it("renders all five server classifications without deriving a conflict", async () => {
    api.listOperationalDocuments.mockResolvedValue([
      document("no_change", 1),
      document("external_change_outside_managed", 2),
      document("external_change_in_managed", 3),
      document("file_replaced_or_moved", 4),
      document("access_unavailable", 5),
    ]);
    let root: any;
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });

    const text = JSON.stringify(root.toJSON());
    expect(text).toContain("Không có thay đổi");
    expect(text).toContain("Thay đổi ngoài vùng quản lý");
    expect(text).toContain("Thay đổi trong vùng quản lý");
    expect(text).toContain("Không xác minh được tệp gốc");
    expect(text).toContain("Chưa thể truy cập OneDrive");
    expect(text).toContain("không mặc định là xung đột");
    expect(text).not.toContain("xung đột phiên bản");
  });

  it("preserves returned document list when connection is disconnected", async () => {
    api.getOneDriveConnection.mockResolvedValue({
      connection_id: null,
      drive_id: null,
      status: "not_connected",
      last_verified_at: null,
      capability_state: "read-only",
      read_available: false,
      appfolder_write_available: false,
    });
    api.listOperationalDocuments.mockResolvedValue([
      document("no_change", 1),
      document("file_replaced_or_moved", 2),
    ]);
    let root: any;
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });

    const text = JSON.stringify(root.toJSON());
    expect(text).toContain("Kết nối OneDrive hiện chưa sẵn sàng. Các tài liệu trong hồ sơ vẫn được hiển thị bên dưới.");
    expect(text).toContain("Báo cáo 1");
    expect(text).toContain("Báo cáo 2");
  });

  it("distinguishes permission denied (403) from empty documents", async () => {
    api.listOperationalDocuments.mockRejectedValue(new ApiError("Forbidden", 403));
    let root: any;
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });

    const text = JSON.stringify(root.toJSON());
    expect(text).toContain("Không có quyền xem tài liệu hồ sơ");
    expect(text).toContain("Tài khoản hiện tại chưa có quyền truy cập không gian tài liệu này.");
    expect(text).not.toContain("Chưa có tài liệu trong hồ sơ");
    expect(text).not.toContain("Bộ tài liệu hồ sơ");
  });

  it("adopts one selected DOCX with the unchanged server snapshot", async () => {
    api.listOperationalDocuments.mockResolvedValue([]);
    let root: any;
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });

    const fileButton = root.root.findAllByType("button").find((button: any) =>
      button.findAllByType("strong").some((strong: any) => strong.children.includes("Bao-cao.docx")),
    );
    act(() => fileButton.props.onClick());
    const titleInput = root.root.findByType("input");
    act(() => titleInput.props.onChange({ target: { value: "Báo cáo canonical" } }));
    const adoptButton = root.root.findAllByType("button").find((button: any) =>
      button.children.includes("Nhận làm tài liệu hồ sơ"),
    );
    await act(async () => adoptButton.props.onClick());

    expect(api.provisionOperationalDocument).toHaveBeenCalledWith(
      "project-1",
      expect.objectContaining({
        connection_id: "connection-1",
        drive_item_id: "item-1",
        template_version_id: "template-1",
        title: "Báo cáo canonical",
        data_snapshot: snapshot,
      }),
    );
  });

  it("keeps adoption unavailable without project:update", async () => {
    session.permissions = ["project:read"];
    api.listOperationalDocuments.mockResolvedValue([]);
    let root: any;
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });

    expect(JSON.stringify(root.toJSON())).toContain("chưa có quyền nhận tài liệu");
    expect(api.getAdoptionOptions).not.toHaveBeenCalled();
  });

  it("keeps initial connection unavailable without project:update", async () => {
    session.permissions = ["project:read"];
    api.getOneDriveConnection.mockResolvedValue({
      connection_id: null,
      drive_id: null,
      status: "not_connected",
      last_verified_at: null,
    });
    let root: any;
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });

    const text = JSON.stringify(root.toJSON());
    expect(text).toContain("Tài khoản cần quyền cập nhật hồ sơ để kết nối");
    expect(root.root.findAllByType("button").some((button: any) =>
      button.children.includes("Kết nối OneDrive"),
    )).toBe(false);
    expect(api.beginOneDriveAuthorization).not.toHaveBeenCalled();
  });

  it("disables a document reconnect recovery without project:update", async () => {
    session.permissions = ["project:read"];
    const untrusted = document("file_replaced_or_moved", 1);
    untrusted.readiness.next_action = "reconnect_or_rebind";
    untrusted.readiness.recovery_code = "binding_untrusted";
    untrusted.readiness.baseline_eligible = false;
    api.listOperationalDocuments.mockResolvedValue([untrusted]);
    let root: any;
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });

    const text = JSON.stringify(root.toJSON());
    expect(text).toContain("Cần quyền kết nối lại");
    expect(text).toContain("Mã hỗ trợ: ");
    expect(text).toContain("binding_untrusted");
    const recovery = root.root.findAllByType("button").find((button: any) =>
      button.children.includes("Cần quyền kết nối lại"),
    );
    expect(recovery.props.disabled).toBe(true);
    expect(api.beginOneDriveAuthorization).not.toHaveBeenCalled();
  });

  it("revalidates once when focus returns from a Word handoff", async () => {
    let focusListener: (() => void) | undefined;
    const storedDocument = document("no_change", 1);
    vi.stubGlobal("sessionStorage", {
      getItem: vi.fn(() => "document-1"),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
    vi.stubGlobal("window", {
      addEventListener: vi.fn((name: string, listener: () => void) => {
        if (name === "focus") focusListener = listener;
      }),
      removeEventListener: vi.fn(),
      open: vi.fn(),
      location: { assign: vi.fn() },
    });
    api.listOperationalDocuments.mockResolvedValue([storedDocument]);
    await act(async () => {
      create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });

    await act(async () => focusListener?.());

    expect(api.revalidateOperationalDocument).toHaveBeenCalledWith(
      "project-1",
      storedDocument.readiness,
    );
    expect(sessionStorage.removeItem).toHaveBeenCalledWith("valora:m365-word-handoff");
  });

  it("keeps usable documents visible during background revalidation check and on failure", async () => {
    const doc = document("no_change", 1);
    api.listOperationalDocuments.mockResolvedValue([doc]);
    api.revalidateOperationalDocument.mockRejectedValueOnce(new Error("Network glitch"));
    let root: any;
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });

    expect(JSON.stringify(root.toJSON())).toContain("Báo cáo 1");

    const checkButton = root.root.findAllByType("button").find((button: any) =>
      button.children.includes("Kiểm tra lại"),
    );
    await act(async () => checkButton.props.onClick());

    const text = JSON.stringify(root.toJSON());
    expect(text).toContain("Chưa thể kiểm tra thay đổi. Thông tin hiện tại được giữ ở trạng thái cũ.");
    expect(text).toContain("Báo cáo 1");
  });

  it("handles next_action variants for check_changes and review_managed_changes", async () => {
    const checkDoc = document("external_change_in_managed", 1);
    checkDoc.readiness.next_action = "check_changes";

    const reviewDoc = document("external_change_in_managed", 2);
    reviewDoc.readiness.next_action = "review_managed_changes";

    api.listOperationalDocuments.mockResolvedValue([checkDoc, reviewDoc]);
    let root: any;
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });

    const checkBtn = root.root.findAllByType("button").find((button: any) =>
      button.children.includes("Kiểm tra thay đổi"),
    );
    expect(checkBtn).toBeDefined();
    await act(async () => checkBtn.props.onClick());
    expect(api.revalidateOperationalDocument).toHaveBeenCalledWith("project-1", checkDoc.readiness);

    const reviewBtn = root.root.findAllByType("article")[1].findAllByType("button").find((button: any) =>
      button.children.includes("Mở trong Word"),
    );
    expect(reviewBtn).toBeDefined();
    act(() => reviewBtn.props.onClick());
    expect(sessionStorage.setItem).toHaveBeenCalledWith("valora:m365-word-handoff", "document-2");
    expect(window.open).toHaveBeenCalledWith(reviewDoc.readiness.web_url, "_blank", "noopener,noreferrer");
  });

  it("uses server next_action for the primary recovery action", async () => {
    const untrusted = document("file_replaced_or_moved", 1);
    untrusted.readiness.next_action = "reconnect_or_rebind";
    untrusted.readiness.recovery_code = "binding_untrusted";
    untrusted.readiness.baseline_eligible = false;
    api.listOperationalDocuments.mockResolvedValue([untrusted]);
    let root: any;
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });
    const recovery = root.root.findAllByType("button").find((button: any) =>
      button.children.includes("Kết nối lại OneDrive"),
    );

    await act(async () => recovery.props.onClick());

    expect(api.beginOneDriveAuthorization).toHaveBeenCalledOnce();
    expect(window.location.assign).toHaveBeenCalledWith(
      "https://login.microsoftonline.com/consumers",
    );
  });

  it("renders callback outcome from authoritative connection status", async () => {
    const navigate = vi.fn();
    let root: any;
    await act(async () => {
      root = create(
        React.createElement(M365ReturnPage, {
          currentPath: "/workbench/m365/return?m365=connected",
          onNavigate: navigate,
        }),
      );
    });

    expect(JSON.stringify(root.toJSON())).toContain("OneDrive Personal đã sẵn sàng");
    expect(api.getOneDriveConnection).toHaveBeenCalledOnce();
  });

  it("keeps Exchange write actions behind explicit reconsent", async () => {
    api.listOperationalDocuments.mockResolvedValue([]);
    let root: any;
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });
    const text = JSON.stringify(root.toJSON());
    expect(text).toContain("OneDrive Personal");
    expect(text).toContain("Cấp quyền trao đổi tệp");
    expect(text).toContain("Lưu trong Word chưa cập nhật phiên bản chính thức trong VALORA.");
    const upgrade = root.root.findAllByType("button").find((button: any) =>
      button.children.includes("Cấp quyền trao đổi tệp"),
    );
    await act(async () => upgrade.props.onClick());
    expect(api.beginOneDriveAuthorization).toHaveBeenCalledWith("exchange_write");
  });

  it("shows bounded Exchange capabilities only for an AppFolder grant", async () => {
    api.getOneDriveConnection.mockResolvedValue({
      connection_id: "connection-1",
      drive_id: "drive-1",
      status: "active",
      last_verified_at: "2026-09-13T00:00:00Z",
      capability_state: "exchange-write-ready",
      read_available: true,
      appfolder_write_available: true,
    });
    api.listOperationalDocuments.mockResolvedValue([]);
    let root: any;
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });
    const text = JSON.stringify(root.toJSON());
    expect(text).toContain("Thư mục trao đổi AppFolder đã sẵn sàng cho các thao tác bên dưới.");
    expect(text).toContain("Trao đổi tệp có kiểm soát");
    expect(text).toContain("Bản làm việc");
    expect(text).toContain("Nhập nguồn Excel");
    expect(text).toContain("Xuất sang OneDrive");
    expect(text).not.toContain("Cấp quyền trao đổi tệp");
  });

  it("wires AppFolder actions to bounded Exchange API commands", async () => {
    api.getOneDriveConnection.mockResolvedValue({
      connection_id: "connection-1",
      drive_id: "drive-1",
      status: "active",
      last_verified_at: "2026-09-13T00:00:00Z",
      capability_state: "exchange-write-ready",
      read_available: true,
      appfolder_write_available: true,
    });
    api.listOperationalDocuments.mockResolvedValue([document("no_change", 1)]);
    api.listExchangeArtifacts.mockResolvedValue([
      {
        artifact_id: "working-1",
        connection_id: "connection-1",
        role: "inbox",
        media: "xlsx",
        state: "AVAILABLE",
        display_name: "Bang-tinh-working.xlsx",
        document_id: "document-1",
        document_revision_id: "revision-1",
        excel_import_batch_id: null,
        excel_source_artifact_id: null,
      },
    ]);
    let root: any;
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });

    const working = root.root.findAllByType("button").find((button: any) =>
      button.children.includes("Bản làm việc"),
    );
    await act(async () => working.props.onClick());
    expect(api.createExchangeCopy).toHaveBeenCalledWith(
      "project-1",
      "document-1",
      "working",
      expect.objectContaining({ connection_id: "connection-1" }),
    );

    const reimport = root.root.findAllByType("button").find((button: any) =>
      button.children.includes("Nhập nguồn Excel"),
    );
    await act(async () => reimport.props.onClick());
    expect(api.reimportExchangeArtifact).toHaveBeenCalledWith(
      "project-1",
      "working-1",
      null,
    );
  });

  it("prohibits DOCX working copy from re-import and excludes DOCX from Excel re-import select", async () => {
    api.getOneDriveConnection.mockResolvedValue({
      connection_id: "connection-1",
      drive_id: "drive-1",
      status: "active",
      last_verified_at: "2026-09-13T00:00:00Z",
      capability_state: "exchange-write-ready",
      read_available: true,
      appfolder_write_available: true,
    });
    api.listOperationalDocuments.mockResolvedValue([document("no_change", 1)]);
    api.listExchangeArtifacts.mockResolvedValue([
      {
        artifact_id: "working-docx-1",
        connection_id: "connection-1",
        role: "working",
        media: "docx",
        state: "AVAILABLE",
        display_name: "Bao-cao-working.docx",
        document_id: "document-1",
        document_revision_id: "revision-1",
        excel_import_batch_id: null,
        excel_source_artifact_id: null,
      },
    ]);
    let root: any;
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });

    const select = root.root.findAllByType("select").find((sel: any) =>
      sel.findAllByType("option").some((opt: any) => opt.children.includes("Chưa có tệp Excel nguồn")),
    );
    expect(select).toBeDefined();

    const optionsText = JSON.stringify(select.findAllByType("option").map((opt: any) => opt.children));
    expect(optionsText).not.toContain("Bao-cao-working.docx");

    const reimportBtn = root.root.findAllByType("button").find((button: any) =>
      button.children.includes("Nhập nguồn Excel"),
    );
    expect(reimportBtn.props.disabled).toBe(true);

    const text = JSON.stringify(root.toJSON());
    expect(text).not.toContain("Nhập thay đổi");
    expect(text).not.toContain("Nhập lại DOCX");

    expect(api.reimportExchangeArtifact).not.toHaveBeenCalled();
  });

  it("allows XLSX artifact to call reimportExchangeArtifact with null template while excluding DOCX from that select", async () => {
    api.getOneDriveConnection.mockResolvedValue({
      connection_id: "connection-1",
      drive_id: "drive-1",
      status: "active",
      last_verified_at: "2026-09-13T00:00:00Z",
      capability_state: "exchange-write-ready",
      read_available: true,
      appfolder_write_available: true,
    });
    api.listOperationalDocuments.mockResolvedValue([document("no_change", 1)]);
    api.listExchangeArtifacts.mockResolvedValue([
      {
        artifact_id: "docx-artifact-1",
        connection_id: "connection-1",
        role: "working",
        media: "docx",
        state: "AVAILABLE",
        display_name: "Bao-cao-working.docx",
        document_id: "document-1",
        document_revision_id: "revision-1",
        excel_import_batch_id: null,
        excel_source_artifact_id: null,
      },
      {
        artifact_id: "xlsx-artifact-1",
        connection_id: "connection-1",
        role: "inbox",
        media: "xlsx",
        state: "AVAILABLE",
        display_name: "So-lieu.xlsx",
        document_id: "document-1",
        document_revision_id: "revision-1",
        excel_import_batch_id: null,
        excel_source_artifact_id: null,
      },
    ]);
    let root: any;
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });

    const select = root.root.findAllByType("select").find((sel: any) =>
      sel.findAllByType("option").some((opt: any) => opt.children.some((c: any) => typeof c === "string" && c.includes("So-lieu.xlsx"))),
    );
    expect(select).toBeDefined();

    const optionsLabels = select.findAllByType("option").map((opt: any) => opt.children.join(""));
    expect(optionsLabels).toContain("So-lieu.xlsx · XLSX");
    expect(optionsLabels.some((label: string) => label.includes("Bao-cao-working.docx"))).toBe(false);

    const reimportBtn = root.root.findAllByType("button").find((button: any) =>
      button.children.includes("Nhập nguồn Excel"),
    );
    expect(reimportBtn.props.disabled).toBe(false);

    await act(async () => reimportBtn.props.onClick());
    expect(api.reimportExchangeArtifact).toHaveBeenCalledWith(
      "project-1",
      "xlsx-artifact-1",
      null,
    );
  });

  it("Working copy copy states Word save or check is not an official revision", async () => {
    api.listOperationalDocuments.mockResolvedValue([]);
    let root: any;
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });

    const text = JSON.stringify(root.toJSON());
    expect(text).toContain("Lưu trong Word chưa cập nhật phiên bản chính thức trong VALORA.");
    expect(text).toContain(
      "Quy trình rà soát và xác nhận thay đổi từ bản làm việc Word chưa khả dụng trên giao diện này. Lưu hoặc kiểm tra thay đổi từ bản làm việc không tạo phiên bản chính thức mới.",
    );
  });

  it("gates Exchange actions panel behind project:update permission", async () => {
    session.permissions = ["project:read"];
    api.getOneDriveConnection.mockResolvedValue({
      connection_id: "connection-1",
      drive_id: "drive-1",
      status: "active",
      last_verified_at: "2026-09-13T00:00:00Z",
      capability_state: "exchange-write-ready",
      read_available: true,
      appfolder_write_available: true,
    });
    api.listOperationalDocuments.mockResolvedValue([]);
    let root: any;
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });

    const text = JSON.stringify(root.toJSON());
    expect(text).not.toContain("Trao đổi tệp có kiểm soát");
    expect(api.listExchangeArtifacts).not.toHaveBeenCalled();

    api.getOneDriveConnection.mockResolvedValue({
      connection_id: "connection-1",
      drive_id: "drive-1",
      status: "active",
      last_verified_at: "2026-09-13T00:00:00Z",
      capability_state: "read-only",
      read_available: true,
      appfolder_write_available: false,
    });
    await act(async () => {
      root = create(React.createElement(M365WorkspacePage, { projectRef: "project-1" }));
    });
    const readOnlyText = JSON.stringify(root.toJSON());
    expect(readOnlyText).toContain("Cần cấp quyền trao đổi từ người có quyền cập nhật hồ sơ.");
    expect(
      root.root.findAllByType("button").some((button: any) =>
        button.children.includes("Cấp quyền trao đổi tệp"),
      ),
    ).toBe(false);
  });
});
