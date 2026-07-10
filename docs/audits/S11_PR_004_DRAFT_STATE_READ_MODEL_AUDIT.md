# S11-PR-004: Draft State Read Model Audit Report

This report documents the verification audit for creating the read-only Draft State Read Model for Live Workbench asset lines.

## 1. Files Changed
- [VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md)
- [S11_PR_004_DRAFT_STATE_READ_MODEL_AUDIT.md](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/audits/S11_PR_004_DRAFT_STATE_READ_MODEL_AUDIT.md)
- [workbench_schemas.py](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/modules/project_master_data/workbench_schemas.py) (modified)
- [projects.py](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/api/projects.py) (modified)
- [test_projects_api.py](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/tests/test_projects_api.py) (modified)
- [projects.ts](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/api/projects.ts) (modified)
- [useWorkbenchDraftState.ts](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/workbench/hooks/useWorkbenchDraftState.ts) (new)
- [useWorkbenchDraftState.test.ts](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/workbench/hooks/__tests__/useWorkbenchDraftState.test.ts) (new)
- [AssetGrid.tsx](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/workbench/AssetGrid.tsx) (modified)
- [WorkbenchLayout.tsx](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/layout/WorkbenchLayout.tsx) (modified)

## 2. Pre-flight Reading Summary
- **Design Book v1.3**: Mandates frozen MVP workflow limits and forbids exposing ORM concurrency tracking details like `version_token`/`row_version` in visible fields.
- **Vietnamese i18n Dictionary**: Sets Vietnamese-first templates and translations for system action items.
- **Non-IT Error Message Registry**: Directs error code mapping to Vietnamese dialogues and masks raw network/server codes.
- **S11-PR-001 API Contract**: Defines the `GET /api/v1/projects/{project_id}/asset-lines` wrapper schema.
- **S11-PR-002 Read Adapter Audit**: Connected grid to read adapter.
- **S11-PR-002A Resolver Audit**: Implemented route slug UUID resolution.
- **S11-PR-003 Context Drawer Audit**: Connected right drawer metadata.

## 3. Existing Draft/Workbench Model Inspection Summary
- **Inspection**: Mapped `InlineEditDraft` and `WorkbenchSession` database tables. `InlineEditDraft` contains targeted `session_id`, `target_type`, `target_id`, `field_key`, `draft_value`, `base_value`, and `base_row_version` attributes suitable for reading draft status details.

## 4. Draft State Strategy Chosen
- **Strategy A**: Backend draft state endpoint. Implemented a dedicated read-only draft state endpoint to retrieve active drafts matching the current user's active session, calculating staleness based on `base_row_version < current_line.row_version`.

## 5. Backend Endpoint Summary
- **Route**: `GET /api/v1/projects/{project_id}/asset-lines/draft-state`
- **Permission**: `project:read`
- **Response Shape**:
  ```json
  {
    "project_id": "uuid-string",
    "items": [
      {
        "asset_line_id": "uuid-string",
        "has_saved_draft": true,
        "has_unsaved_changes": false,
        "is_locked": false,
        "is_stale": false,
        "draft_status": "saved_draft",
        "changed_fields": ["appraised_price"]
      }
    ],
    "total": 1
  }
  ```
- **Scoping**: Filters exclusively within the authenticated user's `organization_id` (returns `404` for cross-org queries).

## 6. Frontend Read Model Summary
- Created the hook [useWorkbenchDraftState.ts](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/workbench/hooks/useWorkbenchDraftState.ts).
- Resolves row values and exposes status-to-badge mapping helpers: `Cần cập nhật mới` (stale), `Đang khóa` (locked), `Chưa lưu` (local unsaved changes), `Đã lưu nháp` (saved draft), `Không có thay đổi` (clean).

## 7. Grid/Drawer Integration Summary
- Added a read-only **Trạng thái nháp** status badge column inside [AssetGrid.tsx](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/workbench/AssetGrid.tsx) displaying the live localized indicators.

## 8. i18n / Error UX Behavior
- Fully localized the draft status column title and badges to Vietnamese:
  - `Cần cập nhật mới` (stale) -> `warning`
  - `Đang khóa` (locked) -> `blocking`
  - `Chưa lưu` (unsaved) -> `draft`
  - `Đã lưu nháp` (saved_draft) -> `review`
  - `Không có thay đổi` (clean) -> `approved`

## 9. Runtime/User-Visible Behavior Changed
- Yes — Workbench rows now show read-only draft state indicators under the "Trạng thái nháp" column.

## 10. Tests/Commands Run
- **`python -m pytest`**: Passed (205 tests passed).
- **`npm run lint`**: Passed (0 diagnostics).
- **`npm run build`**: Passed (production Vite bundle successfully generated).
- **`npx vitest run src/components/workbench/hooks/__tests__/useWorkbenchDraftState.test.ts --globals`**: Passed (2 tests passed).
- **`npx vitest run src/components/workbench/hooks/__tests__/useProjectAssetLines.test.ts --globals`**: Passed (5 tests passed).
- **`npx vitest run src/components/workbench/hooks/__tests__/useAssetLineContext.test.ts --globals`**: Passed (2 tests passed).
- **`npx vitest run src/i18n/__tests__/i18n.test.ts --globals`**: Passed (4 tests passed).
- **`npx vitest run src/errors/__tests__/errorRegistry.test.ts --globals`**: Passed (5 tests passed).

## 11. Backend Change Statement
- Yes, a backend read-only draft state endpoint `GET /api/v1/projects/{project_id}/asset-lines/draft-state` was introduced alongside corresponding unit tests.

## 12. Risks / Deferred Items
- Mutation endpoints, draft write/save/commits, and AI recommendations remain deferred.

## 13. Design Consistency Check
- Design Book v1.3 checked: Yes
- Sprint 10 final acceptance checked: Yes
- S11-PR-001 API contract checked: Yes
- S11-PR-002 read adapter checked: Yes
- S11-PR-002A project UUID resolver checked: Yes
- S11-PR-003 context drawer adapter checked: Yes
- Astryx mapping checked: Yes
- Vietnamese i18n dictionary checked: Yes
- Non-IT error registry checked: Yes
- RBAC/scoping checked: Yes
- Runtime behavior statement verified from git diff: Yes
- Audit file lists every changed file: Yes
- No hardcoded project UUID introduced: Yes
- No all-zero UUID fallback introduced: Yes
- No dashboard/revenue/CRM scope introduced: Yes
- No Gemini/DeepSeek runtime integration introduced: Yes
- No backend auth/JWT change introduced: Yes
- No inline editing introduced: Yes
- No draft save introduced: Yes
- No official commit introduced: Yes
- No Excel import implementation introduced: Yes
- No report generation implementation introduced: Yes
- No version_token rendered to users: Yes
- No row_version/session_id rendered to users: Yes
- No raw technical errors exposed to users: Yes
- No new English user-facing labels introduced: Yes

## 14. Final Status
PASS
