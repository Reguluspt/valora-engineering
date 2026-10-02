import { act } from "react-test-renderer";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook } from "../../hooks/__tests__/renderHook";
import { useAssetReview } from "../useAssetReview";
import { fetchCaseState, type CaseStateResponse } from "../../../../api/caseState";
import { fetchAssetReviewReceipt, submitAssetReview, type LineCommandResponse } from "../../../../api/assetReview";
import type { AssetLineGridRow } from "../../AssetGridTypes";
vi.mock("../../../../api/caseState", () => ({ fetchCaseState: vi.fn() }));
vi.mock("../../../../api/assetReview", () => ({ fetchAssetReviewReceipt: vi.fn(), submitAssetReview: vi.fn() }));
const projectId = "11111111-1111-4111-8111-111111111111";
const lineId = "22222222-2222-4222-8222-222222222222";
const commandId = "33333333-3333-4333-8333-333333333333";
const token = "a".repeat(64);
function projection(reason = "line_validation_required"): CaseStateResponse {
  const blocked = reason.startsWith("review_") || reason === "validation_invalid";
  const reviewing = reason === "line_human_review_required";
  return { case_version: token, current_stage: "ASSET_REVIEW", stages: [{ stage: "ASSET_REVIEW", result: "INCOMPLETE" }],
    capabilities: [{ stage: "ASSET_REVIEW", available: true, provider_key: "asset_review_line_decision_v1", version: "asset_review_line_decision_v1" }],
    next_action: { kind: blocked ? "BLOCKER" : "PENDING", stage: "ASSET_REVIEW", validation_issue_id: null,
      semantic_route_key: blocked ? "asset_review_line_blocked" : reviewing ? "asset_review_line_review_required" : "asset_review_line_validate_required",
      context: { kind: "line", project_id: projectId, case_version: token, line_id: lineId,
        line_row_version: 1, confirmation_required: true, reason_code: reason,
        contract_version: reviewing || reason.startsWith("review_") ? "asset-line-human-review-v1" : "asset-line-validation-v1" } },
  } as CaseStateResponse;
}
const response = { result: { command_id: commandId, project_id: projectId, line_id: lineId,
  contract_version: "asset-line-validation-v1", proof_id: "generation-1", validation_outcome: "valid" },
  historical: false, replayed: false, current_case_version: token } as LineCommandResponse;
let roots: ReturnType<typeof renderHook>[] = [];
const mount = (changes = {}) => {
  const props = { projectId, sessionId: "owned-session", sessionBlocked: false,
    rows: [{ project_asset_line_id: lineId, row_version: 1 }] as AssetLineGridRow[],
    gridLoading: false, gridError: false, hasMore: false, loadingMore: false,
    loadMore: vi.fn(async () => {}), refreshGrid: vi.fn(), selectLine: vi.fn(), ...changes };
  const hook = renderHook(() => useAssetReview(props)); roots.push(hook);
  return { ...hook, props };
};
beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal("crypto", { randomUUID: () => commandId });
  vi.mocked(fetchCaseState).mockResolvedValue(projection());
  vi.mocked(submitAssetReview).mockResolvedValue(response);
});
afterEach(() => { roots.forEach(r => r.unmount()); roots = []; vi.unstubAllGlobals(); });
const settle = () => act(async () => { await Promise.resolve(); });

