export const nativeProtocol = "valora.native/1" as const;
export const nativeProtocolV2 = "valora.native/2" as const;
export const nativeProductFileLimit = 10 * 1024 * 1024;
export const nativeResourcePrefix = "/api/v1/.valora-native/v2/";
export const nativeMessageLimit = 64 * 1024;
export const nativePendingLimit = 8;
const fileLimit = 64 * 1024 * 1024;
const requestTimeout = 120_000;
const v1CapabilityNames = ["pickExcelFile", "pickDocumentFile", "openInExcel", "openInWord",
  "saveDownloadedArtifact", "dragDrop", "showNotification", "deepLink", "openExternalUrl"] as const;
const capabilityNames = [...v1CapabilityNames, "prepareSelectedFileTransfer", "prepareArtifactCapture"] as const;
const errorNames = ["BAD_PROTOCOL", "BAD_MESSAGE", "NOT_TRUSTED", "CAPABILITY_UNAVAILABLE", "INVALID_ARGUMENT",
  "CANCELLED", "HANDLE_INVALID", "TYPE_NOT_ALLOWED", "SIZE_LIMIT", "BUSY", "OS_UNAVAILABLE", "BRIDGE_REVOKED", "FAILED"] as const;
export type NativeCapability = typeof capabilityNames[number];
export type NativeErrorCode = typeof errorNames[number];
export type NativeState = "unavailable" | "connecting" | "ready" | "revoked" | "disposed";
export type FileHandle = { handle: string; name: string; extension: ".xls" | ".xlsx" | ".docx"; sizeBytes: number };
export type NativeEvent = { event: "filesDropped"; payload: FileHandle } | { event: "deepLink"; payload: { route: string } };
type Payloads = {
  prepareSelectedFileTransfer: { handle: string };
  prepareArtifactCapture: ArtifactCaptureMetadata;
  pickExcelFile: Record<string, never>; pickDocumentFile: Record<string, never>;
  openInExcel: { handle: string }; openInWord: { handle: string };
  saveDownloadedArtifact: { artifactHandle: string; suggestedFilename: string };
  showNotification: { title: string; body: string }; openExternalUrl: { url: string };
};
type Results = {
  prepareSelectedFileTransfer: { url: string };
  prepareArtifactCapture: { url: string };
  pickExcelFile: { selected: false } | ({ selected: true } & FileHandle);
  pickDocumentFile: { selected: false } | ({ selected: true } & FileHandle);
  openInExcel: { opened: true }; openInWord: { opened: true };
  saveDownloadedArtifact: { saved: boolean }; showNotification: { shown: true }; openExternalUrl: { opened: true };
};
export type NativeRequestCapability = keyof Payloads;
export type ArtifactCaptureMetadata = {
  resultId: string; resultVersion: number; contentType: string; extension: ".xlsx"; sizeBytes: number; sha256: string;
};
export interface WebViewTransport {
  postMessage(message: unknown): void;
  addEventListener(type: "message", listener: (event: { data: unknown }) => void): void;
  removeEventListener(type: "message", listener: (event: { data: unknown }) => void): void;
}
export type NativeHost = { chrome?: { webview?: WebViewTransport } };
export type NativeAvailability = { state: "unavailable" | "ready"; capabilities: readonly NativeCapability[]; clientCompatibility?: number };

