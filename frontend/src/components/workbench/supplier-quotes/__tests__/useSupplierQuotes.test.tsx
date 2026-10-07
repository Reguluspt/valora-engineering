import { act } from "react-test-renderer";
import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { renderHook } from "../../hooks/__tests__/renderHook";
import { useSupplierQuotes } from "../useSupplierQuotes";
import { fetchCaseState } from "../../../../api/caseState";
import { fetchQuotePreparation, fetchQuoteHistory, fetchQuoteSuppliers, fetchQuoteSources, fetchQuoteReceipt, submitQuoteCommand } from "../../../../api/supplierQuotes";
import { id, revision, command, token, state, prep, quote, source, supplier, receipt } from "./fixtures";
vi.mock("../../../../api/caseState", () => ({ fetchCaseState: vi.fn() }));
vi.mock("../../../../api/supplierQuotes", async original => ({ ...await original<typeof import("../../../../api/supplierQuotes")>(),
  fetchQuotePreparation: vi.fn(), fetchQuoteHistory: vi.fn(), fetchQuoteSuppliers: vi.fn(), fetchQuoteSources: vi.fn(), fetchQuoteReceipt: vi.fn(), submitQuoteCommand: vi.fn() }));
let roots: ReturnType<typeof renderHook>[] = [];
let storage: Map<string, string>;
const settle = () => act(async () => { await Promise.resolve(); });
const intent = { operation: "confirm" as const, quote_id: id, revision_id: revision };
const mount = (changes = {}) => { const props = { projectId: id, sessionId: id, sessionBlocked: false, actorScope: "actor", onRefresh: vi.fn(), ...changes };
  const hook = renderHook(() => useSupplierQuotes(props)); roots.push(hook); return { ...hook, props }; };
