import { act } from "react-test-renderer";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { renderHook } from "../../hooks/__tests__/renderHook";
import { useAssetWorkbench } from "../useAssetWorkbench";
import { fetchCaseState, type CaseStateResponse } from "../../../../api/caseState";
import { fetchWorkbenchPreparation, fetchWorkbenchReceipt, submitWorkbench, type WorkbenchPreparation } from "../../../../api/assetWorkbench";
vi.mock("../../../../api/caseState", () => ({ fetchCaseState: vi.fn() }));
vi.mock("../../../../api/assetWorkbench", () => ({ fetchWorkbenchPreparation: vi.fn(), fetchWorkbenchReceipt: vi.fn(), submitWorkbench: vi.fn() }));
const id = "11111111-1111-4111-8111-111111111111";
const command = "22222222-2222-4222-8222-222222222222";
const token = "a".repeat(64);
const snapshot: WorkbenchPreparation = { project_id: id, case_version: token, project_row_version: 7, seal_id: id,
  authoritative_set_sha256: token, membership_version: 1, line_versions: [{ line_id: id, row_version: 5 }, { line_id: command, row_version: 3 }],
  prior_confirmation_id: null, withdrawn: false, can_confirm: true, can_withdraw: false, can_edit_description: true };
const state = { case_version: token, stages: [{ stage: "ASSET_WORKBENCH", result: "INCOMPLETE" }],
  capabilities: [{ stage: "ASSET_WORKBENCH", available: true, provider_key: "asset_workbench_confirmation_v1" }] } as CaseStateResponse;
const response = { result: { command_id: command, project_id: id, contract_version: "asset-workbench-confirmation-v1" }, historical: false } as any;
let roots: ReturnType<typeof renderHook>[] = [];
const settle = () => act(async () => { await Promise.resolve(); });
const mount = (changes = {}) => {
  const props = { projectId: id, sessionId: id, sessionBlocked: false, onRefresh: vi.fn(), ...changes };
  const hook = renderHook(() => useAssetWorkbench(props)); roots.push(hook); return { ...hook, props };
};
beforeEach(() => {
  vi.clearAllMocks(); vi.stubGlobal("crypto", { randomUUID: () => command });
  vi.mocked(fetchCaseState).mockResolvedValue(state);
  vi.mocked(fetchWorkbenchPreparation).mockResolvedValue({ ...snapshot });
  vi.mocked(submitWorkbench).mockResolvedValue(response);
});
afterEach(() => { roots.forEach(root => root.unmount()); roots = []; vi.unstubAllGlobals(); });
it("uses the entire server set, null optional price, and never forces COMPLETE from a receipt", async () => {
  const hook = mount(); await settle(); expect(submitWorkbench).not.toHaveBeenCalled();
  await act(async () => { await hook.result.current.submit("confirm", "", hook.result.current.snapshot!); });
  expect(submitWorkbench).toHaveBeenCalledExactlyOnceWith(id, {
    contract_version: "asset-workbench-confirmation-v1", command_id: command, confirm: true, expected_project_row_version: 7,
    expected_case_version: token, expected_seal_id: id, expected_authoritative_set_sha256: token, expected_membership_version: 1,
    expected_line_versions: snapshot.line_versions, reason_note: null, supersedes_confirmation_id: null,
  });
  expect(hook.result.current.projection?.stages[0].result).toBe("INCOMPLETE");
  expect(fetchCaseState).toHaveBeenCalledTimes(2);
});
it.each([400, 401, 403, 404, 409])("%s reloads and never silently resubmits", async status => {
  vi.mocked(submitWorkbench).mockRejectedValue({ status }); const hook = mount(); await settle();
  await act(async () => { await hook.result.current.submit("confirm", "", hook.result.current.snapshot!); });
  expect(submitWorkbench).toHaveBeenCalledOnce(); expect(fetchWorkbenchReceipt).not.toHaveBeenCalled();
  expect(fetchCaseState).toHaveBeenCalledTimes(2);
});
it("keeps uncertain outcome blocked until scoped receipt recovery succeeds", async () => {
  vi.mocked(submitWorkbench).mockRejectedValue({ status: 0 }); vi.mocked(fetchWorkbenchReceipt).mockRejectedValue({ status: 0 });
  const hook = mount(); await settle();
  await act(async () => { await hook.result.current.submit("confirm", "", hook.result.current.snapshot!); });
  expect(hook.result.current.pending?.commandId).toBe(command); expect(hook.result.current.canConfirm).toBe(false);
  vi.mocked(fetchWorkbenchReceipt).mockResolvedValue(response);
  await act(async () => { await hook.result.current.recover(); });
  expect(hook.result.current.pending).toBeNull(); expect(submitWorkbench).toHaveBeenCalledOnce();
});
it("fails closed when snapshots disagree, access is denied or session is blocked", async () => {
  vi.mocked(fetchWorkbenchPreparation).mockResolvedValue({ ...snapshot, case_version: "b".repeat(64) });
  const mismatch = mount(); await settle(); expect(mismatch.result.current.canConfirm).toBe(false);
  vi.mocked(fetchWorkbenchPreparation).mockRejectedValue({ status: 403 });
  const denied = mount(); await settle(); expect(denied.result.current.projection).toEqual(state); expect(denied.result.current.canConfirm).toBe(false);
  vi.mocked(fetchWorkbenchPreparation).mockResolvedValue(snapshot);
  const blocked = mount({ sessionBlocked: true }); await settle(); expect(blocked.result.current.canConfirm).toBe(false);
});
it("requires protected reason for reconfirmation and withdrawal while obeying server eligibility", async () => {
  vi.mocked(fetchWorkbenchPreparation).mockResolvedValue({ ...snapshot, prior_confirmation_id: id, can_withdraw: true });
  const hook = mount(); await settle();
  await act(async () => { await hook.result.current.submit("confirm", " ", hook.result.current.snapshot!); });
  expect(submitWorkbench).not.toHaveBeenCalled();
  await act(async () => { await hook.result.current.submit("confirm", "  refreshed facts  ", hook.result.current.snapshot!); });
  expect(vi.mocked(submitWorkbench).mock.calls[0][1]).toMatchObject({ reason_note: "refreshed facts", supersedes_confirmation_id: id });
  vi.mocked(submitWorkbench).mockResolvedValue({ ...response, result: { ...response.result, contract_version: "asset-workbench-withdrawal-v1" } });
  await act(async () => { await hook.result.current.submit("withdraw", "Explicit withdrawal", hook.result.current.snapshot!); });
  expect(vi.mocked(submitWorkbench).mock.calls[1][1]).toMatchObject({ expected_confirmation_id: id, contract_version: "asset-workbench-withdrawal-v1" });
  expect(vi.mocked(submitWorkbench).mock.calls[1][1]).not.toHaveProperty("supersedes_confirmation_id");
});
it("rejects an earlier dialog snapshot after refresh", async () => {
  const hook = mount(); await settle(); const old = hook.result.current.snapshot!;
  vi.mocked(fetchWorkbenchPreparation).mockResolvedValue({ ...snapshot });
  await act(async () => { await hook.result.current.refresh(); });
  await act(async () => { await hook.result.current.submit("confirm", "", old); });
  expect(submitWorkbench).not.toHaveBeenCalled();
});
it("does not offer an older preparation after the review surface observes a newer case token", async () => {
  const hook = mount({ revision: "b".repeat(64) }); await settle();
  expect(hook.result.current.canConfirm).toBe(false);
  await act(async () => { await hook.result.current.submit("confirm", "", hook.result.current.snapshot!); });
  expect(submitWorkbench).not.toHaveBeenCalled();
});
