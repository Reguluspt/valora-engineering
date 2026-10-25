import { ApiError } from "../../api/client";
import { CommittedCreate, UUID4, getPreliminaryCreate, isUnresolved, normalizeCreateFields, postPreliminaryCreate } from "../../api/preliminaryCreate";

export interface CreateScope { organization_id: string; actor_user_id: string }
export interface IntentMarker extends CreateScope {
  version: 1; request_id: string; first_sent_at: string;
  phase: "UNCERTAIN" | "PARKED" | "COMMITTED";
  project_id?: string; receipt_id?: string;
}
const stores = new Map<string, PreliminaryCreateIntents>();
let activeScope = "";
let scopeGeneration = 0;
export const scopeKey = (scope: CreateScope) => `${scope.organization_id}:${scope.actor_user_id}`;
export function activateCreateScope(scope: CreateScope | null) {
  const next = scope ? scopeKey(scope) : "";
  if (next !== activeScope) { scopeGeneration++; activeScope = next; }
}
export function clearCreatePayloads() { for (const store of stores.values()) store.clearPayloads(); activateCreateScope(null); }
export function createIntents(scope: CreateScope) {
  const key = scopeKey(scope);
  let store = stores.get(key);
  if (!store) { store = new PreliminaryCreateIntents(scope); stores.set(key, store); }
  return store;
}

