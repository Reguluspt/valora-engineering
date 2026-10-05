import { afterEach, describe, expect, it, vi } from "vitest";
import { NativeBridge, nativeProductFileLimit, nativeProtocolV2, nativeResourcePrefix, type WebViewTransport } from "../bridge";
import { evaluateCompatibility, parseCompatibility, requiredProductCapabilities } from "../compatibility";
import { captureAndSaveArtifact, materializeSelectedExcel, xlsxContentType } from "../transfers";

const contract = {
  contract: "valora.client-compat/1", api_contract: "valora.api/1", web_contract: "valora.web/1",
  required_native_protocol: nativeProtocolV2, minimum_client_compatibility: 1, recommended_client_compatibility: 1,
};
const adapters: NativeBridge[] = [];
afterEach(() => { adapters.forEach(adapter => adapter.dispose()); adapters.length = 0; vi.unstubAllGlobals(); });
function host(protocol = nativeProtocolV2, hello: object = { protocol, capabilities: [...requiredProductCapabilities], clientCompatibility: 1 }) {
  const listeners = new Set<(event: { data: unknown }) => void>();
  const messages: any[] = [];
  const transport: WebViewTransport = {
    postMessage(message: any) {
      messages.push(message);
      queueMicrotask(() => {
        const result = message.capability === "hello" ? hello :
          message.capability === "prepareSelectedFileTransfer" ? { url: nativeResourcePrefix + "selected/" + "a".repeat(48) } :
          message.capability === "prepareArtifactCapture" ? { url: nativeResourcePrefix + "capture/" + "b".repeat(48) } : { saved: false };
        listeners.forEach(listener => listener({ data: { protocol, type: "response", requestId: message.requestId, ok: true, result } }));
      });
    },
    addEventListener(_, listener) { listeners.add(listener); },
    removeEventListener(_, listener) { listeners.delete(listener); },
  };
  const bridge = new NativeBridge({ chrome: { webview: transport } }, nativeProtocolV2);
  adapters.push(bridge);
  return { bridge, messages };
}
const native = { protocol: nativeProtocolV2, clientCompatibility: 1, capabilities: [...requiredProductCapabilities] };
describe("WIN-4A compatibility", () => {
  it("accepts the exact authenticated contract and warns only on a recommended mismatch", () => {
    expect(parseCompatibility(contract)).toEqual(contract);
    expect(evaluateCompatibility(contract, native)).toEqual({ state: "native-compatible", warning: false });
    expect(evaluateCompatibility({ ...contract, recommended_client_compatibility: 2 }, native)).toEqual({ state: "native-compatible", warning: true });
  });
  it.each(["contract", "api_contract", "web_contract", "required_native_protocol"])("blocks a wrong %s", key => {
    expect(evaluateCompatibility({ ...contract, [key]: "wrong/99" }, native).state).toBe("native-incompatible/update-required");
  });
  it("blocks minimum mismatch, missing capability and v1 without downgrading", () => {
    expect(evaluateCompatibility({ ...contract, minimum_client_compatibility: 2 }, native).state).toBe("native-incompatible/update-required");
    expect(evaluateCompatibility(contract, { ...native, capabilities: [] }).state).toBe("native-incompatible/update-required");
    expect(evaluateCompatibility(contract, { ...native, protocol: "valora.native/1" }).state).toBe("native-incompatible/update-required");
  });
  it.each([{ ...contract, identity: "private" }, { ...contract, minimum_client_compatibility: "1" }, {}])("rejects an expansive or malformed schema", value => {
    expect(() => parseCompatibility(value)).toThrow();
  });
  it("requires the exact v2 hello and explicitly rejects a v1-only host", async () => {
    const good = host(); await good.bridge.ready; expect(good.bridge.clientCompatibility).toBe(1);
    const legacy = host("valora.native/1", { protocol: "valora.native/1", capabilities: [] });
    await expect(legacy.bridge.ready).rejects.toMatchObject({ code: "BAD_PROTOCOL" });
    const expansive = host(nativeProtocolV2, { protocol: nativeProtocolV2, capabilities: [], clientCompatibility: 1, path: "private" });
    await expect(expansive.bridge.ready).rejects.toThrow();
  });
});
describe("browser-owned native transfer", () => {
  it.each([".xls", ".xlsx"])("creates a byte-identical File from %s without any upload", async extension => {
    const { bridge, messages } = host(); await bridge.ready;
    const bytes = new Uint8Array([0, 255, 8]);
    const mime = extension === ".xlsx" ? xlsxContentType : "application/vnd.ms-excel";
    const fetcher = vi.fn().mockResolvedValue(new Response(bytes, { headers: { "Content-Type": mime } }));
    vi.stubGlobal("fetch", fetcher);
    const file = await materializeSelectedExcel(bridge, { handle: "a".repeat(48), name: "assets" + extension, extension, sizeBytes: bytes.length }, new AbortController().signal);
    expect(new Uint8Array(await file.arrayBuffer())).toEqual(bytes);
    expect(file.name).toBe("assets" + extension);
    expect(fetcher).toHaveBeenCalledOnce();
    expect(fetcher.mock.calls[0][1]).toMatchObject({ method: "GET", credentials: "omit", redirect: "error", mode: "same-origin", cache: "no-store" });
    expect(messages.map(message => message.capability)).toEqual(["hello", "prepareSelectedFileTransfer"]);
    expect(JSON.stringify(messages)).not.toMatch(/base64|path|bytes":/i);
  });
  it("rejects oversize metadata, wrong type, growing body and stale bridge", async () => {
    const { bridge } = host(); await bridge.ready;
    const selected = { handle: "a".repeat(48), name: "assets.xlsx", extension: ".xlsx", sizeBytes: 1 };
    await expect(materializeSelectedExcel(bridge, { ...selected, sizeBytes: nativeProductFileLimit + 1 }, new AbortController().signal)).rejects.toMatchObject({ code: "SIZE_LIMIT" });
    await expect(materializeSelectedExcel(bridge, { ...selected, extension: ".exe" }, new AbortController().signal)).rejects.toMatchObject({ code: "TYPE_NOT_ALLOWED" });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(new Uint8Array([1, 2]), { headers: { "Content-Type": xlsxContentType } })));
    await expect(materializeSelectedExcel(bridge, selected, new AbortController().signal)).rejects.toMatchObject({ code: "SIZE_LIMIT" });
    bridge.dispose();
    await expect(materializeSelectedExcel(bridge, selected, new AbortController().signal)).rejects.toMatchObject({ code: "BRIDGE_REVOKED" });
  });
  it("downloads through the supplied browser API, verifies bytes, and preserves Save As cancellation", async () => {
    const { bridge, messages } = host(); await bridge.ready;
    const bytes = new Uint8Array([1, 2, 3]);
    const checksum = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))).map(value => value.toString(16).padStart(2, "0")).join("");
    const metadata = { resultId: "47fa8032-58e4-4860-9243-077f0cb13327", resultVersion: 3, contentType: xlsxContentType, extension: ".xlsx", sizeBytes: 3, sha256: checksum };
    const download = vi.fn().mockResolvedValue(new Blob([bytes], { type: xlsxContentType }));
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ artifactHandle: "c".repeat(48) }), { status: 201, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetcher);
    expect(await captureAndSaveArtifact(bridge, metadata, download, "result.xlsx", new AbortController().signal)).toBe(false);
    expect(download).toHaveBeenCalledOnce();
    expect(fetcher).toHaveBeenCalledOnce();
    const options = fetcher.mock.calls[0][1];
    expect(options).toMatchObject({ method: "POST", credentials: "omit", headers: { "Content-Type": xlsxContentType } });
    expect(new Uint8Array(await options.body.arrayBuffer())).toEqual(bytes);
    expect(messages.map(message => message.capability)).toEqual(["hello", "prepareArtifactCapture", "saveDownloadedArtifact"]);
    fetcher.mockClear();
    await expect(captureAndSaveArtifact(bridge, { ...metadata, sha256: "0".repeat(64) }, download, "result.xlsx", new AbortController().signal)).rejects.toMatchObject({ code: "INVALID_ARGUMENT" });
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("blocks service-worker interception before issuing a token", async () => {
    const { bridge, messages } = host(); await bridge.ready;
    vi.stubGlobal("navigator", { serviceWorker: { controller: {} } });
    await expect(materializeSelectedExcel(bridge, { handle: "a".repeat(48), name: "a.xlsx", extension: ".xlsx", sizeBytes: 1 }, new AbortController().signal)).rejects.toMatchObject({ code: "CAPABILITY_UNAVAILABLE" });
    expect(messages).toHaveLength(1);
  });
});
