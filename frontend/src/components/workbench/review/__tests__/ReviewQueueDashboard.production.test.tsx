import React from "react";
import renderer, { act } from "react-test-renderer";
import { describe, expect, it } from "vitest";

import { ReviewQueueDashboard } from "../ReviewQueueDashboard";

describe("ReviewQueueDashboard production boundary", () => {
  it("starts empty and never renders demonstration records or a role switcher", () => {
    let root: renderer.ReactTestRenderer;
    act(() => {
      root = renderer.create(<ReviewQueueDashboard />);
    });
    const rendered = JSON.stringify(root!.toJSON());

    expect(rendered).toContain("Chưa có nhiệm vụ cần duyệt");
    expect(rendered).not.toContain("Mock Role Context");
    expect(rendered).not.toContain("Gia Lai LED Road Build");
    expect(rendered).not.toContain("Trạm biến áp Chư Prông");
  });
});
