# VALORA UI/UX v2.3 — Kết quả đồng bộ hàng loạt — Baseline Addendum

**Status:** Baseline / Design Authority  
**Iteration:** 1  
**Date:** 31/08/2026

## 1. Quyết định baseline
Mockup `Kết quả đồng bộ hàng loạt — Iteration 1`, phiên bản **đã bỏ luồng xuất file PDF**, được nâng thành Baseline / Design Authority.

Phiên bản mockup trước còn panel/tác vụ `Báo cáo tóm tắt (PDF)` bị supersede và không còn authority.

## 2. Vị trí trong flow
```text
Chọn nguồn dữ liệu mới
→ Xem thay đổi & phạm vi cập nhật
→ Xem trước kết quả [zero-write]
→ Xử lý xung đột nếu có [zero-write]
→ Xác nhận & Đồng bộ [write boundary]
→ Kết quả đồng bộ hàng loạt
→ Xem & quản lý revision / Quay lại workspace
```

Đây là màn post-execution. Không thực hiện thêm ghi dữ liệu chỉ vì user mở màn kết quả.

## 3. Layout authority
- Header/breadcrumb + stepper hoàn tất.
- Summary cards: `Đã đồng bộ thành công / Không có thay đổi / Bỏ qua (theo quyết định) / Lỗi (thất bại) / Tổng tài liệu`.
- Main table `Chi tiết kết quả theo tài liệu`: tên tài liệu, loại, vùng thay đổi, kết quả, Revision mới (VALORA), phiên bản M365, thời gian xử lý, tác vụ chi tiết.
- Panel phải: tổng quan phiên đồng bộ và breakdown kết quả theo tài liệu.
- Ghi chú dưới bảng giải thích semantics từng trạng thái.
- Primary CTA: `Xem & quản lý revision`.
- Secondary actions có thể gồm `Quay lại workspace`, `Mở thư mục hồ sơ`, `Đồng bộ lại` theo context.

## 4. Result semantics
Mỗi tài liệu có một kết quả riêng; không dùng success chung để che partial failure.

Trạng thái authority:
- `Đã đồng bộ`: Managed Regions trong sync plan đã được ghi thành công; tạo Document Revision mới và ghi nhận Microsoft 365 file/version.
- `Không thay đổi`: không ghi, không tạo revision mới.
- `Bỏ qua`: không ghi trong lần sync này; không tạo revision mới; vùng/tài liệu liên quan vẫn cần trạng thái phù hợp để user biết chưa cập nhật.
- `Lỗi`: chưa hoàn tất; không được giả định toàn bộ thay đổi đã được ghi. User có thể xem chi tiết và retry sau khi xử lý.

## 5. Version & lineage
Chỉ tài liệu thực sự cập nhật thành công mới có lineage mới:
```text
Template Version → Data Snapshot → Document Revision mới → Microsoft 365 file/version
```
`Document Revision != Microsoft 365 file version`. Published revision/release immutable.

## 6. Retry semantics
`Đồng bộ lại` phải dựa trên trạng thái hiện tại, revalidate Data Snapshot/Word state và không được mặc định replay nguyên sync plan cũ nếu plan đã stale. Retry/idempotency là implementation concern cần ADR nếu thay đổi persistence/transaction semantics.

## 7. Export authority
**Không có luồng xuất file PDF tại màn Kết quả đồng bộ hàng loạt.**

Nếu có nhu cầu tải báo cáo kỹ thuật/đối soát trong tương lai, đó phải là capability riêng được thiết kế và phê duyệt; không được suy diễn từ mockup cũ. Publishing authority hiện hành cũng tiếp tục **không có `Xuất PDF`**.

## 8. Guardrails
- Single-user.
- Không fake Word editor.
- Không silent retry/resync.
- Không tạo revision cho unchanged/skipped/failed document nếu chưa cập nhật thành công.
- Không che partial failure bằng trạng thái thành công batch.
- Không export PDF trong baseline này.
- Một primary CTA mỗi context.

## 9. ADR
Nếu implementation thay đổi partial-success model, retry/idempotency, recovery semantics, result persistence, revision/version creation hoặc stale-plan revalidation thì phải đánh giá ADR riêng trước khi sửa product code.
