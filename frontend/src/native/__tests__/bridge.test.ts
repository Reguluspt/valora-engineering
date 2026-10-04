import { afterEach, describe, expect, it, vi } from "vitest";
import { NativeBridge, NativeBridgeError, nativeMessageLimit, nativeProtocol, type WebViewTransport } from "../bridge";

class Transport implements WebViewTransport {
  messages: any[] = [];
  listeners = new Set<(event: { data: unknown }) => void>();
  postMessage = vi.fn((message: unknown) => { this.messages.push(message); });
  addEventListener = vi.fn((_: "message", listener: (event: { data: unknown }) => void) => { this.listeners.add(listener); });
  removeEventListener = vi.fn((_: "message", listener: (event: { data: unknown }) => void) => { this.listeners.delete(listener); });
  receive(value: unknown) { for (const listener of [...this.listeners]) listener({ data: value }); }
  success(request: any, result: unknown) { this.receive({ protocol: nativeProtocol, type: "response", requestId: request.requestId, ok: true, result }); }
  error(request: any, code: string, message = "Native operation unavailable or rejected.") {
    this.receive({ protocol: nativeProtocol, type: "response", requestId: request.requestId, ok: false, error: { code, message } });
  }
}
const adapters: NativeBridge[] = [];
afterEach(() => { for (const adapter of adapters) adapter.dispose(); adapters.length = 0; vi.useRealTimers(); });
const file = { handle: "a".repeat(48), name: "Tài sản.xlsx", extension: ".xlsx", sizeBytes: 12 };
async function ready(capabilities = ["pickExcelFile", "openInExcel", "dragDrop", "deepLink", "showNotification", "saveDownloadedArtifact", "openExternalUrl"]) {
  const transport = new Transport();
  const adapter = new NativeBridge({ chrome: { webview: transport } }); adapters.push(adapter);
  transport.success(transport.messages[0], { protocol: nativeProtocol, capabilities });
  await adapter.ready;
  return { adapter, transport };
}
const settle = () => Promise.resolve();

