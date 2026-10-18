import { act } from "react-test-renderer";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { renderHook } from "../../hooks/__tests__/renderHook";
import { useQuotationDocumentImport } from "../useQuotationDocumentImport";
import { fetchImportContext, fetchImportStatus, importQuotationTxt } from "../../../../api/quotationDocuments";
vi.mock("../../../../api/quotationDocuments", () => ({ fetchImportContext: vi.fn(), fetchImportStatus: vi.fn(), importQuotationTxt: vi.fn() }));
const project = "11111111-1111-4111-8111-111111111111";
const context = { contract_version: "quotation-txt-import-v1" as const, project_id: project, project_code: "SYNTHETIC", project_name: "Synthetic",
  case_version: "a".repeat(64), project_row_version: 1, can_import: true, blocked_codes: [], extension: ".txt" as const,
  encoding: "utf-8" as const, max_bytes: 1048576, retention_policy_code: "quotation-txt-record-10y-v1", policy_version: 1 };
let roots: ReturnType<typeof renderHook>[] = [], stored: Map<string, string>;
const settle = () => act(async () => { await Promise.resolve(); });
const mount = (changes = {}) => { const props = { projectId: project, actorScope: "tenant:actor", onImported: vi.fn(), ...changes };
  const hook = renderHook(() => useQuotationDocumentImport(props)); roots.push(hook); return { ...hook, props }; };
