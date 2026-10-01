import { describe, expect, it } from "vitest";
import type { CaseStateResponse } from "../../../api/caseState";
import {
  attemptCommitted, attemptRetryable, canBindCustomer, canCommitIntake, canGenerateResult,
  type CompletionAttempt,
} from "../preliminaryCompletionModel";

function state(): CaseStateResponse {
  return {
    case_version: "a".repeat(64), current_stage: "PRELIMINARY_READY",
    next_action: { kind: "PENDING", stage: "PRELIMINARY_READY", semantic_route_key: "preliminary_ready_pending", validation_issue_id: null },
    stages: [
      { stage: "PRELIMINARY_ANALYSIS", result: "COMPLETE", provider_key: "analysis" },
      { stage: "PRELIMINARY_READY", result: "INCOMPLETE", provider_key: "result" },
      { stage: "OFFICIAL_INTAKE", result: "INCOMPLETE", provider_key: "intake" },
    ],
    blockers: [], warnings: [], stale: [], capabilities: [],
    preliminary: {
      project_id: "project-1", customer_id: null, project_row_version: 7,
      current_preliminary_import_batch_id: "batch-1", current_source_artifact_id: "source-1",
      current_preliminary_analysis_snapshot_id: "analysis-2", current_preliminary_analysis_version: 2,
      current_preliminary_result_artifact_id: null, current_preliminary_result_version: null,
      official_intake_commit_id: null,
    },
  };
}

const resultAttempt: CompletionAttempt = { kind: "result", payload: {
  preliminary_analysis_snapshot_id: "analysis-2", expected_project_version: 7,
  idempotency_key: "stable-result", confirmed: true,
} };
const customerAttempt: CompletionAttempt = { kind: "customer", payload: {
  customer_id: "customer-1", expected_project_version: 7, idempotency_key: "stable-customer",
} };
const intakeAttempt: CompletionAttempt = { kind: "intake", payload: {
  preliminary_result_artifact_id: "result-2", expected_preliminary_result_version: 2,
  expected_project_version: 7, idempotency_key: "stable-intake", confirmed: true,
} };

describe("Pre-case completion authority", () => {
  it("generates only from the selected Analysis under the server route and blocker gate", () => {
    const ready = state();
    expect(canGenerateResult(ready)).toBe(true);
    expect(attemptRetryable(ready, resultAttempt, false)).toBe(true);
    ready.preliminary.current_preliminary_analysis_snapshot_id = null;
    expect(canGenerateResult(ready)).toBe(false);
    ready.preliminary.current_preliminary_analysis_snapshot_id = "analysis-2";
    ready.next_action!.semantic_route_key = "official_intake_pending";
    expect(canGenerateResult(ready)).toBe(false);
    ready.next_action!.semantic_route_key = "preliminary_ready_pending";
    ready.blockers.push({ id: "issue-1", target_type: "project", target_id: "project-1", severity: "blocking", status: "open", row_version: 1 });
    expect(canGenerateResult(ready)).toBe(false);
  });

  it("recognizes a selected Result without choosing a historical row or regenerating", () => {
    const ready = state();
    ready.preliminary.current_preliminary_result_artifact_id = "result-2";
    ready.preliminary.current_preliminary_result_version = 2;
    ready.next_action!.semantic_route_key = "official_intake_pending";
    expect(canGenerateResult(ready)).toBe(false);
    expect(canBindCustomer(ready)).toBe(true);
    expect(attemptCommitted(ready, resultAttempt)).toBe(true);
    expect(attemptRetryable(ready, customerAttempt, true)).toBe(true);
    ready.preliminary.customer_id = "other-customer";
    expect(canBindCustomer(ready)).toBe(false);
    expect(attemptCommitted(ready, customerAttempt)).toBe(false);
  });

  it("requires exact Result, Customer, blocker-free server route and version for Intake", () => {
    const ready = state();
    ready.preliminary.current_preliminary_result_artifact_id = "result-2";
    ready.preliminary.current_preliminary_result_version = 2;
    ready.preliminary.customer_id = "customer-1";
    ready.next_action!.semantic_route_key = "official_intake_pending";
    expect(canCommitIntake(ready, true)).toBe(true);
    expect(attemptRetryable(ready, intakeAttempt, true)).toBe(true);
    expect(canCommitIntake(ready, false)).toBe(false);
    ready.preliminary.project_row_version = 8;
    expect(attemptRetryable(ready, intakeAttempt, true)).toBe(false);
    ready.preliminary.project_row_version = 7;
    ready.preliminary.current_preliminary_result_version = 3;
    expect(attemptRetryable(ready, intakeAttempt, true)).toBe(false);
    ready.preliminary.current_preliminary_result_version = 2;
    ready.blockers.push({ id: "issue-1", target_type: "project", target_id: "project-1", severity: "blocking", status: "open", row_version: 1 });
    expect(canCommitIntake(ready, true)).toBe(false);
    ready.blockers = [];
    ready.preliminary.official_intake_commit_id = "commit-1";
    expect(canCommitIntake(ready, true)).toBe(false);
    expect(attemptCommitted(ready, intakeAttempt)).toBe(true);
  });
});
