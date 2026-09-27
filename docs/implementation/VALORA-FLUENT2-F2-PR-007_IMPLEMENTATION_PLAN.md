# F2-PR-007 — Provider-Neutral Document Workspace & M365 Return Remediation

**Status:** READY FOR DEV
**Depends on:** F2-PR-003
**Authority:** Document Workspace baseline + M365 Return/Revalidation + ADR 0043–0045
**Risk:** HIGH — wording must not promote non-authoritative Working changes

## File manifest
**MODIFY:** `M365WorkspacePage.tsx`, `m365Workspace.css`, focused tests.
**PRESERVE unless required:** M365 API methods and G8 Exchange/storage mechanics.

## Product parent
Top-level product title/IA is `Không gian tài liệu` / `Bộ tài liệu hồ sơ`. OneDrive/Word/Microsoft 365 appear only as integration/account/file actions.

## Layout target
Where current data permits: folder/document navigation area, central document/content area, contextual metadata/sync/version area and Fluent command bar. Do not fabricate Word preview or folder data not returned by current APIs; use truthful empty/unavailable states until OS-G3 supplies missing runtime capability.

## Command semantics
Allowed current concepts include `Mở trong Word`, `Kiểm tra thay đổi`, `Xem & xác nhận thay đổi` only when a DocumentChangeCandidate exists, `Tạo/Xác nhận phiên bản` only at the authoritative candidate boundary, `So sánh`, secondary menu.

Historical generic `Nhập thay đổi` must not be presented as direct authoritative promotion. Existing Exchange re-import mechanics may remain as non-authoritative intake/revalidation plumbing, but user-facing copy must describe observation/import for review and must not imply Revision N+1. Do not add `Khóa phiên bản` or Export PDF.

## Return/revalidation
On focus return keep usable workspace and show BACKGROUND_REFRESH; do not blank page. Preserve server classification outcomes and server `next_action`. M365 version/save does not create Revision. Access unavailable keeps last-known data when safe and marks freshness unknown.

## Tests
Preserve existing five-classification, adoption, permission, focus-return revalidation, server-next-action and Exchange grant tests. Update assertions whose wording becomes provider-neutral/current-authority. Add explicit negative assertion: no copy implies Word Save/M365 version/direct re-import automatically creates DocumentRevision.

## DoD
Provider-neutral parent surface, Fluent light presentation, G8 mechanics unchanged, ADR-0045 wording boundary respected, browser/screenshot evidence accepted.
