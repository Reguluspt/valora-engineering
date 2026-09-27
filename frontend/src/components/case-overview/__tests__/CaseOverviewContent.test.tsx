import React from "react";
import { act, create } from "react-test-renderer";
import { describe, expect, it, vi } from "vitest";

import type { CaseStateResponse } from "../../../api/caseState";
import { CANONICAL_CASE_STAGES } from "../../../contracts/valoraV23";
import { CaseOverviewContent } from "../CaseOverviewPage";

function buildProjection(): CaseStateResponse {
  return {
    case_version: "a".repeat(64),
    current_stage: "PRELIMINARY_ANALYSIS",
    next_action: {
      kind: "PENDING",
      stage: "PRELIMINARY_ANALYSIS",
      semantic_route_key: "preliminary_analysis_pending",
      validation_issue_id: null,
    },
    stages: CANONICAL_CASE_STAGES.map((stage, index) => ({
      stage,
      result: index === 0 ? "COMPLETE" : index < 4 ? "INCOMPLETE" : "NOT_AVAILABLE",
      provider_key: index < 4 ? `${stage.toLowerCase()}_v1` : null,
    })),
    blockers: [],
    warnings: [{
      id: "warning-1",
      target_type: "project",
      target_id: "project-1",
      severity: "warning",
      status: "open",
      row_version: 1,
    }],
    stale: [],
    capabilities: CANONICAL_CASE_STAGES.map((stage, index) => ({
      stage,
      available: index < 4,
      provider_key: index < 4 ? `${stage.toLowerCase()}_v1` : null,
      version: "pr01-prefix-v1",
    })),
  };
}

describe("CaseOverviewContent", () => {
  it("renders all server-ordered stages and one mapped primary action", () => {
    const navigate = vi.fn();
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(
        <CaseOverviewContent
          projectName="Hồ sơ HD-01"
          projection={buildProjection()}
          workbenchPath="/workbench/projects/project-1"
          onNavigate={navigate}
        />
      );
    });

    const stageRows = root.root.findAll((node) => Boolean(node.props["data-case-stage"]));
    expect(stageRows).toHaveLength(16);
    expect(stageRows.map((node) => node.props["data-case-stage"])).toEqual(
      CANONICAL_CASE_STAGES
    );
    const primaryActions = root.root.findAllByProps({ "data-primary-action": true });
    expect(primaryActions).toHaveLength(1);
    act(() => primaryActions[0].props.onClick());
    expect(navigate).toHaveBeenCalledWith("/workbench/projects/project-1");
  });

  it("keeps warning separate and does not invent a route for a blocker", () => {
    const projection = buildProjection();
    projection.next_action = {
      kind: "BLOCKER",
      stage: "OFFICIAL_INTAKE",
      semantic_route_key: null,
      validation_issue_id: "blocker-1",
    };
    projection.blockers = [{
      id: "blocker-1",
      target_type: "project",
      target_id: "project-1",
      severity: "blocking",
      status: "open",
      row_version: 1,
    }];

    let root: ReturnType<typeof create>;
    act(() => {
      root = create(
        <CaseOverviewContent
          projectName="Hồ sơ HD-01"
          projection={projection}
          workbenchPath="/workbench/projects/project-1"
          onNavigate={vi.fn()}
        />
      );
    });

    expect(root.root.findAllByProps({ "data-primary-action": true })).toHaveLength(0);
    expect(root.root.findAllByProps({ "data-issue-kind": "blocking" })).toHaveLength(1);
    expect(root.root.findAllByProps({ "data-issue-kind": "warning" })).toHaveLength(1);
  });

  it("keeps the stage order supplied by the projection", () => {
    const projection = buildProjection();
    const first = projection.stages[0];
    projection.stages[0] = projection.stages[1];
    projection.stages[1] = first;
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(
        <CaseOverviewContent
          projectName="Hồ sơ HD-01"
          projection={projection}
          workbenchPath="/workbench/projects/project-1"
          onNavigate={vi.fn()}
        />
      );
    });
    const stageRows = root.root.findAll((node) => Boolean(node.props["data-case-stage"]));
    expect(stageRows.map((node) => node.props["data-case-stage"])).toEqual(
      projection.stages.map((stage) => stage.stage),
    );
  });

  it("renders stale projection entries in their own review section", () => {
    const projection = buildProjection();
    projection.stale = [{
      kind: "SOURCE_STALE",
      target_type: "project",
      target_id: "project-1",
    }];

    let root: ReturnType<typeof create>;
    act(() => {
      root = create(
        <CaseOverviewContent
          projectName="Hồ sơ HD-01"
          projection={projection}
          workbenchPath="/workbench/projects/project-1"
          onNavigate={vi.fn()}
        />
      );
    });

    expect(root.root.findAllByProps({ "data-issue-kind": "stale" })).toHaveLength(1);
  });

});
