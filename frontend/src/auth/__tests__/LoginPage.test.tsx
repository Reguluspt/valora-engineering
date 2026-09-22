import React from "react";
import { act, create } from "react-test-renderer";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LoginPage } from "../LoginPage";

const session = vi.hoisted(() => ({
  error: null as string | null,
  login: vi.fn(),
}));

vi.mock("../SessionProvider", () => ({
  useSession: () => session,
}));

describe("LoginPage", () => {
  beforeEach(() => {
    session.error = null;
    session.login.mockReset();
    session.login.mockResolvedValue(undefined);
  });

  it("preserves the login payload and session-provider flow", async () => {
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(<LoginPage />);
    });

    act(() => {
      root!.root.findByProps({ name: "organization_slug" }).props.onChange({ target: { value: " gia-lai " } });
      root!.root.findByProps({ name: "email" }).props.onChange({ target: { value: " operator@example.com " } });
      root!.root.findByProps({ name: "password" }).props.onChange({ target: { value: "secret" } });
    });
    await act(async () => {
      await root!.root.findByType("form").props.onSubmit({ preventDefault: vi.fn() });
    });

    expect(session.login).toHaveBeenCalledWith({
      organization_slug: "gia-lai",
      email: "operator@example.com",
      password: "secret",
    });
  });

  it("uses the shared Fluent light field and button primitives", () => {
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(<LoginPage />);
    });

    expect(root!.root.findAllByType("input").every((input) => input.props.className === "valora-field")).toBe(true);
    expect(root!.root.findByType("button").props.className).toContain("valora-button--primary");
    expect(JSON.stringify(root!.toJSON())).toContain("Không gian làm việc thẩm định giá");
    expect(JSON.stringify(root!.toJSON())).not.toContain("OneDrive Personal");
  });

  it("associates a sanitized session error with the form", () => {
    session.error = "Tài khoản hoặc mật khẩu chưa đúng.";
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(<LoginPage />);
    });

    expect(root!.root.findByType("form").props["aria-describedby"]).toBe("login-error");
    expect(root!.root.findByProps({ id: "login-error" }).props.role).toBe("alert");
  });
});
