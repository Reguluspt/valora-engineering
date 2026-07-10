# S11-PR-002A: Workbench Route Project UUID Resolution Audit Report

This report documents the verification audit for resolving route slugs to real project UUIDs and loading real data in the Live Workbench grid.

## 1. Files Changed
- [VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md)
- [S11_PR_002A_WORKBENCH_ROUTE_PROJECT_UUID_RESOLUTION_AUDIT.md](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/audits/S11_PR_002A_WORKBENCH_ROUTE_PROJECT_UUID_RESOLUTION_AUDIT.md)
- [schemas.py](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/modules/project_master_data/schemas.py) (modified)
- [projects.py](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/api/projects.py) (modified)
- [test_projects_api.py](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/tests/test_projects_api.py) (modified)
- [projects.ts](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/api/projects.ts) (new)
- [client.ts](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/api/client.ts) (modified)
- [useProjectAssetLines.ts](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/workbench/hooks/useProjectAssetLines.ts) (modified)
- [useProjectAssetLines.test.ts](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/components/workbench/hooks/__tests__/useProjectAssetLines.test.ts) (modified)

## 2. Pre-flight Reading Summary
- **Design Book v1.3**: Mandates frozen MVP workflow limits and forbids exposing ORM concurrency tracking details like `version_token`/`row_version` in visible fields.
- **Vietnamese i18n Dictionary**: Sets Vietnamese-first templates and translations for system action items.
- **Non-IT Error Message Registry**: Directs error code mapping to Vietnamese dialogues and masks raw network/server codes.
- **S11-PR-001 API Contract**: Defines the `GET /api/v1/projects/{project_id}/asset-lines` wrapper schema.
- **S11-PR-002 Read Adapter Audit**: Recorded PASS WITH LIMITATION because route slug `hd-98-gia-lai` blocked backend calls due to lack of resolution logic.

## 3. Current Route/Project Reference Inspection Summary
- Route parameter represents a slug or UUID.
- Slugs like `hd-98-gia-lai` need to be resolved to their corresponding unique project UUID.
- Inspected the project model [models.py](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/backend/app/modules/project_master_data/models.py) to check for UUID/slug capabilities.

## 4. Project Model Lookup Capability Summary
- The backend `Project` model has `id`, `code`, and `name` attributes. It does not have a dedicated `slug` column.
- We support exact case-insensitive matches on `id`, `code`, and `name`, falling back to a deterministic slugified Python comparison of `code` and `name` across the organization's projects.

## 5. Chosen Resolver Strategy
- **UUID Bypassing**: If the route parameter matches a standard UUID pattern, the resolver is bypassed and the UUID is used directly.
- **Slug Resolution**: Otherwise, the backend resolver endpoint is called to retrieve the project UUID.

## 6. Backend Resolver Endpoint Summary
- **Route**: `GET /api/v1/projects/resolve?ref={project_ref}`
- **Permission**: `project:read`
- **Response Shape**:
  ```json
  {
    "project_id": "033781ee-adca-4af2-a58b-43e7e43823b8",
    "display_name": "Hồ sơ Gia Lai Số 98",
    "matched_by": "id|code|name|code_slug|name_slug"
  }
  ```
- **Scoping**: Enforces tenant-isolation by filtering matches using the active user's `organization_id`.
- **Ambiguity**: Returns `409 Conflict` if multiple projects match the same slug.

## 7. Frontend Resolver Integration Summary
- Extended frontend API with `resolveProjectReference` in `frontend/src/api/projects.ts`.
- Integrated lookup calls directly inside `useProjectAssetLines.ts` to automatically resolve slugs before calling the asset lines API.

## 8. Project ID Resolution Behavior
- Route slug `hd-98-gia-lai` successfully resolves to its corresponding project UUID from the seeded DB on startup, allowing the grid to transition to loading and rendering real data.

## 9. Loading / Empty / Error UX Behavior
- While resolving, the UI displays `Đang tải danh sách tài sản...`.
- If resolver yields `404`, displays Vietnamese friendly text: "Không tìm thấy hồ sơ".
- If resolver yields `409`, displays: "Trùng lặp hồ sơ" (Có nhiều hồ sơ trùng thông tin, vui lòng chọn từ danh sách hồ sơ).
- If resolver yields `403`, displays: "Không có quyền truy cập" (Hồ sơ không thuộc phạm vi truy cập của tài khoản này).

## 10. Runtime/User-Visible Behavior Changed
Yes — Workbench route slugs now resolve to real project UUIDs before loading asset lines. Backend resolver endpoint was added. No inline editing, draft commit, or visible technical details were introduced.

## 11. Quality Gates Run
The following commands were run and verified:
- **`python -m pytest`**: Passed (204 tests passed).
- **`npm run lint`**: Passed (0 diagnostics).
- **`npm run build`**: Passed (production Vite bundle successfully generated).
- **`npx vitest run src/components/workbench/hooks/__tests__/useProjectAssetLines.test.ts --globals`**: Passed (5 tests passed).
- **`npx vitest run src/i18n/__tests__/i18n.test.ts --globals`**: Passed (4 tests passed).
- **`npx vitest run src/errors/__tests__/errorRegistry.test.ts --globals`**: Passed (5 tests passed).

## 12. Backend Change Statement
- Yes, a backend resolver endpoint `GET /api/v1/projects/resolve` was introduced alongside corresponding unit tests.

## 13. Risks / Deferred Items
- Inline editing, draft saves, and commits remain deferred.

## 14. Design Consistency Check
- Design Book v1.3 checked: Yes
- Sprint 10 final acceptance checked: Yes
- S11-PR-001 API contract checked: Yes
- S11-PR-002 read adapter checked: Yes
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
- No draft commit introduced: Yes
- No Excel import implementation introduced: Yes
- No report generation implementation introduced: Yes
- No version_token rendered to users: Yes
- No raw technical errors exposed to users: Yes
- No new English user-facing labels introduced: Yes

## 15. Final Status
PASS
