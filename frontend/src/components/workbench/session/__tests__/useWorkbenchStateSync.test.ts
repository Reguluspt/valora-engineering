import { expect, it, vi, beforeEach } from "vitest";
import { useWorkbenchStateSync } from "../useWorkbenchStateSync";
import { saveSelection } from "../../../../api/workbenchState";
import { ApiError } from "../../../../api/client";
vi.mock("react", () => ({ useCallback: (fn: unknown) => fn }));
vi.mock("../../../../api/workbenchState", () => ({ saveSelection: vi.fn() }));
beforeEach(() => vi.clearAllMocks());
it("acknowledges a persisted selection so its caller can refresh the server session version", async () => {
  vi.mocked(saveSelection).mockResolvedValue({});
  expect(await useWorkbenchStateSync("session").syncSelection("project_asset_line", ["line"])) .toBe(true);
  expect(saveSelection).toHaveBeenCalledExactlyOnceWith("session", { selected_target_type: "project_asset_line", selected_target_ids: ["line"] });
});
it("does not acknowledge denied or absent session selection writes", async () => {
  const error = vi.fn(); vi.mocked(saveSelection).mockRejectedValue(new ApiError("Denied", 403));
  expect(await useWorkbenchStateSync("session", error).syncSelection("project_asset_line", ["line"])) .toBe(false);
  expect(error).toHaveBeenCalledWith("Denied");
  expect(await useWorkbenchStateSync(undefined).syncSelection("project_asset_line", ["line"])) .toBe(false);
  expect(saveSelection).toHaveBeenCalledOnce();
});
