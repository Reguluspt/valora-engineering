import { useCallback, useEffect, useRef, useState, type PointerEvent, type RefObject } from "react";

const INTERACTIVE = "input, textarea, select, button, a[href], summary, [contenteditable]:not([contenteditable=false]), [role=button], [role=checkbox], [role=link], [role=separator], [role=switch], [role=textbox]";

function isPanSurface(target: EventTarget | null): target is Element {
  return target instanceof Element && !target.closest(INTERACTIVE);
}

export function useTableMousePan(tableRef: RefObject<HTMLDivElement | null>, hasRows: boolean) {
  const hoverTarget = useRef<Element | null>(null);
  const armed = useRef(false);
  const drag = useRef<{ table: HTMLDivElement; id: number; x: number; y: number; left: number; top: number } | null>(null);
  const [mode, setMode] = useState<"ready" | "dragging">();

  const finish = useCallback((clearSpace: boolean) => {
    if (clearSpace) armed.current = false;
    const active = drag.current;
    drag.current = null;
    if (active?.table.hasPointerCapture(active.id)) active.table.releasePointerCapture(active.id);
    setMode(armed.current && hoverTarget.current ? "ready" : undefined);
  }, []);

  useEffect(() => {
    if (!hasRows || typeof window === "undefined") return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        finish(true);
        return;
      }
      if (event.code !== "Space" || event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
      const table = tableRef.current;
      const hovered = hoverTarget.current;
      if (drag.current) {
        event.preventDefault();
        return;
      }
      if (!table || !hovered || !table.contains(hovered) || !isPanSurface(event.target)) return;
      if (event.target !== document.body && event.target !== document.documentElement && !table.contains(event.target)) return;
      if (!armed.current && event.repeat) return;
      event.preventDefault();
      armed.current = true;
      setMode("ready");
    };
    const onKeyUp = (event: KeyboardEvent) => { if (event.code === "Space") finish(true); };
    const onBlur = () => {
      hoverTarget.current = null;
      finish(true);
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    window.addEventListener("blur", onBlur);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      window.removeEventListener("blur", onBlur);
      onBlur();
    };
  }, [finish, hasRows, tableRef]);

  const updateHover = (event: PointerEvent<HTMLDivElement>) => {
    if (event.pointerType !== "mouse" || drag.current) return;
    hoverTarget.current = isPanSurface(event.target) ? event.target : null;
    if (armed.current) setMode(hoverTarget.current ? "ready" : undefined);
  };

  return {
    "data-table-pan": mode,
    onPointerOver: updateHover,
    onPointerLeave(event: PointerEvent<HTMLDivElement>) {
      if (event.pointerType !== "mouse") return;
      hoverTarget.current = null;
      if (!drag.current && armed.current) setMode(undefined);
    },
    onPointerDown(event: PointerEvent<HTMLDivElement>) {
      if (!armed.current || drag.current || event.defaultPrevented || event.pointerType !== "mouse" || event.button !== 0 || !isPanSurface(event.target)) return;
      const table = event.currentTarget;
      drag.current = { table, id: event.pointerId, x: event.clientX, y: event.clientY, left: table.scrollLeft, top: table.scrollTop };
      table.setPointerCapture(event.pointerId);
      event.preventDefault();
      setMode("dragging");
    },
    onPointerMove(event: PointerEvent<HTMLDivElement>) {
      const active = drag.current;
      if (!active) {
        updateHover(event);
        return;
      }
      if (active.id !== event.pointerId) return;
      active.table.scrollLeft = active.left + active.x - event.clientX;
      active.table.scrollTop = active.top + active.y - event.clientY;
    },
    onPointerUp(event: PointerEvent<HTMLDivElement>) { if (drag.current?.id === event.pointerId) finish(false); },
    onPointerCancel(event: PointerEvent<HTMLDivElement>) { if (drag.current?.id === event.pointerId) finish(true); },
    onLostPointerCapture(event: PointerEvent<HTMLDivElement>) { if (drag.current?.id === event.pointerId) finish(true); },
  };
}
