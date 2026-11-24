import React, { type RefObject } from "react";
import { act, create, type ReactTestRenderer } from "react-test-renderer";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useTableMousePan } from "../useTableMousePan";

class Surface {
  constructor(private interactive = false) {}
  closest() { return this.interactive ? this : null; }
}

let root: ReactTestRenderer;
let listeners: Map<string, (event: unknown) => void>;
let body: Surface;
let cell: Surface;

beforeEach(() => {
  listeners = new Map();
  body = new Surface();
  cell = new Surface();
  vi.stubGlobal("Element", Surface);
  vi.stubGlobal("document", { body });
  vi.stubGlobal("window", {
    addEventListener: (name: string, listener: (event: unknown) => void) => listeners.set(name, listener),
    removeEventListener: (name: string) => listeners.delete(name),
  });
});

afterEach(() => {
  if (listeners.size) act(() => root.unmount());
  vi.unstubAllGlobals();
});

function mountPan() {
  const table = {
    contains: (target: Surface) => target === cell,
    scrollLeft: 100, scrollTop: 200,
    setPointerCapture: vi.fn(), hasPointerCapture: () => true, releasePointerCapture: vi.fn(),
  };
  const ref = { current: table } as unknown as RefObject<HTMLDivElement>;
  function Harness() { return <div {...useTableMousePan(ref, true)} />; }
  act(() => { root = create(<Harness />); });
  const props = () => root.root.findByType("div").props;
  const pointer = { pointerType: "mouse", button: 0, pointerId: 2, currentTarget: table, target: cell, clientX: 100, clientY: 100, preventDefault: vi.fn() };
  const key = { code: "Space", key: " ", target: body, preventDefault: vi.fn() };
  return { props, table, pointer, key };
}

describe("table mouse pan", () => {
  it.each(["pointerup", "pointercancel", "lost capture", "Space up", "Escape", "blur", "unmount"])(
    "moves both axes and releases capture on %s", (end) => {
      const { props, table, pointer, key } = mountPan();
      act(() => props().onPointerOver(pointer));
      act(() => listeners.get("keydown")!(key));
      expect(key.preventDefault).toHaveBeenCalledOnce();
      expect(props()["data-table-pan"]).toBe("ready");
      act(() => props().onPointerDown(pointer));
      expect(table.setPointerCapture).toHaveBeenCalledWith(2);
      expect(props()["data-table-pan"]).toBe("dragging");
      act(() => props().onPointerMove({ ...pointer, clientX: 45, clientY: 170 }));
      expect([table.scrollLeft, table.scrollTop]).toEqual([155, 130]);
      act(() => {
        switch (end) {
          case "pointerup": props().onPointerUp(pointer); break;
          case "pointercancel": props().onPointerCancel(pointer); break;
          case "lost capture": props().onLostPointerCapture(pointer); break;
          case "Space up": listeners.get("keyup")!(key); break;
          case "Escape": listeners.get("keydown")!({ key: "Escape" }); break;
          case "blur": listeners.get("blur")!(null); break;
          case "unmount": root.unmount(); break;
        }
      });
      expect(table.releasePointerCapture).toHaveBeenCalledWith(2);
      if (end === "unmount") {
        expect(listeners.size).toBe(0);
      } else {
        expect(props()["data-table-pan"]).toBe(end === "pointerup" ? "ready" : undefined);
        act(() => props().onPointerMove({ ...pointer, clientX: 5, clientY: 5 }));
        expect([table.scrollLeft, table.scrollTop]).toEqual([155, 130]);
      }
    },
  );

  it("leaves Space, pointer presses and native touch alone on other controls", () => {
    const { props, table, pointer, key } = mountPan();
    const control = new Surface(true);
    act(() => {
      listeners.get("keydown")!(key);
      props().onPointerOver({ ...pointer, target: control });
      listeners.get("keydown")!(key);
      props().onPointerOver(pointer);
      listeners.get("keydown")!({ ...key, target: control });
    });
    expect(key.preventDefault).not.toHaveBeenCalled();
    act(() => {
      listeners.get("keydown")!(key);
      props().onPointerDown({ ...pointer, target: control });
      props().onPointerDown({ ...pointer, pointerType: "touch" });
      props().onPointerDown({ ...pointer, button: 2 });
    });
    expect(table.setPointerCapture).not.toHaveBeenCalled();
  });
});
