import React from "react";
import { act, create } from "react-test-renderer";
import { afterEach, describe, expect, it, vi } from "vitest";
const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("../../api/client", () => api);
import { useNativeIntegration } from "../useNativeIntegration";
import { nativeProtocolV2 } from "../bridge";
import { requiredProductCapabilities } from "../compatibility";
const contract = { contract: "valora.client-compat/1", api_contract: "valora.api/1",
  web_contract: "valora.web/1", required_native_protocol: nativeProtocolV2,
  minimum_client_compatibility: 1, recommended_client_compatibility: 1 };
let current: ReturnType<typeof useNativeIntegration>;
function Consumer() { current = useNativeIntegration(); return <p>{current.statusText}</p>; }
afterEach(() => { vi.unstubAllGlobals(); vi.resetAllMocks(); });
function installHost(protocol = nativeProtocolV2) {
  const listeners = new Set<(value: { data: unknown }) => void>();
  vi.stubGlobal("chrome", { webview: {
    postMessage(message: any) {
      queueMicrotask(() => listeners.forEach(listener => listener({ data: {
        protocol, type: "response", requestId: message.requestId, ok: true,
        result: protocol === nativeProtocolV2 ? { protocol, capabilities: [...requiredProductCapabilities], clientCompatibility: 1 }
          : { protocol, capabilities: [] },
      } })));
    },
    addEventListener(_: string, listener: any) { listeners.add(listener); },
    removeEventListener(_: string, listener: any) { listeners.delete(listener); },
  } });
  return listeners;
}
describe("native product availability", () => {
  it("keeps an ordinary browser usable without making a compatibility request", async () => {
    let tree: ReturnType<typeof create>;
    await act(async () => { tree = create(<Consumer />); });
    expect(current.availability.state).toBe("browser-only");
    expect(api.request).not.toHaveBeenCalled();
    await act(async () => tree!.unmount());
  });
  it.each([
    [nativeProtocolV2, contract, "native-compatible"],
    ["valora.native/1", contract, "native-incompatible/update-required"],
    [nativeProtocolV2, { ...contract, api_contract: "wrong/1" }, "native-incompatible/update-required"],
    [nativeProtocolV2, { ...contract, minimum_client_compatibility: 2, recommended_client_compatibility: 2 }, "native-incompatible/update-required"],
  ])("shows the explicit state for %s", async (protocol, compatibility, state) => {
    installHost(protocol as string);
    api.request.mockResolvedValue(compatibility);
    let tree: ReturnType<typeof create>;
    await act(async () => { tree = create(<Consumer />); });
    expect(current.availability.state).toBe(state);
    if (state === "native-compatible") expect(api.request).toHaveBeenCalledWith("/api/v1/client-compatibility");
    else await expect(current.pickExcelFile()).rejects.toMatchObject({ code: "CAPABILITY_UNAVAILABLE" });
    await act(async () => tree!.unmount());
  });
  it("shows revoked/error and blocks actions after generation loss", async () => {
    const listeners = installHost();
    api.request.mockResolvedValue(contract);
    let tree: ReturnType<typeof create>;
    await act(async () => { tree = create(<Consumer />); });
    await act(async () => listeners.forEach(listener => listener({ data: { protocol: nativeProtocolV2,
      type: "event", event: "bridgeRevoked", payload: { code: "BRIDGE_REVOKED" } } })));
    expect(current.availability.state).toBe("revoked/error");
    await expect(current.saveArtifact({} as any, vi.fn(), "result.xlsx")).rejects.toMatchObject({ code: "CAPABILITY_UNAVAILABLE" });
    await act(async () => tree!.unmount());
  });
});