export class NativeBridgeError extends Error {
  constructor(public readonly code: NativeErrorCode) { super(`Native operation: ${code}`); this.name = "NativeBridgeError"; }
}

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new NativeBridgeError("BAD_MESSAGE");
  return value as Record<string, unknown>;
}
function shape(value: unknown, keys: string[]): Record<string, unknown> {
  const record = object(value);
  const names = Object.keys(record);
  if (names.length !== keys.length || keys.some(key => !Object.prototype.hasOwnProperty.call(record, key))) throw new NativeBridgeError("BAD_MESSAGE");
  return record;
}
function text(value: unknown, maximum: number, nonempty = true): value is string {
  if (typeof value !== "string" || (nonempty && value.length === 0) || [...value].length > maximum || /[\u0000-\u001f\u007f]/u.test(value)) return false;
  for (const character of value) {
    const point = character.codePointAt(0)!;
    if (point >= 0xd800 && point <= 0xdfff) return false;
  }
  return true;
}
function filename(value: unknown): value is string {
  return text(value, 255) && !/[\\/:*?"<>|]/u.test(value) && !/[. ]$/u.test(value) && value !== "." && value !== "..";
}
function handle(value: unknown): value is string { return typeof value === "string" && /^[a-f0-9]{48}$/u.test(value); }
function uuid(value: unknown): value is string { return typeof value === "string" && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/u.test(value); }
function route(value: unknown): value is string {
  if (!text(value, 2048) || value.length > 2048 || !value.startsWith("/") || value.startsWith("//") || /[\\\s]/u.test(value)) return false;
  try {
    const path = decodeURIComponent(value.split(/[?#]/u)[0]);
    return !path.startsWith("//") && !/[\\%\s\u0000-\u001f\u007f]/u.test(path) && !path.split("/").some(segment => segment === "." || segment === "..");
  } catch { return false; }
}
function metadata(value: unknown, selected = false): FileHandle {
  const record = shape(value, selected ? ["selected", "handle", "name", "extension", "sizeBytes"] : ["handle", "name", "extension", "sizeBytes"]);
  if (!handle(record.handle) || !filename(record.name) || ![".xls", ".xlsx", ".docx"].includes(record.extension as string) ||
    !record.name.toLowerCase().endsWith(record.extension as string) || typeof record.sizeBytes !== "number" ||
    !Number.isSafeInteger(record.sizeBytes) || record.sizeBytes < 0 || record.sizeBytes > fileLimit) throw new NativeBridgeError("BAD_MESSAGE");
  return { handle: record.handle, name: record.name, extension: record.extension as FileHandle["extension"], sizeBytes: record.sizeBytes };
}
function payload(capability: string, value: unknown): void {
  switch (capability) {
    case "hello": case "pickExcelFile": case "pickDocumentFile": shape(value, []); break;
    case "openInExcel": case "openInWord":
    case "prepareSelectedFileTransfer":
      if (!handle(shape(value, ["handle"]).handle)) throw new NativeBridgeError("HANDLE_INVALID"); break;
    case "prepareArtifactCapture": {
      const record = shape(value, ["resultId", "resultVersion", "contentType", "extension", "sizeBytes", "sha256"]);
      if (!uuid(record.resultId) || !Number.isSafeInteger(record.resultVersion) || (record.resultVersion as number) < 1 ||
        record.contentType !== "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" || record.extension !== ".xlsx" ||
        !Number.isSafeInteger(record.sizeBytes) || (record.sizeBytes as number) < 1 || (record.sizeBytes as number) > nativeProductFileLimit ||
        typeof record.sha256 !== "string" || !/^[a-f0-9]{64}$/u.test(record.sha256)) throw new NativeBridgeError("INVALID_ARGUMENT");
      break;
    }
    case "saveDownloadedArtifact": {
      const record = shape(value, ["artifactHandle", "suggestedFilename"]);
      if (!handle(record.artifactHandle)) throw new NativeBridgeError("HANDLE_INVALID");
      if (!filename(record.suggestedFilename)) throw new NativeBridgeError("INVALID_ARGUMENT"); break;
    }
    case "showNotification": {
      const record = shape(value, ["title", "body"]);
      if (!text(record.title, 80) || !text(record.body, 256)) throw new NativeBridgeError("INVALID_ARGUMENT"); break;
    }
    case "openExternalUrl":
      if (!text(shape(value, ["url"]).url, 2048)) throw new NativeBridgeError("INVALID_ARGUMENT"); break;
    default: throw new NativeBridgeError("CAPABILITY_UNAVAILABLE");
  }
}
function result(capability: string, value: unknown, protocol: string): unknown {
  if (capability === "hello") {
    const record = shape(value, protocol === nativeProtocolV2 ? ["protocol", "capabilities", "clientCompatibility"] : ["protocol", "capabilities"]);
    const allowed: readonly string[] = protocol === nativeProtocolV2 ? capabilityNames : v1CapabilityNames;
    if (record.protocol !== protocol || (protocol === nativeProtocolV2 && record.clientCompatibility !== 1) ||
      !Array.isArray(record.capabilities) || record.capabilities.length > allowed.length ||
      record.capabilities.some(c => !allowed.includes(c)) || new Set(record.capabilities).size !== record.capabilities.length) throw new NativeBridgeError("BAD_PROTOCOL");
    return { protocol, capabilities: Object.freeze([...record.capabilities]) };
  }
  if (capability === "prepareSelectedFileTransfer" || capability === "prepareArtifactCapture") {
    const record = shape(value, ["url"]);
    const kind = capability === "prepareSelectedFileTransfer" ? "selected" : "capture";
    if (typeof record.url !== "string" || record.url !== nativeResourcePrefix + kind + "/" + record.url.slice(-48) ||
      !/^[a-f0-9]{48}$/u.test(record.url.slice(-48))) throw new NativeBridgeError("BAD_MESSAGE");
    return { url: record.url };
  }
  if (capability === "pickExcelFile" || capability === "pickDocumentFile") {
    if (object(value).selected === false) { shape(value, ["selected"]); return { selected: false }; }
    if (object(value).selected !== true) throw new NativeBridgeError("BAD_MESSAGE");
    const file = metadata(value, true);
    if (capability === "pickDocumentFile" ? file.extension !== ".docx" : file.extension === ".docx") throw new NativeBridgeError("TYPE_NOT_ALLOWED");
    return { selected: true, ...file };
  }
  const field = capability === "saveDownloadedArtifact" ? "saved" : capability === "showNotification" ? "shown" : "opened";
  const record = shape(value, [field]);
  if (typeof record[field] !== "boolean" || (field !== "saved" && record[field] !== true)) throw new NativeBridgeError("BAD_MESSAGE");
  return { [field]: record[field] };
}
type Pending = { capability: string; resolve: (result: unknown) => void; reject: (error: NativeBridgeError) => void; timer: ReturnType<typeof setTimeout> };

export class NativeBridge {
  private transport?: WebViewTransport;
  private pending = new Map<string, Pending>();
  private listeners = new Set<(event: NativeEvent) => void>();
  private stateListeners = new Set<(state: NativeState) => void>();
  private currentState: NativeState = "unavailable";
  private enabled: readonly NativeCapability[] = Object.freeze([]);
  readonly ready: Promise<NativeAvailability>;
  get state(): NativeState { return this.currentState; }
  get capabilities(): readonly NativeCapability[] { return this.enabled; }
  get clientCompatibility(): number | undefined { return this.protocol === nativeProtocolV2 && this.currentState === "ready" ? 1 : undefined; }

  constructor(host: NativeHost = globalThis as NativeHost, readonly protocol: typeof nativeProtocol | typeof nativeProtocolV2 = nativeProtocol) {
    const candidate = host.chrome?.webview;
    if (!candidate || typeof candidate.postMessage !== "function" || typeof candidate.addEventListener !== "function" || typeof candidate.removeEventListener !== "function") {
      this.ready = Promise.resolve({ state: "unavailable", capabilities: this.enabled });
      return;
    }
    this.transport = candidate;
    this.currentState = "connecting";
    this.transport.addEventListener("message", this.receive);
    this.ready = this.send("hello", {}).then(value => {
      if (this.currentState !== "connecting") throw new NativeBridgeError("BRIDGE_REVOKED");
      this.enabled = (value as { capabilities: readonly NativeCapability[] }).capabilities;
      this.currentState = "ready";
      this.notifyState();
      return { state: "ready", capabilities: this.enabled } as const;
    }).catch(error => {
      this.invalidate(error instanceof NativeBridgeError ? error.code : "FAILED");
      throw error;
    });
    // A late unavailable handshake must not become an unhandled rejection when the caller only disposes.
    void this.ready.catch(() => {});
  }

  async request<K extends NativeRequestCapability>(capability: K, value: Payloads[K]): Promise<Results[K]> {
    if (!this.transport) throw new NativeBridgeError("CAPABILITY_UNAVAILABLE");
    await this.ready;
    if (this.currentState !== "ready") throw new NativeBridgeError("BRIDGE_REVOKED");
    if (!this.enabled.includes(capability)) throw new NativeBridgeError("CAPABILITY_UNAVAILABLE");
    return await this.send(capability, value) as Results[K];
  }

  onEvent(listener: (event: NativeEvent) => void): () => void { this.listeners.add(listener); return () => this.listeners.delete(listener); }
  onState(listener: (state: NativeState) => void): () => void { this.stateListeners.add(listener); return () => this.stateListeners.delete(listener); }
  private notifyState(): void { for (const listener of this.stateListeners) listener(this.currentState); }

  private send(capability: string, value: unknown): Promise<unknown> {
    if (this.protocol === nativeProtocol && (capability === "prepareSelectedFileTransfer" || capability === "prepareArtifactCapture")) {
      return Promise.reject(new NativeBridgeError("BAD_PROTOCOL"));
    }
    try { payload(capability, value); } catch (error) { return Promise.reject(error); }
    if (this.pending.size >= nativePendingLimit) return Promise.reject(new NativeBridgeError("BUSY"));
    const requestId = crypto.randomUUID();
    const message = { protocol: this.protocol, type: "request", requestId, capability, payload: value };
    if (new TextEncoder().encode(JSON.stringify(message)).byteLength > nativeMessageLimit) return Promise.reject(new NativeBridgeError("SIZE_LIMIT"));
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => this.invalidate("FAILED"), requestTimeout);
      this.pending.set(requestId, { capability, resolve, reject, timer });
      try { this.transport!.postMessage(message); }
      catch { this.invalidate("FAILED"); }
    });
  }

  private receive = (event: { data: unknown }): void => {
    if (this.currentState === "disposed" || this.currentState === "revoked") return;
    try {
      const serialized = typeof event.data === "string" ? event.data : JSON.stringify(event.data);
      if (typeof serialized !== "string" || new TextEncoder().encode(serialized).byteLength > nativeMessageLimit) throw new NativeBridgeError("SIZE_LIMIT");
      const message = object(typeof event.data === "string" ? JSON.parse(serialized) : event.data);
      if (message.protocol !== this.protocol) throw new NativeBridgeError("BAD_PROTOCOL");
      if (message.type === "event") {
        shape(message, ["protocol", "type", "event", "payload"]);
        if (message.event === "bridgeRevoked") {
          if (shape(message.payload, ["code"]).code !== "BRIDGE_REVOKED") throw new NativeBridgeError("BAD_MESSAGE");
          this.invalidate("BRIDGE_REVOKED"); return;
        }
        if (this.currentState !== "ready") throw new NativeBridgeError("BAD_MESSAGE");
        let nativeEvent: NativeEvent;
        if (message.event === "filesDropped" && this.enabled.includes("dragDrop")) {
          nativeEvent = { event: "filesDropped", payload: metadata(message.payload) };
        } else if (message.event === "deepLink" && this.enabled.includes("deepLink")) {
          const value = shape(message.payload, ["route"]).route;
          if (!route(value)) throw new NativeBridgeError("BAD_MESSAGE");
          nativeEvent = { event: "deepLink", payload: { route: value } };
        } else throw new NativeBridgeError("BAD_MESSAGE");
        for (const listener of this.listeners) listener(nativeEvent);
        return;
      }
      if (message.type !== "response" || !uuid(message.requestId) || typeof message.ok !== "boolean") throw new NativeBridgeError("BAD_MESSAGE");
      const pending = this.pending.get(message.requestId);
      if (!pending) throw new NativeBridgeError("BAD_MESSAGE");
      if (message.ok) {
        shape(message, ["protocol", "type", "requestId", "ok", "result"]);
        const value = result(pending.capability, message.result, this.protocol);
        this.pending.delete(message.requestId); clearTimeout(pending.timer); pending.resolve(value);
      } else {
        shape(message, ["protocol", "type", "requestId", "ok", "error"]);
        const error = shape(message.error, ["code", "message"]);
        if (!errorNames.includes(error.code as NativeErrorCode) || !text(error.message, 256)) throw new NativeBridgeError("BAD_MESSAGE");
        this.pending.delete(message.requestId); clearTimeout(pending.timer);
        pending.reject(new NativeBridgeError(error.code as NativeErrorCode));
        if (error.code === "BRIDGE_REVOKED" || error.code === "NOT_TRUSTED") this.invalidate("BRIDGE_REVOKED");
      }
    } catch (error) { this.invalidate(error instanceof NativeBridgeError ? error.code : "BAD_MESSAGE"); }
  };

  private invalidate(code: NativeErrorCode): void {
    this.currentState = "revoked";
    this.enabled = Object.freeze([]);
    this.notifyState();
    this.transport?.removeEventListener("message", this.receive);
    for (const pending of this.pending.values()) { clearTimeout(pending.timer); pending.reject(new NativeBridgeError(code)); }
    this.pending.clear();
    this.listeners.clear();
  }

  dispose(): void { this.invalidate("BRIDGE_REVOKED"); this.currentState = "disposed"; this.notifyState(); this.stateListeners.clear(); }
}
