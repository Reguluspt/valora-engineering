import { useEffect, useRef, useState } from "react";

// These presentation breakpoints match the AppShell rules in index.css.
const PHONE_QUERY = "(max-width: 680px)";
const COMPACT_QUERY = "(max-width: 1100px)";
const PREFERENCE_KEY = "valora.ui.sidebar.compact";

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
  const [compact, setCompact] = useState(() => (
    matches(PHONE_QUERY) ? true : desktopPreference.current ?? matches(COMPACT_QUERY)
  ));

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const phone = window.matchMedia(PHONE_QUERY);
    const narrow = window.matchMedia(COMPACT_QUERY);
    let wasPhone = phone.matches;

    const handleViewportChange = () => {
      if (phone.matches) {
        setCompact(true);
      } else if (wasPhone || desktopPreference.current === null) {
        setCompact(desktopPreference.current ?? narrow.matches);
      }
      wasPhone = phone.matches;
    };

    phone.addEventListener("change", handleViewportChange);
    narrow.addEventListener("change", handleViewportChange);
    return () => {
      phone.removeEventListener("change", handleViewportChange);
      narrow.removeEventListener("change", handleViewportChange);
    };
  }, []);

  useEffect(() => {
    if (matches(PHONE_QUERY)) setCompact(true);
  }, [currentPath]);

  const toggleSidebar = () => {
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

  const collapseOnPhone = () => {
    if (matches(PHONE_QUERY)) setCompact(true);
  };

  return { compact, toggleSidebar, collapseOnPhone };
}
