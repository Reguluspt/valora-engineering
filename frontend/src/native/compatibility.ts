import { request } from "../api/client";
import { nativeProtocolV2, type NativeCapability } from "./bridge";

export interface ClientCompatibility {
  contract: string;
  api_contract: string;
  web_contract: string;
  required_native_protocol: string;
  minimum_client_compatibility: number;
  recommended_client_compatibility: number;
}
export type IntegrationAvailability = {
  state: "browser-only" | "checking" | "native-compatible" | "native-incompatible/update-required" | "revoked/error";
  warning?: boolean;
};
export const requiredProductCapabilities = ["pickExcelFile", "prepareSelectedFileTransfer",
  "prepareArtifactCapture", "saveDownloadedArtifact"] as const;

export function parseCompatibility(value: unknown): ClientCompatibility {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid compatibility contract");
  const record = value as Record<string, unknown>;
  const keys = ["contract", "api_contract", "web_contract", "required_native_protocol",
    "minimum_client_compatibility", "recommended_client_compatibility"];
  if (Object.keys(record).length !== keys.length || keys.some(key => !Object.prototype.hasOwnProperty.call(record, key)) ||
    keys.slice(0, 4).some(key => typeof record[key] !== "string") ||
    !Number.isSafeInteger(record.minimum_client_compatibility) || (record.minimum_client_compatibility as number) < 1 ||
    !Number.isSafeInteger(record.recommended_client_compatibility) ||
    (record.recommended_client_compatibility as number) < (record.minimum_client_compatibility as number)) {
    throw new Error("Invalid compatibility contract");
  }
  return record as unknown as ClientCompatibility;
}

export async function getClientCompatibility(): Promise<ClientCompatibility> {
  return parseCompatibility(await request<unknown>("/api/v1/client-compatibility"));
}

export function evaluateCompatibility(server: ClientCompatibility, client: {
  protocol: string; clientCompatibility: number; capabilities: readonly NativeCapability[];
}): IntegrationAvailability {
  if (server.contract !== "valora.client-compat/1" || server.api_contract !== "valora.api/1" ||
    server.web_contract !== "valora.web/1" || server.required_native_protocol !== nativeProtocolV2 ||
    client.protocol !== nativeProtocolV2 || !Number.isSafeInteger(client.clientCompatibility) ||
    client.clientCompatibility < server.minimum_client_compatibility ||
    requiredProductCapabilities.some(capability => !client.capabilities.includes(capability))) {
    return { state: "native-incompatible/update-required" };
  }
  return { state: "native-compatible", warning: client.clientCompatibility < server.recommended_client_compatibility };
}

export function nativeStatusText(availability: IntegrationAvailability): string {
  switch (availability.state) {
    case "browser-only": return "Đang dùng trình duyệt. Chọn và tải tệp bằng trình duyệt.";
    case "checking": return "Đang kiểm tra khả năng Windows…";
    case "native-compatible": return availability.warning
      ? "Windows đã sẵn sàng. Khuyến nghị cập nhật ứng dụng." : "Windows đã sẵn sàng.";
    case "native-incompatible/update-required": return "Ứng dụng Windows chưa tương thích. Cập nhật ứng dụng hoặc dùng thao tác trình duyệt.";
    case "revoked/error": return "Kết nối Windows không còn khả dụng. Tải lại trang hoặc dùng thao tác trình duyệt.";
  }
}
