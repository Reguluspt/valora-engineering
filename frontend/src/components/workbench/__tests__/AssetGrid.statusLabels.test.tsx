import { describe, it, expect } from "vitest";
import { validationLabel, reviewLabel } from "../AssetGrid";

describe("AssetGrid status labels", () => {
  it("validationLabel returns Vietnamese for every supported value", () => {
    expect(validationLabel("valid")).toBe("Hợp lệ");
    expect(validationLabel("warning")).toBe("Cảnh báo");
    expect(validationLabel("error")).toBe("Lỗi");
    expect(validationLabel("blocking")).toBe("Chặn");
    expect(validationLabel("unvalidated")).toBe("Chưa kiểm tra");
    expect(validationLabel("needs_review")).toBe("Cần kiểm tra");
  });

  it("reviewLabel returns Vietnamese for every supported value", () => {
    expect(reviewLabel("raw")).toBe("Thô");
    expect(reviewLabel("parsed")).toBe("Đã phân tích");
    expect(reviewLabel("identity_suggested")).toBe("Đề xuất định danh");
    expect(reviewLabel("identity_approved")).toBe("Đã định danh");
    expect(reviewLabel("taxonomy_approved")).toBe("Đã phân loại");
    expect(reviewLabel("knowledge_matched")).toBe("Đã khớp dữ liệu");
    expect(reviewLabel("price_reviewed")).toBe("Đã thẩm định giá");
    expect(reviewLabel("approved")).toBe("Đã duyệt");
    expect(reviewLabel("locked")).toBe("Đã khóa");
    expect(reviewLabel("excluded")).toBe("Đã loại");
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
