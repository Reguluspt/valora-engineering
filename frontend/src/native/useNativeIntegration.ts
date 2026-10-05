import { useEffect, useState } from "react";
import { NativeBridge, NativeBridgeError, nativeProtocolV2, type ArtifactCaptureMetadata, type NativeHost } from "./bridge";
import { evaluateCompatibility, getClientCompatibility, nativeStatusText, type IntegrationAvailability } from "./compatibility";
import { captureAndSaveArtifact, materializeSelectedExcel } from "./transfers";

export function useNativeIntegration() {
  const [availability, setAvailability] = useState<IntegrationAvailability>({ state: "browser-only" });
  const [connection, setConnection] = useState<{ bridge: NativeBridge; abort: AbortController } | null>(null);
  useEffect(() => {
    const bridge = new NativeBridge(globalThis as NativeHost, nativeProtocolV2);
    const abort = new AbortController();
    let active = true;
    const unsubscribe = bridge.onState(state => {
      if (active && (state === "revoked" || state === "disposed")) {
        abort.abort();
        setAvailability({ state: "revoked/error" });
      }
    });
    setConnection({ bridge, abort });
    if (bridge.state === "unavailable") {
      setAvailability({ state: "browser-only" });
    } else {
      setAvailability({ state: "checking" });
      void bridge.ready.then(async () => {
        const server = await getClientCompatibility();
        if (!active) return;
        if (bridge.state !== "ready") throw new NativeBridgeError("BRIDGE_REVOKED");
        if (globalThis.navigator?.serviceWorker?.controller) {
          setAvailability({ state: "revoked/error" });
          return;
        }
        setAvailability(evaluateCompatibility(server, {
          protocol: bridge.protocol, clientCompatibility: bridge.clientCompatibility!,
          capabilities: bridge.capabilities,
        }));
      }).catch(error => {
        if (active) setAvailability({ state: error instanceof NativeBridgeError &&
          (error.code === "BAD_PROTOCOL" || error.code === "BAD_MESSAGE" || error.code === "CAPABILITY_UNAVAILABLE")
          ? "native-incompatible/update-required" : "revoked/error" });
      });
    }
    return () => { active = false; unsubscribe(); abort.abort(); bridge.dispose(); };
  }, []);
  const required = () => {
    if (!connection || availability.state !== "native-compatible") throw new NativeBridgeError("CAPABILITY_UNAVAILABLE");
    return connection;
  };
  return {
    availability, statusText: nativeStatusText(availability),
    async pickExcelFile(): Promise<File | null> {
      const { bridge, abort } = required();
      const selected = await bridge.request("pickExcelFile", {});
      return selected.selected ? materializeSelectedExcel(bridge, selected, abort.signal) : null;
    },
    async saveArtifact(metadata: ArtifactCaptureMetadata, download: () => Promise<Blob>, suggestedFilename: string): Promise<boolean> {
      const { bridge, abort } = required();
      return captureAndSaveArtifact(bridge, metadata, download, suggestedFilename, abort.signal);
    },
  };
}