export class PreliminaryCreateIntents {
  readonly key: string;
  markers: IntentMarker[] = [];
  problem = "";
  message = "";
  conflict = new Set<string>();
  busy = new Set<string>();
  private originals = new Map<string, string>();
  private sends = new Map<string, number>();
  private listeners = new Set<() => void>();
  private version = 0;
  constructor(readonly scope: CreateScope) {
    this.key = `valora.preliminary-create.v1:${scopeKey(scope)}`;
    try {
      const raw = sessionStorage.getItem(this.key);
      const parsed: unknown = raw === null ? [] : JSON.parse(raw);
      if (!Array.isArray(parsed) || parsed.length > 32 || !parsed.every(m => this.validMarker(m))) throw new Error();
      if (new Set(parsed.map(m => m.request_id)).size !== parsed.length) throw new Error();
      this.markers = parsed;
    } catch { this.problem = "Không thể đọc dữ liệu khôi phục. Hãy kiểm tra bộ nhớ trình duyệt và liên hệ quản trị viên; không tạo lại yêu cầu chưa rõ kết quả."; }
  }
  private validMarker(m: IntentMarker) {
    const allowed = ["version", "organization_id", "actor_user_id", "request_id", "first_sent_at", "phase", "project_id", "receipt_id"];
    return m && typeof m === "object" && Object.keys(m).every(k => allowed.includes(k))
      && m.version === 1 && m.organization_id === this.scope.organization_id && m.actor_user_id === this.scope.actor_user_id
      && UUID4.test(m.request_id) && typeof m.first_sent_at === "string" && Number.isFinite(Date.parse(m.first_sent_at))
      && ["UNCERTAIN", "PARKED", "COMMITTED"].includes(m.phase)
      && (m.phase !== "COMMITTED" || (UUID4.test(m.project_id || "") && UUID4.test(m.receipt_id || "")));
  }
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  snapshot = () => this.version;
  private changed() { this.version++; this.listeners.forEach(f => f()); }
  isActive() { return activeScope === scopeKey(this.scope); }
  original(id: string) { return this.originals.get(id); }
  clearPayloads() { this.originals.clear(); this.changed(); }
  private persist(markers: IntentMarker[]) {
    try {
      const raw = JSON.stringify(markers);
      sessionStorage.setItem(this.key, raw);
      if (sessionStorage.getItem(this.key) !== raw) throw new Error();
      this.markers = markers;
      return true;
    } catch {
      this.problem = "Không thể lưu dữ liệu khôi phục. Chưa xác định kết quả; tải mã khôi phục và liên hệ quản trị viên.";
      return false;
    } finally { this.changed(); }
  }
  private commit(result: CommittedCreate) {
    const marker = this.markers.find(m => m.request_id === result.request_id);
    if (!marker) return false;
    const updated: IntentMarker = { ...marker, phase: "COMMITTED", project_id: result.project.id, receipt_id: result.receipt.id };
    this.originals.delete(result.request_id);
    const saved = this.persist(this.markers.map(m => m === marker ? updated : m));
    // Keep the acknowledged identity available even if storage failed; never reopen create.
    if (!saved) { this.markers = this.markers.map(m => m === marker ? updated : m); this.changed(); }
    return saved;
  }
  async submit(name: string, description: string, distinct = false) {
    if (!this.isActive() || this.problem || this.busy.size) return;
    if (this.markers.some(m => m.phase === "UNCERTAIN") || (this.markers.length && !distinct)) return;
    const fields = normalizeCreateFields(name, description);
    if (this.markers.length >= 32) throw new Error("Đã đạt giới hạn mã khôi phục. Vui lòng liên hệ quản trị viên.");
    if (!globalThis.crypto?.randomUUID) throw new Error("Cần trình duyệt có kết nối an toàn và bộ tạo mã bảo mật.");
    const id = crypto.randomUUID();
    if (!UUID4.test(id)) throw new Error("Không thể tạo mã yêu cầu an toàn.");
    const body = JSON.stringify({ request_id: id, ...fields });
    const marker: IntentMarker = { ...this.scope, version: 1, request_id: id, first_sent_at: new Date().toISOString(), phase: "UNCERTAIN" };
    if (!this.persist([...this.markers, marker])) return;
    this.originals.set(id, body);
    return this.send(id, body);
  }
  private async send(id: string, body: string) {
    if (!this.isActive() || this.busy.size) return;
    const generation = scopeGeneration;
    this.busy.add(id);
    const attempt = (this.sends.get(id) || 0) + 1;
    this.sends.set(id, attempt);
    this.message = "Đang tạo yêu cầu…"; this.changed();
    try {
      const result = await postPreliminaryCreate(body, id);
      if (!this.isActive() || generation !== scopeGeneration) return;
      this.message = "Yêu cầu đã được tạo.";
      return this.commit(result) ? result : undefined;
    } catch (error) {
      if (!this.isActive() || generation !== scopeGeneration) return;
      if (attempt === 1 && error instanceof ApiError && [401, 403, 422].includes(error.status)
          && (Array.isArray(error.detail?.detail) || typeof error.detail?.detail?.title === "string")) {
        this.originals.delete(id);
        this.persist(this.markers.filter(m => m.request_id !== id));
        this.message = error.status === 401 ? "Phiên làm việc hết hạn. Vui lòng đăng nhập lại."
          : error.code === "CSRF_ERROR" ? "Phiên làm việc cần được làm mới. Vui lòng tải lại trang."
          : error.status === 403 ? "Tài khoản chưa có quyền tạo yêu cầu sơ bộ." : "Thông tin chưa hợp lệ. Vui lòng kiểm tra lại.";
      } else {
        if (error instanceof ApiError && error.status === 409 && error.code === "POST_CONFLICT") this.conflict.add(id);
        this.message = this.conflict.has(id) ? "Mã yêu cầu đã gắn với nội dung khác. Nội dung vừa gửi chưa được lưu; chỉ mở hồ sơ đã gắn sau khi xác nhận."
          : "Chưa xác định yêu cầu đã được tạo hay chưa.";
      }
    } finally { this.busy.delete(id); this.changed(); }
  }
  async check(id: string) {
    if (!this.isActive()) return;
    const generation = scopeGeneration;
    try {
      const result = await getPreliminaryCreate(id);
      if (!this.isActive() || generation !== scopeGeneration) return;
      this.commit(result); this.message = "Đã tìm thấy hồ sơ của mã yêu cầu này. Chọn mở hồ sơ để tiếp tục.";
      return result;
    } catch (error) {
      if (!this.isActive() || generation !== scopeGeneration) return;
      this.message = isUnresolved(error, id) ? "Chưa xác định yêu cầu đã được tạo hay chưa."
        : "Chưa thể kiểm tra kết quả. Hãy khôi phục phiên làm việc hoặc liên hệ quản trị viên.";
    } finally { this.changed(); }
  }
  async replay(id: string) {
    const body = this.originals.get(id);
    if (!body || !this.isActive() || this.busy.size || this.problem || this.conflict.has(id)) return;
    const generation = scopeGeneration;
    // Lock before GET too: two explicit replay clicks must never dispatch two POSTs.
    this.busy.add(id); this.changed();
    let unresolved = false;
    try {
      const result = await getPreliminaryCreate(id);
      if (this.isActive() && generation === scopeGeneration) {
        this.commit(result);
        this.message = "Đã tìm thấy hồ sơ của mã yêu cầu này. Chọn mở hồ sơ để tiếp tục.";
      }
      return;
    }
    catch (error) { unresolved = isUnresolved(error, id); }
    finally { this.busy.delete(id); this.changed(); }
    if (unresolved && this.isActive() && generation === scopeGeneration && this.originals.get(id) === body) return this.send(id, body);
    this.message = "Chưa đủ điều kiện gửi lại. Hãy kiểm tra kết quả hoặc mở hồ sơ đã tạo."; this.changed();
  }
  park(id: string) {
    this.persist(this.markers.map(m => m.request_id === id && m.phase !== "COMMITTED" ? { ...m, phase: "PARKED" } : m));
  }
  retireCommitted() { this.persist(this.markers.filter(m => m.phase !== "COMMITTED")); }
  recoveryHandle(marker: IntentMarker) {
    return JSON.stringify({ version: 1, ...this.scope, request_id: marker.request_id, first_sent_at: marker.first_sent_at }, null, 2);
  }
}
