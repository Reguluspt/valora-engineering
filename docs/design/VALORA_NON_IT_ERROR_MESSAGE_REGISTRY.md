# Non-IT Error Message Registry Design Contract

This document outlines the design architecture for mapping raw system/API/DB errors to user-friendly Vietnamese notifications.

---

## 1. Purpose & Strategy
Valora's non-IT business users should never deal with HTTP protocols, system stack traces, database transaction IDs, or AI provider naming parameters. 

The centralized Error Message Registry acts as a gateway proxy to translate raw HTTP statuses or connectivity drops into clear, Vietnamese-first instructions with next-action guidance.

### 1.1 Relationship to Design Book v1.3
- Design Book v1.3 requires Vietnamese-first, non-IT UX.
- This registry implements the error shielding layer required by that design contract.
- Raw backend/system errors must never be exposed to ordinary users.

### 1.2 Relationship to Vietnamese i18n Dictionary
- S10-PR-004 owns the typed Vietnamese label foundation.
- S10-PR-005 owns structured error messages with title, message, nextAction, severity, retryable.
- Error message values must stay Vietnamese and user-friendly.
- Future registry entries should reuse i18n labels where practical.

### 1.3 Relationship to Astryx Feedback Surfaces
- Astryx provides the visual surfaces: toast, inline alert, banner, modal/dialog, empty state.
- The error registry provides the text payload and severity.
- Future UI components should render FriendlyError using Astryx feedback patterns.

---

## 2. Forbidden Technical Terms
To comply with the security and usability guardrails, the following parameters are strictly blocked from user-facing strings:
- **HTTP status codes**: `401`, `403`, `409`, `422`, `500`
- **Internal protocol variables**: `API`, `RBAC`, `row_version`, `session_id`, `stack trace`, raw JSON exception logs
- **AI Backend Engines**: `Gemini`, `DeepSeek` (must always map to *Trợ lý Valora*)

---

## 3. Error Category Taxonomy
The registry structures errors across eight key categories:
1. **Network / Connectivity**: Timeout drops (`network_failure`, `request_timeout`, `server_unreachable`).
2. **Authentication / Permission**: Expiration blocks (`session_expired`, `insufficient_permission`).
3. **Data Conflict / Validation**: Optimistic lock collisions (`optimistic_conflict`, `stale_data`, `validation_error`).
4. **Import / File Handling**: Ingest failures (`excel_parse_error`, `empty_excel_file`).
5. **Workbench / Draft Save**: State backup issues (`draft_save_failed`, `unsaved_changes_before_leave`).
6. **AI Assistant**: Advisory analysis delays (`assistant_timeout`, `assistant_unavailable`).
7. **Report Generation**: Output compilation blockages (`report_generation_failed`, `report_data_not_ready`).
8. **Generic Fallback**: Missing metadata handles (`unknown_error`, `server_error`, `temporary_failure`).

---

## 4. Centralized Friendly Error Shape
Every mapped exception returns a unified type-safe dictionary block:

```typescript
export type FriendlyError = {
  title: string;       // Vietnamese Title
  message: string;     // Non-technical Vietnamese description
  nextAction: string;  // Explicit guidance on what the user should do next
  severity: "info" | "warning" | "error" | "blocking";
  retryable: boolean;  // Renders a retry button in the UI
};
```

### 4.1 Examples of Mapping Rules
- **Raw HTTP 409 Conflict**: Returns `optimistic_conflict` ("Dữ liệu hồ sơ này đã được thay đổi bởi người dùng khác", advising the user to click 'Cập nhật mới' to re-sync).
- **Gemini API Timeout**: Returns `assistant_timeout` ("Trợ lý Valora phản hồi chậm", advising the user to submit the query again after a few seconds).
- **Raw HTTP 403 Forbidden**: Returns `forbidden` ("Tài khoản chưa được cấp quyền thực hiện thao tác này", advising the user to contact the Administrator).

---

## 5. Adoption & Migration Plan
- S10-PR-005 establishes the registry and safely adopts it in `ApiErrorBanner` only.
- Future PRs should migrate `RbacLockNotice`, `ConflictWarning`, import validation, Workbench draft save, AI assistant errors, and report generation errors.
- Any new MVP error display must use the registry.

---

## 6. Review Blockers for Future PRs
- Any raw status code (e.g. `Error 500`) rendered in UI warning banners.
- Displaying stack traces or JSON response error logs directly to users.
- Displaying third-party provider names inside ordinary user views.
- Mapped errors lacking a defined `nextAction` instruction.
