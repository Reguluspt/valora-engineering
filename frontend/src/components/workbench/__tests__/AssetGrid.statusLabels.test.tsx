import { describe, it, expect } from "vitest";
import { validationLabel, reviewLabel } from "../AssetGrid";

describe("AssetGrid status labels", () => {
  it("validationLabel returns Vietnamese for every supported value", () => {
    expect(validationLabel("valid")).toBe("Hợp lệ");
    expect(validationLabel("warning")).toBe("Cảnh báo");
    expect(validationLabel("invalid")).toBe("Không hợp lệ");
    expect(validationLabel("unvalidated")).toBe("Chưa kiểm tra");
    expect(validationLabel("needs_review")).toBe("Chưa xác định");
    expect(validationLabel("error")).toBe("Chưa xác định");
    expect(validationLabel("blocking")).toBe("Chưa xác định");
  });

  it("reviewLabel returns Vietnamese for every supported value", () => {
    expect(reviewLabel("pending")).toBe("Chờ rà soát");
    expect(reviewLabel("accepted")).toBe("Đã chấp nhận");
    expect(reviewLabel("flagged")).toBe("Đã gắn cờ");
    expect(reviewLabel("rejected")).toBe("Đã từ chối");
    for (const value of ["raw", "parsed", "approved", "locked", "excluded", "identity_approved"])
      expect(reviewLabel(value)).toBe("Chưa xác định");
  });

  it("unknown/null/undefined all return Chưa xác định", () => {
    expect(validationLabel("nonexistent")).toBe("Chưa xác định");
    expect(reviewLabel("foobar")).toBe("Chưa xác định");
    expect(validationLabel(null)).toBe("Chưa xác định");
    expect(reviewLabel(null)).toBe("Chưa xác định");
    expect(validationLabel(undefined)).toBe("Chưa xác định");
    expect(reviewLabel(undefined)).toBe("Chưa xác định");
  });

  it("helpers do not mutate the original enum variables", () => {
    const rawValidation = "valid";
    const rawReview = "raw";
    validationLabel(rawValidation);
    reviewLabel(rawReview);
    expect(rawValidation).toBe("valid");
    expect(rawReview).toBe("raw");
  });
});
