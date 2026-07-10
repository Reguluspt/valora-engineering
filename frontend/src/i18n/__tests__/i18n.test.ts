import { t, TranslationKey } from "../index";
import { vi } from "../vi";

describe("Vietnamese i18n label dictionary tests", () => {
  it("resolves known key translations to Vietnamese correctly", () => {
    expect(t("workbench.pageTitle")).toBe("Bàn làm việc hồ sơ");
    expect(t("nav.import")).toBe("Nhập dữ liệu");
    expect(t("nav.validate")).toBe("Kiểm tra dữ liệu");
    expect(t("action.saveDraft")).toBe("Lưu nháp");
    expect(t("nav.submitReview")).toBe("Gửi duyệt");
    expect(t("report.exportDraft")).toBe("Xuất báo cáo nháp");
    expect(t("auth.roleLabel")).toBe("Vai trò");
    expect(t("auth.orgLabel")).toBe("Đơn vị");
    expect(t("auth.org.gialai")).toBe("Chi nhánh Gia Lai");
    expect(t("workbench.statusLabel")).toBe("Trạng thái:");
    expect(t("workbench.issuesLabel")).toBe("Số lỗi: ");
    expect(t("workbench.unsavedChangesCount")).toBe("thay đổi chưa lưu");
    expect(t("workbench.sessionActive")).toBe("ĐANG HOẠT ĐỘNG");
    expect(t("workbench.sessionLocked")).toBe("Đã khóa");
    expect(t("workbench.status.initializing")).toBe("Đang khởi tạo phiên làm việc...");
    expect(t("workbench.status.stale")).toBe("Dữ liệu hồ sơ này đã được thay đổi bởi người dùng khác.");
    expect(t("workbench.status.staleAction")).toBe("Cập nhật mới");
    expect(t("workbench.status.retry")).toBe("Thử lại kết nối");
    expect(t("workbench.status.connectionError")).toBe("Lỗi kết nối máy chủ");
  });

  it("handles fallback defaults safely", () => {
    const fakeKey = "non_existent_key_test" as any;
    expect(t(fakeKey)).toBe(fakeKey);
  });

  it("asserts that zero user-facing labels leak forbidden technical keys or raw provider names", () => {
    const forbiddenTerms = [
      "API",
      "RBAC",
      "row_version",
      "session_id",
      "stack trace",
      "401",
      "403",
      "409",
      "422",
      "500",
      "Gemini",
      "DeepSeek"
    ];

    const entries = Object.entries(vi);
    for (const [key, val] of entries) {
      for (const term of forbiddenTerms) {
        // Assert that the user-facing translated string doesn't include the technical keyword
        const containsForbidden = val.toLowerCase().includes(term.toLowerCase());
        expect(containsForbidden).toBe(false);
      }
    }
  });

  it("assures that Valora Assistant maps to Trợ lý Valora", () => {
    expect(vi["assistant.name"]).toBe("Trợ lý Valora");
  });
});
