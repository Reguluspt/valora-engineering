import { afterEach, expect, it, vi } from "vitest";
import { applyAssetImport, validateAssetImport } from "../assetImports";
const token = "a".repeat(64);
afterEach(() => vi.unstubAllGlobals());
it("sends only the exact accepted bodies, credentials and CSRF; no command ID/session", async () => {
  vi.stubGlobal("document", { cookie: "XSRF-TOKEN=test-xsrf" });
  const fetcher = vi.fn().mockImplementation(async () => new Response("{}", { status: 200 })); vi.stubGlobal("fetch", fetcher);
  await validateAssetImport("p", "b", { expected_case_version: token, leaked: "discard" } as any);
  await applyAssetImport("p", "b", { confirm: true, contract_version: "s12-post-intake-guarded-apply-v2", expected_case_version: token, command_id: "discard" } as any);
  expect(fetcher.mock.calls.map(c => [c[0], JSON.parse(c[1].body)])).toEqual([
    ["/api/v1/projects/p/asset-imports/b/validate", { expected_case_version: token }],
    ["/api/v1/projects/p/asset-imports/b/apply", { confirm: true, contract_version: "s12-post-intake-guarded-apply-v2", expected_case_version: token }],
  ]);
  for (const [, options] of fetcher.mock.calls) { expect(options.credentials).toBe("include"); expect(options.headers.get("X-CSRF-Token")).toBe("test-xsrf"); }
});
it.each(["validate", "apply"] as const)("never refreshes or replays %s after a 401", async kind => {
  const fetcher = vi.fn().mockResolvedValue(new Response("{}", { status: 401 })); vi.stubGlobal("fetch", fetcher);
  const promise = kind === "validate" ? validateAssetImport("p", "b", { expected_case_version: token })
    : applyAssetImport("p", "b", { confirm: true, contract_version: "s12-post-intake-guarded-apply-v2", expected_case_version: token });
  await expect(promise).rejects.toMatchObject({ status: 401 });
  expect(fetcher).toHaveBeenCalledTimes(1); expect(fetcher.mock.calls[0][0]).toMatch(new RegExp(`/${kind}$`));
});