describe("Asset Review authority and recovery", () => {
  it("never mutates on loading/selection; confirms exact row/case with a new UUID", async () => {
    const hook = mount(); await settle();
    expect(submitAssetReview).not.toHaveBeenCalled();
    expect(hook.props.selectLine).toHaveBeenCalledWith(lineId);
    await act(async () => { await hook.result.current.submit("validate", "", token, lineId); });
    expect(submitAssetReview).toHaveBeenCalledExactlyOnceWith(projectId, lineId, {
      command_id: commandId, confirm: true, expected_case_version: token, expected_row_version: 1,
      contract_version: "asset-line-validation-v1",
    });
    expect(hook.props.refreshGrid).toHaveBeenCalledOnce();
    expect(fetchCaseState).toHaveBeenCalledTimes(2);
  });
  it("retains old-dialog scope and refuses a confirmation for a different version or line", async () => {
    const hook = mount(); await settle();
    await act(async () => { await hook.result.current.submit("validate", "", "b".repeat(64), lineId); });
    await act(async () => { await hook.result.current.submit("validate", "", token, projectId); });
    expect(submitAssetReview).not.toHaveBeenCalled();
  });
  it.each(["line_validation_warning", "validation_invalid", "permission_required", "session_required"])(
    "never offers Accept for %s", async reason => {
      const fresh = projection(reason);
      if (reason.endsWith("required") && !reason.startsWith("line_")) {
        fresh.next_action!.kind = "UNAVAILABLE"; fresh.next_action!.semantic_route_key = null;
      }
      vi.mocked(fetchCaseState).mockResolvedValue(fresh);
      const hook = mount(); await settle();
      expect(hook.result.current.canAccept).toBe(false);
      if (reason === "line_validation_warning") expect(hook.result.current.canValidate).toBe(false);
      await act(async () => { await hook.result.current.submit("accepted", "", token, lineId); });
      expect(submitAssetReview).not.toHaveBeenCalled();
    });
  it("loads existing bounded pagination to find the authoritative line; exhausted grid never invents it", async () => {
    const hook = mount({ rows: [], hasMore: true }); await settle();
    expect(hook.props.loadMore).toHaveBeenCalled();
    expect(hook.result.current.canValidate).toBe(false);
    hook.props.hasMore = false; hook.rerender(); await settle();
    expect(hook.result.current.row).toBeUndefined();
  });
  it("refreshes on session establishment and does not reuse pre-session authority", async () => {
    const hook = mount({ sessionId: undefined }); await settle();
    expect(hook.result.current.canValidate).toBe(false);
    hook.props.sessionId = "new-session"; hook.rerender(); await settle();
    expect(fetchCaseState).toHaveBeenCalledTimes(2);
    expect(hook.result.current.canValidate).toBe(true);
  });
  it("409 refreshes authority with no receipt polling or silent POST retry", async () => {
    vi.mocked(submitAssetReview).mockRejectedValue({ status: 409 });
    const hook = mount(); await settle();
    await act(async () => { await hook.result.current.submit("validate", "", token, lineId); });
    expect(submitAssetReview).toHaveBeenCalledOnce();
    expect(fetchAssetReviewReceipt).not.toHaveBeenCalled();
    expect(fetchCaseState).toHaveBeenCalledTimes(2);
    expect(hook.result.current.notice).toContain("xác nhận mới");
  });
  it("unknown outcome uses the exact receipt and zero extra POSTs", async () => {
    vi.mocked(submitAssetReview).mockRejectedValue({ status: 0 });
    vi.mocked(fetchAssetReviewReceipt).mockResolvedValue({ ...response, historical: true });
    const hook = mount(); await settle();
    await act(async () => { await hook.result.current.submit("validate", "", token, lineId); });
    expect(fetchAssetReviewReceipt).toHaveBeenCalledExactlyOnceWith(projectId, lineId, commandId);
    expect(submitAssetReview).toHaveBeenCalledOnce();
    expect(hook.result.current.result?.historical).toBe(true);
    expect(hook.result.current.pending).toBeNull();
  });
  it("unresolved receipt retains UUID and blocks new mutations; absence refetches before reconfirmation", async () => {
    vi.mocked(submitAssetReview).mockRejectedValue({ status: 500 });
    vi.mocked(fetchAssetReviewReceipt).mockRejectedValue({ status: 0 });
    const hook = mount(); await settle();
    await act(async () => { await hook.result.current.submit("validate", "", token, lineId); });
    expect(hook.result.current.pending?.commandId).toBe(commandId);
    expect(hook.result.current.canValidate).toBe(false);
    vi.mocked(fetchAssetReviewReceipt).mockRejectedValue({ status: 404 });
    await act(async () => { await hook.result.current.recover(); });
    expect(hook.result.current.pending).toBeNull();
    expect(fetchCaseState).toHaveBeenCalledTimes(3);
    expect(submitAssetReview).toHaveBeenCalledOnce();
  });
  it("negative holds require explicit valid-generation-bound reversal with prior ID and reason", async () => {
    const held = projection("review_flagged");
    held.next_action!.context!.prior_decision_id = "prior-decision";
    held.next_action!.context!.validation_generation_id = "generation-1";
    vi.mocked(fetchCaseState).mockResolvedValue(held);
    const hook = mount(); await settle();
    expect(hook.result.current.canAccept).toBe(false);
    await act(async () => { await hook.result.current.submit("validate", "", token, lineId); });
    expect(hook.result.current.canAccept).toBe(true);
    await act(async () => { await hook.result.current.submit("accepted", "", token, lineId); });
    expect(submitAssetReview).toHaveBeenCalledOnce();
    await act(async () => { await hook.result.current.submit("accepted", " Hold resolved ", token, lineId); });
    expect(vi.mocked(submitAssetReview).mock.calls[1][2]).toMatchObject({
      target_review_status: "accepted", reason_note: "Hold resolved", supersedes_decision_id: "prior-decision",
      contract_version: "asset-line-human-review-v1",
    });
  });
  it("refresh does not derive COMPLETE from accepted/valid grid strings", async () => {
    const hook = mount({ rows: [{ project_asset_line_id: lineId, row_version: 1,
      validation_status: "valid", review_status: "accepted" }] as AssetLineGridRow[] }); await settle();
    expect(hook.result.current.projection?.stages[0].result).toBe("INCOMPLETE");
    expect(hook.result.current.canValidate).toBe(true);
  });
});
