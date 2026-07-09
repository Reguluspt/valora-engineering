import { getFriendlyError, getFriendlyErrorFromHttpStatus, getFriendlyErrorFromUnknown } from "../errorRegistry";
import { ERROR_REGISTRY } from "../errorRegistry";
import { ErrorCode } from "../errorTypes";

describe("Non-IT central error message registry tests", () => {
  it("maps HTTP status codes to friendly Vietnamese error dialog blocks correctly", () => {
    const err401 = getFriendlyErrorFromHttpStatus(401);
    expect(err401.title).toBe("Phiên làm việc đã hết hạn");
    expect(err401.severity).toBe("blocking");

    const err403 = getFriendlyErrorFromHttpStatus(403);
    expect(err403.title).toBe("Tài khoản chưa được cấp quyền thực hiện thao tác này");
    expect(err403.severity).toBe("error");

    const err409 = getFriendlyErrorFromHttpStatus(409);
    expect(err409.title).toBe("Dữ liệu hồ sơ này đã được thay đổi bởi người dùng khác");
    expect(err409.severity).toBe("error");

    const err422 = getFriendlyErrorFromHttpStatus(422);
    expect(err422.title).toBe("Thông tin nhập vào chưa đúng định dạng");
    expect(err422.severity).toBe("warning");

    const err500 = getFriendlyErrorFromHttpStatus(500);
    expect(err500.title).toBe("Hệ thống gặp lỗi xử lý nội bộ");
    expect(err500.severity).toBe("error");
  });

  it("ensures user-facing translated string blocks contain zero forbidden technical terms", () => {
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

    const codes = Object.keys(ERROR_REGISTRY) as ErrorCode[];
    for (const code of codes) {
      const err = ERROR_REGISTRY[code];
      
      // All fields must be populated
      expect(err.title).toBeTruthy();
      expect(err.message).toBeTruthy();
      expect(err.nextAction).toBeTruthy();
      expect(err.severity).toBeTruthy();
      expect(err.retryable !== undefined).toBe(true);

      for (const term of forbiddenTerms) {
        expect(err.title.toLowerCase()).not.toContain(term.toLowerCase());
        expect(err.message.toLowerCase()).not.toContain(term.toLowerCase());
        expect(err.nextAction.toLowerCase()).not.toContain(term.toLowerCase());
      }
    }
  });

  it("shields AI provider names and maps errors to Trợ lý Valora", () => {
    const errTimeout = getFriendlyError("assistant_timeout");
    expect(errTimeout.title).toContain("Trợ lý Valora");
    expect(errTimeout.title).not.toContain("Gemini");
    expect(errTimeout.title).not.toContain("DeepSeek");

    const errUnavailable = getFriendlyError("assistant_unavailable");
    expect(errUnavailable.title).toContain("Trợ lý Valora");
    expect(errUnavailable.message).toContain("hỗ trợ thông minh");
  });

  it("handles unknown/corrupted error types safely without leaking internal logs", () => {
    const fallback = getFriendlyErrorFromUnknown({ status: 999 });
    expect(fallback.title).toBe("Hệ thống gặp sự cố không xác định");
    expect(fallback.message).not.toContain("999");
  });

  it("verifies generic fallback codes exist and have expected structure", () => {
    const unknownErr = getFriendlyError("unknown_error");
    expect(unknownErr.title).toBe("Hệ thống gặp sự cố không xác định");
    expect(unknownErr.retryable).toBe(true);

    const serverErr = getFriendlyError("server_error");
    expect(serverErr.title).toBe("Hệ thống gặp lỗi xử lý nội bộ");
    expect(serverErr.retryable).toBe(true);

    const tempErr = getFriendlyError("temporary_failure");
    expect(tempErr.title).toBe("Thao tác tạm thời thất bại");
    expect(tempErr.retryable).toBe(true);
  });
});
