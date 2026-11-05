import React from "react";

export type ShellIconName = "requests" | "workbench" | "overview" | "documents"
  | "suppliers" | "upload" | "analysis" | "results" | "sidebar" | "logout";

const paths: Record<ShellIconName, React.ReactNode> = {
  requests: <><rect x="5" y="3" width="14" height="18" rx="3" /><path d="M9 8h6M9 12h6M9 16h4" /></>,
  workbench: <><rect x="3" y="4" width="18" height="16" rx="3" /><path d="M3 10h18M9 10v10M15 10v10" /></>,
  overview: <><rect x="3" y="3" width="7" height="7" rx="2" /><rect x="14" y="3" width="7" height="7" rx="2" /><rect x="3" y="14" width="7" height="7" rx="2" /><rect x="14" y="14" width="7" height="7" rx="2" /></>,
  documents: <><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6M8 13h8M8 17h5" /></>,
  suppliers: <><path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-5h6v5M9 9h1m4 0h1M9 12h1m4 0h1" /></>,
  upload: <><path d="M12 16V3m-4 4 4-4 4 4M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4" /></>,
  analysis: <><rect x="3" y="4" width="18" height="16" rx="3" /><path d="M3 9h18M8 9v11M12 13h5m-5 4h3" /></>,
  results: <><path d="M4 3v18h17M9 16v-5m5 5V7m5 9V4" /></>,
  sidebar: <><rect x="3" y="4" width="18" height="16" rx="3" /><path d="M9 4v16m7-11-3 3 3 3" /></>,
  logout: <><path d="M9 4H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4m6-12 4 4-4 4M8 12h11" /></>,
};

export function ShellIcon({ name }: { name: ShellIconName }) {
  return <svg className="shell-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
    {paths[name]}
  </svg>;
}