const file = () => new File(["synthetic original\r\n"], "synthetic.txt", { type: "text/plain" });
beforeEach(() => {
  vi.clearAllMocks(); stored = new Map(); vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  vi.stubGlobal("sessionStorage", { getItem: (k: string) => stored.get(k) || null, setItem: (k: string, v: string) => stored.set(k, v), removeItem: (k: string) => stored.delete(k) });
  vi.mocked(fetchImportContext).mockResolvedValue(context);
});
afterEach(() => { roots.forEach(r => r.unmount()); roots = []; vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("selection and refresh do not mutate; explicit double submit sends one command and persists no content", async () => {
  const hook = mount(); await settle();
  await act(async () => { await hook.result.current.select(file()); });
  expect(importQuotationTxt).not.toHaveBeenCalled(); expect(hook.result.current.enabled).toBe(true);
  let finish!: (value: any) => void;
  vi.mocked(importQuotationTxt).mockImplementation((_project, command) => new Promise(resolve => {
    finish = () => resolve({ project_id: project, contract_version: command.contract_version, command_id: command.command_id,
      sha256: command.expected_sha256, byte_length: command.expected_byte_length, outcome: "pending", storage_state_version: 2, recovery_permitted: true } as any);
  }));
  let pending!: Promise<boolean>;
  act(() => { pending = hook.result.current.submit(); void hook.result.current.submit(); });
  expect(importQuotationTxt).toHaveBeenCalledOnce();
  expect([...stored.values()][0]).not.toContain("synthetic original"); expect([...stored.values()][0]).not.toContain("synthetic.txt");
  await act(async () => { finish(null); await pending; });
  expect(hook.props.onImported).not.toHaveBeenCalled(); expect(hook.result.current.selection).toBeNull();
  expect(hook.result.current.canRecover).toBe(false);
});

it("storage failure prevents dispatch", async () => {
  const hook = mount(); await settle(); await act(async () => { await hook.result.current.select(file()); });
  vi.stubGlobal("sessionStorage", { getItem: () => null, setItem: () => { throw new Error("unavailable"); } });
  await act(async () => { await hook.result.current.submit(); });
  expect(importQuotationTxt).not.toHaveBeenCalled(); expect(hook.result.current.error).toContain("Chưa gửi");
});

it("unknown outcome survives remount and reconciles by GET before requiring exact-file explicit recovery", async () => {
  vi.mocked(importQuotationTxt).mockRejectedValue({ status: 0 });
  const first = mount(); await settle(); await act(async () => { await first.result.current.select(file()); await first.result.current.submit(); });
  // Selection updates must render before the independent confirmation action.
  await act(async () => { await first.result.current.submit(); });
  const original = first.result.current.pending!.command;
  first.unmount(); roots = [];
  const next = mount(); await settle();
  expect(next.result.current.pending?.command).toEqual(original);
  const calls = vi.mocked(importQuotationTxt).mock.calls.length;
  vi.mocked(fetchImportStatus).mockResolvedValue({ contract_version: original.contract_version, project_id: project,
    command_id: original.command_id, sha256: original.expected_sha256, byte_length: original.expected_byte_length,
    outcome: "pending", storage_state_version: 7, recovery_permitted: true } as any);
  await act(async () => { await next.result.current.reconcile(); });
  expect(fetchImportStatus).toHaveBeenCalledWith(project, original.command_id);
  expect(importQuotationTxt).toHaveBeenCalledTimes(calls); expect(next.result.current.enabled).toBe(false);
  await act(async () => { await next.result.current.select(new File(["different"], "synthetic.txt")); });
  expect(next.result.current.enabled).toBe(false);
  await act(async () => { await next.result.current.select(file()); });
  expect(next.result.current.canRecover).toBe(true);
  await act(async () => { await next.result.current.submit(); });
  expect(importQuotationTxt).toHaveBeenLastCalledWith(project, original, expect.any(File), 7);
});

it("actor change ignores a late mutation response", async () => {
  const hook = mount(); await settle(); await act(async () => { await hook.result.current.select(file()); });
  let finish!: (value: any) => void;
  vi.mocked(importQuotationTxt).mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  let submitted!: Promise<boolean>;
  act(() => { submitted = hook.result.current.submit(); });
  hook.props.actorScope = "tenant:other"; hook.rerender(); await settle();
  await act(async () => { finish({ outcome: "finalized" }); await submitted; });
  expect(hook.result.current.status).toBeNull(); expect(hook.result.current.pending).toBeNull();
  expect(hook.props.onImported).not.toHaveBeenCalled();
});

it("a known static denial followed by GET absence permits a fresh human attempt without retrying", async () => {
  vi.mocked(importQuotationTxt).mockRejectedValue({ status: 409 });
  vi.mocked(fetchImportStatus).mockRejectedValue({ status: 404 });
  const hook = mount(); await settle(); await act(async () => { await hook.result.current.select(file()); });
  await act(async () => { await hook.result.current.submit(); });
  expect(hook.result.current.pending).not.toBeNull();
  await act(async () => { await hook.result.current.reconcile(); });
  expect(hook.result.current.pending).toBeNull(); expect(hook.result.current.selection).toBeNull();
  expect(hook.result.current.enabled).toBe(false); expect(importQuotationTxt).toHaveBeenCalledOnce();
  expect(hook.result.current.error).toContain("Chọn lại tệp");
});

it("server custody capability controls import independently of professional quotation state", async () => {
  vi.mocked(fetchImportContext).mockResolvedValue({ ...context, can_import: false, blocked_codes: ["permission_required"] });
  const hook = mount(); await settle(); await act(async () => { await hook.result.current.select(file()); });
  expect(hook.result.current.enabled).toBe(false);
  await act(async () => { await hook.result.current.submit(); }); expect(importQuotationTxt).not.toHaveBeenCalled();
});

it("unsafe display filenames invalidate the selection before confirmation", async () => {
  const hook = mount(); await settle();
  for (const filename of ["report\u202e.txt", "../report.txt", "CON.txt", "a".repeat(256) + ".txt"]) {
    await act(async () => { await hook.result.current.select(new File(["synthetic"], filename)); });
    expect(hook.result.current.selection).toBeNull(); expect(hook.result.current.enabled).toBe(false);
  }
  expect(importQuotationTxt).not.toHaveBeenCalled();
});
