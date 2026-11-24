import { useEffect, useLayoutEffect, useRef, useState, type MouseEvent, type PointerEvent } from "react";

// These presentation breakpoints match the AppShell rules in index.css.
const PHONE_QUERY = "(max-width: 680px)";
const COMPACT_QUERY = "(max-width: 1100px)";
const EXTREME_QUERY = "(max-width: 240px)";
const PREFERENCE_KEY = "valora.ui.sidebar.compact";
const SWIPE_DIRECTION_THRESHOLD = 10;
const SWIPE_DISTANCE = 40;
const SWIPE_AXIS_RATIO = 1.5;

interface SidebarSwipe {
  pointerId: number;
  x: number;
  y: number;
  direction: 1 | -1;
  locked: boolean;
  returnTo: SidebarReturn | null;
}

interface SidebarReturn {
  focus: HTMLElement | null;
  scrollY: number;
  anchorY: number;
}

function matches(query: string): boolean {
  return typeof window !== "undefined"
    && typeof window.matchMedia === "function"
    && window.matchMedia(query).matches;
}

function readPreference(): boolean | null {
  try {
    const value = window.localStorage.getItem(PREFERENCE_KEY);
    return value === "true" ? true : value === "false" ? false : null;
  } catch {
    return null;
  }
}

export function useInlineSidebar(currentPath: string) {
  const desktopPreference = useRef(readPreference());
  const [phone, setPhone] = useState(() => matches(PHONE_QUERY));
  const [compact, setCompact] = useState(() => (
    matches(PHONE_QUERY) ? true : desktopPreference.current ?? matches(COMPACT_QUERY)
  ));
  const [extreme, setExtreme] = useState(() => matches(EXTREME_QUERY));
  const [extremeOpen, setExtremeOpen] = useState(false);
  const phoneOverlay = phone && !extreme && !compact;
  const sidebarRef = useRef<HTMLElement>(null);
  const openButtonRef = useRef<HTMLButtonElement>(null);
  const toggleButtonRef = useRef<HTMLButtonElement>(null);
  const workspaceRef = useRef<HTMLElement>(null);
  const wasExtremeOpen = useRef(false);
  const wasPhoneOverlay = useRef(false);
  const swipe = useRef<SidebarSwipe | null>(null);
  const completedSwipe = useRef<number | null>(null);
  const sidebarReturn = useRef<SidebarReturn | null>(null);

  const clearSwipe = () => {
    swipe.current = null;
    completedSwipe.current = null;
  };

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const phone = window.matchMedia(PHONE_QUERY);
    const narrow = window.matchMedia(COMPACT_QUERY);
    const extremeViewport = window.matchMedia(EXTREME_QUERY);
    let wasPhone = phone.matches;

    const handleViewportChange = () => {
      setPhone(phone.matches);
      if (phone.matches) {
        setCompact(true);
      } else if (wasPhone || desktopPreference.current === null) {
        setCompact(desktopPreference.current ?? narrow.matches);
      }
      wasPhone = phone.matches;
    };

    const handleExtremeChange = () => {
      clearSwipe();
      sidebarReturn.current = null;
      setExtremeOpen(false);
      setExtreme(extremeViewport.matches);
    };

    phone.addEventListener("change", handleViewportChange);
    narrow.addEventListener("change", handleViewportChange);
    extremeViewport.addEventListener("change", handleExtremeChange);
    window.addEventListener?.("resize", clearSwipe);
    return () => {
      phone.removeEventListener("change", handleViewportChange);
      narrow.removeEventListener("change", handleViewportChange);
      extremeViewport.removeEventListener("change", handleExtremeChange);
      window.removeEventListener?.("resize", clearSwipe);
    };
  }, []);

  useLayoutEffect(() => {
    clearSwipe();
    sidebarReturn.current = null;
    setExtremeOpen(false);
    if (matches(PHONE_QUERY) && !matches(EXTREME_QUERY)) setCompact(true);
  }, [currentPath]);

  useLayoutEffect(() => {
    if (!extreme && (phoneOverlay || wasPhoneOverlay.current)) {
      toggleButtonRef.current?.focus({ preventScroll: true });
    }
    wasPhoneOverlay.current = phoneOverlay;
  }, [extreme, phoneOverlay]);

  useLayoutEffect(() => {
    const wasOpen = wasExtremeOpen.current;
    wasExtremeOpen.current = extremeOpen;
    if (extremeOpen) {
      const toggle = toggleButtonRef.current;
      if (sidebarReturn.current) {
        toggle?.focus({ preventScroll: true });
        toggle?.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "instant" });
      } else {
        toggle?.focus();
      }
      return;
    }
    if (!extreme || !(wasOpen || sidebarRef.current?.contains(document.activeElement))) return;

    const previous = sidebarReturn.current;
    if (!previous) {
      openButtonRef.current?.focus({ preventScroll: true });
      return;
    }

    let cancelled = false;
    const restore = () => {
      if (cancelled || sidebarReturn.current !== previous) return;
      sidebarReturn.current = null;
      const workspace = workspaceRef.current;
      if (previous.focus && workspace?.contains(previous.focus)) previous.focus.focus({ preventScroll: true });
      if (!previous.focus || document.activeElement !== previous.focus) workspace?.focus({ preventScroll: true });
      const anchorShift = workspace ? workspace.getBoundingClientRect().top + window.scrollY - previous.anchorY : 0;
      window.scrollTo({ top: previous.scrollY + anchorShift, behavior: "instant" });
    };

    // The discrete display transition keeps the sidebar in the grid until it finishes.
    const animations = sidebarRef.current?.getAnimations?.() ?? [];
    if (animations.length) void Promise.allSettled(animations.map(animation => animation.finished)).then(restore);
    else restore();
    return () => { cancelled = true; };
  }, [extreme, extremeOpen]);

  const toggleSidebar = () => {
    if (extreme) {
      setExtremeOpen(false);
      return;
    }
    const next = !compact;
    setCompact(next);
    if (!matches(PHONE_QUERY)) {
      desktopPreference.current = next;
      try {
        window.localStorage.setItem(PREFERENCE_KEY, String(next));
      } catch {
        // Navigation remains usable when a browser does not allow preferences.
      }
    }
  };

  const collapseSidebar = () => {
    if (extreme) setExtremeOpen(false);
    else setCompact(true);
  };

  const collapseOnPhone = () => {
    if (matches(PHONE_QUERY)) collapseSidebar();
  };

  const swipeHandlers = {
    onPointerDown: (event: PointerEvent<HTMLElement>) => {
      if (event.pointerType !== "touch") return;
      clearSwipe();
      if (!event.isPrimary) return;
      const workspace = workspaceRef.current;
      const active = document.activeElement;
      const returnTo = !extremeOpen && workspace ? {
        focus: active instanceof HTMLElement && workspace.contains(active) ? active : null,
        scrollY: window.scrollY,
        anchorY: workspace.getBoundingClientRect().top + window.scrollY,
      } : null;
      swipe.current = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, direction: extremeOpen ? -1 : 1, locked: false, returnTo };
    },
    onPointerMove: (event: PointerEvent<HTMLElement>) => {
      const start = swipe.current;
      if (!start || start.pointerId !== event.pointerId || start.locked) return;
      const dx = (event.clientX - start.x) * start.direction;
      const dy = Math.abs(event.clientY - start.y);
      if (Math.max(Math.abs(dx), dy) < SWIPE_DIRECTION_THRESHOLD) return;
      if (dx >= dy * SWIPE_AXIS_RATIO && dx > 0) start.locked = true;
      else swipe.current = null;
    },
    onPointerUp: (event: PointerEvent<HTMLElement>) => {
      const start = swipe.current;
      if (!start || start.pointerId !== event.pointerId) return;
      swipe.current = null;
      if (start.locked && (event.clientX - start.x) * start.direction >= SWIPE_DISTANCE) {
        completedSwipe.current = event.pointerId;
        if (start.direction === 1) sidebarReturn.current = start.returnTo;
        setExtremeOpen(start.direction === 1);
      }
    },
    onPointerCancel: (event: PointerEvent<HTMLElement>) => {
      if (swipe.current?.pointerId === event.pointerId) clearSwipe();
    },
    onClickCapture: (event: MouseEvent<HTMLElement>) => {
      const pointer = event.nativeEvent as globalThis.PointerEvent;
      if (pointer.pointerType === "touch" && pointer.pointerId === completedSwipe.current) {
        event.preventDefault();
        event.stopPropagation();
      }
    },
  };

  return {
    compact, extreme, extremeOpen, phoneOverlay, toggleSidebar, collapseOnPhone, collapseSidebar,
    openExtremeSidebar: () => {
      sidebarReturn.current = null;
      setExtremeOpen(true);
    },
    discardSidebarReturn: (path: string) => {
      if (path !== currentPath) sidebarReturn.current = null;
    },
    sidebarRef, openButtonRef, toggleButtonRef, workspaceRef, swipeHandlers,
  };
}
