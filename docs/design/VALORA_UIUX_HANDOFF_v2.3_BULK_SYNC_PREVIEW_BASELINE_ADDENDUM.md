# VALORA UI/UX v2.3 — Xem trước kết quả đồng bộ — Baseline Addendum

**Status:** Baseline / Design Authority  
**Iteration:** 1  
**Date:** 31/08/2026

## 1. Quyết định baseline
Mockup `Xem trước kết quả đồng bộ — Iteration 1` được nâng thành Baseline / Design Authority. Đây là bước 3/4 của `Đồng bộ dữ liệu hàng loạt`, sau `Xem thay đổi & phạm vi cập nhật` và trước `Xác nhận & Đồng bộ`.

## 2. Mental flow
```text
Chọn nguồn dữ liệu mới
→ Xem thay đổi & phạm vi cập nhật
→ Xem trước kết quả
→ [Xử lý xung đột nếu có]
→ Xác nhận & Đồng bộ
```

Bước preview là read-only simulation: **chưa ghi dữ liệu vào tài liệu, chưa tạo Document Revision, chưa tạo Microsoft 365 version**.

## 3. Layout authority
- Header/breadcrumb + stepper 4 bước; bước 3 active.
- Trái trên: `Thông tin phiên xem trước` gồm nguồn dữ liệu/Data Snapshot, snapshot so sánh, phạm vi cập nhật, thời gian preview.
- Giữa trên: summary `Sẽ được cập nhật / Không thay đổi / Cảnh báo (Warning) / Lỗi chặn (Blocking)`.
- Bảng chính: tài liệu, loại, mức ảnh hưởng, vùng thay đổi, thay đổi dữ liệu, thay đổi nội dung Word, kết quả dự kiến, revision mới dự kiến.
- Panel phải `Chi tiết thay đổi`: tài liệu đang chọn, revision hiện tại/dự kiến, thống kê vùng, top changes current→after sync, Warning/Blocking.
- Footer: `Hủy`, `Quay lại: Xem thay đổi`, action `Xử lý xung đột (nếu có)` khi cần, và một primary CTA `Tiếp tục: Xác nhận & Đồng bộ`.

## 4. Preview semantics
- `Sẽ cập nhật` nghĩa là tài liệu sẽ được ghi nếu user xác nhận ở bước 4; không phải đã cập nhật.
- `Không thay đổi` không tạo revision mới.
- `Revision dự kiến` chỉ là preview; chỉ trở thành revision thực sau sync thành công.
- User phải xem được current value và value sau sync ở mức Managed Region.
- Có thể lọc theo `Sẽ cập nhật / Không thay đổi / Cảnh báo / Lỗi chặn`.

## 5. Conflict authority
`Thay đổi nội dung (Word)` biểu thị các Managed Regions/nội dung liên quan đã thay đổi trong Word kể từ lần đồng bộ gần nhất. Nếu thay đổi tạo conflict với dữ liệu VALORA mới, user phải đi qua `Xử lý xung đột` trước khi xác nhận.

Conflict không được tự giải quyết bằng cách ưu tiên VALORA hoặc Word. User quyết định theo diff authority hiện hành.

## 6. Validation gate
- `Blocking > 0`: không cho đi tới thực thi đồng bộ cho tới khi Blocking được xử lý.
- `Warning > 0`: hiển thị rõ; không tự Blocking nếu rule hiện hành cho phép tiếp tục.
- Preview không silent sửa dữ liệu/mapping/content để giảm Warning/Blocking.

## 7. Data source clarification
Tên file `.xlsx` trên mockup chỉ là dữ liệu minh họa của source/Data Snapshot. Canonical business data vẫn Workbench/database; baseline không ràng buộc Bulk Sync phải lấy dữ liệu trực tiếp từ Excel.

## 8. Guardrails
- Single-user.
- Preview read-only; zero-write.
- Không silent sync/overwrite/conflict resolution.
- Không fake Word editor.
- Không tạo revision/version ở bước preview.
- Một primary CTA theo context.
- Published revision/release immutable.

## 9. ADR
Nếu implementation cần persist preview simulation, reserve revision numbers, cache diff, hoặc thay đổi conflict/validation transaction boundary thì phải đánh giá ADR riêng trước khi sửa product code.