describe("native bridge infrastructure", () => {
  it("normal browser is explicitly unavailable, never a native-success fallback", async () => {
    const adapter = new NativeBridge({}); adapters.push(adapter);
    expect(await adapter.ready).toEqual({ state: "unavailable", capabilities: [] });
    await expect(adapter.request("pickExcelFile", {})).rejects.toMatchObject({ code: "CAPABILITY_UNAVAILABLE" });
  });

  it("negotiates only protocol and enabled capabilities and keeps discovery immutable", async () => {
    const { adapter, transport } = await ready(["pickExcelFile"]);
    expect(transport.messages[0]).toMatchObject({ protocol: nativeProtocol, type: "request", capability: "hello", payload: {} });
    expect(transport.messages[0].requestId).toMatch(/^[a-f0-9-]{36}$/);
    expect(Object.keys(transport.messages[0]).sort()).toEqual(["protocol", "type", "requestId", "capability", "payload"].sort());
    expect(adapter.state).toBe("ready");
    expect(adapter.capabilities).toEqual(["pickExcelFile"]);
    expect(Object.isFrozen(adapter.capabilities)).toBe(true);
    await expect(adapter.request("openInWord", { handle: file.handle })).rejects.toMatchObject({ code: "CAPABILITY_UNAVAILABLE" });
    expect(transport.messages).toHaveLength(1);
  });

  it.each([
    { protocol: "valora.native/2", capabilities: [] },
    { protocol: nativeProtocol, capabilities: ["execute_process"] },
    { protocol: nativeProtocol, capabilities: ["pickExcelFile", "pickExcelFile"] },
    { protocol: nativeProtocol, capabilities: [], identity: "private" },
  ])("rejects incompatible or expansive hello %#", async result => {
    const transport = new Transport();
    const adapter = new NativeBridge({ chrome: { webview: transport } }); adapters.push(adapter);
    transport.success(transport.messages[0], result);
    await expect(adapter.ready).rejects.toBeInstanceOf(NativeBridgeError);
    expect(adapter.state).toBe("revoked"); expect(adapter.capabilities).toEqual([]);
  });

  it("correlates out-of-order success and cancellation without reading unrelated state", async () => {
    const { adapter, transport } = await ready();
    const selected = adapter.request("pickExcelFile", {});
    const cancelled = adapter.request("pickExcelFile", {});
    await settle();
    transport.success(transport.messages[2], { selected: false });
    transport.success(transport.messages[1], { selected: true, ...file });
    expect(await selected).toEqual({ selected: true, ...file });
    expect(await cancelled).toEqual({ selected: false });
    expect(adapter.state).toBe("ready");
  });

  it("sanitizes native errors and does not forward raw exception messages", async () => {
    const { adapter, transport } = await ready();
    const pending = adapter.request("pickExcelFile", {}); await settle();
    transport.error(transport.messages[1], "FAILED", "C:\\private\\file secret failure");
    await expect(pending).rejects.toMatchObject({ code: "FAILED", message: "Native operation: FAILED" });
  });

  it.each([
    (id: string) => ({ protocol: "other/1", type: "response", requestId: id, ok: true, result: { selected: false } }),
    (id: string) => ({ protocol: nativeProtocol, type: "other", requestId: id, ok: true, result: { selected: false } }),
    (_: string) => ({ protocol: nativeProtocol, type: "response", requestId: "bad", ok: true, result: { selected: false } }),
    (id: string) => ({ protocol: nativeProtocol, type: "response", requestId: id, ok: true, result: { selected: false }, path: "C:/private" }),
    (id: string) => ({ protocol: nativeProtocol, type: "response", requestId: id, ok: "true", result: { selected: false } }),
    (id: string) => ({ protocol: nativeProtocol, type: "response", requestId: id, ok: false, error: { code: "arbitrary", message: "wrong" } }),
    (id: string) => ({ protocol: nativeProtocol, type: "response", requestId: id, ok: false, error: { code: "FAILED", message: "x".repeat(257) } }),
  ])("rejects malformed native envelopes %#", async build => {
    const { adapter, transport } = await ready();
    const pending = adapter.request("pickExcelFile", {}); await settle();
    transport.receive(build(transport.messages[1].requestId));
    await expect(pending).rejects.toBeInstanceOf(NativeBridgeError);
    expect(adapter.state).toBe("revoked");
  });

  it.each([
    { selected: true, ...file, handle: "forged" },
    { selected: true, ...file, name: "C:\\private\\selection.xlsx" },
    { selected: true, ...file, extension: ".exe" },
    { selected: true, ...file, sizeBytes: 64 * 1024 * 1024 + 1 },
    { selected: true, ...file, sizeBytes: -1 },
    { selected: true, ...file, sizeBytes: 1.5 },
    { selected: true, ...file, path: "C:/private" },
    { selected: false, handle: file.handle },
  ])("rejects unsafe or expansive file metadata %#", async result => {
    const { adapter, transport } = await ready();
    const pending = adapter.request("pickExcelFile", {}); await settle();
    transport.success(transport.messages[1], result);
    await expect(pending).rejects.toBeInstanceOf(NativeBridgeError);
  });

  it("has the same eight-pending bound and revokes every pending operation", async () => {
    const { adapter, transport } = await ready();
    const pending = Array.from({ length: 8 }, () => adapter.request("openInExcel", { handle: file.handle }));
    await settle();
    await expect(adapter.request("pickExcelFile", {})).rejects.toMatchObject({ code: "BUSY" });
    expect(transport.messages).toHaveLength(9);
    transport.receive({ protocol: nativeProtocol, type: "event", event: "bridgeRevoked", payload: { code: "BRIDGE_REVOKED" } });
    for (const promise of pending) await expect(promise).rejects.toMatchObject({ code: "BRIDGE_REVOKED" });
    expect(adapter.state).toBe("revoked"); expect(adapter.capabilities).toEqual([]);
    await expect(adapter.request("pickExcelFile", {})).rejects.toMatchObject({ code: "BRIDGE_REVOKED" });
  });

  it("disposes listeners/pending state and ignores late replies", async () => {
    const { adapter, transport } = await ready();
    const pending = adapter.request("pickExcelFile", {}); await settle();
    adapter.dispose(); adapter.dispose();
    await expect(pending).rejects.toMatchObject({ code: "BRIDGE_REVOKED" });
    transport.success(transport.messages[1], { selected: true, ...file });
    expect(adapter.state).toBe("disposed"); expect(transport.listeners.size).toBe(0);
  });

  it("bounded native events carry only scoped metadata/navigation context", async () => {
    const { adapter, transport } = await ready(); const listener = vi.fn();
    const unsubscribe = adapter.onEvent(listener);
    transport.receive({ protocol: nativeProtocol, type: "event", event: "filesDropped", payload: file });
    transport.receive({ protocol: nativeProtocol, type: "event", event: "deepLink", payload: { route: "/workbench/projects?returnTarget=/workbench#context" } });
    expect(listener).toHaveBeenCalledTimes(2);
    unsubscribe();
    transport.receive({ protocol: nativeProtocol, type: "event", event: "filesDropped", payload: file });
    expect(listener).toHaveBeenCalledTimes(2);
  });

  it.each(["//foreign.test", "https://foreign.test", "/%2f%2fforeign", "/../escape", "/%252fescape", "/\\foreign", "/x\ncommand"]) (
    "rejects unsafe navigation event %s", async route => {
      const { adapter, transport } = await ready(); const listener = vi.fn(); adapter.onEvent(listener);
      transport.receive({ protocol: nativeProtocol, type: "event", event: "deepLink", payload: { route } });
      expect(listener).not.toHaveBeenCalled(); expect(adapter.state).toBe("revoked");
    });

  it("unknown/unadvertised events and oversized messages revoke rather than invent success", async () => {
    const { adapter, transport } = await ready(["pickExcelFile"]);
    const pending = adapter.request("pickExcelFile", {}); await settle();
    transport.receive("x".repeat(nativeMessageLimit + 1));
    await expect(pending).rejects.toMatchObject({ code: "SIZE_LIMIT" });
    const next = await ready(["pickExcelFile"]);
    next.transport.receive({ protocol: nativeProtocol, type: "event", event: "filesDropped", payload: file });
    expect(next.adapter.state).toBe("revoked");
  });

  it("strict request payloads cannot convey paths, file bytes, commands or unbounded notification text", async () => {
    const { adapter, transport } = await ready();
    await expect(adapter.request("pickExcelFile", { path: "C:/private" } as any)).rejects.toMatchObject({ code: "BAD_MESSAGE" });
    await expect(adapter.request("openInExcel", { handle: "C:/private" })).rejects.toMatchObject({ code: "HANDLE_INVALID" });
    await expect(adapter.request("saveDownloadedArtifact", { artifactHandle: file.handle, suggestedFilename: "C:/result.xlsx" })).rejects.toMatchObject({ code: "INVALID_ARGUMENT" });
    await expect(adapter.request("saveDownloadedArtifact", { artifactHandle: file.handle, suggestedFilename: "result.xlsx", bytes: "aA==" } as any)).rejects.toMatchObject({ code: "BAD_MESSAGE" });
    await expect(adapter.request("showNotification", { title: "😀".repeat(81), body: "body" })).rejects.toMatchObject({ code: "INVALID_ARGUMENT" });
    expect(transport.messages).toHaveLength(1);
  });

  it("accepts bounded typed operations and JSON-serialized responses", async () => {
    const { adapter, transport } = await ready();
    const pending = adapter.request("openInExcel", { handle: file.handle }); await settle();
    transport.receive(JSON.stringify({ protocol: nativeProtocol, type: "response", requestId: transport.messages[1].requestId, ok: true, result: { opened: true } }));
    expect(await pending).toEqual({ opened: true });
  });

  it("timeouts leave native outcome unavailable and never retry or resolve a fake success", async () => {
    vi.useFakeTimers(); const { adapter, transport } = await ready();
    const pending = adapter.request("openInExcel", { handle: file.handle }); await settle();
    const rejected = expect(pending).rejects.toMatchObject({ code: "FAILED" });
    await vi.advanceTimersByTimeAsync(120_000); await rejected;
    expect(adapter.state).toBe("revoked"); expect(transport.messages).toHaveLength(2);
  });
});
