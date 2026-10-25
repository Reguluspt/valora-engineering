import { beforeEach, describe, expect, it, vi } from "vitest";
const api = vi.hoisted(() => ({ post: vi.fn(), get: vi.fn() }));
vi.mock("../../../api/preliminaryCreate", async original => ({ ...await original<object>(), postPreliminaryCreate: api.post, getPreliminaryCreate: api.get }));
import { ApiError } from "../../../api/client";
import { PreliminaryCreateIntents, activateCreateScope, clearCreatePayloads } from "../preliminaryCreateIntent";

const scope = { organization_id: "11111111-1111-4111-8111-111111111111", actor_user_id: "22222222-2222-4222-8222-222222222222" };
const unresolved = (id: string) => new ApiError("", 404, "UNRESOLVED", { detail: { code: "UNRESOLVED", status: "UNRESOLVED", request_id: id, final: false } });
let values: Map<string, string>;
beforeEach(() => {
  values = new Map(); vi.clearAllMocks();
  vi.stubGlobal("sessionStorage", { getItem: (k: string) => values.get(k) ?? null, setItem: (k: string, v: string) => values.set(k, v) });
  activateCreateScope(scope);
});
describe("pending intent lifetime", () => {
  it("A22 serializes duplicate clicks, persists before dispatch, and never stores payload", async () => {
    let done!: () => void;
    api.post.mockImplementation(() => new Promise((_, reject) => { done = () => reject(new ApiError("network", 0)); }));
    const store = new PreliminaryCreateIntents(scope);
    const first = store.submit("Private title", "Private content");
    await store.submit("Private title", "Private content");
    expect(api.post).toHaveBeenCalledTimes(1);
    expect([...values.values()].join()).not.toMatch(/Private/);
    done(); await first;
    expect(store.markers[0].phase).toBe("UNCERTAIN");
    expect(api.post).toHaveBeenCalledTimes(1);
  });
  it("A24 replays only exact frozen bytes following fresh GET and retains prior unknown after 403", async () => {
    api.post.mockRejectedValueOnce(new ApiError("network", 0));
    const store = new PreliminaryCreateIntents(scope);
    await store.submit("Original", "Body");
    const id = store.markers[0].request_id;
    const body = api.post.mock.calls[0][0];
    api.get.mockRejectedValue(unresolved(id));
    api.post.mockRejectedValue(new ApiError("Denied", 403, undefined, { detail: { title: "Denied" } }));
    await store.replay(id);
    expect(api.get).toHaveBeenCalledTimes(1);
    expect(api.post.mock.calls[1][0]).toBe(body);
    expect(store.markers[0].phase).toBe("UNCERTAIN");
  });
  it("keeps the confirmed recovery message when replay GET finds COMMITTED without another POST", async () => {
    api.post.mockRejectedValueOnce(new ApiError("network", 0));
    const store = new PreliminaryCreateIntents(scope);
    await store.submit("Original", "Body");
    const id = store.markers[0].request_id;
    api.get.mockResolvedValueOnce({ request_id: id, project: { id: scope.actor_user_id }, receipt: { id: scope.actor_user_id } });
    await store.replay(id);
    expect(store.markers[0].phase).toBe("COMMITTED");
    expect(store.message).toBe("Đã tìm thấy hồ sơ của mã yêu cầu này. Chọn mở hồ sơ để tiếp tục.");
    expect(store.original(id)).toBeUndefined();
    expect(api.post).toHaveBeenCalledTimes(1);
  });
  it("checks COMMITTED without automatically posting", async () => {
    api.post.mockRejectedValueOnce(new ApiError("network", 0));
    const store = new PreliminaryCreateIntents(scope);
    await store.submit("Original", "Body");
    const id = store.markers[0].request_id;
    api.get.mockResolvedValueOnce({ request_id: id, project: { id: scope.actor_user_id }, receipt: { id: scope.actor_user_id } });
    await store.check(id);
    expect(store.markers[0].phase).toBe("COMMITTED");
    expect(store.message).toMatch(/^Đã tìm thấy hồ sơ/);
    expect(api.post).toHaveBeenCalledTimes(1);
  });
  it("keeps UNRESOLVED GET non-final without automatically posting", async () => {
    api.post.mockRejectedValueOnce(new ApiError("network", 0));
    const store = new PreliminaryCreateIntents(scope);
    await store.submit("Original", "Body");
    const id = store.markers[0].request_id;
    api.get.mockRejectedValueOnce(unresolved(id));
    await store.check(id);
    expect(store.markers[0].phase).toBe("UNCERTAIN");
    expect(store.message).toBe("Chưa xác định yêu cầu đã được tạo hay chưa.");
    expect(store.original(id)).toBe(api.post.mock.calls[0][0]);
    expect(api.post).toHaveBeenCalledTimes(1);
  });
  it("retains uncertainty and original bytes when recovery GET fails on the network", async () => {
    api.post.mockRejectedValueOnce(new ApiError("network", 0));
    const store = new PreliminaryCreateIntents(scope);
    await store.submit("Original", "Body");
    const id = store.markers[0].request_id;
    api.get.mockRejectedValueOnce(new ApiError("network", 0));
    await store.replay(id);
    expect(store.markers[0].phase).toBe("UNCERTAIN");
    expect(store.message).toMatch(/^Chưa đủ điều kiện gửi lại/);
    expect(store.original(id)).toBe(api.post.mock.calls[0][0]);
    expect(api.post).toHaveBeenCalledTimes(1);
  });
  it("A25 storage failure and unavailable CSPRNG block dispatch", async () => {
    vi.stubGlobal("sessionStorage", { getItem: () => null, setItem: () => { throw new Error("quota"); } });
    const store = new PreliminaryCreateIntents(scope);
    await store.submit("A", "");
    expect(api.post).not.toHaveBeenCalled();
    vi.stubGlobal("crypto", {});
    await expect(new PreliminaryCreateIntents(scope).submit("A", "")).rejects.toThrow("bảo mật");
    vi.unstubAllGlobals();
  });
  it("A26 reload loses body, retains locator, and disables replay", async () => {
    api.post.mockRejectedValue(new ApiError("network", 0));
    const first = new PreliminaryCreateIntents(scope);
    await first.submit("A", "B");
    const restored = new PreliminaryCreateIntents(scope);
    expect(restored.markers).toEqual(first.markers);
    expect(restored.original(first.markers[0].request_id)).toBeUndefined();
    await restored.replay(first.markers[0].request_id);
    expect(api.post).toHaveBeenCalledTimes(1);
    expect(restored.recoveryHandle(restored.markers[0])).not.toMatch(/"name"|description|cookie|token/);
  });
  it("A27 parking retains uncertainty and requires distinct-intent acknowledgement", async () => {
    api.post.mockRejectedValue(new ApiError("network", 0));
    const store = new PreliminaryCreateIntents(scope);
    await store.submit("A", ""); store.park(store.markers[0].request_id);
    await store.submit("A", ""); expect(api.post).toHaveBeenCalledTimes(1);
    await store.submit("A", "", true); expect(api.post).toHaveBeenCalledTimes(2);
    expect(store.markers).toHaveLength(2);
  });
  it("A26 quarantines late responses through logout/login of the same account", async () => {
    let finish!: (result: unknown) => void;
    api.post.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
    const store = new PreliminaryCreateIntents(scope);
    const promise = store.submit("A", "");
    const id = store.markers[0].request_id;
    clearCreatePayloads(); activateCreateScope(scope);
    finish({ request_id: id, project: { id: scope.actor_user_id }, receipt: { id: scope.actor_user_id } });
    expect(await promise).toBeUndefined(); expect(store.markers[0].phase).toBe("UNCERTAIN");
  });
});
