import { useLayoutEffect, useRef, useState, type MouseEvent, type RefObject } from "react";

export function useAnalysisTableLayout(tableRef: RefObject<HTMLDivElement | null>) {
  const [maximized, setMaximized] = useState(false);
  const workspace = useRef<HTMLDivElement>(null);
  const focusBeforePointer = useRef<HTMLElement | null>(null);
  const returnTo = useRef<{
    x: number;
    y: number;
    left: number;
    top: number;
    focus: HTMLElement | null;
    control: HTMLButtonElement;
  } | null>(null);

  useLayoutEffect(() => {
    const saved = returnTo.current;
    if (!saved) return;
    if (maximized) {
      window.scrollTo({ left: 0, top: 0, behavior: "instant" });
      tableRef.current?.scrollTo({ left: saved.left, top: saved.top, behavior: "instant" });
      saved.control.focus({ preventScroll: true });
    } else {
      returnTo.current = null;
      (saved.focus?.isConnected && saved.focus.getClientRects().length ? saved.focus : saved.control).focus({ preventScroll: true });
      tableRef.current?.scrollTo({ left: saved.left, top: saved.top, behavior: "instant" });
      window.scrollTo({ left: saved.x, top: saved.y, behavior: "instant" });
    }
  }, [maximized, tableRef]);

  useLayoutEffect(() => {
    const element = workspace.current;
    if (!maximized || !element) return;
    const viewport = window.visualViewport;
    if (!viewport) return;
    const resize = () => {
      if (viewport.scale === 1) element.style.setProperty("--analysis-visual-height", viewport.height + "px");
      else element.style.removeProperty("--analysis-visual-height");
    };
    resize();
    viewport.addEventListener("resize", resize);
    return () => {
      viewport.removeEventListener("resize", resize);
      element.style.removeProperty("--analysis-visual-height");
    };
  }, [maximized]);

  const rememberFocus = () => {
    const active = document.activeElement;
    focusBeforePointer.current = active instanceof HTMLElement && active !== document.body ? active : null;
  };
  const toggle = (event: MouseEvent<HTMLButtonElement>) => {
    if (!maximized) {
      const active = event.detail ? focusBeforePointer.current : document.activeElement;
      returnTo.current = {
        x: window.scrollX, y: window.scrollY,
        left: tableRef.current?.scrollLeft ?? 0, top: tableRef.current?.scrollTop ?? 0,
        focus: active && active instanceof HTMLElement ? active : null, control: event.currentTarget,
      };
    }
    focusBeforePointer.current = null;
    setMaximized(!maximized);
  };

  return { maximized, workspace, rememberFocus, toggle };
}
