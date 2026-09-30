import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  finalizePreliminaryAnalysis,
  getPreliminaryAnalysis,
  type PreliminaryAnalysisFinalizeRequest,
} from "../preliminaryAnalysis";
import { request } from "../client";

vi.mock("../client", () => ({ request: vi.fn() }));

describe("preliminaryAnalysis API", () => {
  beforeEach(() => vi.clearAllMocks());

  it("finalizes preliminary analysis with encoded project id and payload", async () => {
    const responsePayload = {
      id: "analysis-1",
      project_id: "prj/1",
      version: 1,
      expected_project_version: 2,
      import_batch_id: "batch-1",
      source_artifact_id: "artifact-1",
    };
    vi.mocked(request).mockResolvedValueOnce(responsePayload);

    const requestPayload: PreliminaryAnalysisFinalizeRequest = {
      expected_project_version: 2,
      import_batch_id: "batch-1",
      source_artifact_id: "artifact-1",
      structure_snapshot_id: "structure-1",
      mapping_decision_id: "decision-1",
      mapping_profile_usage_id: "usage-1",
      mapping_decision_digest_sha256: "0".repeat(64),
      profile_usage_mapping_digest_sha256: "1".repeat(64),
      line_manifest: [
        {
          identity: "line-item-1",
          accepted_price_basis: "historical_invoice",
          confirmed_reference_price: 1500000,
          transport_percentage: 5,
          proposed_unit_price: 1575000,
          human_line_confirmed: true,
          has_unresolved_blocking_line: false,
          source_row_number: 4,
          quantity: 2,
        },
      ],
      idempotency_key: "idemp-1",
      confirmed: true,
    };

    const result = await finalizePreliminaryAnalysis("prj/1", requestPayload);
    expect(result).toBe(responsePayload);
    expect(request).toHaveBeenCalledWith(
      "/api/v1/projects/prj%2F1/preliminary-analyses",
      {
        method: "POST",
        body: JSON.stringify(requestPayload),
      }
    );
  });

  it("reads preliminary analysis with encoded project id and analysis id", async () => {
    const responsePayload = {
      id: "analysis-1",
      project_id: "prj/1",
      version: 1,
      import_batch_id: "batch-1",
      source_artifact_id: "artifact-1",
      structure_snapshot_id: "structure-1",
      mapping_decision_id: "decision-1",
      mapping_profile_usage_id: "usage-1",
      mapping_decision_digest_sha256: "0".repeat(64),
      profile_usage_mapping_digest_sha256: "1".repeat(64),
      line_manifest: [],
      line_manifest_digest_sha256: "2".repeat(64),
      finalized_by_user_id: "user-1",
      finalized_at: "2026-09-30T10:00:00Z",
    };
    vi.mocked(request).mockResolvedValueOnce(responsePayload);

    const signal = new AbortController().signal;
    const result = await getPreliminaryAnalysis("prj/1", "analysis/1", signal);
    expect(result).toBe(responsePayload);
    expect(request).toHaveBeenCalledWith(
      "/api/v1/projects/prj%2F1/preliminary-analyses/analysis%2F1",
      { signal }
    );
  });
});
