import React, { useState } from "react";
import { act, create } from "react-test-renderer";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AnalysisNumberInput } from "../AnalysisNumberInput";
import { AnalysisBasisInput } from "../AnalysisBasisInput";
import { analysisNumberCaret, formatAnalysisNumber, parseAnalysisNumberInput } from "../analysisPresentation";
import { buildAnalysisManifest, type AnalysisDraft } from "../analysisReviewModel";

const mounted: ReturnType<typeof create>[] = [];
afterEach(() => { for (const renderer of mounted.splice(0)) act(() => renderer.unmount()); });

function mount(value = "92400000") {
  const changed = vi.fn();
  const caret = vi.fn();
  function Editor() {
    const [raw, setRaw] = useState(value);
    return <><AnalysisNumberInput value={raw} onChange={(next) => { changed(next); setRaw(next); }} /><output>{raw}</output></>;
  }
  let renderer: ReturnType<typeof create>;
  act(() => { renderer = create(<Editor />, { createNodeMock: node => node.type === "input" ? { setSelectionRange: caret } : null }); });
  mounted.push(renderer!);
  return { renderer: renderer!, input: () => renderer!.root.findByType("input"), changed, caret };
}

describe("Vietnamese analysis number entry", () => {
  it.each([
    ["92400000", "92400000"], ["92.400.000", "92400000"], [" 92.400.000\t\r\n", "92400000"],
    ["", ""], ["0", "0"], ["000", "0"], ["00012", "12"], ["5,25", "5.25"], ["5,", "5."],
    ["1.234,567890123456", "1234.567890123456"], ["9007199254740993", "9007199254740993"],
  ])("parses %j to canonical %j", (display, raw) => expect(parseAnalysisNumberInput(display)).toBe(raw));

  it.each(["12.34", "1..000", "-5", "+5", "1e3", "NaN", "Infinity", "１２３", "١٢٣", "1\u200b000", "1 000", "5.25", "1\t2", "1\n2", "1,2,3", "9".repeat(310)])(
    "rejects malformed or ambiguous pasted value %j", display => expect(parseAnalysisNumberInput(display)).toBeNull());

  it.each([
    ["92400000", "92.400.000"], ["0", "0"], ["", ""], ["5.25", "5,25"], ["5.", "5,"],
    ["9007199254740993", "9.007.199.254.740.993"], ["1234.567890123456", "1.234,567890123456"],
  ])("displays canonical %j without precision loss", (raw, display) => expect(formatAnalysisNumber(raw, "")).toBe(display));

  it("keeps grouped digits on focus and blur without changing the draft", () => {
    const { input, changed } = mount();
    act(() => input().props.onFocus({}));
    expect(input().props.value).toBe("92.400.000");
    act(() => input().props.onBlur({}));
    expect(input().props.value).toBe("92.400.000");
    expect(changed).not.toHaveBeenCalled();
  });

  it("maps a middle insertion and selection independently of grouping", () => {
    const { input, changed, caret } = mount();
    act(() => input().props.onChange({ target: { value: "92.4900.000", selectionStart: 5, selectionEnd: 5 }, nativeEvent: { inputType: "insertText", data: "9" } }));
    expect(changed).toHaveBeenLastCalledWith("924900000");
    expect(input().props.value).toBe("924.900.000");
    expect(caret).toHaveBeenLastCalledWith(5, 5, "none");
    expect(analysisNumberCaret("92.400.000", 4, "924.000.000")).toBe(3);
  });

  it.each([["Backspace", 3, "9400000", "9.400.000", 1], ["Delete", 2, "9200000", "9.200.000", 3]])(
    "%s at a grouping separator removes the adjacent digit", (key, position, raw, display, nextCaret) => {
      const { input, changed, caret } = mount();
      const preventDefault = vi.fn();
      act(() => input().props.onKeyDown({ key, target: { selectionStart: position, selectionEnd: position }, preventDefault }));
      expect(preventDefault).toHaveBeenCalledOnce();
      expect(changed).toHaveBeenLastCalledWith(raw);
      expect(input().props.value).toBe(display);
      expect(caret).toHaveBeenLastCalledWith(nextCaret, nextCaret, "none");
    });

  it("pastes a grouped Excel cell into a raw draft and rejects a malformed replacement", () => {
    const { input, changed, renderer } = mount();
    const paste = (text: string) => act(() => input().props.onPaste({ target: { selectionStart: 0, selectionEnd: 10 }, preventDefault: vi.fn(), clipboardData: { getData: () => text } }));
    paste("88.000.000\r\n");
    expect(changed).toHaveBeenLastCalledWith("88000000");
    expect(input().props.value).toBe("88.000.000");
    paste("12.34");
    expect(changed).toHaveBeenCalledTimes(1);
    expect(input().props.value).toBe("88.000.000");
    expect(input().props["aria-invalid"]).toBe(true);
    expect(renderer.root.findByProps({ role: "alert" }).children.join("")).toContain("Chưa áp dụng");
  });

  it("holds IME composition outside the draft and rejects Unicode without losing valid digits", () => {
    const { input, changed } = mount();
    act(() => input().props.onCompositionStart({}));
    act(() => input().props.onChange({ target: { value: "１２３" } }));
    expect(changed).not.toHaveBeenCalled();
    expect(input().props.value).toBe("１２３");
    act(() => input().props.onCompositionEnd({ target: { value: "１２３", selectionStart: 3, selectionEnd: 3 } }));
    expect(changed).not.toHaveBeenCalled();
    expect(input().props.value).toBe("92.400.000");
  });

  it("passes canonical values into the unchanged human-confirmed price manifest", () => {
    const draft: AnalysisDraft = { source_row_number: 1, quantity: "2", identity: "Máy", accepted_price_basis: "Báo giá",
      confirmed_reference_price: parseAnalysisNumberInput("88.000.000")!, proposed_unit_price: parseAnalysisNumberInput("92.400.000")!,
      transport_percentage: parseAnalysisNumberInput("5,25")!, human_line_confirmed: true, has_unresolved_blocking_line: false };
    expect(buildAnalysisManifest([draft])).toEqual([{ ...draft, quantity: 2, confirmed_reference_price: 88000000, proposed_unit_price: 92400000, transport_percentage: 5.25 }]);
    expect(buildAnalysisManifest([{ ...draft, transport_percentage: "100.01" }])).toBeNull();
  });
});

describe("analysis basis limit feedback", () => {
  it("rejects a long paste in full and keeps the valid draft and accessible counter", () => {
    const changed = vi.fn();
    let renderer: ReturnType<typeof create>;
    act(() => { renderer = create(<AnalysisBasisInput value="Cơ sở hợp lệ" onChange={changed} />); });
    mounted.push(renderer!);
    const preventDefault = vi.fn();
    act(() => renderer!.root.findByType("textarea").props.onPaste({ target: { selectionStart: 12, selectionEnd: 12 }, preventDefault, clipboardData: { getData: () => "d".repeat(65) } }));
    expect(preventDefault).toHaveBeenCalledOnce();
    expect(changed).not.toHaveBeenCalled();
    expect(renderer!.root.findByType("textarea").props.value).toBe("Cơ sở hợp lệ");
    expect(JSON.stringify(renderer!.toJSON())).toContain("Nội dung chưa được áp dụng");
    expect(renderer!.root.findByType("textarea").props["aria-describedby"]).toBeTruthy();
  });
});
