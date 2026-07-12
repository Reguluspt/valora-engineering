import React from "react";
import { create, act } from "react-test-renderer";

export function renderHook<T>(useHook: () => T): {
  result: { current: T };
  rerender: () => void;
  unmount: () => void;
} {
  const result = { current: null as unknown as T };
  let root: any = null;

  function TestComponent() {
    result.current = useHook();
    return null;
  }

  act(() => {
    root = create(React.createElement(TestComponent));
  });

  return {
    result,
    rerender: () => {
      act(() => {
        root!.update(React.createElement(TestComponent));
      });
    },
    unmount: () => {
      act(() => {
        root!.unmount();
      });
    },
  };
}
