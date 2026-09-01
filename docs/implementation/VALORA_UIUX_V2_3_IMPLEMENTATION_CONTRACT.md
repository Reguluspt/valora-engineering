# VALORA UI/UX v2.3 — Lightweight Implementation Contract

**Task:** PR-00 — Authority Alignment Guard

**Mode:** Ratchet-only; no runtime semantic change

**Authority branch:** `docs/uiux-handoff-v2.2`

**Authority tip inspected:** `1cf50460e54ba19d2f6a9d8f933ab123e4e615d6`

## Reading order

1. `docs/design/VALORA_UIUX_HANDOFF_v2.3.md`
2. `docs/design/VALORA_UIUX_V2_3_AUTHORITY_INDEX.md`
3. The v2.3 addendum directly governing the implementation slice.

This file is an implementation guard, not a copy of the canonical master. Newer explicit design
authority continues to win within its stated scope.

## Guarded vocabulary

Global Case State has exactly 16 canonical stages:

```text
PRELIMINARY_REQUEST | PRELIMINARY_ANALYSIS | PRELIMINARY_READY | OFFICIAL_INTAKE
| ASSET_REVIEW | ASSET_WORKBENCH | PRICE_EVIDENCE | SUPPLIER_QUOTES
| SUPPLIER_SELECTION | APPRAISAL_RESULT | DOCUMENT_WORKSPACE | DOCUMENT_SYNC_REVIEW
| PUBLISHING_PREPARATION | PUBLISHING_EXCEPTION_REVIEW | PUBLISHING_CONFIRMATION | PUBLISHED
```

Cross-product UI state has exactly 17 canonical values:

```text
INITIAL_LOADING | SECTION_LOADING | BACKGROUND_REFRESH | PROCESSING
| EMPTY_FIRST_USE | EMPTY_NO_RESULTS | EMPTY_NOT_APPLICABLE | EMPTY_COMPLETED
| INLINE_ERROR | SECTION_ERROR | PAGE_ERROR | FATAL_ERROR | STALE_DATA
| VERSION_CONFLICT | OFFLINE | RECONNECTING | PARTIAL_SUCCESS
```

The constants introduced by PR-00 are not runtime enums and are not connected to persistence,
workflow transitions, API schemas or URL decisions. Runtime adoption starts only in its assigned PR.

## Permanent boundaries protected by the ratchet

- Single-user workflow; AI remains advisory and human confirmation owns official decisions.
- Warning is not Blocking by default.
- No last-write-wins or blind retry for an uncertain mutation.
- No new KSCL/QC workflow, multi-level approval, standalone lock-version screen, NCCQ intermediate
  screen, standalone rule-check screen, global Audit screen or Export PDF surface.
- Audit/lineage remains context-first; persistence primitive names are not primary UI labels.
- `Project.status` and `WorkflowInstance.current_state` are reusable inputs, not Global Case State or
  frontend route authority by themselves.

## Known legacy conflict inventory

The following pre-v2.3 surfaces remain unchanged and are debt, not approved north-star behavior:

- backend workflow commands `SubmitProjectForQC`, `ApproveProject`, `RejectProject`;
- backend `/api/v1/workflow/approval-gates`;
- frontend `/workbench/queue` review queue;
- frontend `/workbench/validation` standalone validation dashboard;
- related QC, assignment and approval terminology in the legacy Workbench UI.

Contract tests permit only the inventoried occurrences and fail if the legacy backend commands or
frontend standalone routes expand. Removing or reinterpreting this debt requires a separately
authorized runtime remediation with migration/ADR review when persistence semantics are affected.

## Explicitly not implemented by PR-00

- no Global Case State projection or resume persistence;
- no workflow transition, enum, schema or migration change;
- no NCC Selection, Microsoft 365 integration, Managed Region sync or Publishing;
- no removal/deprecation of existing legacy records or endpoints.