beforeEach(() => {
  vi.clearAllMocks(); storage = new Map(); vi.stubGlobal("sessionStorage", { getItem: (k: string) => storage.get(k) || null,
    setItem: (k: string, v: string) => storage.set(k, v), removeItem: (k: string) => storage.delete(k) });
  vi.spyOn(crypto, "randomUUID").mockReturnValue(command);
  vi.mocked(fetchCaseState).mockResolvedValue(state); vi.mocked(fetchQuotePreparation).mockResolvedValue(prep);
  vi.mocked(fetchQuoteHistory).mockResolvedValue({ items: [quote], case_version: token, offset: 0, limit: 50, next_offset: null });
  vi.mocked(fetchQuoteSuppliers).mockResolvedValue({ items: [supplier], offset: 0, limit: 50, next_offset: null });
  vi.mocked(fetchQuoteSources).mockResolvedValue({ items: [source], offset: 0, limit: 50, next_offset: null });
  vi.mocked(submitQuoteCommand).mockResolvedValue(receipt);
});
afterEach(() => { roots.forEach(r => r.unmount()); roots = []; vi.restoreAllMocks(); vi.unstubAllGlobals(); });
it("one click sends once and fetches fresh preparation/history/Case State without locally confirming", async () => {
  const hook = mount(); await settle(); expect(hook.result.current.enabled).toBe(true);
  vi.clearAllMocks(); await act(async () => { await hook.result.current.submit(intent, token); });
  expect(submitQuoteCommand).toHaveBeenCalledOnce(); expect(fetchQuotePreparation).toHaveBeenCalledOnce();
  expect(fetchQuoteHistory).toHaveBeenCalledOnce(); expect(fetchCaseState).toHaveBeenCalledOnce();
  expect(hook.result.current.history?.items[0].status).toBe("draft"); expect(hook.result.current.snapshot?.result).toBe("INCOMPLETE");
});
it.each([0, 500])("unknown %s keeps original UUID across remount and reconciles receipt before fresh reads", async status => {
  vi.mocked(submitQuoteCommand).mockRejectedValue({ status }); const first = mount(); await settle();
  await act(async () => { await first.result.current.submit(intent, token); });
  expect(first.result.current.pending?.commandId).toBe(command); expect(first.result.current.enabled).toBe(false);
  first.unmount(); roots = []; const restored = mount(); await settle(); vi.mocked(fetchQuoteReceipt).mockResolvedValue(receipt);
  vi.clearAllMocks(); await act(async () => { await restored.result.current.recover(); });
  expect(fetchQuoteReceipt).toHaveBeenCalledExactlyOnceWith(id, command); expect(submitQuoteCommand).not.toHaveBeenCalled();
  expect(vi.mocked(fetchQuoteReceipt).mock.invocationCallOrder[0]).toBeLessThan(vi.mocked(fetchQuotePreparation).mock.invocationCallOrder[0]);
  expect(restored.result.current.pending).toBeNull(); expect(restored.result.current.snapshot?.result).toBe("INCOMPLETE");
});
it.each([404, 500])("receipt %s does not permit blind retry or allocate another UUID", async status => {
  vi.mocked(submitQuoteCommand).mockRejectedValue({ status: 500 }); const hook = mount(); await settle();
  await act(async () => { await hook.result.current.submit(intent, token); }); vi.mocked(fetchQuoteReceipt).mockRejectedValue({ status });
  await act(async () => { await hook.result.current.recover(); await hook.result.current.submit(intent, token); });
  expect(hook.result.current.pending?.commandId).toBe(command); expect(submitQuoteCommand).toHaveBeenCalledOnce(); expect(crypto.randomUUID).toHaveBeenCalledOnce();
});
it.each([400, 401, 403, 404, 409])("command %s refreshes authority and never retries", async status => {
  vi.mocked(submitQuoteCommand).mockRejectedValue({ status }); const hook = mount(); await settle(); vi.clearAllMocks();
  await act(async () => { await hook.result.current.submit(intent, token); });
  expect(submitQuoteCommand).toHaveBeenCalledOnce(); expect(fetchCaseState).toHaveBeenCalledOnce(); expect(hook.result.current.notice).not.toBe("");
  if ([401, 403].includes(status)) expect(hook.result.current.enabled).toBe(false);
});
it.each([401, 403, 404])("read %s removes protected content and locks writes", async status => {
  const hook = mount(); await settle(); vi.mocked(fetchQuoteHistory).mockRejectedValue({ status });
  await act(async () => { await hook.result.current.refresh(); });
  expect(hook.result.current.history).toBeNull(); expect(hook.result.current.snapshot).toBeNull(); expect(hook.result.current.enabled).toBe(false);
});
it("preserves usable content during background error and refuses incoherent or old form context", async () => {
  const hook = mount(); await settle(); vi.mocked(fetchQuoteHistory).mockRejectedValue({ status: 500 });
  await act(async () => { await hook.result.current.refresh(); }); expect(hook.result.current.history?.items).toEqual([quote]); expect(hook.result.current.enabled).toBe(false);
  vi.mocked(fetchQuoteHistory).mockResolvedValue({ items: [quote], case_version: "b".repeat(64), offset: 0, limit: 50, next_offset: null });
  await act(async () => { await hook.result.current.refresh(); }); expect(hook.result.current.enabled).toBe(false);
  await act(async () => { await hook.result.current.submit(intent, "b".repeat(64)); }); expect(submitQuoteCommand).not.toHaveBeenCalled();
});
it("shows the server STALE result when integrity prevents reading quotation history", async () => {
  vi.mocked(fetchCaseState).mockResolvedValue({ ...state, stages: [{ stage: "SUPPLIER_QUOTES", result: "STALE", provider_key: "supplier_quotes_v1" }] });
  vi.mocked(fetchQuotePreparation).mockResolvedValue({ ...prep, result: "STALE", writable: false });
  vi.mocked(fetchQuoteHistory).mockRejectedValue({ status: 409 }); const hook = mount(); await settle();
  expect(hook.result.current.snapshot?.result).toBe("STALE"); expect(hook.result.current.history).toBeNull();
  expect(hook.result.current.enabled).toBe(false); expect(hook.result.current.error).not.toBe("");
});
it("keeps authoritative preparation diagnostics visible if shared Case State also refuses an integrity read", async () => {
  vi.mocked(fetchCaseState).mockRejectedValue({ status: 409 });
  vi.mocked(fetchQuotePreparation).mockResolvedValue({ ...prep, result: "STALE", writable: false });
  vi.mocked(fetchQuoteHistory).mockRejectedValue({ status: 409 }); const hook = mount(); await settle();
  expect(hook.result.current.snapshot?.result).toBe("STALE"); expect(hook.result.current.projection).toBeNull();
  expect(hook.result.current.enabled).toBe(false); expect(hook.result.current.history).toBeNull();
});
it.each([{ sessionBlocked: true }, { sessionId: undefined }, { actorScope: undefined }, { revision: "b".repeat(64) }])("fails closed on invalid session/actor/upstream %j", async changes => {
  const hook = mount(changes); await settle(); await act(async () => { await hook.result.current.submit(intent, token); }); expect(submitQuoteCommand).not.toHaveBeenCalled();
});
it("non-DRAFT/current COMPLETE remains readable with no writes and no downstream action", async () => {
  vi.mocked(fetchQuotePreparation).mockResolvedValue({ ...prep, writable: false, result: "COMPLETE" });
  vi.mocked(fetchCaseState).mockResolvedValue({ ...state, stages: [{ stage: "SUPPLIER_QUOTES", result: "COMPLETE", provider_key: "supplier_quotes_v1" }], next_action: { kind: "NO_AUTHORIZED_DOWNSTREAM_ACTION", stage: null, semantic_route_key: null, validation_issue_id: null } });
  const hook = mount(); await settle(); expect(hook.result.current.snapshot?.result).toBe("COMPLETE"); expect(hook.result.current.enabled).toBe(false);
});
it("only server permitted actions execute, including warnings not blocking confirmation", async () => {
  vi.mocked(fetchQuotePreparation).mockResolvedValue({ ...prep, quotes: prep.quotes.map(q => ({ ...q, can_confirm: false })) });
  const hook = mount(); await settle(); await act(async () => { await hook.result.current.submit(intent, token); }); expect(submitQuoteCommand).not.toHaveBeenCalled();
  vi.mocked(fetchQuotePreparation).mockResolvedValue(prep); vi.mocked(fetchQuoteHistory).mockResolvedValue({ items: [{ ...quote, items: quote.items.map(i => ({ ...i, warning_codes: ["below_working_price", "difference_exceeds_15_percent"] })) }], case_version: token, offset: 0, limit: 50, next_offset: null });
  await act(async () => { await hook.result.current.refresh(); }); await act(async () => { await hook.result.current.submit(intent, token); }); expect(submitQuoteCommand).toHaveBeenCalledOnce();
});
