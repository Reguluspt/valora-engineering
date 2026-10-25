import React from "react";
import { act, create } from "react-test-renderer";
import { beforeEach, expect, it, vi } from "vitest";
import { Checkbox } from "@fluentui/react-components";
const api = vi.hoisted(() => ({ post: vi.fn(), get: vi.fn() }));
vi.mock("../../../api/preliminaryCreate", async original => ({ ...await original<object>(), postPreliminaryCreate: api.post, getPreliminaryCreate: api.get }));
import { ApiError } from "../../../api/client";
import { PreliminaryRequestCreatePage } from "../PreliminaryRequestCreatePage";
import { activateCreateScope, createIntents } from "../preliminaryCreateIntent";

let storage: Map<string, string>;
beforeEach(() => {
  storage = new Map(); vi.clearAllMocks();
  vi.stubGlobal("sessionStorage", { getItem: (k: string) => storage.get(k) ?? null, setItem: (k: string, v: string) => storage.set(k, v) });
});
async function mount(canCreate = true) {
  const scope = { organization_id: crypto.randomUUID(), actor_user_id: crypto.randomUUID() };
  activateCreateScope(scope);
  const onNavigate = vi.fn(); let root: any;
  await act(async () => { root = create(<PreliminaryRequestCreatePage scope={scope} canCreate={canCreate} onNavigate={onNavigate} onSessionExpired={vi.fn()} />); });
  return { root, onNavigate, store: createIntents(scope) };
}
it("A01 shows name/description without manual code and sends normalized captured input", async () => {
  api.post.mockRejectedValue(new ApiError("network", 0));
  const { root, onNavigate } = await mount();
  expect(root.root.findAllByType("input").some((i: any) => i.props.name === "code")).toBe(false);
  await act(async () => {
    root.root.findAllByType("input").find((i: any) => i.props.name === "name").props.onChange({ target: { value: " Nhà máy " } });
  });
  await act(async () => { await root.root.findByType("form").props.onSubmit({ preventDefault() {} }); });
  expect(JSON.parse(api.post.mock.calls[0][0]).name).toBe("Nhà máy");
  expect(onNavigate).not.toHaveBeenCalled();
  expect(JSON.stringify(root.toJSON())).toContain("Chưa xác định");
});
it("A20 viewer cannot dispatch and sees denial", async () => {
  const { root } = await mount(false);
  await act(async () => { await root.root.findByType("form").props.onSubmit({ preventDefault() {} }); });
  expect(api.post).not.toHaveBeenCalled();
  expect(JSON.stringify(root.toJSON())).toContain("chưa có quyền");
});

it.each(["parked", "committed"])("A27 requires a fresh distinct-intent acknowledgment after the previous intent becomes %s", async outcome => {
  api.post.mockRejectedValue(new ApiError("network", 0));
  const { root, store } = await mount();
  const submit = () => root.root.findByType("form").props.onSubmit({ preventDefault() {} });
  await act(async () => {
    root.root.findAllByType("input").find((i: any) => i.props.name === "name").props.onChange({ target: { value: "First intent" } });
  });
  await act(async () => { await submit(); });
  await act(async () => { store.park(store.markers[0].request_id); });
  const distinct = () => root.root.findAllByType(Checkbox).find((c: any) => c.props.label.startsWith("Tạo yêu cầu khác"));
  await act(async () => { distinct().props.onChange({}, { checked: true }); });
  await act(async () => { await submit(); });
  expect(api.post).toHaveBeenCalledTimes(2);
  const secondId = store.markers[1].request_id;
  if (outcome === "parked") {
    await act(async () => { store.park(secondId); });
  } else {
    api.get.mockResolvedValue({ status: "COMMITTED", request_id: secondId,
      project: { id: crypto.randomUUID(), code: "1".repeat(39) },
      receipt: { id: crypto.randomUUID(), canonical_version: "preliminary-create-v1", recorded_at: new Date().toISOString() } });
    await act(async () => { await store.check(secondId); });
  }
  expect(distinct().props.checked).toBe(false);
  expect(root.root.findAllByType("button").find((b: any) => b.props.type === "submit").props.disabled).toBe(true);
  await act(async () => { await submit(); });
  expect(api.post).toHaveBeenCalledTimes(2);
});
