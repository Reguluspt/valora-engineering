import { describe, expect, it } from "vitest";
import { allValid, coherentPage, importContext, promotionProven, validApplyResponse } from "../postIntakeImportModel";
import { applied, batch, id, projection, rows, target } from "./fixtures";

describe("post-Intake authoritative selection", () => {
  it.each(["validate", "apply"] as const)("accepts the exact %s pair and token", kind => {
    expect(importContext(projection(kind), id(1))).toEqual(target(kind));
  });
  it.each(["wrong-project", "wrong-token", "wrong-result", "wrong-intake", "wrong-batch", "wrong-usage", "wrong-kind", "wrong-key", "unavailable", "blocked", "stale", "wrong-contract", "not-confirmed", "missing-context"])("rejects %s", fault => {
    const p = projection("apply"); const c = p.next_action!.context as any;
    if (fault === "wrong-project") c.project_id = id(9);
    if (fault === "wrong-token") c.case_version = "f".repeat(64);
    if (fault === "wrong-result") c.result_id = id(9);
    if (fault === "wrong-intake") c.official_intake_commit_id = id(9);
    if (fault === "wrong-batch") c.batch_id = id(9);
    if (fault === "wrong-usage") c.staging_usage_id = null;
    if (fault === "wrong-kind") c.kind = "line";
    if (fault === "wrong-key") p.next_action!.semantic_route_key = "other";
    if (fault === "unavailable") p.capabilities[0].available = false;
    if (fault === "blocked") p.stages.find(s => s.stage === "ASSET_REVIEW")!.result = "BLOCKED";
    if (fault === "stale") p.stale = [{}];
    if (fault === "wrong-contract") c.contract_version = "s12-pr-004-v1";
    if (fault === "not-confirmed") c.confirmation_required = "true";
    if (fault === "missing-context") p.next_action!.context = null;
    expect(importContext(p, id(1))).toBeNull();
  });
  it("checks page envelopes, duplicate locators and actual totals", () => {
    expect(coherentPage(batch(), rows(), id(1), id(2), 0)).toBe(true);
    expect(coherentPage(batch(), { ...rows(), total: 2 }, id(1), id(2), 0)).toBe(false);
    expect(coherentPage(batch(), { ...rows(), project_id: id(9) }, id(1), id(2), 0)).toBe(false);
    const duplicate = rows(); duplicate.items[1] = duplicate.items[0];
    expect(coherentPage(batch(), duplicate, id(1), id(2), 0)).toBe(false);
  });
  it("does not interpret ready_for_review or a valid visible page as full-set readiness", () => {
    expect(allValid(batch(true), rows(true))).toBe(true);
    expect(allValid({ ...batch(true), valid_rows: 2, invalid_rows: 1 }, rows(true))).toBe(false);
    expect(allValid(batch(true), rows(false))).toBe(false);
    expect(allValid({ ...batch(true), warning_rows: 1 }, rows(true))).toBe(false);
  });
  it("requires correspondence and exact scoped server bridge, without deriving COMPLETE", () => {
    const result = { project_id: id(1), import_batch_id: id(2), status: "applied", created_count: 3,
      created_lines: rows().items.map((row, i) => ({ line_id: id(i + 20), staging_row_id: row.id, source_row_number: row.source_row_number })) };
    expect(validApplyResponse(result, batch(true), rows(true))).toBe(true);
    expect(validApplyResponse({ ...result, import_batch_id: id(9) }, batch(true), rows(true))).toBe(false);
    expect(validApplyResponse({ ...result, created_lines: [result.created_lines[0], result.created_lines[0], result.created_lines[2]] }, batch(true), rows(true))).toBe(false);
    const b = { ...batch(true), status: "applied" as const };
    expect(promotionProven(applied(), b, target("apply"))).toBe(true);
    expect(promotionProven(projection("apply"), b, target("apply"))).toBe(false);
    expect(promotionProven(applied(), { ...b, id: id(9) }, target("apply"))).toBe(false);
  });
});
