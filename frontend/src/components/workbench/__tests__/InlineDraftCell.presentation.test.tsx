import { act, create } from "react-test-renderer";
import { describe, expect, it, vi } from "vitest";
import { InlineDraftCell } from "../drafts/InlineDraftCell";

describe("InlineDraftCell presentation lock", () => {
  it("keeps Enter, Escape and blur behavior with a visible draft label", () => {
    const onSave = vi.fn();
    let root: ReturnType<typeof create>;
    act(() => { root = create(<InlineDraftCell value="100" isDirty onSave={onSave} />); });
    expect(JSON.stringify(root!.toJSON())).toContain("Nháp chưa áp dụng");
    const stopPropagation = vi.fn();
    act(() => root!.root.findByType("button").props.onClick({ stopPropagation }));
    expect(stopPropagation).toHaveBeenCalledOnce();
    let input = root!.root.findByType("input");
    act(() => input.props.onChange({ target: { value: "120" } }));
    act(() => input.props.onKeyDown({ key: "Escape" }));
    expect(onSave).not.toHaveBeenCalled();
    expect(JSON.stringify(root!.toJSON())).toContain("100");

    act(() => root!.root.findByType("button").props.onClick({ stopPropagation }));
    input = root!.root.findByType("input");
    act(() => input.props.onChange({ target: { value: "130" } }));
    act(() => input.props.onKeyDown({ key: "Enter" }));
    expect(onSave).toHaveBeenCalledExactlyOnceWith("130");

    act(() => root!.root.findByType("button").props.onClick({ stopPropagation }));
    input = root!.root.findByType("input");
    act(() => input.props.onBlur());
    expect(onSave).toHaveBeenCalledTimes(2);
  });
});
