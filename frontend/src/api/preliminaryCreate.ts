import { ApiError, request } from "./client";

export const CANONICAL_VERSION = "preliminary-create-v1";
export const UUID4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const W = /^[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/g;

export interface PreliminaryCreateInput { request_id: string; name: string; description?: string | null }
export interface CommittedCreate {
  status: "COMMITTED";
  request_id: string;
  project: { id: string; code: string };
  receipt: { id: string; canonical_version: typeof CANONICAL_VERSION; recorded_at: string };
}

export function normalizeCreateFields(name: string, description: string | null = null) {
  const scalar = (s: string) => [...s].length;
  const invalidScalar = (s: string) => [...s].some(c => { const n = c.codePointAt(0)!; return n >= 0xd800 && n <= 0xdfff; });
  if (scalar(name) > 4096 || (description !== null && scalar(description) > 16384)
      || invalidScalar(name) || (description !== null && invalidScalar(description))) throw new Error("Thông tin vượt giới hạn hoặc có ký tự không hợp lệ.");
  const n = name.normalize("NFC").replace(W, "");
  const d = description?.replace(/\r\n?/g, "\n").normalize("NFC").replace(W, "") || null;
  if (!n || scalar(n) > 255 || /[\u0000-\u001f\u007f-\u009f\u2028\u2029]/.test(n)
      || (d !== null && (scalar(d) > 4000 || /[\u0000-\u0008\u000b-\u001f\u007f-\u009f]/.test(d)))) {
    throw new Error("Tên yêu cầu sơ bộ là bắt buộc (tối đa 255 ký tự); mô tả tối đa 4.000 ký tự. Vui lòng kiểm tra ký tự điều khiển.");
  }
  return { name: n, description: d };
}

function exactKeys(value: object, keys: string[]) {
  return Object.keys(value).length === keys.length && keys.every(k => Object.prototype.hasOwnProperty.call(value, k));
}

export function committedResponse(value: unknown, requestId: string): CommittedCreate {
  const v = value as CommittedCreate;
  if (!v || typeof v !== "object" || !exactKeys(v, ["status", "request_id", "project", "receipt"])
      || v.status !== "COMMITTED" || v.request_id !== requestId
      || !v.project || !exactKeys(v.project, ["id", "code"]) || !UUID4.test(v.project.id)
      || !/^[0-9]{39}$/.test(v.project.code) || BigInt(v.project.code) !== BigInt(`0x${v.project.id.replace(/-/g, "")}`)
      || !v.receipt || !exactKeys(v.receipt, ["id", "canonical_version", "recorded_at"])
      || !UUID.test(v.receipt.id) || v.receipt.canonical_version !== CANONICAL_VERSION
      || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/.test(v.receipt.recorded_at)
      || !Number.isFinite(Date.parse(v.receipt.recorded_at))) throw new ApiError("Chưa thể xác minh kết quả tạo yêu cầu.", 0);
  return v;
}

export async function postPreliminaryCreate(body: string, requestId: string) {
  return committedResponse(await request<unknown>("/api/v1/projects/preliminary-create", { method: "POST", body }, true), requestId);
}

export function isUnresolved(error: unknown, requestId: string): boolean {
  if (!(error instanceof ApiError)) return false;
  const d = error.detail?.detail;
  return error.status === 404 && d?.code === "UNRESOLVED" && d.status === "UNRESOLVED"
    && d.request_id === requestId && d.final === false;
}

export async function getPreliminaryCreate(requestId: string) {
  if (!UUID4.test(requestId)) throw new Error("Mã khôi phục không hợp lệ.");
  return committedResponse(await request<unknown>(`/api/v1/projects/preliminary-create-requests/${requestId}`), requestId);
}
