import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getCurrentAccount, login, logout } from "../auth";
import {
  getAdoptionOptions,
  getOneDriveConnection,
  listOperationalDocuments,
  provisionOperationalDocument,
  revalidateOperationalDocument,
} from "../m365";
import { listProjects } from "../projects";

function response(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  };
}

describe("operational API clients", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    vi.stubGlobal("document", { cookie: "XSRF-TOKEN=csrf-value" });
  });

  afterEach(() => vi.unstubAllGlobals());

  it("logs in with organization context and reads the server session", async () => {
    (fetch as any)
      .mockResolvedValueOnce(response({ status: "ok" }))
      .mockResolvedValueOnce(response({
        id: "user-1",
        email: "operator@example.com",
        full_name: "Operator",
        organization_id: "org-1",
        organization_slug: "gia-lai",
        status: "active",
        roles: ["operator"],
        permissions: ["project:read"],
      }));

    const account = await login({
      organization_slug: "gia-lai",
      email: "operator@example.com",
      password: "secret",
    });

    expect(account.organization_slug).toBe("gia-lai");
    expect((fetch as any).mock.calls[0][0]).toContain("/api/v1/auth/login");
    expect(JSON.parse((fetch as any).mock.calls[0][1].body)).toEqual({
      organization_slug: "gia-lai",
      email: "operator@example.com",
      password: "secret",
    });
    expect((fetch as any).mock.calls[0][1].credentials).toBe("include");
    expect((fetch as any).mock.calls[0][1].headers.get("X-CSRF-Token")).toBe("csrf-value");
    expect((fetch as any).mock.calls[1][0]).toContain("/api/v1/auth/me");
  });

  it("restores and logs out without browser token storage", async () => {
    (fetch as any)
      .mockResolvedValueOnce(response({ id: "u", organization_slug: "org" }))
      .mockResolvedValueOnce(response({}, 204));

    await getCurrentAccount();
    await logout();

    expect((fetch as any).mock.calls[0][0]).toContain("/api/v1/auth/me");
    expect((fetch as any).mock.calls[1][0]).toContain("/api/v1/auth/logout");
    expect((fetch as any).mock.calls[1][1].method).toBe("POST");
  });

  it("loads the tenant project list from the real endpoint", async () => {
    (fetch as any).mockResolvedValueOnce(response([{ id: "project-1", code: "HS-01" }]));

    const projects = await listProjects();

    expect(projects[0].id).toBe("project-1");
    expect((fetch as any).mock.calls[0][0]).toContain("/api/v1/projects?page=1&page_size=100");
  });

  it("uses read-only M365 options and passes the server snapshot unchanged", async () => {
    const snapshot = {
      contract_version: "valora-operational-adoption-v1",
      project_id: "project-1",
      project_row_version: 4,
    };
    (fetch as any)
      .mockResolvedValueOnce(response({ status: "active", connection_id: "connection-1" }))
      .mockResolvedValueOnce(response({ data_snapshot: snapshot, items: [], templates: [] }))
      .mockResolvedValueOnce(response({ document_id: "document-1" }));

    await getOneDriveConnection();
    const options = await getAdoptionOptions("project-1", "folder/one");
    await provisionOperationalDocument("project-1", {
      template_version_id: "template-version-1",
      connection_id: "connection-1",
      drive_item_id: "item-1",
      title: "Báo cáo",
      data_snapshot: options.data_snapshot,
      idempotency_key: "adoption-1",
    });

    expect((fetch as any).mock.calls[1][0]).toContain("parent_item_id=folder%2Fone");
    const body = JSON.parse((fetch as any).mock.calls[2][1].body);
    expect(body.data_snapshot).toEqual(snapshot);
    expect(body).not.toHaveProperty("classification");
  });

  it("revalidates using only expected lineage and then reads documents", async () => {
    const readiness = {
      document_id: "document-1",
      document_revision_id: "revision-1",
      document_revision: 2,
    } as any;
    (fetch as any)
      .mockResolvedValueOnce(response({ classification: "no_change" }))
      .mockResolvedValueOnce(response([{ document_id: "document-1" }]));

    await revalidateOperationalDocument("project-1", readiness);
    const documents = await listOperationalDocuments("project-1");

    const body = JSON.parse((fetch as any).mock.calls[0][1].body);
    expect(body.expected_document_revision_id).toBe("revision-1");
    expect(body.expected_document_revision).toBe(2);
    expect(body.trigger).toBe("explicit_refresh");
    expect(body).not.toHaveProperty("classification");
    expect(documents[0].document_id).toBe("document-1");
  });
});
