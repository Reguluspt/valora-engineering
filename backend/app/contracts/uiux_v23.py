"""VALORA UI/UX v2.3 vocabulary guard for implementation alignment.

These constants are intentionally not wired into workflow persistence or routing.
PR-01 and later slices must make any runtime adoption through their own design and ADR gates.
"""

AUTHORITY_VERSION = "2.3"
AUTHORITY_BRANCH = "docs/uiux-handoff-v2.2"
AUTHORITY_TIP = "1cf50460e54ba19d2f6a9d8f933ab123e4e615d6"

CANONICAL_CASE_STAGES = (
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
    "PUBLISHED",
)

CANONICAL_CROSS_PRODUCT_UI_STATES = (
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
    "PARTIAL_SUCCESS",
)

# Known pre-v2.3 runtime debt. The ratchet test permits only these exact occurrences and
# rejects expansion. This is not approval of their semantics and is not a runtime allowlist.
LEGACY_BACKEND_CONFLICT_RATCHET = {
    "SubmitProjectForQC": {"app/api/workflow.py": 1},
    "ApproveProject": {"app/api/workflow.py": 1},
    "RejectProject": {"app/api/workflow.py": 1},
    '"/approval-gates"': {"app/api/workflow.py": 1},
}

FORBIDDEN_NEW_BACKEND_SURFACE_MARKERS = (
    "/kscl",
    "KSCLWorkflow",
    "/multi-level-approval",
    "MultiLevelApproval",
    "/lock-version",
    "LockVersionScreen",
    "/nccq-intermediate",
    "/nccq-aggregate",
    "NCCQIntermediate",
    "/rule-check",
    "RuleCheckScreen",
    "/global-audit",
    "GlobalAuditScreen",
    "/export-pdf",
    "/pdf-export",
    "Export PDF",
    "PDF export",
)
