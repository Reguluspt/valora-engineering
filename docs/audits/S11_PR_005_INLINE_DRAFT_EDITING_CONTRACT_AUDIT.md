# S11-PR-005: Inline Draft Editing Contract Audit Report

This report documents the verification audit for the S11-PR-005 Inline Draft Editing Contract.

## 1. Files Changed
- [VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md)
- [S11_PR_005_INLINE_DRAFT_EDITING_CONTRACT_AUDIT.md](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/audits/S11_PR_005_INLINE_DRAFT_EDITING_CONTRACT_AUDIT.md)
- [workbench_schemas.py](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/modules/project_master_data/workbench_schemas.py) (modified)
- [projects.py](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/api/projects.py) (modified)
- [test_projects_api.py](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/tests/test_projects_api.py) (modified)
- [projects.ts](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/api/projects.ts) (modified)
- [useWorkbenchDraftSync.ts](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/workbench/session/useWorkbenchDraftSync.ts) (modified)
- [useWorkbenchDraftSync.test.ts](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/workbench/session/__tests__/useWorkbenchDraftSync.test.ts) (new)
- [WorkbenchLayout.tsx](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/layout/WorkbenchLayout.tsx) (modified)

## 2. Pre-flight Reading Summary
- **Design Book v1.3**: Directs strict separation between draft edits and committed values. Prohibits direct mutations of master records prior to official commit sequence.
- **Vietnamese i18n Dictionary**: Preserves business-friendly Vietnamese badge statuses.
- **Non-IT Error Registry**: Maps technical exceptions (e.g. `409 Conflict` or stale versions) to friendly descriptions.
- **S11-PR-004 Read Model Audit**: Draft read status columns now live in Vietnamese.

## 3. Existing Draft/Workbench Model Inspection Summary
- **Inspection**: The database model `InlineEditDraft` maps perfectly to individual fields via `field_key` and contains `base_row_version` to track concurrency conflicts.

## 4. Editable Field Allowlist
- Backend draft endpoint allowlist supports `description` and `appraised_unit_price`.
- Current Workbench inline editing UI exposes only `appraised_price -> appraised_unit_price`.
- `normalized_name` is read-only and is not mapped to `description`.

No internal status fields, IDs, or timestamps are mutable.

## 5. Backend Draft Save Endpoint Summary
- **Route**: `PATCH /api/v1/projects/{project_id}/asset-lines/{line_id}/draft`
- **Permission**: `workbench:edit`
- **Strategy**: Persisted via the existing `InlineEditDraft` and `WorkbenchSession` models.
- **Concurrency Check**: Enforces `version_token` checks, returning `409` on stale values.
- **Organization Security**: Resolves scoping against current user's authenticated `organization_id` to block cross-org harvesting.

## 6. Frontend Draft Editing Summary
- Bound inline price cell in the grid to call `saveAssetLineDraft` on save.
- Mapped field keys: `appraised_price -> appraised_unit_price` before triggering the API.
- `normalized_name` remains read-only and is not sent to the draft save API.
- Unsupported fields trigger the Vietnamese message: “Trường dữ liệu này chưa hỗ trợ chỉnh sửa.”
- Destructured `reloadDrafts()` callback in the grid hook to reload draft indicators instantly on successful save.

## 7. Official Value Immutability Verification
- Verified that `ProjectAssetLine` table columns are completely unaffected by `PATCH` draft persistence calls. Only `InlineEditDraft` rows are inserted or updated.

## 8. i18n / Error UX Behavior
- Status states are fully localized into Vietnamese badges: `Chưa lưu`, `Đã lưu nháp`, `Cần cập nhật mới`.

## 9. Tests / Quality Gates Run
- **`python -m pytest`**: Passed (206 tests passed).
- **`npm run lint`**: Passed (0 diagnostics).
- **`npm run build`**: Passed (production bundle built successfully).
- **`npx vitest run src/components/workbench/session/__tests__/useWorkbenchDraftSync.test.ts --globals`**: Passed (2 tests passed).
- **`npx vitest run --globals`**: Passed (All 20 tests passed).

## 10. Runtime/User-Visible Behavior Changed
- Yes — supported Workbench cells can now be edited and saved as draft without changing official asset line values.

## 11. Backend Change Statement
- Yes, a backend draft save endpoint `PATCH /api/v1/projects/{project_id}/asset-lines/{line_id}/draft` was introduced alongside corresponding unit tests. The read-only draft state endpoint from S11-PR-004 was reused.

## 12. Risks / Deferred Items
- Official commits, report generations, and AI recommendations are deferred.

## 13. Design Consistency Check
- Design Book v1.3 checked: Yes
- Sprint 10 final acceptance checked: Yes
- S11-PR-001 API contract checked: Yes
- S11-PR-002 read adapter checked: Yes
- S11-PR-002A project UUID resolver checked: Yes
- S11-PR-003 context drawer adapter checked: Yes
- S11-PR-004 draft state read model checked: Yes
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
- No official commit introduced: Yes
- No Excel import implementation introduced: Yes
- No report generation implementation introduced: Yes
- No AI recommendation introduced: Yes
- ProjectAssetLine official values not mutated by draft save: Yes
- No version_token rendered to users: Yes
- No row_version/session_id rendered to users: Yes
- No raw technical errors exposed to users: Yes
- No new English user-facing labels introduced: Yes

## 14. Final Status
PASS
