export const UIUX_V23_AUTHORITY = {
  version: "2.3",
  branch: "docs/uiux-handoff-v2.2",
  tip: "1cf50460e54ba19d2f6a9d8f933ab123e4e615d6"
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
  legacyReviewQueue: "/workbench/queue",
  legacyValidationDashboard: "/workbench/validation"
} as const;

export const LEGACY_ROUTE_ALIASES = {
  reviewQueue: "/queue",
  validationDashboard: "/validation"
} as const;

// Known pre-v2.3 navigation debt. Keeping these paths here prevents silent expansion while
// leaving removal/deprecation to a separately authorized runtime remediation task.
export const LEGACY_ROUTE_RATCHET = [
  APP_ROUTES.legacyReviewQueue,
  APP_ROUTES.legacyValidationDashboard
] as const;

export const FORBIDDEN_NEW_STANDALONE_ROUTE_FRAGMENTS = [
  "/kscl",
  "/qc",
  "/approval",
  "/lock-version",
  "/nccq",
  "/rule-check",
  "/audit",
  "/export-pdf",
  "/pdf-export"
] as const;
