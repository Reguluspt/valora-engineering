# VALORA UI/UX v2.3 — M365 Return & Revalidation — Iteration 1

**Status:** Baseline / Design Authority  
**Iteration:** 1  
**Date promoted:** 01/09/2026  
**Semantic authority:** `Microsoft 365 Return / Revalidation Contract v1`

## 1. Baseline decision
Mockup `M365 Return & Revalidation — Iteration 1` được người dùng explicit nâng thành Baseline / Design Authority.

Visual này là cross-layer integration/state pattern cho Microsoft 365 Document Workspace; không phải workflow checkpoint hay business commit mới.

## 2. Visual authority
Approved board thể hiện các vùng chính:
1. `Return & Revalidation Flow (High-level)` — Mở trong Word → Ghi nhận Handoff → Quay lại VALORA → Revalidate background → So sánh & phân loại → State & Hành động.
2. `Revalidation Outcomes` — 5 semantic outcomes.
3. `Return & Revalidation — State UI Patterns` — ví dụ UI cho từng outcome.
4. `Xem thay đổi (3-chiều)` — Snapshot cũ / VALORA hiện tại / Word hiện tại.
5. `Xử lý xung đột (Decision)` — explicit per-region decision.
6. `Revalidation Indicator (Background Refresh)` — giữ usable workspace trong lúc kiểm tra.
7. `Nguyên tắc bắt buộc` — safety/immutability/anti-silent-overwrite rules.

## 3. Canonical semantic outcomes
Visual phải map vào đúng contract:
`NO_CHANGE | EXTERNAL_CHANGE_OUTSIDE_MANAGED | EXTERNAL_CHANGE_IN_MANAGED | FILE_REPLACED_OR_MOVED | ACCESS_UNAVAILABLE`.

Business-facing label ưu tiên tiếng Việt; enum kỹ thuật chỉ là secondary implementation/design label.

## 4. Flow authority
```text
Mở trong Word
→ ghi nhận handoff context
→ user quay lại / regain focus / explicit refresh / action cần freshness
→ BACKGROUND_REFRESH
→ revalidate M365 file state
→ compare với baseline đã bind
→ classify
→ derive document state/action
```

Return/Revalidation không làm tăng completion và không tạo Document Revision chỉ vì M365 version thay đổi.

## 5. State-card behavior
### NO_CHANGE
Hiển thị trạng thái tích cực `Tài liệu không có thay đổi`; user có thể tiếp tục công việc. Không tạo revision mới.

### EXTERNAL_CHANGE_OUTSIDE_MANAGED
Hiển thị `Có thay đổi ngoài vùng quản lý`; cho phép xem chi tiết và tiếp tục sync dữ liệu hợp lệ. Không mặc định conflict.

### EXTERNAL_CHANGE_IN_MANAGED
Hiển thị `Có thay đổi trong vùng quản lý`; CTA dẫn tới xem thay đổi/xử lý nếu cần. Không silent overwrite.

### FILE_REPLACED_OR_MOVED
Hiển thị file đã thay thế/di chuyển hoặc binding không còn đáng tin cậy; yêu cầu xác minh/liên kết lại theo implementation authority. Không auto-bind theo filename.

### ACCESS_UNAVAILABLE
Giữ last-known usable state nếu có, hiển thị `Không truy cập được file` / chưa xác minh và recovery như `Thử lại` hoặc kiểm tra quyền. Không fake sync/publish readiness.

## 6. Three-way comparison authority
Board thể hiện bảng so sánh:
`Snapshot cũ | VALORA hiện tại | Word hiện tại | Trạng thái`.

Semantic authority vẫn là contract:
- VALORA và Word không đổi → no change;
- Word-only edit → bảo toàn Word;
- VALORA-only change → cần cập nhật;
- cả VALORA và Word thay đổi khác semantic value → conflict;
- hội tụ cùng semantic value có thể non-conflict nếu audit/lineage đủ.

## 7. Conflict decision authority
Visual decision surface minh họa explicit lựa chọn theo Managed Region. Implementation phải kế thừa `Xử lý xung đột khi đồng bộ` baseline: không silent default, không auto-win, decision cập nhật sync plan trước write boundary.

## 8. Background refresh authority
`Đang kiểm tra thay đổi từ Microsoft 365…` là background revalidation indicator. Khi có usable data:
- không blank workspace;
- không biến thành full-page loading;
- có thể hiển thị chi tiết contextual;
- mutation phụ thuộc freshness có thể chờ revalidation.

## 9. Hard guardrails
- Quay lại VALORA không phải bằng chứng Word đã đổi.
- Không tạo Document Revision mới chỉ vì phát hiện M365 version mới.
- Thay đổi ngoài Managed Region không mặc định conflict.
- Thay đổi trong Managed Region không silent overwrite.
- User edit trong Managed Region + VALORA data đổi mới dùng conflict semantics.
- Không tự bind file thay thế theo filename.
- ACCESS_UNAVAILABLE giữ dữ liệu cũ nhưng đánh dấu chưa xác minh.
- Sync/Publishing phải revalidate khi freshness là điều kiện bắt buộc.
- Return/Revalidation không phải business commit và không tạo workflow checkpoint.
- Published revision/release immutable.
- Không fake Word editor; không Export PDF.

## 10. Approved visual asset
Exact approved mockup in the working handoff package:
`a_high_resolution_ui_ux_design_board_dashboard_m.png`

Khi đóng gói master DOCX, phải dùng đúng approved visual này, không redraw/reinterpret nếu chưa có quyết định mới.

## 11. Relationship / supersession
Addendum này nâng visual `M365 Return & Revalidation — Iteration 1` thành authority và kế thừa toàn bộ semantic contract `Microsoft 365 Return / Revalidation Contract v1`.

Nếu visual wording minh họa mâu thuẫn với semantic contract, **semantic contract thắng**. Các baseline Document Workspace, Sync-Version, Conflict Resolution, Cross-product State, Global Case State và Publishing tiếp tục có hiệu lực trong scope riêng.

## 12. ADR
Visual promotion không đồng nghĩa code đã implement. Các thay đổi persistence/integration về Graph, M365 file identity/version, webhook, Managed Region fingerprint/diff, freshness policy hoặc revalidation audit vẫn cần đánh giá ADR kỹ thuật theo contract v1.