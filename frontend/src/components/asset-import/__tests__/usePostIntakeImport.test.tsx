import React, { useState } from "react";
import { act, create, type ReactTestRenderer } from "react-test-renderer";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { fetchCaseState } from "../../../api/caseState";
import { getCurrentAccount } from "../../../api/auth";
import { applyAssetImport, validateAssetImport, fetchAssetImportBatches, fetchAssetImportRows } from "../../../api/assetImports";
import { usePostIntakeImport, type PostIntakeImportController } from "../usePostIntakeImport";
import { applied, batch, id, projection, rows } from "./fixtures";
vi.mock("../../../api/caseState", () => ({ fetchCaseState: vi.fn() }));
vi.mock("../../../api/auth", () => ({ getCurrentAccount: vi.fn() }));
vi.mock("../../../api/assetImports", () => ({ applyAssetImport: vi.fn(), validateAssetImport: vi.fn(), fetchAssetImportBatches: vi.fn(), fetchAssetImportRows: vi.fn() }));
let flow: PostIntakeImportController, tree: ReactTestRenderer | undefined;
let server = projection(), valid = false, appliedBatch = false;
let storage: Map<string, string>;
let events: Record<string, (event: any) => void>;
const key = `valora:post-intake:tenant:actor:${id(1)}`;
function Harness({ editable = true, scope = "tenant:actor" }: { editable?: boolean; scope?: string }) {
  const [p, setP] = useState(server);
  flow = usePostIntakeImport({ projectId: id(1), actorScope: scope, canEdit: editable, projection: p, onProjection: setP });
  return null;
}
async function mount(editable = true) { await act(async () => { tree = create(<Harness editable={editable} />); }); }
beforeEach(() => {
  vi.clearAllMocks(); server = projection(); valid = false; appliedBatch = false; storage = new Map(); events = {};
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  vi.stubGlobal("localStorage", { getItem: (k: string) => storage.get(k) || null, setItem: (k: string, v: string) => storage.set(k, v), removeItem: (k: string) => storage.delete(k) });
  vi.stubGlobal("window", { addEventListener: (k: string, cb: any) => { events[k] = cb; }, removeEventListener: vi.fn() });
  vi.mocked(fetchCaseState).mockImplementation(async () => structuredClone(server));
  vi.mocked(getCurrentAccount).mockResolvedValue({ organization_id: "tenant", id: "actor", status: "active", permissions: ["workbench:edit"] } as any);
  vi.mocked(fetchAssetImportBatches).mockImplementation(async () => [{ ...batch(valid), ...(appliedBatch ? { status: "applied" as const } : {}) }]);
  vi.mocked(fetchAssetImportRows).mockImplementation(async () => rows(valid));
});
afterEach(async () => { if (tree) await act(async () => tree!.unmount()); tree = undefined; vi.unstubAllGlobals(); });
it("mount performs only bracketed GETs; validation is a human click and refreshes token/rows", async () => {
  await mount(); expect(flow.canValidate).toBe(true); expect(validateAssetImport).not.toHaveBeenCalled();
  vi.mocked(validateAssetImport).mockImplementation(async () => { server = projection("apply"); valid = true; return batch(true); });
  await act(async () => { await flow.submit("validate"); });
  expect(validateAssetImport).toHaveBeenCalledExactlyOnceWith(id(1), id(2), { expected_case_version: "a".repeat(64) });
  expect(flow.snapshot?.projection.case_version).toBe("b".repeat(64)); expect(flow.canApply).toBe(true);
  expect(storage.has(key)).toBe(false); expect(applyAssetImport).not.toHaveBeenCalled();
});
it("retains exact staged findings after validation returns a server blocker; ready_for_review cannot enable Apply", async () => {
  await mount();
  vi.mocked(validateAssetImport).mockImplementation(async () => {
    server = projection("apply"); server.next_action = { kind: "BLOCKER", stage: "ASSET_REVIEW", semantic_route_key: "asset_review_entry_blocked", validation_issue_id: null,
      context: { kind: "entry", project_id: id(1), case_version: server.case_version, reason_code: "rows_not_ready", batch_id: id(2) } as any };
    server.stages.find(s => s.stage === "ASSET_REVIEW")!.result = "BLOCKED";
    vi.mocked(fetchAssetImportBatches).mockResolvedValue([{ ...batch(true), valid_rows: 2, invalid_rows: 1 }]);
    const invalid = rows(true); invalid.items[0].validation_status = "invalid";
    invalid.items[0].validation_errors = [{ message_key: "excel.validation.quantity_invalid" }];
    vi.mocked(fetchAssetImportRows).mockResolvedValue(invalid);
    return { ...batch(true), valid_rows: 2, invalid_rows: 1 };
  });
  await act(async () => { await flow.submit("validate"); });
  expect(flow.snapshot?.rows.items[0].validation_status).toBe("invalid"); expect(flow.canApply).toBe(false);
  expect(flow.snapshot?.target.batch_id).toBe(id(2)); expect(applyAssetImport).not.toHaveBeenCalled();
});
it("cancel never sends Apply; confirm/double-click sends exactly one request", async () => {
  server = projection("apply"); valid = true; await mount();
  await act(async () => { await flow.openConfirmation(); }); expect(flow.confirmation).not.toBeNull();
  await act(async () => flow.closeConfirmation()); expect(applyAssetImport).not.toHaveBeenCalled();
  await act(async () => { await flow.openConfirmation(); });
  vi.mocked(applyAssetImport).mockImplementation(async () => { expect(storage.has(key)).toBe(true); server = applied(); appliedBatch = true;
    return { project_id: id(1), import_batch_id: id(2), status: "applied", created_count: 3,
      created_lines: rows().items.map((r, i) => ({ line_id: id(i + 20), staging_row_id: r.id, source_row_number: r.source_row_number })) }; });
  await act(async () => { await Promise.all([flow.submit("apply"), flow.submit("apply")]); });
  expect(applyAssetImport).toHaveBeenCalledTimes(1); expect(flow.proven).toBe(true); expect(storage.has(key)).toBe(false);
  expect(flow.canApply).toBe(false); expect(flow.confirmation).toBeNull();
});
it("a changed token or selection after dialog opening prevents dispatch", async () => {
  server = projection("apply"); valid = true; await mount();
  await act(async () => { await flow.openConfirmation(); });
  server.case_version = "e".repeat(64); server.next_action!.context!.case_version = server.case_version;
  await act(async () => { await flow.submit("apply"); });
  expect(applyAssetImport).not.toHaveBeenCalled(); expect(flow.confirmation).toBeNull();
});
it.each([400, 401, 403, 404, 409, 422])("known %s rejection closes the dialog and never retries", async status => {
  server = projection("apply"); valid = true; await mount(); await act(async () => { await flow.openConfirmation(); });
  vi.mocked(applyAssetImport).mockRejectedValue({ status });
  await act(async () => { await flow.submit("apply"); });
  expect(applyAssetImport).toHaveBeenCalledTimes(1); expect(flow.confirmation).toBeNull(); expect(storage.has(key)).toBe(false);
  expect(flow.notice).not.toBe("");
  if (status !== 409) expect(flow.canApply).toBe(false);
});
it.each([
  ["apply_version_conflict", "Trạng thái hồ sơ đã thay đổi. Tải lại dữ liệu mới nhất rồi rà soát và xác nhận lại."],
  ["apply_lineage_conflict", "Nguồn dữ liệu của lô nhập đã thay đổi. Tải lại dữ liệu mới nhất rồi rà soát trước khi tiếp tục."],
  ["apply_rows_not_ready", "Lô nhập chưa sẵn sàng để áp dụng. Rà soát các dòng chưa hợp lệ rồi tải lại dữ liệu."],
] as const)("maps verified 409 code %s to safe actionable feedback", async (code, message) => {
  server = projection("apply"); valid = true; await mount(); await act(async () => { await flow.openConfirmation(); });
  vi.mocked(applyAssetImport).mockRejectedValue({ status: 409, code });
  await act(async () => { await flow.submit("apply"); });
  expect(applyAssetImport).toHaveBeenCalledTimes(1); expect(flow.notice).toBe(message); expect(flow.conflict).toBe(true);
});
it("uses the generic safe 409 feedback for unknown or malformed codes without echoing server content", async () => {
  server = projection("apply"); valid = true; await mount(); await act(async () => { await flow.openConfirmation(); });
  const secret = "internal-token-or-diagnostic";
  vi.mocked(applyAssetImport).mockRejectedValue({ status: 409, code: "unknown_conflict", detail: { error_code: secret, detail: secret } });
  await act(async () => { await flow.submit("apply"); });
  expect(flow.notice).toBe("Trạng thái, nguồn hoặc phiên bản hồ sơ đã thay đổi. Rà soát dữ liệu mới và xác nhận lại.");
  expect(flow.notice).not.toContain(secret); expect(flow.conflict).toBe(true);
});
it.each([
  ["constructor", { status: 409, code: "constructor" }],
  ["toString", { status: 409, detail: { error_code: "toString" } }],
  ["__proto__", { status: 409, code: "__proto__" }],
  ["unknown string", { status: 409, code: "not_a_conflict_code" }],
  ["malformed nested payload", { status: 409, detail: { error_code: { raw: "internal diagnostic" }, detail: { code: ["apply_lineage_conflict"] } } }],
] as const)("uses the generic safe 409 fallback for %s", async (_case, cause) => {
  server = projection("apply"); valid = true; await mount(); await act(async () => { await flow.openConfirmation(); });
  vi.mocked(applyAssetImport).mockRejectedValue(cause);
  await act(async () => { await flow.submit("apply"); });
  expect(flow.notice).toBe("Trạng thái, nguồn hoặc phiên bản hồ sơ đã thay đổi. Rà soát dữ liệu mới và xác nhận lại.");
  expect(typeof flow.notice).toBe("string"); expect(flow.conflict).toBe(true);
});
it.each([0, 500])("unknown %s outcome survives remount and old-looking GETs cannot unlock", async status => {
  server = projection("apply"); valid = true; await mount(); await act(async () => { await flow.openConfirmation(); });
  vi.mocked(applyAssetImport).mockRejectedValue({ status }); await act(async () => { await flow.submit("apply"); });
  expect(storage.has(key)).toBe(true); expect(flow.canApply).toBe(false);
  await act(async () => tree!.unmount()); await mount(); await act(async () => { await flow.refresh(); });
  expect(flow.pending).not.toBeNull(); expect(flow.canApply).toBe(false); expect(applyAssetImport).toHaveBeenCalledTimes(1);
  server = applied(); appliedBatch = true; await act(async () => { await flow.refresh(); });
  expect(flow.proven).toBe(true); expect(flow.pending).toBeNull(); expect(applyAssetImport).toHaveBeenCalledTimes(1);
});
it("malformed success remains uncertain; no receipt endpoint is called", async () => {
  server = projection("apply"); valid = true; await mount(); await act(async () => { await flow.openConfirmation(); });
  vi.mocked(applyAssetImport).mockResolvedValue({ project_id: id(9) } as any); await act(async () => { await flow.submit("apply"); });
  expect(flow.pending).not.toBeNull(); expect(storage.has(key)).toBe(true); expect(flow.proven).toBe(false);
});
it("storage failure prevents dispatch and viewer cannot open confirmation", async () => {
  server = projection("apply"); valid = true; await mount(false);
  await act(async () => { await flow.openConfirmation(); await flow.submit("apply"); }); expect(flow.canApply).toBe(false);
  await act(async () => tree!.unmount()); await mount(); await act(async () => { await flow.openConfirmation(); });
  vi.stubGlobal("localStorage", { getItem: (k: string) => storage.get(k) || null, setItem: () => { throw new Error("quota"); } });
  await act(async () => { await flow.submit("apply"); }); expect(applyAssetImport).not.toHaveBeenCalled(); expect(flow.pending).not.toBeNull();
});
it("a scope switch neutralizes late protected responses", async () => {
  let resolve!: (p: ReturnType<typeof projection>) => void;
  vi.mocked(fetchCaseState).mockImplementationOnce(() => new Promise(r => { resolve = r; }));
  await mount(); await act(async () => tree!.unmount());
  server = projection("apply"); valid = true;
  vi.mocked(getCurrentAccount).mockResolvedValue({ organization_id: "tenant", id: "other", status: "active", permissions: ["workbench:edit"] } as any);
  await act(async () => { tree = create(<Harness scope="tenant:other" />); });
  await act(async () => resolve(projection()));
  expect(flow.snapshot?.target.kind).toBe("apply"); expect(validateAssetImport).not.toHaveBeenCalled();
});
it("incoherent reads and window changes disable writes", async () => {
  await mount(); await act(async () => events.focus({})); expect(flow.canValidate).toBe(false);
  let n = 0; vi.mocked(fetchCaseState).mockImplementation(async () => n++ % 2 ? projection("apply") : projection());
  await act(async () => { await flow.refresh(); }); expect(flow.snapshot).toBeNull(); expect(flow.error).not.toBe("");
});
it("a cookie actor change or permission revocation without a page session update clears protected data", async () => {
  await mount();
  vi.mocked(getCurrentAccount).mockResolvedValue({ organization_id: "other", id: "actor", status: "active", permissions: [] } as any);
  await act(async () => { await flow.refresh(); });
  expect(flow.snapshot).toBeNull(); expect(flow.canValidate).toBe(false); expect(flow.error).not.toBe("");
});
