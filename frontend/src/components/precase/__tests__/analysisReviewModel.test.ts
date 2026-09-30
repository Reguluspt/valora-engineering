import { describe, expect, it } from "vitest";
import {
  analysisContextReady,
  buildAnalysisManifest,
  draftFromStaging,
} from "../analysisReviewModel";

const staging = (source_row_number: number, proposed_quantity = "2") => ({
  id: `row-${source_row_number}`,
  import_batch_id: "batch-1",
  source_row_number,
  proposed_asset_name: `Thiết bị ${source_row_number}`,
  proposed_quantity,
  validation_status: "pending" as const,
  validation_errors: [],
  validation_warnings: [],
});

const reviewed = (source_row_number: number, proposed_quantity = "2") => ({
  ...draftFromStaging(staging(source_row_number, proposed_quantity)),
  accepted_price_basis: "Giá tham chiếu đã kiểm tra",
  confirmed_reference_price: "100",
  transport_percentage: "0",
  proposed_unit_price: "110",
  human_line_confirmed: true,
});

describe("analysis review model", () => {
  it("uses server row provenance and accepts zero quantity and transport", () => {
    const manifest = buildAnalysisManifest([reviewed(27, "0")]);
    expect(manifest).toEqual([{
      identity: "Thiết bị 27",
      accepted_price_basis: "Giá tham chiếu đã kiểm tra",
      confirmed_reference_price: 100,
      transport_percentage: 0,
      proposed_unit_price: 110,
      human_line_confirmed: true,
      has_unresolved_blocking_line: false,
      source_row_number: 27,
      quantity: 0,
    }]);
  });

  it("rejects duplicate or invalid source rows and missing source quantity", () => {
    expect(buildAnalysisManifest([reviewed(27), reviewed(27)])).toBeNull();
    expect(buildAnalysisManifest([reviewed(0)])).toBeNull();
    expect(buildAnalysisManifest([reviewed(27, "")])).toBeNull();
    expect(buildAnalysisManifest([reviewed(27, "1,5")])).toBeNull();
  });

  it("requires explicit review with no unresolved line", () => {
    expect(buildAnalysisManifest([{ ...reviewed(27), human_line_confirmed: false }])).toBeNull();
    expect(buildAnalysisManifest([{ ...reviewed(27), has_unresolved_blocking_line: true }])).toBeNull();
  });

  it("rejects missing basis, identity, invalid numbers and transport outside 0..100", () => {
    const row = reviewed(27);
    expect(buildAnalysisManifest([{ ...row, identity: " " }])).toBeNull();
    expect(buildAnalysisManifest([{ ...row, accepted_price_basis: " " }])).toBeNull();
    expect(buildAnalysisManifest([{ ...row, confirmed_reference_price: "-1" }])).toBeNull();
    expect(buildAnalysisManifest([{ ...row, confirmed_reference_price: "NaN" }])).toBeNull();
    expect(buildAnalysisManifest([{ ...row, proposed_unit_price: "abc" }])).toBeNull();
    expect(buildAnalysisManifest([{ ...row, transport_percentage: "101" }])).toBeNull();
    expect(buildAnalysisManifest([{ ...row, transport_percentage: "-0.1" }])).toBeNull();
  });

  it("requires the selected materialized usage on exact current source", () => {
    const preliminary = {
      project_id: "project-1",
      current_preliminary_import_batch_id: "batch-1",
      current_source_artifact_id: "source-1",
      current_preliminary_analysis_snapshot_id: null,
      official_intake_commit_id: null,
    };
    const recovery = {
      project_id: "project-1",
      batch_id: "batch-1",
      status: "materialized" as const,
      current_batch_id: "batch-1",
      current_source_artifact_id: "source-1",
      selected_source_artifact_id: "source-1",
      selected_structure_snapshot_id: "structure-1",
      selected_confirmation_decision_id: "decision-1",
      selected_usage_id: "usage-1",
      current_staging_usage_id: "usage-1",
      mapping_digest_sha256: "decision-digest",
      materialized_mapping_digest_sha256: "usage-digest",
      official_intake_closed: false,
    };
    expect(analysisContextReady(preliminary, recovery)).toBe(true);
    expect(analysisContextReady(preliminary, { ...recovery, current_staging_usage_id: null })).toBe(false);
    expect(analysisContextReady(preliminary, { ...recovery, status: "selected_unmaterialized" })).toBe(false);
    expect(analysisContextReady(preliminary, { ...recovery, selected_source_artifact_id: "old" })).toBe(false);
    expect(analysisContextReady(preliminary, { ...recovery, project_id: "another" })).toBe(false);
    expect(analysisContextReady(preliminary, { ...recovery, batch_id: "another" })).toBe(false);
    expect(analysisContextReady({ ...preliminary, official_intake_commit_id: "commit-1" }, recovery)).toBe(false);
  });
});
