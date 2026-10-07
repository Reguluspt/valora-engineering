import { act } from "react-test-renderer";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { renderHook } from "../../hooks/__tests__/renderHook";
import { usePriceEvidence } from "../usePriceEvidence";
import { fetchCaseState, type CaseStateResponse } from "../../../../api/caseState";
import { fetchEvidencePreparation, fetchEvidenceWorkspace, fetchEvidenceReceipt, submitEvidence, EVIDENCE_CONTRACTS,
  type EvidencePreparation, type EvidenceWorkspace, type EvidenceReceipt, type EvidenceIntent } from "../../../../api/priceEvidence";
vi.mock("../../../../api/caseState", () => ({ fetchCaseState: vi.fn() }));
vi.mock("../../../../api/priceEvidence", async original => ({ ...await original<typeof import("../../../../api/priceEvidence")>(),
  fetchEvidencePreparation: vi.fn(), fetchEvidenceWorkspace: vi.fn(), fetchEvidenceReceipt: vi.fn(), submitEvidence: vi.fn() }));
const id = "11111111-1111-4111-8111-111111111111", command = "22222222-2222-4222-8222-222222222222", token = "a".repeat(64);
const prep: EvidencePreparation = { project_id: id, case_version: token, project_row_version: 5, seal_id: id,
  authoritative_set_sha256: token, membership_version: 1, workbench_confirmation_id: id, prior_confirmation_id: null,
  lines: [{ line_id: id, row_version: 2, proof_sha256: token }, { line_id: command, row_version: 3, proof_sha256: token }],
  sources: [], decisions: [], can_register: true, can_decide: true, can_confirm: true, can_withdraw: true };
const view: EvidenceWorkspace = { project_id: id, case_version: token, line_id: id, sealed_count: 2, covered_count: 2,
  confirmation_id: null, confirmation_withdrawn: false, confirmation_current: false, can_withdraw_confirmation: false,
  line_covered: true, line_hold: false, reason_codes: [], sources: [], offset: 0, total: 0, next_offset: null };
const state = { case_version: token, stages: [{ stage: "PRICE_EVIDENCE", result: "INCOMPLETE" }],
  capabilities: [{ stage: "PRICE_EVIDENCE", provider_key: "price_evidence_confirmation_v1", available: true }] } as CaseStateResponse;
