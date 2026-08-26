import React from "react";
import renderer, { act } from "react-test-renderer";
import { describe, expect, it } from "vitest";

import { DemoReviewQueuePage } from "../DemoReviewQueuePage";

describe("DemoReviewQueuePage", () => {
  it("labels every demonstration-data surface explicitly", () => {
    let root: renderer.ReactTestRenderer;
    act(() => {
      root = renderer.create(<DemoReviewQueuePage />);
    });
    const rendered = JSON.stringify(root!.toJSON());

    expect(rendered).toContain("DỮ LIỆU MINH HỌA — KHÔNG PHẢI HỒ SƠ THẬT");
    expect(rendered).toContain("MINH-HOA-01");
    expect(rendered).toContain("Vai trò minh họa");
  });
});
