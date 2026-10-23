import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../client";
import { committedResponse, getPreliminaryCreate, isUnresolved, normalizeCreateFields, postPreliminaryCreate } from "../preliminaryCreate";

const nonce = "11111111-1111-4111-8111-111111111111";
afterEach(() => vi.unstubAllGlobals());
describe("preliminary create wire contract", () => {
  it("A23 sends a mutation once on 401 without refresh or automatic replay", async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({ detail: { title: "Expired" } }) });
    vi.stubGlobal("fetch", fetch);
    await expect(postPreliminaryCreate("{}", nonce)).rejects.toMatchObject({ status: 401 });
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][0]).toContain("/preliminary-create");
  });
  it("A29 distinguishes a bare old-node 404 from typed unresolved", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({ detail: "Not Found" }) }));
    try { await getPreliminaryCreate(nonce); } catch (error) { expect(isUnresolved(error, nonce)).toBe(false); }
    expect(isUnresolved(new ApiError("", 404, "UNRESOLVED", { detail: { code: "UNRESOLVED", status: "UNRESOLVED", request_id: nonce, final: false } }), nonce)).toBe(true);
  });
  it("A03 follows frozen Unicode normalization and scalar boundaries", () => {
    expect(normalizeCreateFields(" \u0085e\u0302\u0301 😀\u3000", " A\r\nB\rC ")).toEqual({ name: "ế 😀", description: "A\nB\nC" });
    expect(normalizeCreateFields("😀".repeat(255), "😀".repeat(4000)).name).toHaveLength(510);
    for (const name of ["\ud800", "a\u2028b", "a".repeat(256), " ".repeat(4097)]) expect(() => normalizeCreateFields(name)).toThrow();
    expect(normalizeCreateFields("A  B\u200b").name).toBe("A  B\u200b");
  });
  it("A22 rejects malformed or mismatched success as uncertain", () => {
    for (const body of [null, {}, { status: "COMMITTED", request_id: "wrong" }]) expect(() => committedResponse(body, nonce)).toThrow();
  });
});
