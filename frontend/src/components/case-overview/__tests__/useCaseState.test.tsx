import React from "react";
import { act, create } from "react-test-renderer";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../../../api/caseState";
import { useCaseState } from "../useCaseState";

vi.mock("../../../api/caseState", () => ({ fetchCaseState: vi.fn() }));

function renderCaseState(initialProjectId: string) {
  const result = { current: null as ReturnType<typeof useCaseState> | null };
  function Probe({ projectId }: { projectId: string }) {
    result.current = useCaseState(projectId);
    return null;
  }
  let root: ReturnType<typeof create>;
  act(() => {
    root = create(<Probe projectId={initialProjectId} />);
  });
  return {
    result,
    switchTo(projectId: string) {
      act(() => root.update(<Probe projectId={projectId} />));
    },
  };
}

const projection = (stage: string) => ({
  case_version: stage.padEnd(64, "a").slice(0, 64),
  current_stage: stage,
  next_action: {
    kind: "UNAVAILABLE",
    stage,
    semantic_route_key: null,
    validation_issue_id: null,
  },
  stages: [],
  blockers: [],
  warnings: [],
  stale: [],
  capabilities: [],
}) as api.CaseStateResponse;

describe("useCaseState", () => {
  beforeEach(() => vi.clearAllMocks());

  it("loads the server projection and supports a real retry", async () => {
    vi.mocked(api.fetchCaseState)
      .mockRejectedValueOnce(Object.assign(new Error("failed"), { status: 500 }))
      .mockResolvedValueOnce(projection("PRELIMINARY_REQUEST"));
    const { result } = renderCaseState("project-a");

    await vi.waitFor(() => expect(result.current?.state).toBe("PAGE_ERROR"));
    act(() => result.current?.retry());
    await vi.waitFor(() => expect(result.current?.state).toBe("READY"));

    expect(api.fetchCaseState).toHaveBeenCalledTimes(2);
    expect(result.current?.projection?.current_stage).toBe("PRELIMINARY_REQUEST");
  });

  it("clears the prior projection immediately when the project changes", async () => {
    vi.mocked(api.fetchCaseState).mockResolvedValueOnce(projection("PRELIMINARY_REQUEST"));
    const { result, switchTo } = renderCaseState("project-a");
    await vi.waitFor(() => expect(result.current?.state).toBe("READY"));

    let resolveB: (value: api.CaseStateResponse) => void = () => {};
    vi.mocked(api.fetchCaseState).mockReturnValueOnce(
      new Promise((resolve) => { resolveB = resolve; })
    );
    switchTo("project-b");

    expect(result.current?.state).toBe("INITIAL_LOADING");
    expect(result.current?.projection).toBeNull();
    await act(async () => resolveB(projection("OFFICIAL_INTAKE")));
    expect(result.current?.projection?.current_stage).toBe("OFFICIAL_INTAKE");
  });

});
