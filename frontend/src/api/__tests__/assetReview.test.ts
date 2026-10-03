import { beforeEach, expect, it, vi } from "vitest";
import { request } from "../client";
import { submitAssetReview, fetchAssetReviewReceipt, type LineCommandRequest } from "../assetReview";
vi.mock("../client", () => ({ request: vi.fn() }));
beforeEach(() => vi.clearAllMocks());
it("sends only exact typed confirmed contracts through existing A4 routes", () => {
  const payload: LineCommandRequest = { command_id: "uuid", confirm: true, expected_row_version: 7,
    expected_case_version: "a".repeat(64), contract_version: "asset-line-validation-v1" };
  submitAssetReview("project", "line", payload);
  expect(request).toHaveBeenCalledWith("/api/v1/projects/project/asset-lines/line/validate", {
    method: "POST", body: JSON.stringify(payload),
  });
  const review = { ...payload, contract_version: "asset-line-human-review-v1" as const,
    target_review_status: "flagged" as const, reason_note: "Human reason", supersedes_decision_id: "prior" };
  submitAssetReview("project", "line", review);
  expect(request).toHaveBeenLastCalledWith("/api/v1/projects/project/asset-lines/line/review-decision", {
    method: "POST", body: JSON.stringify(review),
  });
});
it("receipt recovery is scoped GET with the original UUID, never a POST replay", () => {
  fetchAssetReviewReceipt("project", "line", "original");
  expect(request).toHaveBeenCalledExactlyOnceWith("/api/v1/projects/project/asset-lines/line/command-receipts/original");
});
