# VALORA UI/UX v2.3 — Xác nhận & Đồng bộ hàng loạt — Baseline Addendum

**Status:** Baseline / Design Authority  
**Iteration:** 1  
**Date:** 31/08/2026

## 1. Quyết định baseline
Mockup `Xác nhận & Đồng bộ hàng loạt — Iteration 1` được nâng thành Baseline / Design Authority. Đây là execution gate của Bulk Data Sync: các bước preview/conflict trước đó là zero-write; chỉ tại primary action của bước này VALORA mới được phép thực thi sync plan.

## 2. Flow authority
```text
Chọn nguồn dữ liệu mới
→ Xem thay đổi & phạm vi cập nhật
→ Xem trước kết quả [zero-write]
→ Xử lý xung đột nếu có [zero-write]
→ Xác nhận & Đồng bộ [execution]
→ Kết quả đồng bộ hàng loạt
```

## 3. Layout authority
- Header + stepper, `Xác nhận & Đồng bộ` là bước thực thi cuối.
- Summary sau xử lý conflict: tổng tài liệu trong scope, tài liệu sẽ cập nhật, không thay đổi, bỏ qua theo quyết định, số Managed Regions sẽ cập nhật.
- Main table `Phạm vi đồng bộ cuối cùng`: tài liệu, loại, mức ảnh hưởng, số vùng thay đổi, quyết định cuối cùng, revision dự kiến, trạng thái readiness.
- Panel phải `Kiểm tra trước khi đồng bộ`: Blocking, Warning, Conflict đã xử lý, Không có thay đổi; bên dưới là chi tiết Warning và thông tin Data Snapshot/source.
- Banner trước footer phải giải thích đây là hành động ghi dữ liệu thực tế.
- Footer: Hủy, quay lại Xử lý xung đột khi cần, một primary CTA `Xác nhận & Đồng bộ`.

## 4. Execution gate
Primary CTA chỉ enabled khi:
- `Blocking = 0`;
- tất cả conflict bắt buộc trong scope đã có explicit decision;
- sync plan vẫn còn hợp lệ với trạng thái Word/Data Snapshot hiện tại.

Nếu dữ liệu hoặc Word đã thay đổi kể từ preview/conflict decision, implementation phải phát hiện stale plan và yêu cầu review lại thay vì silent thực thi kế hoạch cũ.

## 5. Execution semantics
Khi user nhấn `Xác nhận & Đồng bộ`:
- chỉ ghi các Managed Regions được chọn theo sync plan cuối cùng;
- `Giữ nội dung Word` không bị overwrite;
- `Bỏ qua lần này` không bị ghi và không được đánh dấu `Đã đồng bộ`;
- tài liệu `Không thay đổi` không tạo Document Revision mới;
- mỗi tài liệu thực sự cập nhật thành công tạo Document Revision mới và ghi nhận Microsoft 365 file/version tương ứng;
- published revision/release immutable.

Document Revision != Microsoft 365 file version.

## 6. Warning & Blocking
Warning không tự Blocking. User phải thấy Warning trước execution. Blocking ngăn execution cho đến khi được xử lý. Không silent fix để làm Blocking biến mất.

## 7. Batch result semantics
Không được hiển thị một trạng thái `Đồng bộ thành công` cho toàn batch nếu có tài liệu lỗi. Execution phải trả kết quả theo từng tài liệu để màn `Kết quả đồng bộ hàng loạt` thể hiện `Đã đồng bộ / Không thay đổi / Bỏ qua-Cần cập nhật / Lỗi-Cần xử lý` và lineage/version tương ứng.

## 8. Data-source semantics
Tên `.xlsx` trong mockup chỉ minh họa source/Data Snapshot mới; canonical business data vẫn là Workbench/database. Không khóa architecture vào Excel làm nguồn sync duy nhất.

## 9. Guardrails
- Single-user.
- Đây là write boundary; các bước trước vẫn zero-write.
- Không silent overwrite/sync/conflict resolution.
- Không fake Word editor.
- Không revision mới cho tài liệu không thay đổi/bỏ qua.
- Không ghi ngoài Managed Regions.
- Một primary CTA.

## 10. ADR
Implementation phải đánh giá ADR nếu thay đổi multi-document transaction boundary, partial success/rollback, idempotency/retry, stale-plan detection, optimistic concurrency với Microsoft 365, Document Revision creation, hoặc audit/lineage semantics.
