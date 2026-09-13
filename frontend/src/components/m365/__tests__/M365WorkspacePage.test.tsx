import React from "react";
import { act, create } from "react-test-renderer";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  beginOneDriveAuthorization: vi.fn(),
  createIdempotencyKey: vi.fn(() => "adoption-test-key"),
  getAdoptionOptions: vi.fn(),
  getOneDriveConnection: vi.fn(),
  listOperationalDocuments: vi.fn(),
  provisionOperationalDocument: vi.fn(),
  revalidateOperationalDocument: vi.fn(),
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
    expect(text).toContain("đây không phải conflict mặc định");
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
      button.children.includes("Nhận làm tài liệu canonical"),
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
});
