import React from "react";
import { act, create } from "react-test-renderer";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  getCurrentAccount: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
}));

vi.mock("../../api/auth", () => api);

import { SessionProvider, useSession } from "../SessionProvider";

const account = {
  id: "user-1",
  email: "operator@example.com",
  full_name: "Operator",
  organization_id: "org-1",
  organization_slug: "gia-lai",
  status: "active",
  roles: ["operator"],
  permissions: ["project:read", "project:update"],
};

function Probe() {
  const session = useSession();
  return React.createElement(
    "div",
    { "data-status": session.status, "data-org": session.account?.organization_slug },
    React.createElement("button", { id: "logout", onClick: () => void session.logout() }),
  );
}

describe("SessionProvider", () => {
  beforeEach(() => vi.clearAllMocks());

  it("restores account and organization context at boot", async () => {
    api.getCurrentAccount.mockResolvedValue(account);
    let root: any;

    await act(async () => {
      root = create(React.createElement(SessionProvider, null, React.createElement(Probe)));
    });

    const probe = root.root.findByType("div");
    expect(probe.props["data-status"]).toBe("authenticated");
    expect(probe.props["data-org"]).toBe("gia-lai");
  });

  it("clears local account context after logout", async () => {
    api.getCurrentAccount.mockResolvedValue(account);
    api.logout.mockRejectedValue(new Error("server already invalidated session"));
    let root: any;
    await act(async () => {
      root = create(React.createElement(SessionProvider, null, React.createElement(Probe)));
    });

    await act(async () => {
      root.root.findByProps({ id: "logout" }).props.onClick();
      await Promise.resolve();
    });

    expect(root.root.findByType("div").props["data-status"]).toBe("unauthenticated");
  });
});
