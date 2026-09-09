import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { confirmNccSelection, fetchNccSelections } from "../nccSelection";

describe("nccSelection API", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    vi.stubGlobal("document", { cookie: "" });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetchNccSelections GETs the project aggregate", async () => {
    const mockResponse = {
      status: 200,
      ok: true,
      json: async () => ({
        project_id: "project-1",
        kpis: { total_asset_lines: 1, selected: 0, unselected: 1, stale: 0, eligible_quotes: 1 },
        asset_lines: [],
      }),
    };
    (fetch as any).mockResolvedValueOnce(mockResponse);

    const result = await fetchNccSelections("project-1");
    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, options] = (fetch as any).mock.calls[0];
    expect(url).toContain("/api/v1/projects/project-1/ncc-selections");
    expect(options.method).toBeUndefined();
    expect(result.kpis.eligible_quotes).toBe(1);
  });

  it("confirmNccSelection POSTs the exact confirmation body", async () => {
    const mockResponse = {
      status: 200,
      ok: true,
      json: async () => ({
        selection_id: "sel-1",
        selection_revision: 1,
        quote_line_id: "quote-1",
        quote_batch_id: "batch-1",
        quote_batch_revision_number: 1,
        supplier_id: "supplier-1",
        supplier_name: "ABB Vietnam",
        quoted_unit_price: 850,
        currency: "USD",
        quantity: 1,
        unit_of_measure: "set",
        quote_date: null,
        evidence: { evidence_file_id: "ev-1", filename: "quote.pdf", status: "active" },
        current_unit_price: 1000,
        current_unit_price_currency_id: null,
        difference_amount: -150,
        difference_percent: -15,
        warnings: ["NCC_BELOW_CURRENT_PRICE"],
        acknowledged_warning_codes: [],
        confirmed_by_user_id: "user-1",
        confirmed_at: "2026-09-05T00:00:00Z",
        stale: false,
      }),
    };
    (fetch as any).mockResolvedValueOnce(mockResponse);

    const result = await confirmNccSelection("project-1", "line-1", {
      quote_line_id: "quote-1",
      expected_selection_revision: 0,
      acknowledged_warning_codes: ["NCC_BELOW_CURRENT_PRICE"],
      idempotency_key: "key-1",
      confirmed: true,
    });

    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, options] = (fetch as any).mock.calls[0];
    expect(url).toContain(
      "/api/v1/projects/project-1/asset-lines/line-1/ncc-selection"
    );
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({
      quote_line_id: "quote-1",
      expected_selection_revision: 0,
      acknowledged_warning_codes: ["NCC_BELOW_CURRENT_PRICE"],
      idempotency_key: "key-1",
      confirmed: true,
    });
    expect(result.selection_revision).toBe(1);
    expect(result.stale).toBe(false);
  });
});
