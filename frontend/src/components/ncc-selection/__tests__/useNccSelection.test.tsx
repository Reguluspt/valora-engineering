import React from "react";
import { act, create } from "react-test-renderer";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../../../api/nccSelection";
import { useNccSelection } from "../useNccSelection";

vi.mock("../../../api/nccSelection", () => ({ fetchNccSelections: vi.fn() }));

const aggregate = (projectId: string): api.NccSelectionAggregateResponse => ({
  project_id: projectId,
  kpis: { total_asset_lines: 0, selected: 0, unselected: 0, stale: 0, eligible_quotes: 0 },
  asset_lines: [],
});

function renderSelection(projectId: string) {
  const result = { current: null as ReturnType<typeof useNccSelection> | null };
  function Probe() {
    result.current = useNccSelection(projectId);
    return null;
  }
  act(() => { create(<Probe />); });
  return result;
}

describe("useNccSelection", () => {
  beforeEach(() => vi.clearAllMocks());

  it("loads the server aggregate", async () => {
    vi.mocked(api.fetchNccSelections).mockResolvedValueOnce(aggregate("p1"));
    const result = renderSelection("p1");
    await vi.waitFor(() => expect(result.current?.state).toBe("READY"));
    expect(result.current?.aggregate?.project_id).toBe("p1");
  });

  it("shows a page error and supports retry", async () => {
    vi.mocked(api.fetchNccSelections)
      .mockRejectedValueOnce(Object.assign(new Error("failed"), { status: 500 }))
      .mockResolvedValueOnce(aggregate("p1"));
    const result = renderSelection("p1");
    await vi.waitFor(() => expect(result.current?.state).toBe("PAGE_ERROR"));
    act(() => result.current?.retry());
    await vi.waitFor(() => expect(result.current?.state).toBe("READY"));
    expect(api.fetchNccSelections).toHaveBeenCalledTimes(2);
  });
});