const intent: EvidenceIntent = { operation: "confirm", supersedes_confirmation_id: null, reason_note: null };
const result = { result: { project_id: id, command_id: command, contract_version: EVIDENCE_CONTRACTS.confirm }, historical: true } as EvidenceReceipt;
let roots: ReturnType<typeof renderHook>[] = [];
let storage: Map<string, string>;
const settle = () => act(async () => { await Promise.resolve(); });
const mount = (changes = {}) => {
  const props = { projectId: id, lineId: id, actorScope: "operator", sessionId: id, sessionBlocked: false, onRefresh: vi.fn(), ...changes };
  const hook = renderHook(() => usePriceEvidence(props)); roots.push(hook); return { ...hook, props };
};
beforeEach(() => {
  vi.clearAllMocks(); storage = new Map();
  vi.stubGlobal("crypto", { randomUUID: vi.fn(() => command) });
  vi.stubGlobal("sessionStorage", { getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value), removeItem: (key: string) => storage.delete(key) });
  vi.mocked(fetchCaseState).mockResolvedValue(state);
  vi.mocked(fetchEvidencePreparation).mockImplementation(async () => ({ ...prep }));
  vi.mocked(fetchEvidenceWorkspace).mockResolvedValue(view);
  vi.mocked(submitEvidence).mockResolvedValue(result);
});
afterEach(() => { roots.forEach(root => root.unmount()); roots = []; vi.unstubAllGlobals(); });
it("submits one exact whole-set snapshot then reads fresh authority without treating receipt as COMPLETE", async () => {
  const hook = mount(); await settle(); expect(hook.result.current.enabled).toBe(true);
  const before = vi.mocked(fetchCaseState).mock.calls.length;
  await act(async () => { await hook.result.current.submit(intent, hook.result.current.snapshot!); });
  expect(submitEvidence).toHaveBeenCalledExactlyOnceWith(id, intent, prep, command);
  expect(fetchCaseState).toHaveBeenCalledTimes(before + 1);
  expect(hook.result.current.projection?.stages[0].result).toBe("INCOMPLETE");
  expect(hook.props.onRefresh).toHaveBeenCalledOnce(); expect(storage.size).toBe(0);
});
it.each([400, 401, 403, 404, 409])("%s refreshes without replay or automatic receipt lookup", async status => {
  vi.mocked(submitEvidence).mockRejectedValue({ status }); const hook = mount(); await settle();
  await act(async () => { await hook.result.current.submit(intent, hook.result.current.snapshot!); });
  expect(submitEvidence).toHaveBeenCalledOnce(); expect(fetchEvidenceReceipt).not.toHaveBeenCalled();
  expect(hook.result.current.pending).toBeNull(); expect(storage.size).toBe(0);
});
it.each([0, 500])("unknown %s persists the original UUID through remount and requires explicit scoped historical receipt recovery", async status => {
  vi.mocked(submitEvidence).mockRejectedValue({ status }); const first = mount(); await settle();
  await act(async () => { await first.result.current.submit(intent, first.result.current.snapshot!); });
  expect(first.result.current.enabled).toBe(false); expect(first.result.current.pending?.commandId).toBe(command);
  expect(fetchEvidenceReceipt).not.toHaveBeenCalled(); first.unmount(); roots = [];
  const restored = mount(); await settle(); expect(restored.result.current.pending?.commandId).toBe(command);
  vi.mocked(fetchEvidenceReceipt).mockResolvedValue(result);
  await act(async () => { await restored.result.current.recover(); });
  expect(fetchEvidenceReceipt).toHaveBeenCalledExactlyOnceWith(id, command);
  expect(restored.result.current.pending).toBeNull(); expect(submitEvidence).toHaveBeenCalledOnce();
  expect(restored.result.current.projection?.stages[0].result).toBe("INCOMPLETE");
});
it("rejects mismatched or nonhistorical receipts and retains recovery while fresh reads fail", async () => {
  vi.mocked(submitEvidence).mockResolvedValue({ ...result, historical: false }); const hook = mount(); await settle();
  await act(async () => { await hook.result.current.submit(intent, hook.result.current.snapshot!); });
  expect(hook.result.current.pending?.commandId).toBe(command);
  vi.mocked(fetchEvidenceReceipt).mockResolvedValue({ ...result, result: { ...result.result, project_id: command } });
  await act(async () => { await hook.result.current.recover(); });
  expect(hook.result.current.pending?.commandId).toBe(command);
  vi.mocked(fetchEvidenceReceipt).mockResolvedValue(result); vi.mocked(fetchEvidenceWorkspace).mockRejectedValue({ status: 500 });
  await act(async () => { await hook.result.current.recover(); });
  expect(hook.result.current.pending?.commandId).toBe(command); expect(hook.result.current.workspace).toEqual(view);
  expect(hook.result.current.enabled).toBe(false);
});
it.each([401, 403, 404])("denied read %s removes retained protected display and locks writes", async status => {
  const hook = mount(); await settle(); vi.mocked(fetchEvidenceWorkspace).mockRejectedValue({ status });
  await act(async () => { await hook.result.current.refresh(); });
  expect(hook.result.current.workspace).toBeNull(); expect(hook.result.current.projection).toBeNull();
  expect(hook.result.current.enabled).toBe(false); expect(hook.result.current.error).not.toBe("");
});
it("keeps usable data on background error, but disables writes", async () => {
  const hook = mount(); await settle(); vi.mocked(fetchEvidenceWorkspace).mockRejectedValue({ status: 500 });
  await act(async () => { await hook.result.current.refresh(); });
  expect(hook.result.current.workspace).toEqual(view); expect(hook.result.current.enabled).toBe(false);
  expect(hook.result.current.error).not.toBe("");
});
it("rejects old dialog snapshot, newer upstream case, mismatched line, provider and invalid session", async () => {
  const hook = mount(); await settle(); const old = hook.result.current.snapshot!;
  const newerToken = "b".repeat(64);
  vi.mocked(fetchCaseState).mockResolvedValue({ ...state, case_version: newerToken });
  vi.mocked(fetchEvidencePreparation).mockResolvedValue({ ...prep, case_version: newerToken });
  vi.mocked(fetchEvidenceWorkspace).mockResolvedValue({ ...view, case_version: newerToken });
  await act(async () => { await hook.result.current.refresh(); });
  await act(async () => { await hook.result.current.submit(intent, old); }); expect(submitEvidence).not.toHaveBeenCalled();
  const newer = mount({ revision: token }); await settle(); expect(newer.result.current.enabled).toBe(false);
  const blocked = mount({ sessionBlocked: true }); await settle(); expect(blocked.result.current.enabled).toBe(false);
  vi.mocked(fetchEvidenceWorkspace).mockResolvedValue({ ...view, line_id: command });
  const wrong = mount(); await settle(); expect(wrong.result.current.enabled).toBe(false);
  vi.mocked(fetchEvidenceWorkspace).mockResolvedValue(view); vi.mocked(fetchCaseState).mockResolvedValue({ ...state, capabilities: [] });
  const noProvider = mount(); await settle(); expect(noProvider.result.current.enabled).toBe(false);
});
it("allows an unchanged authoritative dialog token after a harmless refresh", async () => {
  const hook = mount(); await settle(); const approved = hook.result.current.snapshot!;
  await act(async () => { await hook.result.current.refresh(); });
  await act(async () => { await hook.result.current.submit(intent, approved); });
  expect(submitEvidence).toHaveBeenCalledOnce();
});
it("non-DRAFT server flags preserve COMPLETE reads but reject new confirmation", async () => {
  vi.mocked(fetchCaseState).mockResolvedValue({ ...state, stages: [{ ...state.stages[0], result: "COMPLETE" }] });
  vi.mocked(fetchEvidencePreparation).mockResolvedValue({ ...prep, can_confirm: false, can_register: false, can_withdraw: false, can_decide: false });
  const hook = mount(); await settle();
  await act(async () => { await hook.result.current.submit(intent, hook.result.current.snapshot!); });
  expect(submitEvidence).not.toHaveBeenCalled(); expect(hook.result.current.projection?.stages[0].result).toBe("COMPLETE");
});
it("reconfirmation and withdrawal require exact server target and a nonblank reason", async () => {
  vi.mocked(fetchEvidencePreparation).mockResolvedValue({ ...prep, prior_confirmation_id: id });
  vi.mocked(fetchEvidenceWorkspace).mockResolvedValue({ ...view, confirmation_id: id, can_withdraw_confirmation: true });
  const hook = mount(); await settle();
  for (const invalid of [intent, { ...intent, supersedes_confirmation_id: id },
    { operation: "withdraw-confirmation", expected_confirmation_id: command, reason_note: "reason" },
    { operation: "withdraw-confirmation", expected_confirmation_id: id, reason_note: " " }] as EvidenceIntent[]) {
    await act(async () => { await hook.result.current.submit(invalid, hook.result.current.snapshot!); });
  }
  expect(submitEvidence).not.toHaveBeenCalled();
  await act(async () => { await hook.result.current.submit({ ...intent, supersedes_confirmation_id: id, reason_note: "Reviewed current evidence" }, hook.result.current.snapshot!); });
  expect(submitEvidence).toHaveBeenCalledOnce();
});
it("changing actor or project hides prior data and does not adopt another scope's command", async () => {
  vi.mocked(submitEvidence).mockRejectedValue({ status: 0 }); const hook = mount(); await settle();
  await act(async () => { await hook.result.current.submit(intent, hook.result.current.snapshot!); });
  hook.props.actorScope = "viewer"; hook.rerender(); await settle();
  expect(hook.result.current.pending).toBeNull(); expect(fetchEvidenceReceipt).not.toHaveBeenCalled();
  expect(storage.has(`valora:price-evidence:operator:${id}`)).toBe(true);
});
