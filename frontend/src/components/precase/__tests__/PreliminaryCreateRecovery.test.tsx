import React from "react";
import { act, create } from "react-test-renderer";
import { expect, it, vi } from "vitest";
import { PreliminaryCreateRecovery } from "../PreliminaryCreateRecovery";
import { PreliminaryCreateIntents, activateCreateScope } from "../preliminaryCreateIntent";

it("A24/A27 restored intent offers GET, support, download and safe navigation without replay", async () => {
  const scope = { organization_id: crypto.randomUUID(), actor_user_id: crypto.randomUUID() };
  const marker = { ...scope, version: 1, request_id: crypto.randomUUID(), first_sent_at: new Date().toISOString(), phase: "PARKED" };
  vi.stubGlobal("sessionStorage", { getItem: () => JSON.stringify([marker]) });
  const store = new PreliminaryCreateIntents(scope);
  let root: any;
  await act(async () => { root = create(<PreliminaryCreateRecovery store={store} onNavigate={vi.fn()} onSessionExpired={vi.fn()} />); });
  const rendered = JSON.stringify(root.toJSON());
  expect(rendered).toContain("Kiểm tra kết quả");
  expect(rendered).toContain("Tiếp tục công việc khác");
  expect(rendered).toContain("Tải mã khôi phục");
  expect(rendered).not.toContain("Gửi lại yêu cầu ban đầu");
  expect(rendered).toContain("Không tạo lại cùng yêu cầu với mã mới");
});

it("A31 keeps multiple unresolved and committed intents independently identifiable and actionable", async () => {
  const scope = { organization_id: crypto.randomUUID(), actor_user_id: crypto.randomUUID() };
  activateCreateScope(scope);
  const parked = { ...scope, version: 1, request_id: crypto.randomUUID(), first_sent_at: new Date().toISOString(), phase: "PARKED" };
  const committed = { ...scope, version: 1, request_id: crypto.randomUUID(), first_sent_at: new Date().toISOString(), phase: "COMMITTED", project_id: crypto.randomUUID(), receipt_id: crypto.randomUUID() };
  vi.stubGlobal("sessionStorage", { getItem: () => JSON.stringify([parked, committed]) });
  const store = new PreliminaryCreateIntents(scope);
  const check = vi.spyOn(store, "check").mockResolvedValue(undefined);
  const onNavigate = vi.fn(); let root: any;
  await act(async () => { root = create(<PreliminaryCreateRecovery store={store} onNavigate={onNavigate} onSessionExpired={vi.fn()} />); });
  const first = root.root.findByProps({ "aria-label": `Yêu cầu ${parked.request_id}` });
  const second = root.root.findByProps({ "aria-label": `Yêu cầu ${committed.request_id}` });
  const text = (node: any): string => typeof node === "string" ? node : (node.children ?? []).map(text).join(" ");
  expect(text(first)).toContain("Chưa xác định");
  expect(text(first)).not.toContain("Đã xác nhận");
  expect(text(second)).toContain("Đã xác nhận");
  expect(text(second)).not.toContain("Chưa xác định");
  await act(async () => { await first.findAllByType("button").find((b: any) => text(b).trim() === "Kiểm tra kết quả").props.onClick(); });
  expect(check).toHaveBeenCalledExactlyOnceWith(parked.request_id);
  await act(async () => { second.findAllByType("button").find((b: any) => text(b).trim() === "Mở hồ sơ đã gắn với mã yêu cầu").props.onClick(); });
  expect(onNavigate).toHaveBeenCalledWith(`/workbench/projects/${committed.project_id}/preliminary-intake`);
  expect(store.markers).toEqual([parked, committed]);
});

it("A25/A31 distinguishes failed local persistence from an acknowledged committed receipt", async () => {
  const scope = { organization_id: crypto.randomUUID(), actor_user_id: crypto.randomUUID() };
  activateCreateScope(scope);
  const marker = { ...scope, version: 1, request_id: crypto.randomUUID(), first_sent_at: new Date().toISOString(), phase: "UNCERTAIN" };
  vi.stubGlobal("sessionStorage", { getItem: () => JSON.stringify([marker]), setItem: () => { throw new Error("synthetic quota"); } });
  const projectId = crypto.randomUUID();
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ status: "COMMITTED", request_id: marker.request_id,
    project: { id: projectId, code: BigInt(`0x${projectId.replace(/-/g, "")}`).toString().padStart(39, "0") },
    receipt: { id: crypto.randomUUID(), canonical_version: "preliminary-create-v1", recorded_at: new Date().toISOString() } }) }));
  const store = new PreliminaryCreateIntents(scope);
  await store.check(marker.request_id);
  expect(store.problem).not.toBe("");
  expect(store.markers[0].phase).toBe("COMMITTED");
  let root: any;
  await act(async () => { root = create(<PreliminaryCreateRecovery store={store} onNavigate={vi.fn()} onSessionExpired={vi.fn()} />); });
  const rendered = JSON.stringify(root.toJSON());
  expect(rendered).toContain("Đã xác nhận tạo hồ sơ.");
  expect(rendered).toContain("Bộ nhớ trình duyệt chưa lưu được cập nhật");
  expect(rendered).not.toContain("Chưa xác định kết quả");
  expect(rendered).toContain("Tải mã khôi phục");
  vi.unstubAllGlobals();
});
