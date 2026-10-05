import {
  NativeBridge, NativeBridgeError, nativeProductFileLimit, nativeProtocolV2,
  type ArtifactCaptureMetadata, type FileHandle,
} from "./bridge";

export const xlsxContentType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
const xlsContentType = "application/vnd.ms-excel";

function checkReady(bridge: NativeBridge): void {
  if (bridge.protocol !== nativeProtocolV2 || bridge.state !== "ready") throw new NativeBridgeError("BRIDGE_REVOKED");
  if (globalThis.navigator?.serviceWorker?.controller) throw new NativeBridgeError("CAPABILITY_UNAVAILABLE");
}

function resourceOptions(signal: AbortSignal): RequestInit {
  return { credentials: "omit", mode: "same-origin", redirect: "error", cache: "no-store",
    referrer: globalThis.location?.href, referrerPolicy: "same-origin", signal };
}

async function boundedBytes(response: Response, expected: number, signal: AbortSignal): Promise<Uint8Array> {
  if (!response.ok || !response.body) throw new NativeBridgeError("FAILED");
  const reader = response.body.getReader();
  const output = new Uint8Array(expected);
  let offset = 0;
  try {
    for (;;) {
      if (signal.aborted) throw new NativeBridgeError("BRIDGE_REVOKED");
      const next = await reader.read();
      if (next.done) break;
      if (offset + next.value.length > expected || offset + next.value.length > nativeProductFileLimit) {
        throw new NativeBridgeError("SIZE_LIMIT");
      }
      output.set(next.value, offset);
      offset += next.value.length;
    }
    if (offset !== expected) throw new NativeBridgeError("INVALID_ARGUMENT");
    return output;
  } finally { await reader.cancel(); reader.releaseLock(); }
}

export async function materializeSelectedExcel(bridge: NativeBridge, selected: FileHandle, signal: AbortSignal): Promise<File> {
  checkReady(bridge);
  if (selected.extension !== ".xls" && selected.extension !== ".xlsx") throw new NativeBridgeError("TYPE_NOT_ALLOWED");
  if (selected.sizeBytes < 1 || selected.sizeBytes > nativeProductFileLimit) throw new NativeBridgeError("SIZE_LIMIT");
  const prepared = await bridge.request("prepareSelectedFileTransfer", { handle: selected.handle });
  checkReady(bridge);
  const response = await fetch(prepared.url, { ...resourceOptions(signal), method: "GET" });
  const mime = selected.extension === ".xlsx" ? xlsxContentType : xlsContentType;
  if (response.headers.get("Content-Type") !== mime) throw new NativeBridgeError("TYPE_NOT_ALLOWED");
  const bytes = await boundedBytes(response, selected.sizeBytes, signal);
  checkReady(bridge);
  return new File([bytes as Uint8Array<ArrayBuffer>], selected.name, { type: mime });
}

export async function captureAndSaveArtifact(bridge: NativeBridge, metadata: ArtifactCaptureMetadata,
  download: () => Promise<Blob>, suggestedFilename: string, signal: AbortSignal): Promise<boolean> {
  checkReady(bridge);
  const prepared = await bridge.request("prepareArtifactCapture", metadata);
  const blob = await download();
  checkReady(bridge);
  if (blob.type !== metadata.contentType) throw new NativeBridgeError("TYPE_NOT_ALLOWED");
  if (blob.size !== metadata.sizeBytes || blob.size > nativeProductFileLimit) throw new NativeBridgeError("SIZE_LIMIT");
  const digest = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", await blob.arrayBuffer())))
    .map(value => value.toString(16).padStart(2, "0")).join("");
  if (digest !== metadata.sha256) throw new NativeBridgeError("INVALID_ARGUMENT");
  checkReady(bridge);
  const response = await fetch(prepared.url, { ...resourceOptions(signal), method: "POST",
    headers: { "Content-Type": metadata.contentType }, body: blob });
  if (!response.ok || response.headers.get("Content-Type") !== "application/json") throw new NativeBridgeError("FAILED");
  if (!response.body) throw new NativeBridgeError("BAD_MESSAGE");
  const reader = response.body.getReader();
  const bytes = new Uint8Array(256);
  let size = 0;
  try {
    for (;;) {
      if (signal.aborted) throw new NativeBridgeError("BRIDGE_REVOKED");
      const chunk = await reader.read();
      if (chunk.done) break;
      if (size + chunk.value.length > bytes.length) throw new NativeBridgeError("BAD_MESSAGE");
      bytes.set(chunk.value, size);
      size += chunk.value.length;
    }
  } finally { await reader.cancel(); reader.releaseLock(); }
  const text = new TextDecoder("utf-8", { fatal: true }).decode(bytes.subarray(0, size));
  const captured: unknown = JSON.parse(text);
  if (!captured || typeof captured !== "object" || Array.isArray(captured) ||
    Object.keys(captured).length !== 1 || !("artifactHandle" in captured) ||
    typeof captured.artifactHandle !== "string" || !/^[a-f0-9]{48}$/u.test(captured.artifactHandle)) {
    throw new NativeBridgeError("BAD_MESSAGE");
  }
  checkReady(bridge);
  return (await bridge.request("saveDownloadedArtifact", { artifactHandle: captured.artifactHandle, suggestedFilename })).saved;
}
