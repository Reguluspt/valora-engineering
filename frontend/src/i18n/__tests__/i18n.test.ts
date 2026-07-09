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
