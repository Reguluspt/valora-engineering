import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { commitAssetLineDraft } from "../projects";

describe("commitAssetLineDraft API", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    vi.stubGlobal("document", { cookie: "" });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("serializes version_token, confirm, and field_keys exactly in POST body", async () => {
    const mockResponse = {
      status: 200,
      ok: true,
      json: async () => ({
        project_id: "project-1",
        asset_line_id: "line-1",
        committed_fields: ["appraised_unit_price"],
        draft_status: "clean",
        has_saved_draft: false,
        has_unsaved_changes: false,
        is_stale: false,
        committed_at: "2026-07-12T10:00:00Z"
      })
    };
    (fetch as any).mockResolvedValueOnce(mockResponse);

    const result = await commitAssetLineDraft("project-1", "line-1", {
      field_keys: ["appraised_unit_price"],
      confirm: true,
      version_token: "7"
    });

    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, options] = (fetch as any).mock.calls[0];
    expect(url).toContain("/api/v1/projects/project-1/asset-lines/line-1/draft/commit");
    expect(options.method).toBe("POST");

    const body = JSON.parse(options.body);
    expect(body).toEqual({
      field_keys: ["appraised_unit_price"],
      confirm: true,
      version_token: "7"
    });

    expect(result.committed_fields).toEqual(["appraised_unit_price"]);
    expect(result.draft_status).toBe("clean");
  });

  it("serializes multiple field_keys with version_token", async () => {
    const mockResponse = {
      status: 200,
      ok: true,
      json: async () => ({
        project_id: "p2",
        asset_line_id: "l2",
        committed_fields: ["description", "appraised_unit_price"],
        draft_status: "clean",
        has_saved_draft: false,
        has_unsaved_changes: false,
        is_stale: false,
        committed_at: "2026-07-12T10:00:00Z"
      })
    };
    (fetch as any).mockResolvedValueOnce(mockResponse);

    await commitAssetLineDraft("p2", "l2", {
      field_keys: ["description", "appraised_unit_price"],
      confirm: true,
      version_token: "3"
    });

    const body = JSON.parse((fetch as any).mock.calls[0][1].body);
    expect(body.version_token).toBe("3");
    expect(body.field_keys).toEqual(["description", "appraised_unit_price"]);
    expect(body.confirm).toBe(true);
  });
});
