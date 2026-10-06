import { beforeEach, expect, it, vi } from "vitest";
import { request } from "../client";
import { fetchWorkbenchPreparation, fetchWorkbenchReceipt, submitWorkbench, type WorkbenchCommand } from "../assetWorkbench";
vi.mock("../client", () => ({ request: vi.fn() }));
beforeEach(() => vi.clearAllMocks());
it("uses the scoped preparation and receipt reads", async () => {
  await fetchWorkbenchPreparation("p/1"); await fetchWorkbenchReceipt("p/1", "command/1");
  expect(request).toHaveBeenNthCalledWith(1, "/api/v1/projects/p%2F1/asset-workbench/preparation");
  expect(request).toHaveBeenNthCalledWith(2, "/api/v1/projects/p%2F1/asset-workbench/command-receipts/command%2F1");
});
it.each(["asset-workbench-confirmation-v1", "asset-workbench-withdrawal-v1"] as const)("posts the unchanged %s contract once", async contract => {
  const command = { contract_version: contract, reason_note: "Protected text", confirm: true } as WorkbenchCommand;
  await submitWorkbench("p", command);
  expect(request).toHaveBeenCalledExactlyOnceWith(`/api/v1/projects/p/asset-workbench/${contract === "asset-workbench-confirmation-v1" ? "confirm" : "withdraw"}`,
    { method: "POST", body: JSON.stringify(command) });
});
