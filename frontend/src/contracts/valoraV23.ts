export const UIUX_V23_AUTHORITY = {
  version: "2.3",
  master: "docs/design/VALORA_UIUX_HANDOFF_v2.3.md",
  authorityIndex: "docs/design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md"
} as const;

export const CANONICAL_CASE_STAGES = [
  "PRELIMINARY_REQUEST",
  "PRELIMINARY_ANALYSIS",
  "PRELIMINARY_READY",
  "OFFICIAL_INTAKE",
  "ASSET_REVIEW",
  "ASSET_WORKBENCH",
  "PRICE_EVIDENCE",
  "SUPPLIER_QUOTES",
  "SUPPLIER_SELECTION",
  "APPRAISAL_RESULT",
  "DOCUMENT_WORKSPACE",
  "DOCUMENT_SYNC_REVIEW",
  "PUBLISHING_PREPARATION",
  "PUBLISHING_EXCEPTION_REVIEW",
  "PUBLISHING_CONFIRMATION",
  "PUBLISHED"
] as const;

export const CANONICAL_CROSS_PRODUCT_UI_STATES = [
  "INITIAL_LOADING",
  "SECTION_LOADING",
  "BACKGROUND_REFRESH",
  "PROCESSING",
  "EMPTY_FIRST_USE",
  "EMPTY_NO_RESULTS",
  "EMPTY_NOT_APPLICABLE",
  "EMPTY_COMPLETED",
  "INLINE_ERROR",
  "SECTION_ERROR",
  "PAGE_ERROR",
  "FATAL_ERROR",
  "STALE_DATA",
  "VERSION_CONFLICT",
  "OFFLINE",
  "RECONNECTING",
  "PARTIAL_SUCCESS"
] as const;

export const APP_ROUTES = {
  projectList: "/workbench/projects",
  projectDetailPrefix: "/workbench/projects/",
  projectOverviewSuffix: "/overview",
  projectNccSelectionSuffix: "/ncc-selection",
  projectDocumentsSuffix: "/documents",
  m365Return: "/workbench/m365/return"
} as const;

export function projectWorkbenchPath(projectRef: string): string {
  return `${APP_ROUTES.projectDetailPrefix}${encodeURIComponent(projectRef)}`;
}

export function projectOverviewPath(projectRef: string): string {
  return `${projectWorkbenchPath(projectRef)}${APP_ROUTES.projectOverviewSuffix}`;
}

export function projectNccSelectionPath(projectRef: string): string {
  return `${projectWorkbenchPath(projectRef)}${APP_ROUTES.projectNccSelectionSuffix}`;
}

export function projectDocumentsPath(projectRef: string): string {
  return `${projectWorkbenchPath(projectRef)}${APP_ROUTES.projectDocumentsSuffix}`;
}

export function splitProjectRoute(path: string): {
  projectRef: string;
  view: "overview" | "workbench" | "ncc-selection" | "documents";
} | null {
  const pathname = path.split("?", 1)[0];
  if (!pathname.startsWith(APP_ROUTES.projectDetailPrefix)) return null;
  const remainder = pathname.slice(APP_ROUTES.projectDetailPrefix.length);
  const isNccSelection = remainder.endsWith(APP_ROUTES.projectNccSelectionSuffix);
  const isOverview = remainder.endsWith(APP_ROUTES.projectOverviewSuffix);
  const isDocuments = remainder.endsWith(APP_ROUTES.projectDocumentsSuffix);
  const encodedRef = isNccSelection
    ? remainder.slice(0, -APP_ROUTES.projectNccSelectionSuffix.length)
    : isDocuments
      ? remainder.slice(0, -APP_ROUTES.projectDocumentsSuffix.length)
    : isOverview
      ? remainder.slice(0, -APP_ROUTES.projectOverviewSuffix.length)
      : remainder;
  if (!encodedRef || encodedRef.includes("/")) return null;
  try {
    return {
      projectRef: decodeURIComponent(encodedRef),
      view: isNccSelection
        ? "ncc-selection"
        : isDocuments
          ? "documents"
          : isOverview
            ? "overview"
            : "workbench",
    };
  } catch {
    return null;
  }
}

export const FORBIDDEN_NEW_STANDALONE_ROUTE_FRAGMENTS = [
  "/kscl",
  "/qc",
  "/approval",
  "/lock-version",
  "/nccq-intermediate",
  "/nccq-aggregate",
  "/rule-check",
  "/global-audit",
  "/export-pdf",
  "/pdf-export"
] as const;

export const FORBIDDEN_NEW_STANDALONE_ROUTES = [
  "/audit",
  "/workbench/audit",
  "/queue",
  "/validation",
  "/workbench/queue",
  "/workbench/validation"
] as const;
