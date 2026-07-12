import { describe, it, expect, vi } from "vitest";
import { executeDraftCommit } from "../AssetGrid";

describe("executeDraftCommit", () => {
  const MSG = "Xác nhận áp dụng nháp\n\nThao tác này sẽ cập nhật dữ liệu chính thức.";

  it("does not call commit callback when confirm returns false", () => {
    const confirmMock = vi.fn().mockReturnValue(false);
    const commitMock = vi.fn();

    const result = executeDraftCommit(
      confirmMock, commitMock,
      "line-123", 5, ["appraised_unit_price"], MSG
    );

    expect(result).toBe(false);
    expect(confirmMock).toHaveBeenCalledWith(MSG);
    expect(commitMock).not.toHaveBeenCalled();
  });

  it("calls commit callback exactly once with correct args when confirm returns true", () => {
    const confirmMock = vi.fn().mockReturnValue(true);
    const commitMock = vi.fn();

    const result = executeDraftCommit(
      confirmMock, commitMock,
      "line-456", 3, ["appraised_unit_price"], MSG
    );

    expect(result).toBe(true);
    expect(confirmMock).toHaveBeenCalledWith(MSG);
    expect(commitMock).toHaveBeenCalledTimes(1);
    expect(commitMock).toHaveBeenCalledWith(
      "line-456",
      ["appraised_unit_price"],
      "3"
    );
  });

  it("passes String(row.row_version) — string type, not number", () => {
    const confirmMock = vi.fn().mockReturnValue(true);
    const commitMock = vi.fn();

    executeDraftCommit(confirmMock, commitMock, "line-1", 7, ["appraised_unit_price"], MSG);

    const versionArg = commitMock.mock.calls[0][2];
    expect(versionArg).toBe("7");
    expect(typeof versionArg).toBe("string");
  });

  it("passes exact field list ['appraised_unit_price']", () => {
    const confirmMock = vi.fn().mockReturnValue(true);
    const commitMock = vi.fn();

    executeDraftCommit(confirmMock, commitMock, "line-2", 1, ["appraised_unit_price"], MSG);

    expect(commitMock.mock.calls[0][1]).toEqual(["appraised_unit_price"]);
  });
});
